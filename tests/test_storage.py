"""Tests for SQLite storage layer."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tokenwatch.models import UsageRecord
from tokenwatch.storage import Storage


@pytest.fixture
def storage(tmp_path):
    """Create a storage instance with a temp database."""
    db_path = tmp_path / "test.db"
    return Storage(db_path=db_path)


def make_record(**kwargs) -> UsageRecord:
    defaults = {
        "model": "gpt-4",
        "provider": "openai",
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_usd": 0.01,
    }
    defaults.update(kwargs)
    return UsageRecord(**defaults)


def test_record_and_query(storage):
    record = make_record()
    storage.record(record)

    start = datetime.now(UTC) - timedelta(hours=1)
    results = storage.query_period(start)
    assert len(results) == 1
    assert results[0].id == record.id
    assert results[0].model == "gpt-4"


def test_multiple_records(storage):
    for i in range(5):
        storage.record(make_record(cost_usd=float(i)))

    start = datetime.now(UTC) - timedelta(hours=1)
    results = storage.query_period(start)
    assert len(results) == 5


def test_get_total_cost(storage):
    storage.record(make_record(cost_usd=1.0))
    storage.record(make_record(cost_usd=2.5))
    storage.record(make_record(cost_usd=0.5))

    start = datetime.now(UTC) - timedelta(hours=1)
    total = storage.get_total_cost(start)
    assert abs(total - 4.0) < 1e-10


def test_summary_by_model(storage):
    storage.record(make_record(model="gpt-4", cost_usd=1.0))
    storage.record(make_record(model="gpt-4", cost_usd=2.0))
    storage.record(make_record(model="gpt-3.5-turbo", cost_usd=0.5))

    start = datetime.now(UTC) - timedelta(hours=1)
    summary = storage.get_summary_by_model(start)
    assert len(summary) == 2
    # First should be gpt-4 (highest cost)
    assert summary[0]["model"] == "gpt-4"
    assert abs(summary[0]["total_cost"] - 3.0) < 1e-10
    assert summary[0]["request_count"] == 2


def test_summary_by_caller(storage):
    storage.record(make_record(caller="app.py:main", cost_usd=1.0))
    storage.record(make_record(caller="app.py:main", cost_usd=2.0))
    storage.record(make_record(caller="utils.py:helper", cost_usd=0.5))

    start = datetime.now(UTC) - timedelta(hours=1)
    summary = storage.get_summary_by_caller(start)
    assert len(summary) == 2
    assert summary[0]["caller"] == "app.py:main"
    assert abs(summary[0]["total_cost"] - 3.0) < 1e-10


def test_query_period_respects_time_bounds(storage):
    # Record something "old"
    old_record = make_record()
    old_record.timestamp = datetime.now(UTC) - timedelta(days=10)
    storage.record(old_record)

    # Record something recent
    storage.record(make_record())

    start = datetime.now(UTC) - timedelta(days=1)
    results = storage.query_period(start)
    assert len(results) == 1


def test_tags_stored_and_retrieved(storage):
    record = make_record(tags={"feature": "chat", "user_id": "u123"})
    storage.record(record)

    start = datetime.now(UTC) - timedelta(hours=1)
    results = storage.query_period(start)
    assert results[0].tags == {"feature": "chat", "user_id": "u123"}


def test_empty_db_returns_zero(storage):
    start = datetime.now(UTC) - timedelta(hours=1)
    assert storage.get_total_cost(start) == 0.0
    assert storage.query_period(start) == []
    assert storage.get_summary_by_model(start) == []
