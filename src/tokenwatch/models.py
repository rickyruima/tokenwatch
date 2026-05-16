"""Pydantic data models for TokenWatch."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class UsageRecord(BaseModel):
    """A single LLM API usage event."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model: str
    provider: str  # "openai" | "anthropic"
    input_tokens: int
    output_tokens: int
    total_tokens: int = 0
    cost_usd: float
    caller: str = ""  # who made the call (e.g., function name, module)
    tags: dict = Field(default_factory=dict)  # custom metadata

    def model_post_init(self, __context) -> None:
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens
