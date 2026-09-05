# Market Data Backend — Summary

**Status:** Complete, tested, reviewed, all issues resolved.

## What Was Built

A complete market data subsystem in `backend/app/market/` (8 modules, ~500 lines) providing live price simulation and real market data via a unified interface.

### Architecture

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator (default, no API key needed)
└── MassiveDataSource    →  Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        ▼
   PriceCache (thread-safe, in-memory)
        │
        ├──→ SSE stream endpoint (/api/stream/prices)
        ├──→ Portfolio valuation
        └──→ Trade execution
```

### Modules

| File | Purpose |
|------|---------|
| `models.py` | `PriceUpdate` — immutable frozen dataclass (ticker, price, previous_price, timestamp, change, direction) |
| `interface.py` | `MarketDataSource` — abstract base class defining `start/stop/add_ticker/remove_ticker/get_tickers` |
| `cache.py` | `PriceCache` — thread-safe price store with version counter for SSE change detection |
| `seed_prices.py` | Realistic seed prices, per-ticker GBM params (drift/volatility), correlation groups |
| `simulator.py` | `GBMSimulator` (Geometric Brownian Motion with Cholesky-correlated moves) + `SimulatorDataSource` |
| `massive_client.py` | `MassiveDataSource` — REST polling client for Polygon.io via the `massive` package |
| `factory.py` | `create_market_data_source()` — selects simulator or Massive based on `MASSIVE_API_KEY` env var |
| `stream.py` | `create_stream_router()` — FastAPI SSE endpoint factory using version-based change detection |

### Key Design Decisions

- **Strategy pattern** — both data sources implement the same ABC; downstream code is source-agnostic
- **PriceCache as single point of truth** — producers write, consumers read; no direct coupling
- **GBM with correlated moves** — Cholesky decomposition of sector-based correlation matrix; tech stocks correlate at 0.6, finance at 0.5, cross-sector at 0.3
- **Random shock events** — ~0.1% chance per tick per ticker of a 2-5% move for visual drama
- **SSE over WebSockets** — simpler, one-way push, universal browser support

## Test Suite

**84 tests, all passing.** 7 test modules in `backend/tests/market/`.

| Module | Tests | Coverage |
|--------|-------|----------|
| test_models.py | 11 | models.py: 100% |
| test_cache.py | 14 | cache.py: 100% (incl. a multi-thread concurrency test) |
| test_simulator.py | 20 | simulator.py: 98% (incl. the full 10-ticker default watchlist) |
| test_simulator_source.py | 10 | (integration tests) |
| test_factory.py | 7 | factory.py: 100% |
| test_massive.py | 13 | massive_client.py: 56% (expected — API methods mocked) |
| test_stream.py | 9 | stream.py: covers `_generate_events` and `create_stream_router` without a live ASGI server |

`stream.py` previously had no dedicated tests (31% coverage, flagged as a gap in `MARKET_DATA_REVIEW.md` §4.2). `test_stream.py` closes that gap by driving `_generate_events` directly against a minimal fake `Request` (only `is_disconnected()` and `.client.host` are needed), which avoids adding an `httpx`/ASGI-test-client dependency. This also surfaced and fixed a real bug: `create_stream_router` previously registered its route on a shared module-level `APIRouter`, so calling it more than once (e.g. once per test) would double-register the `/prices` route — it now creates a fresh `APIRouter` per call.

## Code Review & Fixes Applied

A comprehensive code review identified 7 issues. All were resolved:

1. **pyproject.toml build config** — added `[tool.hatch.build.targets.wheel] packages = ["app"]`
2. **Lazy imports removed** — `massive` is a core dependency; imports moved to top level
3. **SSE return type fixed** — `_generate_events` annotated as `AsyncGenerator[str, None]`
4. **Public `get_tickers()`** — added to `GBMSimulator` to avoid private attribute access
5. **Correlation constants cleaned up** — removed unused `DEFAULT_CORR`, consolidated into `CROSS_GROUP_CORR`
6. **Unused test imports removed** — `pytest`, `math`, `asyncio` cleaned from 4 test files
7. **Massive test mocks fixed** — `source._client` set in tests, patches target correct names

## Demo

A Rich terminal demo is available at `backend/market_data_demo.py`:

```bash
cd backend
uv run market_data_demo.py
```

Displays a live-updating dashboard with all 10 tickers, sparklines, color-coded direction arrows, and an event log for notable price moves. Runs 60 seconds or until Ctrl+C.

## Usage for Downstream Code

```python
from app.market import PriceCache, create_market_data_source

# Startup
cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY
await source.start(["AAPL", "GOOGL", "MSFT", ...])

# Read prices
update = cache.get("AAPL")          # PriceUpdate or None
price = cache.get_price("AAPL")     # float or None
all_prices = cache.get_all()        # dict[str, PriceUpdate]

# Dynamic watchlist
await source.add_ticker("TSLA")
await source.remove_ticker("GOOGL")

# Shutdown
await source.stop()
```
