"""Fixtures shared by watchlist tests."""

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
    return PriceCache()
