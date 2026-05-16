"""LLM client wrappers that transparently record token usage."""

import inspect
from datetime import datetime
from typing import Any

from .models import UsageRecord
from .pricing import calculate_cost


class WrappedCompletions:
    """Wraps OpenAI's chat.completions to intercept create() calls."""

    def __init__(self, original_completions: Any, recorder: Any):
        self._original = original_completions
        self._recorder = recorder

    def create(self, **kwargs: Any) -> Any:
        """Intercept chat.completions.create() to record usage."""
        # Extract metadata/tags before passing to OpenAI
        tags = kwargs.pop("metadata", {}) or {}

        # Determine caller from call stack
        caller = self._get_caller()

        # Call the original method
        response = self._original.create(**kwargs)

        # Extract usage info from response
        self._record_usage(response, kwargs.get("model", "unknown"), caller, tags)

        return response

    def _record_usage(self, response: Any, model: str, caller: str, tags: dict) -> None:
        """Extract token usage from response and record it."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        cost = calculate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            model=model,
            provider="openai",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            caller=caller,
            tags=tags,
        )
        self._recorder(record)

    def _get_caller(self) -> str:
        """Infer caller from the call stack."""
        frame = inspect.currentframe()
        try:
            # Walk up the stack to find the first frame outside tokenwatch
            if frame is None:
                return "unknown"
            caller_frame = frame
            for _ in range(10):
                caller_frame = caller_frame.f_back
                if caller_frame is None:
                    return "unknown"
                module = caller_frame.f_globals.get("__name__", "")
                if not module.startswith("tokenwatch"):
                    filename = caller_frame.f_code.co_filename
                    funcname = caller_frame.f_code.co_name
                    return f"{filename}:{funcname}"
            return "unknown"
        finally:
            del frame

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the original."""
        return getattr(self._original, name)


class WrappedChat:
    """Wraps OpenAI's chat namespace."""

    def __init__(self, original_chat: Any, recorder: Any):
        self._original = original_chat
        self.completions = WrappedCompletions(original_chat.completions, recorder)

    def __getattr__(self, name: str) -> Any:
        if name == "completions":
            return self.completions
        return getattr(self._original, name)


class WrappedOpenAIClient:
    """Wraps an OpenAI client to transparently record usage."""

    def __init__(self, client: Any, recorder: Any):
        self._client = client
        self.chat = WrappedChat(client.chat, recorder)

    def __getattr__(self, name: str) -> Any:
        if name == "chat":
            return self.chat
        return getattr(self._client, name)


class WrappedAnthropicMessages:
    """Wraps Anthropic's messages to intercept create() calls."""

    def __init__(self, original_messages: Any, recorder: Any):
        self._original = original_messages
        self._recorder = recorder

    def create(self, **kwargs: Any) -> Any:
        """Intercept messages.create() to record usage."""
        tags = kwargs.pop("metadata", {}) or {}

        caller = self._get_caller()

        response = self._original.create(**kwargs)

        self._record_usage(response, kwargs.get("model", "unknown"), caller, tags)

        return response

    def _record_usage(self, response: Any, model: str, caller: str, tags: dict) -> None:
        """Extract token usage from response and record it."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        cost = calculate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            model=model,
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            caller=caller,
            tags=tags,
        )
        self._recorder(record)

    def _get_caller(self) -> str:
        """Infer caller from the call stack."""
        frame = inspect.currentframe()
        try:
            if frame is None:
                return "unknown"
            caller_frame = frame
            for _ in range(10):
                caller_frame = caller_frame.f_back
                if caller_frame is None:
                    return "unknown"
                module = caller_frame.f_globals.get("__name__", "")
                if not module.startswith("tokenwatch"):
                    filename = caller_frame.f_code.co_filename
                    funcname = caller_frame.f_code.co_name
                    return f"{filename}:{funcname}"
            return "unknown"
        finally:
            del frame

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the original."""
        return getattr(self._original, name)


class WrappedAnthropicClient:
    """Wraps an Anthropic client to transparently record usage."""

    def __init__(self, client: Any, recorder: Any):
        self._client = client
        self.messages = WrappedAnthropicMessages(client.messages, recorder)

    def __getattr__(self, name: str) -> Any:
        if name == "messages":
            return self.messages
        return getattr(self._client, name)
