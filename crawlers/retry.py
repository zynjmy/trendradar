"""Lightweight retry logic for crawlers.

Adapted from BettaFish/utils/retry_helper.py — simplified for TrendRadar's
single-function crawler architecture.
"""
import os
import time

import requests


class RetryConfig:
    def __init__(self, max_retries=3, initial_delay=1.0,
                 backoff_factor=2.0, max_delay=30.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay


_RETRYABLE = (
    requests.RequestException,
    ConnectionError,
    TimeoutError,
    RuntimeError,
    OSError,
)


def _load_config() -> RetryConfig:
    max_retries = int(os.environ.get("CRAWLER_MAX_RETRIES", "3"))
    initial_delay = float(os.environ.get("CRAWLER_RETRY_DELAY", "1.0"))
    return RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=2.0,
        max_delay=10.0,
    )


def retry_call(func):
    """Call func() with retry, returning its result or raising the last error.

    Retry count and delay are read from env vars CRAWLER_MAX_RETRIES
    and CRAWLER_RETRY_DELAY. Set CRAWLER_MAX_RETRIES=0 to disable retries.
    """
    config = _load_config()
    last_exc = None
    for attempt in range(config.max_retries + 1):
        try:
            return func()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == config.max_retries:
                raise
            delay = min(
                config.initial_delay * (config.backoff_factor ** attempt),
                config.max_delay,
            )
            time.sleep(delay)
    raise last_exc  # pragma: no cover
