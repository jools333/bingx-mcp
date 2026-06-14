"""Rate limiter utility using a token bucket algorithm."""

import asyncio
import time
from collections import defaultdict


class RateLimiter:
    """Asynchronous token-bucket rate limiter.

    Tracks requests per time window per endpoint category and enforces
    BingX API rate limits.  Uses a sliding window approach.
    """

    def __init__(
        self,
        default_rate: int = 5,
        default_period: float = 1.0,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            default_rate: Default max requests per period.
            default_period: Default period in seconds.
        """
        self._default_rate = default_rate
        self._default_period = default_period
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, key: str = "default") -> None:
        """Wait until a request token is available for the given key.

        Args:
            key: Rate limit bucket identifier.
        """
        async with self._locks[key]:
            now = time.monotonic()
            window = self._buckets[key]

            cutoff = now - self._default_period
            self._buckets[key] = [t for t in window if t > cutoff]

            if len(self._buckets[key]) >= self._default_rate:
                sleep_time = self._buckets[key][0] - cutoff
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                self._buckets[key] = [t for t in self._buckets[key] if t > time.monotonic() - self._default_period]

            self._buckets[key].append(time.monotonic())


rate_limiter = RateLimiter()
