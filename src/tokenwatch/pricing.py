"""Hardcoded pricing table for common LLM models.

Prices are in USD per 1M tokens (input / output).
"""

# {model_name: (input_price_per_1M, output_price_per_1M)}
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI models
    "gpt-4": (30.0, 60.0),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-4-turbo-preview": (10.0, 30.0),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.0, 8.0),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-3.5-turbo": (0.50, 1.50),
    "gpt-3.5-turbo-16k": (3.0, 4.0),
    "o1": (15.0, 60.0),
    "o1-mini": (3.0, 12.0),
    "o1-pro": (150.0, 600.0),
    "o3": (10.0, 40.0),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
    # Anthropic models (for future use)
    "claude-3-opus-20240229": (15.0, 75.0),
    "claude-3-sonnet-20240229": (3.0, 15.0),
    "claude-3-haiku-20240307": (0.25, 1.25),
    "claude-3.5-sonnet-20241022": (3.0, 15.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-opus-4-20250514": (15.0, 75.0),
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts.

    Returns 0.0 if the model is not in the pricing table.
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    input_price_per_token = pricing[0] / 1_000_000
    output_price_per_token = pricing[1] / 1_000_000
    return (input_tokens * input_price_per_token) + (output_tokens * output_price_per_token)
