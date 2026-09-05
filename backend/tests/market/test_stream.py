"""Tests for the SSE price streaming endpoint."""

import json

import pytest

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


class _FakeClient:
    """Stand-in for starlette's Request.client (just needs a .host)."""

    host = "127.0.0.1"


class _FakeRequest:
    """Minimal stand-in for FastAPI's Request, exposing only what
    _generate_events touches: `.client.host` and `is_disconnected()`.

    `disconnect_after` controls how many is_disconnected() calls return
    False before the generator is told the client has gone away, which is
    how we cause the otherwise-infinite loop to terminate deterministically.
    """

    def __init__(self, disconnect_after: int) -> None:
        self.client = _FakeClient()
        self._disconnect_after = disconnect_after
        self._checks = 0

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > self._disconnect_after


async def _collect(cache: PriceCache, request: _FakeRequest, interval: float = 0.01) -> list[str]:
    """Drain _generate_events into a list of raw SSE chunks."""
    return [chunk async for chunk in _generate_events(cache, request, interval=interval)]


class TestGenerateEvents:
    """Unit tests for the SSE event generator, exercised without a live ASGI server."""

    async def test_first_chunk_is_retry_directive(self):
        cache = PriceCache()
        request = _FakeRequest(disconnect_after=0)

        chunks = await _collect(cache, request)

        assert chunks[0] == "retry: 1000\n\n"

    async def test_stops_when_client_disconnects(self):
        cache = PriceCache()
        request = _FakeRequest(disconnect_after=0)

        chunks = await _collect(cache, request)

        # Only the retry directive — the loop exits before checking prices.
        assert chunks == ["retry: 1000\n\n"]

    async def test_sends_price_snapshot_when_cache_has_data(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        request = _FakeRequest(disconnect_after=1)

        chunks = await _collect(cache, request)

        data_chunks = [c for c in chunks if c.startswith("data: ")]
        assert len(data_chunks) == 1

        payload = json.loads(data_chunks[0][len("data: ") : -2])
        assert payload["AAPL"]["price"] == 190.50
        assert payload["AAPL"]["direction"] == "flat"

    async def test_no_data_sent_when_cache_is_empty(self):
        cache = PriceCache()
        request = _FakeRequest(disconnect_after=1)

        chunks = await _collect(cache, request)

        assert not any(c.startswith("data: ") for c in chunks)

    async def test_no_duplicate_send_when_version_unchanged(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        request = _FakeRequest(disconnect_after=3)

        chunks = await _collect(cache, request)

        # Cache never changes after the first write, so despite three
        # poll iterations only one snapshot should have been emitted.
        data_chunks = [c for c in chunks if c.startswith("data: ")]
        assert len(data_chunks) == 1

    async def test_sends_new_snapshot_on_version_bump(self):
        """Updating the cache between polls should produce a second, distinct snapshot."""
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        request = _FakeRequest(disconnect_after=3)
        gen = _generate_events(cache, request, interval=0.01)

        assert await gen.__anext__() == "retry: 1000\n\n"

        first = await gen.__anext__()
        assert json.loads(first[len("data: ") : -2])["AAPL"]["price"] == 190.50

        cache.update("AAPL", 191.00)

        second = await gen.__anext__()
        assert json.loads(second[len("data: ") : -2])["AAPL"]["price"] == 191.00

        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    async def test_snapshot_includes_all_tracked_tickers(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        cache.update("GOOGL", 175.25)
        request = _FakeRequest(disconnect_after=1)

        chunks = await _collect(cache, request)

        data_chunks = [c for c in chunks if c.startswith("data: ")]
        payload = json.loads(data_chunks[0][len("data: ") : -2])
        assert set(payload.keys()) == {"AAPL", "GOOGL"}


class TestCreateStreamRouter:
    """Unit tests for the router factory."""

    def test_returns_router_with_prices_route(self):
        cache = PriceCache()
        router = create_stream_router(cache)

        paths = {route.path for route in router.routes}
        assert "/api/stream/prices" in paths

    def test_route_is_get_only(self):
        cache = PriceCache()
        router = create_stream_router(cache)

        route = next(r for r in router.routes if r.path == "/api/stream/prices")
        # Starlette auto-adds HEAD alongside GET; no other verbs should be present.
        assert route.methods == {"GET", "HEAD"}
