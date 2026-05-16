"""Tests for pricing calculator."""

from tokenwatch.pricing import calculate_cost, MODEL_PRICING


def test_gpt4_pricing():
    # gpt-4: $30/1M input, $60/1M output
    cost = calculate_cost("gpt-4", input_tokens=1000, output_tokens=500)
    expected = (1000 * 30 / 1_000_000) + (500 * 60 / 1_000_000)
    assert abs(cost - expected) < 1e-10


def test_gpt4o_mini_pricing():
    # gpt-4o-mini: $0.15/1M input, $0.60/1M output
    cost = calculate_cost("gpt-4o-mini", input_tokens=10000, output_tokens=5000)
    expected = (10000 * 0.15 / 1_000_000) + (5000 * 0.60 / 1_000_000)
    assert abs(cost - expected) < 1e-10


def test_unknown_model_returns_zero():
    cost = calculate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
    assert cost == 0.0


def test_zero_tokens():
    cost = calculate_cost("gpt-4", input_tokens=0, output_tokens=0)
    assert cost == 0.0


def test_all_models_have_two_prices():
    for model, pricing in MODEL_PRICING.items():
        assert len(pricing) == 2
        assert pricing[0] >= 0
        assert pricing[1] >= 0
