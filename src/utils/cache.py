"""
Caching utility with TTL (Time-To-Live) support for performance optimization.

Provides a simple in-memory cache for expensive database operations like
award calculations. Cache entries expire after a configurable TTL period.
"""

import time
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize TTL cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 60)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # key -> (value, timestamp)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]

        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            logger.debug(f"Cache entry expired: {key}")
            return None

        logger.debug(f"Cache hit: {key}")
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())
        logger.debug(f"Cache set: {key}")

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        logger.debug("Cache cleared")

    def invalidate(self, key: str) -> None:
        """
        Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key}")

    def get_or_compute(self, key: str, compute_func: Callable[[], Any]) -> Any:
        """
        Get from cache or compute if not cached.

        This is a convenience method that either returns a cached value
        or computes it using the provided function and caches the result.

        Args:
            key: Cache key
            compute_func: Function to call if not cached (no arguments)

        Returns:
            Cached or computed value
        """
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        logger.debug(f"Cache miss, computing: {key}")
        value = compute_func()
        self.set(key, value)
        return value

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "entries": len(self._cache),
            "ttl_seconds": self.ttl_seconds,
        }


class AwardProgressCache:
    """Specialized cache for award progress calculations"""

    CENTURION_CACHE_KEY = "centurion_progress"
    TRIBUNE_CACHE_KEY = "tribune_progress"
    SENATOR_CACHE_KEY = "senator_progress"
    QRP_CACHE_KEY = "qrp_progress"
    POWER_STATS_CACHE_KEY = "power_statistics"

    def __init__(self, ttl_seconds: int = 30):
        """
        Initialize award progress cache.

        Args:
            ttl_seconds: TTL for cache entries in seconds (default: 30)
        """
        self._cache = TTLCache(ttl_seconds)

    def get_centurion_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached Centurion progress"""
        return self._cache.get(self.CENTURION_CACHE_KEY)

    def set_centurion_progress(self, data: Dict[str, Any]) -> None:
        """Cache Centurion progress data"""
        self._cache.set(self.CENTURION_CACHE_KEY, data)

    def get_tribune_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached Tribune progress"""
        return self._cache.get(self.TRIBUNE_CACHE_KEY)

    def set_tribune_progress(self, data: Dict[str, Any]) -> None:
        """Cache Tribune progress data"""
        self._cache.set(self.TRIBUNE_CACHE_KEY, data)

    def get_senator_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached Senator progress"""
        return self._cache.get(self.SENATOR_CACHE_KEY)

    def set_senator_progress(self, data: Dict[str, Any]) -> None:
        """Cache Senator progress data"""
        self._cache.set(self.SENATOR_CACHE_KEY, data)

    def get_qrp_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached QRP progress"""
        return self._cache.get(self.QRP_CACHE_KEY)

    def set_qrp_progress(self, data: Dict[str, Any]) -> None:
        """Cache QRP progress data"""
        self._cache.set(self.QRP_CACHE_KEY, data)

    def get_power_statistics(self) -> Optional[Dict[str, Any]]:
        """Get cached power statistics"""
        return self._cache.get(self.POWER_STATS_CACHE_KEY)

    def set_power_statistics(self, data: Dict[str, Any]) -> None:
        """Cache power statistics data"""
        self._cache.set(self.POWER_STATS_CACHE_KEY, data)

    def invalidate_all_award_caches(self) -> None:
        """Invalidate all award-related caches when contacts change"""
        self._cache.invalidate(self.CENTURION_CACHE_KEY)
        self._cache.invalidate(self.TRIBUNE_CACHE_KEY)
        self._cache.invalidate(self.SENATOR_CACHE_KEY)
        self._cache.invalidate(self.QRP_CACHE_KEY)
        self._cache.invalidate(self.POWER_STATS_CACHE_KEY)
        logger.debug("All award caches invalidated")

    def clear(self) -> None:
        """Clear all caches"""
        self._cache.clear()
