"""
Endpoint-aware API rate limiter for Angel One SmartAPI.
Includes exponential backoff for AB1004 TooManyRequests errors.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


def _normalize_key(api_name: str) -> str:
    name = (api_name or "").lower()
    if "getcandledata" in name or "candle" in name:
        return "getCandleData"
    if "placeorder" in name or ("place" in name and "order" in name):
        return "placeOrder"
    if "modify" in name and "order" in name:
        return "modifyOrder"
    if "cancel" in name and "order" in name:
        return "cancelOrder"
    if "orderbook" in name:
        return "orderBook"
    if "tradebook" in name:
        return "tradeBook"
    if "position" in name:
        return "position"
    if "ltp" in name:
        return "ltpData"
    return "other"


@dataclass
class _Bucket:
    min_interval: float
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_call_ts: float = 0.0
    total_calls: int = 0
    total_wait_s: float = 0.0
    # Backoff state
    consecutive_errors: int = 0
    backoff_until: float = 0.0


class EndpointRateLimiter:
    """
    Thread-safe per-endpoint rate limiter with exponential backoff
    for AB1004 TooManyRequests errors.
    """

    # Backoff schedule for AB1004: 10s, 20s, 40s, 60s (capped)
    BACKOFF_SCHEDULE = [10.0, 20.0, 40.0, 60.0]

    def __init__(self, bucket_intervals: Optional[Dict[str, float]] = None):
        defaults = {
            "getCandleData": 3.5,   # Max ~17 calls/min — well under Angel One limit
            "ltpData":       0.20,
            "orderBook":     1.10,
            "tradeBook":     1.10,
            "position":      1.10,
            "placeOrder":    0.20,
            "modifyOrder":   0.30,
            "cancelOrder":   0.30,
            "other":         0.30,
        }
        if bucket_intervals:
            defaults.update(bucket_intervals)

        self._buckets: Dict[str, _Bucket] = {
            k: _Bucket(min_interval=v) for k, v in defaults.items()
        }

    def wait(self, api_name: str = "other") -> None:
        """Wait the required interval for this endpoint. Respects active backoff."""
        key    = _normalize_key(api_name)
        bucket = self._buckets.get(key) or self._buckets["other"]

        with bucket.lock:
            now = time.perf_counter()

            # --- Honour active backoff window ---
            if now < bucket.backoff_until:
                wait_s = bucket.backoff_until - now
                print(f"   ⏳ Rate-limit backoff: waiting {wait_s:.1f}s for {key}")
                time.sleep(wait_s)
                now = time.perf_counter()

            # --- Normal per-call spacing ---
            elapsed = now - bucket.last_call_ts
            gap     = bucket.min_interval - elapsed
            if gap > 0:
                time.sleep(gap)
                bucket.total_wait_s += gap
                now = time.perf_counter()

            bucket.last_call_ts = now
            bucket.total_calls += 1

    def report_error(self, api_name: str, error_code: str = "") -> float:
        """
        Call this when an API returns AB1004 / TooManyRequests.
        Applies exponential backoff and returns the backoff duration in seconds.
        """
        key    = _normalize_key(api_name)
        bucket = self._buckets.get(key) or self._buckets["other"]

        with bucket.lock:
            idx       = min(bucket.consecutive_errors, len(self.BACKOFF_SCHEDULE) - 1)
            backoff_s = self.BACKOFF_SCHEDULE[idx]
            bucket.consecutive_errors += 1
            bucket.backoff_until = time.perf_counter() + backoff_s
            print(f"   ⚠️  AB1004 on '{key}' — backoff #{bucket.consecutive_errors}: "
                  f"sleeping {backoff_s}s")
            return backoff_s

    def report_success(self, api_name: str) -> None:
        """Reset consecutive error count after a successful call."""
        key    = _normalize_key(api_name)
        bucket = self._buckets.get(key) or self._buckets["other"]
        with bucket.lock:
            bucket.consecutive_errors = 0

    def log_stats(self) -> None:
        for k, b in self._buckets.items():
            avg = (b.total_wait_s / b.total_calls) if b.total_calls else 0.0
            print(f"{k:16s} calls={b.total_calls:5d} "
                  f"total_wait={b.total_wait_s:7.2f}s avg={avg:.3f}s")

    @property
    def min_delay(self) -> float:
        return float(self._buckets["orderBook"].min_interval)


# Shared singleton
api_rate_limiter = EndpointRateLimiter()


def wait(api_name: str = "other") -> None:
    api_rate_limiter.wait(api_name)
