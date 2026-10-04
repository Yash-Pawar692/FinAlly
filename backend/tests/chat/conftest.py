"""Fixtures shared by chat tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db import Database
from app.market import PriceCache


@pytest.fixture(autouse=True)
def llm_mock_mode(monkeypatch: pytest.MonkeyPatch):
    """Chat tests never call the real LLM — mock mode is deterministic and free."""
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    database.init()
    return database


@pytest.fixture
def price_cache() -> PriceCache:
    cache = PriceCache()
    cache.update("AAPL", 200.0)
    cache.update("TSLA", 100.0)
    return cache
