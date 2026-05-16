"""Tests for data models."""

from datetime import datetime

from tokenwatch.models import UsageRecord


def test_usage_record_defaults():
    record = UsageRecord(
        model="gpt-4",
        provider="openai",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
    )
    assert record.id  # auto-generated
    assert record.timestamp  # auto-generated
    assert record.total_tokens == 150
    assert record.caller == ""
    assert record.tags == {}


def test_usage_record_total_tokens_calculated():
    record = UsageRecord(
        model="gpt-4",
        provider="openai",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.05,
    )
    assert record.total_tokens == 1500


def test_usage_record_with_tags():
    record = UsageRecord(
        model="gpt-4",
        provider="openai",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
        tags={"feature": "chat", "customer_id": "cust_123"},
    )
    assert record.tags["feature"] == "chat"
    assert record.tags["customer_id"] == "cust_123"


def test_usage_record_with_explicit_total():
    """If total_tokens is explicitly 0, it gets calculated."""
    record = UsageRecord(
        model="gpt-4",
        provider="openai",
        input_tokens=100,
        output_tokens=50,
        total_tokens=0,
        cost_usd=0.01,
    )
    assert record.total_tokens == 150
