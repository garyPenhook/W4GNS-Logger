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
    """Specialized cache for award progress calculations - O(1) lookup instead of O(n) recalculation"""

    # All 11 award programs with dedicated cache keys
    CENTURION_CACHE_KEY = "centurion_progress"
    TRIBUNE_CACHE_KEY = "tribune_progress"
    SENATOR_CACHE_KEY = "senator_progress"
    DXCC_CACHE_KEY = "dxcc_progress"
    WAS_CACHE_KEY = "was_progress"
    WAC_CACHE_KEY = "wac_progress"
    QRP_CACHE_KEY = "qrp_progress"
    RAG_CHEW_CACHE_KEY = "rag_chew_progress"
    SKCC_DX_CACHE_KEY = "skcc_dx_progress"
    CANADIAN_MAPLE_CACHE_KEY = "canadian_maple_progress"
    TRIPLE_KEY_CACHE_KEY = "triple_key_progress"
    PFX_CACHE_KEY = "pfx_progress"
    POWER_STATS_CACHE_KEY = "power_statistics"

    # All cache keys for easy iteration (for bulk invalidation)
    ALL_AWARD_CACHE_KEYS = [
        CENTURION_CACHE_KEY,
        TRIBUNE_CACHE_KEY,
        SENATOR_CACHE_KEY,
        DXCC_CACHE_KEY,
        WAS_CACHE_KEY,
        WAC_CACHE_KEY,
        QRP_CACHE_KEY,
        RAG_CHEW_CACHE_KEY,
        SKCC_DX_CACHE_KEY,
        CANADIAN_MAPLE_CACHE_KEY,
        TRIPLE_KEY_CACHE_KEY,
        PFX_CACHE_KEY,
    ]

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

    def get_dxcc_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached DXCC progress"""
        return self._cache.get(self.DXCC_CACHE_KEY)

    def set_dxcc_progress(self, data: Dict[str, Any]) -> None:
        """Cache DXCC progress data"""
        self._cache.set(self.DXCC_CACHE_KEY, data)

    def get_was_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached WAS (Worked All States) progress"""
        return self._cache.get(self.WAS_CACHE_KEY)

    def set_was_progress(self, data: Dict[str, Any]) -> None:
        """Cache WAS progress data"""
        self._cache.set(self.WAS_CACHE_KEY, data)

    def get_wac_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached WAC (Worked All Continents) progress"""
        return self._cache.get(self.WAC_CACHE_KEY)

    def set_wac_progress(self, data: Dict[str, Any]) -> None:
        """Cache WAC progress data"""
        self._cache.set(self.WAC_CACHE_KEY, data)

    def get_qrp_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached QRP progress"""
        return self._cache.get(self.QRP_CACHE_KEY)

    def set_qrp_progress(self, data: Dict[str, Any]) -> None:
        """Cache QRP progress data"""
        self._cache.set(self.QRP_CACHE_KEY, data)

    def get_rag_chew_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached Rag Chew award progress"""
        return self._cache.get(self.RAG_CHEW_CACHE_KEY)

    def set_rag_chew_progress(self, data: Dict[str, Any]) -> None:
        """Cache Rag Chew progress data"""
        self._cache.set(self.RAG_CHEW_CACHE_KEY, data)

    def get_skcc_dx_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached SKCC DX award progress"""
        return self._cache.get(self.SKCC_DX_CACHE_KEY)

    def set_skcc_dx_progress(self, data: Dict[str, Any]) -> None:
        """Cache SKCC DX progress data"""
        self._cache.set(self.SKCC_DX_CACHE_KEY, data)

    def get_canadian_maple_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached Canadian Maple award progress"""
        return self._cache.get(self.CANADIAN_MAPLE_CACHE_KEY)

    def set_canadian_maple_progress(self, data: Dict[str, Any]) -> None:
        """Cache Canadian Maple progress data"""
        self._cache.set(self.CANADIAN_MAPLE_CACHE_KEY, data)

    def get_triple_key_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached Triple Key award progress"""
        return self._cache.get(self.TRIPLE_KEY_CACHE_KEY)

    def set_triple_key_progress(self, data: Dict[str, Any]) -> None:
        """Cache Triple Key progress data"""
        self._cache.set(self.TRIPLE_KEY_CACHE_KEY, data)

    def get_pfx_progress(self) -> Optional[Dict[str, Any]]:
        """Get cached PFX (Prefix) award progress"""
        return self._cache.get(self.PFX_CACHE_KEY)

    def set_pfx_progress(self, data: Dict[str, Any]) -> None:
        """Cache PFX progress data"""
        self._cache.set(self.PFX_CACHE_KEY, data)

    def get_power_statistics(self) -> Optional[Dict[str, Any]]:
        """Get cached power statistics"""
        return self._cache.get(self.POWER_STATS_CACHE_KEY)

    def set_power_statistics(self, data: Dict[str, Any]) -> None:
        """Cache power statistics data"""
        self._cache.set(self.POWER_STATS_CACHE_KEY, data)

    def get_award_progress(self, award_key: str) -> Optional[Dict[str, Any]]:
        """
        Generic method to get any award progress from cache.
        Enables O(1) lookup for any award instead of O(n) recalculation.

        Args:
            award_key: Award cache key (e.g., 'centurion_progress')

        Returns:
            Cached award data if available, None otherwise
        """
        return self._cache.get(award_key)

    def set_award_progress(self, award_key: str, data: Dict[str, Any]) -> None:
        """
        Generic method to cache any award progress.

        Args:
            award_key: Award cache key
            data: Award progress data to cache
        """
        self._cache.set(award_key, data)

    def invalidate_all_award_caches(self) -> None:
        """Invalidate all award-related caches when contacts change - O(1) operation"""
        for key in self.ALL_AWARD_CACHE_KEYS:
            self._cache.invalidate(key)
        logger.debug(f"All {len(self.ALL_AWARD_CACHE_KEYS)} award caches invalidated")

    def clear(self) -> None:
        """Clear all caches"""
        self._cache.clear()
