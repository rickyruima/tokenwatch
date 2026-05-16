"""Tests for OpenAI client wrapper."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tokenwatch import TokenWatch
from tokenwatch.models import UsageRecord


class MockUsage:
    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockResponse:
    def __init__(self, prompt_tokens=100, completion_tokens=50):
        self.usage = MockUsage(prompt_tokens, completion_tokens)
        self.choices = [MagicMock()]


class MockCompletions:
    def create(self, **kwargs):
        return MockResponse()


class MockChat:
    def __init__(self):
        self.completions = MockCompletions()


class MockOpenAIClient:
    """Mock that mimics OpenAI client structure."""

    def __init__(self):
        self.chat = MockChat()


@pytest.fixture
def tw(tmp_path):
    db_path = tmp_path / "test.db"
    return TokenWatch(db_path=db_path)


def test_wrap_openai_client(tw):
    client = MockOpenAIClient()
    wrapped = tw.wrap(client)
    assert hasattr(wrapped, "chat")
    assert hasattr(wrapped.chat, "completions")


def test_wrap_records_usage(tw):
    client = MockOpenAIClient()
    wrapped = tw.wrap(client)

    response = wrapped.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
    )

    # Check that usage was recorded
    start = datetime.utcnow() - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert len(records) == 1
    assert records[0].model == "gpt-4"
    assert records[0].input_tokens == 100
    assert records[0].output_tokens == 50
    assert records[0].provider == "openai"


def test_wrap_passes_through_response(tw):
    client = MockOpenAIClient()
    wrapped = tw.wrap(client)

    response = wrapped.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
    )

    # Should return the mock response
    assert hasattr(response, "usage")
    assert hasattr(response, "choices")


def test_wrap_extracts_metadata_as_tags(tw):
    client = MockOpenAIClient()
    wrapped = tw.wrap(client)

    response = wrapped.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        metadata={"feature": "chat", "customer_id": "c123"},
    )

    start = datetime.utcnow() - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert records[0].tags == {"feature": "chat", "customer_id": "c123"}


def test_wrap_calculates_cost(tw):
    client = MockOpenAIClient()
    wrapped = tw.wrap(client)

    wrapped.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
    )

    start = datetime.utcnow() - timedelta(hours=1)
    records = tw.storage.query_period(start)
    # gpt-4: $30/1M input, $60/1M output
    # 100 input + 50 output = 100*30/1M + 50*60/1M = 0.003 + 0.003 = 0.006
    expected_cost = (100 * 30 / 1_000_000) + (50 * 60 / 1_000_000)
    assert abs(records[0].cost_usd - expected_cost) < 1e-10


def test_wrap_unsupported_client(tw):
    with pytest.raises(TypeError, match="Unsupported client type"):
        tw.wrap("not a client")


def test_manual_record(tw):
    usage = tw.record(
        provider="openai",
        model="gpt-4",
        input_tokens=500,
        output_tokens=200,
        caller="test_func",
        tags={"env": "test"},
    )

    assert usage.model == "gpt-4"
    assert usage.total_tokens == 700

    start = datetime.utcnow() - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert len(records) == 1
    assert records[0].caller == "test_func"


def test_wrap_with_no_usage_in_response(tw):
    """If response has no usage info, don't crash."""
    client = MockOpenAIClient()

    # Override to return response without usage
    class NoUsageResponse:
        usage = None
        choices = []

    client.chat.completions.create = lambda **kwargs: NoUsageResponse()

    wrapped = tw.wrap(client)
    response = wrapped.chat.completions.create(model="gpt-4", messages=[])

    start = datetime.utcnow() - timedelta(hours=1)
    records = tw.storage.query_period(start)
    assert len(records) == 0  # No record created
