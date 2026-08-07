"""Retry policy algorithms for research task step failures."""

from __future__ import annotations


def calculate_backoff_delay(
    attempt_count: int,
    base_delay: int = 10,
    max_delay: int = 600,
) -> int:
    """Calculate exponential backoff delay in seconds.

    formula: min(base_delay * (2 ** (attempt_count - 1)), max_delay)
    """
    if attempt_count <= 0:
        return 0
    exponent = min(attempt_count - 1, 10)
    delay = base_delay * (2**exponent)
    return int(min(delay, max_delay))
