"""Decorator integrations for EcoTrace."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

from ecotrace.client import EcoTrace
from ecotrace.storage.models import TrackingResult

F = TypeVar("F", bound=Callable[..., Any])

_default_client: Optional[EcoTrace] = None


def get_default_client() -> EcoTrace:
    """Get or initialize default EcoTrace client singleton."""
    global _default_client
    if _default_client is None:
        _default_client = EcoTrace()
    return _default_client


def track(
    client: Optional[EcoTrace] = None,
    provider: str = "generic",
    model: str = "unknown",
    extract_prompt: Optional[Callable[..., Any]] = None,
) -> Callable[[F], F]:
    """Decorator to automatically track function calls as AI requests.

    Usage:
        @eco.track
        def ask_ai(prompt: str) -> str:
            return "response"

        # Or with parameters:
        @track(provider="openai", model="gpt-4o-mini")
        def ask_gpt(prompt: str) -> str:
            return "response"
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            eco_client = client or get_default_client()

            # Determine prompt from args/kwargs
            if extract_prompt:
                prompt_data = extract_prompt(*args, **kwargs)
            elif args:
                prompt_data = args[0]
            elif "prompt" in kwargs:
                prompt_data = kwargs["prompt"]
            else:
                prompt_data = str(kwargs)

            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start_time) * 1000

            eco_client.track(
                provider=provider,
                model=model,
                prompt=prompt_data,
                response=result,
                latency_ms=latency_ms,
            )
            return result

        return cast(F, wrapper)

    # Support @track without parentheses if called directly on a function
    if callable(client):
        actual_func = client
        client = None
        return decorator(actual_func)

    return decorator
