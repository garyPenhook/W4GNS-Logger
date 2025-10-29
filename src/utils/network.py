"""
Network utilities: resilient urlopen with retries and exponential backoff.
"""
from __future__ import annotations

import time
import urllib.request
from typing import Optional, Dict


def urlopen_with_retries(
    url: str,
    *,
    timeout: int = 10,
    retries: int = 3,
    backoff: float = 0.5,
    headers: Optional[Dict[str, str]] = None,
):
    """
    Open a URL with retries and exponential backoff.

    Returns a file-like HTTPResponse object compatible with "with ... as resp".

    Args:
        url: Full URL string
        timeout: Timeout in seconds for each attempt
        retries: Number of attempts (>=1)
        backoff: Initial backoff in seconds; doubles on each retry
        headers: Optional headers to include in the request

    Raises:
        The last exception from urllib.request.urlopen if all retries fail.
    """
    if retries < 1:
        retries = 1

    req = urllib.request.Request(url, headers=headers or {})

    attempt = 0
    delay = max(0.0, backoff)

    while True:
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except Exception:
            attempt += 1
            if attempt >= retries:
                # Re-raise last exception
                raise
            time.sleep(delay)
            delay *= 2.0
