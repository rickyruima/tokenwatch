"""TokenWatch — htop for LLM spend. Local cost anomaly detection and attribution."""

__version__ = "0.3.0"

from pathlib import Path
from typing import Any, Optional

from .models import UsageRecord
from .pricing import calculate_cost
from .storage import Storage
from .wrapper import WrappedAnthropicClient, WrappedOpenAIClient


class TokenWatch:
    """Main entry point for TokenWatch SDK.

    Usage:
        tw = TokenWatch()
        client = tw.wrap(openai.OpenAI())
        # Use client normally — usage is recorded automatically.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._storage = Storage(db_path=db_path)

    def wrap(self, client: Any) -> Any:
        """Wrap an LLM client to transparently record usage.

        Supports OpenAI and Anthropic clients. The respective packages do not
        need to be installed — we duck-type the client.
        """
        # Check if it looks like an OpenAI client (has chat.completions)
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            return WrappedOpenAIClient(client, self._record)
        # Check if it looks like an Anthropic client (has messages.create)
        if hasattr(client, "messages") and hasattr(client.messages, "create"):
            return WrappedAnthropicClient(client, self._record)
        raise TypeError(
            f"Unsupported client type: {type(client).__name__}. "
            "Currently only OpenAI and Anthropic clients are supported."
        )

    def record(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float] = None,
        caller: str = "",
        tags: Optional[dict] = None,
    ) -> UsageRecord:
        """Manually record a usage event."""
        if cost_usd is None:
            cost_usd = calculate_cost(model, input_tokens, output_tokens)
        usage = UsageRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            caller=caller,
            tags=tags or {},
        )
        self._storage.record(usage)
        return usage

    def _record(self, usage: UsageRecord) -> None:
        """Internal callback used by wrappers."""
        self._storage.record(usage)

    @property
    def storage(self) -> Storage:
        return self._storage
