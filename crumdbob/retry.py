"""Retry with exponential backoff for transient failures.

Use for any operation that talks to a flaky external dependency: LLM
providers, HTTP APIs, network filesystems. The decorator preserves the
wrapped function's signature and type hints, and only retries the
exception classes the caller explicitly opts into — accidentally retrying
``ValueError`` on a bad-input bug would mask real problems.

Example:

    from crumdbob.retry import retry

    @retry(
        on=(httpx.HTTPError, TimeoutError),
        max_attempts=3,
        base_delay=0.5,
    )
    def fetch_from_llm(prompt: str) -> str:
        return openai_client.chat.completions.create(...)

The backoff is exponential with **full jitter** (the AWS Architecture
Blog formulation) — better thundering-herd resistance than equal-jitter
or no-jitter for the same retry budget.
"""

from __future__ import annotations

import functools
import logging
import secrets
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry(
    *,
    on: tuple[type[BaseException], ...],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator with exponential backoff + full jitter.

    Args:
        on: Exception classes that should trigger a retry. Anything else
            propagates immediately.
        max_attempts: Total number of attempts including the first. Must
            be >= 1. ``max_attempts=1`` disables retries (no behaviour
            change beyond logging).
        base_delay: Base delay in seconds for the first retry. Subsequent
            retries scale as ``base_delay * 2**(attempt-1)`` capped at
            ``max_delay``.
        max_delay: Hard ceiling on per-retry sleep.
        jitter: If True, multiply the computed delay by a uniform random
            factor in [0, 1]. Highly recommended; defaults to True.
        sleep: Injectable sleep function — set to a no-op in tests so the
            retry path is exercised instantly.

    Returns:
        A decorator that wraps a function with retry behaviour.

    Raises:
        ValueError: If ``max_attempts`` is less than 1.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if base_delay < 0:
        raise ValueError("base_delay must be non-negative")

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except on as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.warning(
                            "retry.exhausted",
                            extra={
                                "function": fn.__name__,
                                "attempts": attempt,
                                "exc_type": type(exc).__name__,
                            },
                        )
                        raise
                    raw_delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay = (
                        raw_delay * (secrets.randbelow(1_000_000) / 1_000_000)
                        if jitter
                        else raw_delay
                    )
                    logger.info(
                        "retry.backoff",
                        extra={
                            "function": fn.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 3),
                            "exc_type": type(exc).__name__,
                        },
                    )
                    sleep(delay)
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("retry wrapper exited without returning or raising")

        return wrapper

    return decorator
