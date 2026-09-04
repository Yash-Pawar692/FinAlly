# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── app/
│       └── db/               # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/app/db/`** contains schema SQL definitions and seed logic, matching the `backend/app/<module>/` convention established by `backend/app/market/`. The backend lazily initializes the database once, during application startup (see §7) — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point (a bind mount — see §11). The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts as a real, host-visible file.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies
- Ticker symbols are not validated against a real-symbol list anywhere in the system. An unrecognized ticker added to the active set (see Shared Price Cache below) is assigned a plausible synthetic seed price (random, $50–$300) and behaves identically to a known ticker — there is no "invalid ticker" concept under the simulator, and a price is available immediately (synchronously, before the `POST /api/watchlist` response returns)

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator
- Adding a ticker does not trigger an immediate poll — a newly-added ticker has no cached price for up to one poll interval (as long as 15s on the free tier). This is the routine case, not an edge case, and both the frontend and trade validation (§8) must handle a watchlist entry with no price yet
- If a ticker is invalid or never appears in the Massive snapshot response, it never receives a price — it is permanently priceless, not surfaced as an add-time error (see §8 for how trades against a priceless ticker are handled)

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- SSE streams read from this cache and push updates to connected clients
- The active ticker set passed to the market data source is the **union of the watchlist and any ticker with an open position** — not the watchlist alone. Removing a ticker from the watchlist while a position remains open does not stop its price from being cached or streamed; it drops out of the active set only once the position is fully closed. This keeps `GET /api/portfolio`'s unrealized P&L calculation valid for every open position regardless of watchlist membership
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- The price cache maintains a single global version counter, incremented on every write. The SSE loop checks this counter roughly every 500ms and, whenever it has changed since the last check, pushes one snapshot payload covering every ticker in the active set (watchlist ∪ open positions, per Shared Price Cache above). In practice a new snapshot arrives about every ~500ms under the simulator (which writes every tracked ticker on every tick, so the version changes every tick) and about every `poll_interval` seconds under Massive (as infrequently as every 15s on the free tier) — this is real change-detection at the data-source level, not a per-ticker filter within a single push
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database once, during application startup (a FastAPI `lifespan` handler) — not deferred to the first incoming request. If the file doesn't exist or tables are missing, it creates the schema and seeds default data before the app starts accepting connections and before the market data background task begins streaming. This ordering is required by §2's first-launch promise: the market data source needs the seeded watchlist's ticker list to know what to stream, so DB readiness must precede stream startup. "Lazy" here means:

- No separate migration step or command to run
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically, built the first time the container starts

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`
- On a buy, `avg_cost` is recalculated as the weighted average of the existing position and the new trade (`(old_qty * old_avg_cost + trade_qty * trade_price) / (old_qty + trade_qty)`). A sell leaves `avg_cost` unchanged.
- If a sell brings `quantity` to exactly 0, the row is deleted rather than kept at `quantity=0`. A later buy of the same ticker creates a fresh row (and a fresh `avg_cost`).
- A ticker removed from the watchlist while a position remains open keeps receiving live prices (see §6, Shared Price Cache) until the position is closed — watchlist membership and price availability are independent for held tickers.

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)
- Realized P&L is out of scope for now — it is not stored or computed anywhere; only unrealized P&L on open positions is ever surfaced.
- Readable via `GET /api/portfolio/trades` (§8) and shown in a trade-history/blotter UI element (§10) — the log is not write-only.

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, immediately after each trade execution, and once at profile-seed time (an initial `$10,000` snapshot, so the P&L chart has a data point from first render instead of being empty for up to 30 seconds after a fresh launch).
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |
| GET | `/api/portfolio/trades` | Trade history log (append-only), most recent first |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

### Trade Execution Details

- Trade price is the `PriceCache` value read synchronously at the moment the trade endpoint handles the request — the price in effect for that request, not a value the client passed in.
- `POST /api/portfolio/trade` and `POST /api/watchlist` accept any ticker string without validating it against a real-symbol list (see §6); an unrecognized ticker behaves like a real one under the simulator and like a permanently-priceless one under Massive.
- If a ticker has no cached price yet (routine under Massive, effectively never under the simulator — see §6), a trade against it is rejected before any cash or shares move.
- Trade validation failures — insufficient cash, insufficient shares, no cached price, non-positive quantity — return HTTP 400 with a JSON body `{"error": "<code>", "message": "<human-readable>"}`, where `<code>` is one of `insufficient_cash`, `insufficient_shares`, `no_price_available`, `invalid_quantity`. LLM-initiated trades (§9) run through this exact same validation; the `message` is what gets folded into the chat response rather than surfaced as a REST error.

---

## 9. LLM Integration

When writing code to make calls to LLMs, use the cerebras-inference skill to call LiteLLM via OpenRouter with Cerebras as the inference provider, using whichever model the skill specifies (currently `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`) — the skill is the single source of truth for the model string, so this document doesn't need updating if it changes. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the last 10 rows (i.e., up to 5 user + 5 assistant turns) of conversation history from the `chat_messages` table, ordered oldest to newest
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells — see §8's Trade Execution Details for the full error contract). Trade quantities are always share counts, never dollar amounts — if the user requests a dollar-denominated trade (e.g. "put $500 into AAPL"), the LLM is responsible for converting to a share count using the live price already present in its portfolio context before including it here
- `watchlist_changes` (optional): Array of watchlist modifications. `action` is one of `"add"` or `"remove"`, mirroring the REST `POST`/`DELETE /api/watchlist` pair exactly

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change %, and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here. Like the sparklines, there is no server-side per-ticker price history (only `portfolio_snapshots`, which tracks total value, not per-ticker prices) — the main chart is built entirely from SSE data accumulated client-side since page load, and a page refresh clears it back to empty, filling in progressively again as new ticks arrive. This is accepted behavior, not a bug.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade history (blotter)** — chronological list of executed trades (ticker, side, quantity, price, timestamp), sourced from `GET /api/portfolio/trades`
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Recharts (SVG-based, built on D3) is the charting library for the price/main charts, sparklines, P&L line chart, and the portfolio heatmap (its `Treemap` component) — one library covers every visualization in §10. At this data volume (10 tickers, ~2 price updates/sec) SVG rendering performance is not a concern, so a canvas-based library (e.g. Lightweight Charts) is not needed and was not chosen, since it has no treemap primitive and would require a second library alongside it.
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a **bind mount** of the top-level `db/` directory (not a named volume) — this matches §4's description of `db/` as the runtime mount point and keeps `db/finally.db` visible and inspectable on the host, consistent with the committed `db/.gitkeep` placeholder:

```bash
docker run -v "$(pwd)/db:/app/db" -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path, so `ls ./db/` on the host shows the live database file.

### Canonical Mechanism: `docker-compose.yml`

`docker-compose.yml` is the single canonical definition of how the container is built and run (image build context, the `db/` bind mount, port mapping, and `.env` file). The start/stop scripts are thin wrappers around `docker compose` commands (`docker compose up -d --build`, `docker compose down`), not independent `docker run`/`docker build` invocations — this keeps the volume mechanism, port, and env-file wiring defined in exactly one place so the scripts and compose file cannot drift apart.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Runs `docker compose up -d --build` (or `docker compose up -d` unless a `--build` flag is passed), so image build, the volume mount, port mapping, and env file are all sourced from `docker-compose.yml`
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Runs `docker compose down`
- Does NOT remove the bind-mounted `db/` directory (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows, wrapping the same `docker compose` commands.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- Reject a manual trade (insufficient cash or insufficient shares) and verify the error surfaces visibly in the UI, per the error contract in §8
- SSE resilience: force a disconnect by restarting the app container mid-test (e.g. `docker compose restart` against the app service in `test/docker-compose.test.yml`) while the page is open, then verify the connection-status indicator (§10) moves to reconnecting/disconnected and back to connected, and that price updates resume, once the container is back. `EventSource`'s reconnection itself is native browser behavior and isn't what's under test — only the app's own status indicator and data flow recovering correctly around it

---

## 13. Doc Review Notes (2026-09-03)

A doc review pass on 2026-09-03 (`planning/REVIEW.md`) checked this plan against the completed market data component (`planning/MARKET_DATA_SUMMARY.md`, `backend/app/market/`) and against itself for internal contradictions. All findings from that review have been resolved and folded into the relevant sections above:

- SSE broadcast/version-gating semantics, ticker validation policy, no-cached-price handling per data source → §6
- Watchlist removal orphaning a held position's price feed (active ticker set = watchlist ∪ open positions) → §6, §7
- DB initialization timing vs. market-data startup sequencing (init happens at startup, not first request) → §7
- Trade history read API and UI (previously write-only) → §7, §8, §10
- Initial `portfolio_snapshots` seeding at profile creation → §7
- Trade error contract (status code, body shape, error codes) → §8
- `watchlist_changes` action enum (`"add"` / `"remove"`) and dollar-denominated LLM trades → §9
- Chat history row count ("last 10" = 10 rows, not 10 exchanges) → §9
- Model string duplication between this document and the cerebras-inference skill → §9
- Canvas/Recharts charting library claim (Recharts is SVG, not canvas) → §10
- Main chart's page-refresh/no-server-history behavior stated explicitly, matching the sparklines → §10
- Docker volume mechanism (bind mount, not a named volume) and `docker-compose.yml` as the canonical run mechanism the scripts wrap → §4, §11
- SSE resilience E2E test's disconnect mechanism, and a rejected-trade E2E scenario → §12

No open items remain from this review pass.

