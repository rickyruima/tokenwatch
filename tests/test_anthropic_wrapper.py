"""Tests for Anthropic client wrapper."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tokenwatch import TokenWatch
from tokenwatch.models import UsageRecord


class MockAnthropicUsage:
    def __init__(self, input_tokens=200, output_tokens=100):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class MockAnthropicResponse:
    def __init__(self, input_tokens=200, output_tokens=100):
        self.usage = MockAnthropicUsage(input_tokens, output_tokens)
        self.content = [MagicMock()]
        self.model = "claude-3-opus-20240229"
        self.stop_reason = "end_turn"


class MockMessages:
    def create(self, **kwargs):
        return MockAnthropicResponse()


class MockAnthropicClient:
    """Mock that mimics Anthropic client structure."""

    def __init__(self):
        self.messages = MockMessages()


@pytest.fixture
def tw(tmp_path):
    db_path = tmp_path / "test.db"
    return TokenWatch(db_path=db_path)


def test_wrap_anthropic_client(tw):
    client = MockAnthropicClient()
    wrapped = tw.wrap(client)
    assert hasattr(wrapped, "messages")
    assert hasattr(wrapped.messages, "create")


def test_wrap_anthropic_records_usage(tw):
    client = MockAnthropicClient()
    wrapped = tw.wrap(client)

    response = wrapped.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}],
    )

    start = datetime.now(UTC) - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert len(records) == 1
    assert records[0].model == "claude-3-opus-20240229"
    assert records[0].input_tokens == 200
    assert records[0].output_tokens == 100
    assert records[0].provider == "anthropic"


def test_wrap_anthropic_passes_through_response(tw):
    client = MockAnthropicClient()
    wrapped = tw.wrap(client)

    response = wrapped.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert hasattr(response, "usage")
    assert hasattr(response, "content")


def test_wrap_anthropic_calculates_cost(tw):
    client = MockAnthropicClient()
    wrapped = tw.wrap(client)

    wrapped.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}],
    )

    start = datetime.now(UTC) - timedelta(hours=1)
    records = tw.storage.query_period(start)
    # claude-3-opus: $15/1M input, $75/1M output
    # 200 input + 100 output = 200*15/1M + 100*75/1M = 0.003 + 0.0075 = 0.0105
    expected_cost = (200 * 15 / 1_000_000) + (100 * 75 / 1_000_000)
    assert abs(records[0].cost_usd - expected_cost) < 1e-10


def test_wrap_anthropic_extracts_metadata_as_tags(tw):
    client = MockAnthropicClient()
    wrapped = tw.wrap(client)

    wrapped.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}],
        metadata={"feature": "summarize", "team": "backend"},
    )

    start = datetime.now(UTC) - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert records[0].tags == {"feature": "summarize", "team": "backend"}


def test_wrap_anthropic_no_usage_in_response(tw):
    """If response has no usage info, don't crash."""
    client = MockAnthropicClient()

    class NoUsageResponse:
        usage = None
        content = []

    client.messages.create = lambda **kwargs: NoUsageResponse()

    wrapped = tw.wrap(client)
    response = wrapped.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[],
    )

    start = datetime.now(UTC) - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert len(records) == 0


def test_wrap_anthropic_proxies_other_attributes(tw):
    """Ensure non-messages attributes are proxied."""
    client = MockAnthropicClient()
    client.api_key = "test-key"
    wrapped = tw.wrap(client)
    assert wrapped.api_key == "test-key"
