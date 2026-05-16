"""Tests for the trend CLI command."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from tokenwatch import TokenWatch
from tokenwatch.cli import main


@pytest.fixture
def runner(tmp_path):
    """CLI runner with a temporary database."""
    db_path = tmp_path / "test.db"
    os.environ["TOKENWATCH_DB"] = str(db_path)
    yield CliRunner()
    del os.environ["TOKENWATCH_DB"]


@pytest.fixture
def populated_db_trend(tmp_path):
    """Create a DB with data spread across multiple days."""
    db_path = tmp_path / "test.db"
    tw = TokenWatch(db_path=db_path)

    now = datetime.now(UTC)
    # Insert records for the last 3 days
    for days_ago in range(3):
        record = tw.record(
            provider="openai",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            caller="app.py:main",
        )
        # Manually update timestamp to simulate past days
        record.timestamp = now - timedelta(days=days_ago)
        # Re-insert with corrected timestamp (delete and re-add)
        tw.storage._get_conn().execute(
            "UPDATE events SET timestamp = ? WHERE id = ?",
            (record.timestamp.isoformat(), record.id),
        )
        tw.storage._get_conn().commit()

    os.environ["TOKENWATCH_DB"] = str(db_path)
    yield db_path
    del os.environ["TOKENWATCH_DB"]


def test_trend_no_data(runner):
    result = runner.invoke(main, ["trend"])
    assert result.exit_code == 0
    assert "No usage data" in result.output


def test_trend_with_data(populated_db_trend):
    runner = CliRunner()
    result = runner.invoke(main, ["trend"])
    assert result.exit_code == 0
    assert "Daily spend" in result.output
    assert "$" in result.output
    assert "Total:" in result.output


def test_trend_custom_days(populated_db_trend):
    runner = CliRunner()
    result = runner.invoke(main, ["trend", "--days", "3"])
    assert result.exit_code == 0
    assert "last 3 days" in result.output


def test_trend_shows_bar_chart(populated_db_trend):
    runner = CliRunner()
    result = runner.invoke(main, ["trend"])
    assert result.exit_code == 0
    # Should contain the bar character or at least the pipe separator
    assert "|" in result.output
