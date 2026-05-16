"""Tests for crumdbob.retry — exponential backoff decorator."""

from __future__ import annotations

import pytest

from crumdbob.retry import retry


class _TransientError(Exception):
    """Marker exception we'll retry on."""


class _NonRetryable(Exception):
    """Marker exception that should NOT be retried."""


@pytest.fixture
def _no_sleep():
    """Replace time.sleep so tests don't actually wait."""
    calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    yield fake_sleep, calls


class TestRetry:
    def test_success_first_attempt_no_retry(self, _no_sleep):
        fake_sleep, calls = _no_sleep
        invocations = [0]

        @retry(on=(_TransientError,), max_attempts=3, sleep=fake_sleep)
        def operation():
            invocations[0] += 1
            return "ok"

        assert operation() == "ok"
        assert invocations[0] == 1
        assert calls == []  # No retries means no sleep

    def test_retries_then_succeeds(self, _no_sleep):
        fake_sleep, calls = _no_sleep
        invocations = [0]

        @retry(
            on=(_TransientError,), max_attempts=5, base_delay=0.1, jitter=False, sleep=fake_sleep
        )
        def flaky():
            invocations[0] += 1
            if invocations[0] < 3:
                raise _TransientError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert invocations[0] == 3
        assert len(calls) == 2  # slept twice (before attempt 2 and 3)
        # Exponential backoff: 0.1, 0.2 with no jitter
        assert calls == [0.1, 0.2]

    def test_exhausted_raises_last_exception(self, _no_sleep):
        fake_sleep, _ = _no_sleep

        @retry(
            on=(_TransientError,), max_attempts=3, base_delay=0.01, jitter=False, sleep=fake_sleep
        )
        def always_fails():
            raise _TransientError("persistent")

        with pytest.raises(_TransientError, match="persistent"):
            always_fails()

    def test_non_retryable_propagates_immediately(self, _no_sleep):
        fake_sleep, calls = _no_sleep
        invocations = [0]

        @retry(on=(_TransientError,), max_attempts=5, sleep=fake_sleep)
        def operation():
            invocations[0] += 1
            raise _NonRetryable("real bug")

        with pytest.raises(_NonRetryable, match="real bug"):
            operation()
        assert invocations[0] == 1  # No retries on non-listed exception
        assert calls == []

    def test_max_delay_caps_backoff(self, _no_sleep):
        fake_sleep, calls = _no_sleep

        @retry(
            on=(_TransientError,),
            max_attempts=10,
            base_delay=1.0,
            max_delay=2.0,
            jitter=False,
            sleep=fake_sleep,
        )
        def always_fails():
            raise _TransientError()

        with pytest.raises(_TransientError):
            always_fails()
        # Without cap: 1, 2, 4, 8, 16, 32 ...
        # With cap=2: 1, 2, 2, 2, 2, ...
        assert all(d <= 2.0 for d in calls)

    def test_jitter_keeps_delay_in_range(self, _no_sleep):
        fake_sleep, calls = _no_sleep

        @retry(on=(_TransientError,), max_attempts=5, base_delay=1.0, jitter=True, sleep=fake_sleep)
        def always_fails():
            raise _TransientError()

        with pytest.raises(_TransientError):
            always_fails()
        # With full jitter, each delay is uniform in [0, base * 2^n]
        # so just confirm they're all non-negative and not exceeding the raw value.
        for i, delay in enumerate(calls):
            ceiling = 1.0 * (2**i)
            assert 0.0 <= delay <= ceiling

    def test_zero_attempts_rejected(self):
        with pytest.raises(ValueError, match=">= 1"):
            retry(on=(Exception,), max_attempts=0)

    def test_negative_base_delay_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            retry(on=(Exception,), max_attempts=3, base_delay=-1)

    def test_preserves_function_signature(self):
        @retry(on=(Exception,), max_attempts=1)
        def my_function(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        assert my_function.__name__ == "my_function"
        assert "Add two numbers" in my_function.__doc__

    def test_passes_args_and_kwargs(self):
        @retry(on=(Exception,), max_attempts=1)
        def add(a, b, *, c=0):
            return a + b + c

        assert add(1, 2, c=10) == 13
