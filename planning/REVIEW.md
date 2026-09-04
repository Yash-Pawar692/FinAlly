# PLAN.md Review

Reviewed 2026-09-03 against the current repository state. I read `planning/PLAN.md` in full, `planning/MARKET_DATA_SUMMARY.md`, every module in `backend/app/market/` (`models.py`, `interface.py`, `cache.py`, `simulator.py`, `massive_client.py`, `factory.py`, `stream.py`, `seed_prices.py`), `backend/pyproject.toml`, `backend/CLAUDE.md`, and `.claude/skills/cerebras/SKILL.md`. I also confirmed that `docker-compose.yml`, `scripts/`, `.env.example`, and `db/` do not exist yet in the repo — only the market-data module and its tests are implemented, exactly as the plan's preamble states.

Findings are tagged:
- **[BUG/INCONSISTENCY]** — something that is actually wrong, or contradicts either the shipped code or another part of the plan
- **[OPEN QUESTION]** — a genuine ambiguity that needs a decision before further implementation
- **[NICE-TO-HAVE]** — a suggestion, not a blocker

Items already logged in PLAN.md §13 "Doc Review Notes" are treated as known; I only repeat them where reading the actual code sharpened or changed the picture.

---

## §6 Market Data — SSE streaming

**[BUG/INCONSISTENCY] The plan's "unconditional every ~500ms" description contradicts the shipped `stream.py`, and the shipped code contradicts its own supporting docs.**

§6 states: "Server pushes a price update for every ticker known to the system every ~500ms, unconditionally (**not gated on whether the price changed** since the last tick)." That sentence reads like a deliberate correction of an earlier, different design.

But `stream.py::_generate_events` does exactly the gating the plan disclaims:

```python
current_version = price_cache.version
if current_version != last_version:
    last_version = current_version
    ...
    yield f"data: {payload}\n\n"
```

And `PriceCache.version`'s own docstring/CLAUDE.md description calls it a counter that increments "for SSE change detection" — i.e., the code was written around the premise the plan says is not the behavior.

Today this is **latent, not visible**, because `PriceCache.update()` bumps `_version` unconditionally on *every* call regardless of whether the rounded price actually moved, and `SimulatorDataSource._run_loop()` calls `update()` for every tracked ticker on every tick — so under the simulator (the default path) the version changes every 500ms and the two descriptions produce identical observable output.

It stops being latent as soon as either:
1. The Massive path is exercised — its poll interval is 15s+, so despite the plan's "~500ms" framing, an SSE client genuinely only sees a new payload once per `poll_interval` seconds. The gating is real there, not cosmetic.
2. A future engineer "cleans up" `cache.update()` to skip the version bump when the price is unchanged — a very natural change given the field's stated purpose — which would silently start dropping ticks for flat-moving tickers under the simulator too.

Recommend resolving explicitly in one direction and updating all three places (`PLAN.md` §6, `stream.py`'s docstring, `MARKET_DATA_SUMMARY.md`'s "version-based change detection" phrasing) to say the same thing:
- either rewrite §6 to describe the actual mechanism (single global version bumped on every write, full snapshot re-sent on change — ~500ms under the simulator, up to `poll_interval` seconds under Massive), or
- change `stream.py` to emit unconditionally every 500ms as §6 states, and drop or repurpose the version field.

**[BUG/INCONSISTENCY] Removing a ticker from the watchlist deletes its price even if the user still holds a position in it.**

§6 says the "known to the system" ticker set is, in the single-user model, "equivalent to the user's watchlist." But `positions` (§7) is an independent table — nothing in §8's `DELETE /api/watchlist/{ticker}` blocks removing a ticker you still hold. Both `SimulatorDataSource.remove_ticker()` and `MassiveDataSource.remove_ticker()` call `self._cache.remove(ticker)` unconditionally:

```python
async def remove_ticker(self, ticker: str) -> None:
    if self._sim:
        self._sim.remove_ticker(ticker)
    self._cache.remove(ticker)   # <-- deletes the cache entry outright
```

If the "known tickers" set passed to the market data source is driven purely by watchlist membership, removing a watched-but-held ticker deletes its price from the cache — breaking `GET /api/portfolio`'s current-price/unrealized-P&L calc for that position (nothing to value it against) and dropping it from the SSE stream entirely. This needs an explicit rule: e.g. the source's active set should be `watchlist ∪ open-position tickers`, not watchlist alone; or watchlist removal should be blocked/warned when a position is open; or this is accepted as a known limitation and stated as such. As written it's a silent data-consistency gap, not a documented cut.

**[OPEN QUESTION, code confirms it's not symmetric] "No cached price yet" behavior differs sharply by data source, and for Massive can also mean "never."**

- `SimulatorDataSource.add_ticker()` calls `self._sim.get_price(ticker)` and seeds the cache synchronously — a newly added ticker has a price before the `POST /api/watchlist` response even returns. For an *unrecognized* ticker string, `GBMSimulator._add_ticker_internal` falls back to `random.uniform(50.0, 300.0)` — i.e. the simulator will happily manufacture a plausible-looking price for a typo'd or fictional ticker, with no validation anywhere.
- `MassiveDataSource.add_ticker()` only appends to an internal list and logs "will appear on next poll" — no immediate poll. On the free tier (`poll_interval=15.0`), a newly added ticker can have **no price for up to 15 seconds**, not an edge case but the routine path. Worse, if the ticker is invalid/delisted, Polygon's snapshot response simply won't include it — the price stays missing **permanently**, with no error surfaced anywhere (the `_poll_once` failure handling only logs and skips per-snapshot parse errors, it has no notion of "ticker never showed up").

Any decision on "what does a trade against a priceless ticker do" needs to account for: (a) the wait is routine under Massive, not exceptional, and (b) ticker validity is checked nowhere, so the two backends will diverge in observable behavior for the same bad input (simulator: fake price appears; Massive: no price, ever). Worth deciding whether ticker symbols should be validated against a known list before being accepted by `POST /api/watchlist` / a trade.

**[NICE-TO-HAVE]** "Polls for the union of all watched tickers" — in a single-watchlist system there's only one set, so "union" is a leftover from multi-user phrasing. Simplifying to "polls for all watched tickers" removes a pointless "union of what with what" question for the reader.

## §7 Database vs. §3/startup sequencing

**[OPEN QUESTION, new] "Lazy initialization on first request" is in tension with when market-data streaming needs to start.**

§7 says: "The backend checks for the SQLite database on startup (or first request). If the file doesn't exist... it creates the schema and seeds default data" — i.e., DB setup may be deferred until whatever HTTP request happens to land first.

But the market-data background task needs a list of tickers to call `source.start(tickers)` with (§6's "Shared Price Cache" section: "a single background task... writes to an in-memory price cache," clearly meant to be running continuously, not spun up per-request), and the only source of that ticker list is the `watchlist` table (§7), seeded with the 10 default tickers (§7 "Default Seed Data"). For live-streaming prices to be available the moment the frontend opens (§2 "First Launch": "A watchlist of 10 default tickers with live-updating prices... immediately"), the DB must be seeded and the market data source started together, before any request-driven "lazy" trigger — which means DB initialization in practice needs to happen at application startup, not deferred to first request. As written, §7's "or first request" phrasing either is misleading (DB init actually always happens at startup in practice) or, if taken literally, implies the price stream can't start until some request touches the DB — delaying the "prices are already streaming" first-launch experience the plan promises in §2/§12. Worth pinning down explicitly: DB init happens once, at process startup (via FastAPI lifespan), and "lazy" only describes not requiring a separate migration *command*, not deferring to a request handler.

**[BUG/INCONSISTENCY] `trades` table has no read API and no UI.** §7 defines `trades` as "Trade history (append-only log)," but §8's endpoint table has no `GET /api/trades` / `/api/portfolio/trades`, and §10's frontend element list has no trade-history/blotter view. The log is written but never read back anywhere. Unlike realized P&L (explicitly scoped out with a stated reason), this reads like an oversight rather than a deliberate cut for a "trading terminal" — recommend either adding the endpoint + a simple trade-history view, or explicitly stating the log is write-only/audit-only for now.

**[OPEN QUESTION]** Should a `portfolio_snapshots` row be written at profile-seed time (first launch), in addition to every 30s and after each trade? As specified, a fresh database has zero snapshot rows until 30 seconds elapse or the first trade executes — so the P&L chart is empty for up to 30 seconds after first launch, which is also the very first thing a new user sees. A one-line decision ("seed an initial $10,000 snapshot at profile creation") would close this.

## §8 API Endpoints

**[OPEN QUESTION]** No error contract is specified for `POST /api/portfolio/trade`: status code and body shape for insufficient cash, insufficient shares, unknown/priceless ticker, or non-positive quantity are all undefined. §12's unit-test list presupposes these cases exist ("selling more than owned," "buying with insufficient cash"), and §9 only defines how *chat-initiated* trade failures surface (folded into the LLM's response text) — the manual-trade path has no equivalent. This should be spelled out before frontend/tests are built against it.

**[NICE-TO-HAVE]** Given the previous point about simulator-vs-Massive divergence on unknown tickers, `POST /api/watchlist` and trade validation would benefit from one explicit sentence on whether ticker strings are validated against a known-symbol list or accepted as-is.

## §9 LLM Integration

- Cross-checked: PLAN.md §9's model string `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` matches `MODEL` in `.claude/skills/cerebras/SKILL.md` exactly, and the skill's documented `response_format=<PydanticModel>` structured-output call shape matches §9's "Structured Outputs should be used" requirement. No mismatch as of this review.
- **[NICE-TO-HAVE]** That said, the model string is duplicated in prose in PLAN.md *and* set as the single source of truth inside the skill. `git status` shows `SKILL.md` has already been edited once in this working tree; if it's edited again (a model gets deprecated, a better free-tier model appears) there's no mechanism keeping PLAN.md's copy in sync. Consider having §9 say "the model specified in the cerebras-inference skill" instead of repeating the literal string.
- **[OPEN QUESTION]** "Loads the last 10 messages of conversation history" — 10 rows (5 user + 5 assistant turns) or 10 full exchanges (20 rows)? This is a 2x ambiguity affecting both prompt cost and how far back the assistant can "remember," worth pinning down as an exact row count.
- The `watchlist_changes` action-enum gap is already flagged in §13; concretely, `DELETE /api/watchlist/{ticker}` on the REST side proves "remove" has to be supported end-to-end regardless, so the chat schema's enum should just mirror the REST API's `add`/`remove` pair.
- **[NICE-TO-HAVE]** The trade schema `{"ticker", "side", "quantity"}` is share-count only. Natural chat requests like "put $500 into AAPL" would require the LLM to compute a share count itself from a live price it may or may not have accurately in context — not necessarily wrong, but worth a sentence confirming dollar-denominated trade requests are explicitly out of scope / left to the LLM's own conversions, rather than left implicit.

## §10 Frontend Design

**[BUG/INCONSISTENCY] "Canvas-based charting library preferred (Lightweight Charts or Recharts)" pairs a true claim with a contradicting example.** Lightweight Charts (TradingView) does render to `<canvas>`. Recharts does not — it's built on D3 and renders SVG DOM elements, not canvas. As written this is a factual error about Recharts, not just a loose recommendation.

This has a real downstream consequence for stack size: Lightweight Charts has no treemap primitive, so if "canvas-based" is a hard requirement, the heatmap (§10, "Portfolio heatmap — treemap visualization") needs a *second* library (Recharts' `Treemap`, D3, or visx) alongside it. If canvas rendering doesn't actually matter at this data volume (10 tickers, ~2 updates/sec — SVG handles this fine), then Recharts alone covers price charts, the P&L line chart, *and* the treemap in one library, which is the simpler build. Recommend either dropping the "canvas-based" framing (let Recharts cover everything) or naming Lightweight Charts for price/P&L charts plus a second, explicitly named library for the treemap — but not implying Recharts satisfies a canvas requirement it doesn't.

**[OPEN QUESTION]** There's no backend-persisted per-ticker price history — only `portfolio_snapshots` (total value, not per-ticker) exists in §7, and no endpoint for historical per-ticker prices is listed in §8. That means both the watchlist sparklines *and* the larger main chart for a selected ticker can only be built from SSE data accumulated client-side since page load. §10 says this explicitly for sparklines ("accumulated... since page load... fill in progressively") but is silent on the main chart having the identical limitation — including that a page refresh wipes chart history for whatever ticker is currently selected, same as it wipes the sparklines. Worth either confirming this is intended for the main chart too, or deciding whether the backend should retain a short rolling per-ticker history so a fresh page load isn't visually empty for several seconds/minutes.

## §4/§11 Docker & Deployment — volume mechanism

**[BUG/INCONSISTENCY] The two sections describe different persistence mechanisms.** §4 states the top-level `db/` directory "is the runtime volume mount point," that `db/finally.db` "is created here... persists across container restarts via Docker volume," and the directory tree shows a committed `db/.gitkeep` "so the directory exists in repo" — all of which describes a **bind mount** (`-v "$(pwd)/db:/app/db"`), where the SQLite file is a real, host-visible file at `./db/finally.db`.

§11's actual example command instead uses a **named volume**: `docker run -v finally-data:/app/db ...`. With a named volume, Docker manages storage internally (e.g. under `/var/lib/docker/volumes/finally-data/_data`) and there is no `./db/finally.db` file on the host at all — `db/.gitkeep` would exist for no reason, and anyone following §4's description and running `ls ./db/` after using §11's command won't find the database. Neither `docker-compose.yml` nor the start/stop scripts exist yet, so this is currently a plan-internal contradiction rather than a code bug — but it needs to be resolved to one mechanism before those files are written, since the scripts, `docker-compose.yml`, and Dockerfile all need to agree on which one it is.

## §12 Testing Strategy

- No items beyond the SSE-reconnection question already logged in §13 (worth reiterating it's still unresolved: `EventSource` auto-reconnect is client-side browser behavior, so the Playwright scenario needs a stated mechanism for forcing a disconnect — e.g. restarting the backend container, or a test-only proxy that can be killed — since it's the one E2E scenario in the list that isn't a plain UI interaction).
- **[NICE-TO-HAVE]** Add an E2E scenario for a rejected manual trade (insufficient cash/shares) surfacing a visible error — this would force the §8 error-contract open question to actually get decided and verified, rather than left implicit.

## §5 Environment Variables

**[NICE-TO-HAVE]** `LLM_MOCK` truthiness parsing isn't specified (literal `"true"` only, or also `"1"`/`"True"`/etc.?). `factory.py`'s existing `MASSIVE_API_KEY` check (`os.environ.get(..., "").strip()` then falsy/truthy) is a reasonable precedent to explicitly follow for consistency once the chat route is built.

## §3/§4 Architecture & Directory Structure

**[NICE-TO-HAVE]** The directory tree in §4 shows only `backend/app/db/` under `app/`, even though `backend/app/market/` (and `backend/tests/market/`) already exist and are the template other modules should follow. Updating the tree to show the real layout (`app/market/`, `app/db/`, presumably future `app/portfolio/`, `app/watchlist/`, `app/chat/` as siblings) would make the intended one-module-per-concern convention explicit rather than something downstream agents have to infer from a single existing example.

---

## Summary

The most consequential items are the three genuine **[BUG/INCONSISTENCY]** findings that will produce real bugs or confused behavior if carried forward unresolved:

1. **SSE gating vs. plan wording** — currently invisible under the simulator, will diverge from the plan's stated behavior the moment Massive is wired up or `cache.update()` is optimized.
2. **Watchlist removal deletes a held position's price feed** — a silent data-consistency gap between the `watchlist` and `positions` tables that breaks P&L display for the affected position.
3. **Named volume vs. bind mount** (§4 vs §11) — not yet manifested in code (nothing in `scripts/`/`docker-compose.yml` exists yet), but needs to be picked before those files are written, since three different artifacts (Dockerfile, scripts, compose file) all need to agree.

Close behind is the **Recharts/"canvas-based" claim** in §10, which is a factual error with a real stack-size consequence (does the heatmap need a second library or not), and the **DB lazy-init vs. market-data-startup-sequencing** tension in §7/§3, which affects whether the "prices are already streaming on first launch" promise in §2 actually holds.

Everything else here is a genuine open question worth a one-line decision recorded in PLAN.md (trade error contract, ticker validation policy, chat history row count, initial snapshot seeding, dollar-denominated LLM trades), or a low-stakes wording/structure suggestion.
