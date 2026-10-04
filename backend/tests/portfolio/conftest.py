"""Fixtures shared by portfolio tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db import Database
from app.market import PriceCache


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
