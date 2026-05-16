"""Tests for CLI commands."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from tokenwatch import TokenWatch
from tokenwatch.cli import main
from tokenwatch.models import UsageRecord


@pytest.fixture
def runner(tmp_path):
    """CLI runner with a temporary database."""
    db_path = tmp_path / "test.db"
    os.environ["TOKENWATCH_DB"] = str(db_path)
    yield CliRunner()
    del os.environ["TOKENWATCH_DB"]


@pytest.fixture
def populated_db(tmp_path):
    """Create a DB with some test data."""
    db_path = tmp_path / "test.db"
    tw = TokenWatch(db_path=db_path)
    tw.record(provider="openai", model="gpt-4", input_tokens=1000, output_tokens=500, caller="app.py:main")
    tw.record(provider="openai", model="gpt-4", input_tokens=2000, output_tokens=1000, caller="app.py:main")
    tw.record(provider="openai", model="gpt-3.5-turbo", input_tokens=5000, output_tokens=2000, caller="utils.py:helper")
    os.environ["TOKENWATCH_DB"] = str(db_path)
    yield db_path
    del os.environ["TOKENWATCH_DB"]


def test_report_no_data(runner):
    result = runner.invoke(main, ["report"])
    assert result.exit_code == 0
    assert "No usage data" in result.output


def test_report_with_data(populated_db):
    runner = CliRunner()
    result = runner.invoke(main, ["report"])
    assert result.exit_code == 0
    assert "$" in result.output
    assert "gpt-4" in result.output


def test_top_by_model(populated_db):
    runner = CliRunner()
    result = runner.invoke(main, ["top", "--by", "model"])
    assert result.exit_code == 0
    assert "gpt-4" in result.output


def test_top_by_caller(populated_db):
    runner = CliRunner()
    result = runner.invoke(main, ["top", "--by", "caller"])
    assert result.exit_code == 0
    assert "app.py:main" in result.output


def test_top_no_data(runner):
    result = runner.invoke(main, ["top", "--by", "model"])
    assert result.exit_code == 0
    assert "No data" in result.output


def test_top_invalid_dimension(runner):
    result = runner.invoke(main, ["top", "--by", "invalid"])
    assert result.exit_code != 0


def test_main_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "TokenWatch" in result.output
