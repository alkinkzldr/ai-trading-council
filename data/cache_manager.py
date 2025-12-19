import os
import json
from typing import Any

import redis 
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class CacheManager:
    """Redis-based cache manager for API responses and computed data."""

    _instance = None
    _client: redis.Redis | None = None
    _stats: dict | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host: str = None, port: int = None, db: int = None):
        if self._client is None:
            if host and port:
                self._client = redis.Redis(host=host, port=port, db=db or 0, decode_responses=True)
            else:
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
        if self._stats is None:
            self._stats = {'hits': 0, 'misses': 0}

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client."""
        return self._client

    def get(self, key: str) -> Any | None:
        """Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        value = self._client.get(key)
        if value is None:
            self._stats['misses'] += 1
            return None
        self._stats['hits'] += 1
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set a value in cache with expiration.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 5 minutes)

        Returns:
            True if successful
        """
        serialized = json.dumps(value) if not isinstance(value, str) else value
        return self._client.setex(key, ttl, serialized)

    def delete(self, key: str) -> bool:
        """Delete a key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted
        """
        return bool(self._client.delete(key))

    def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists
        """
        return bool(self._client.exists(key))

    def get_ttl(self, key: str) -> int:
        """Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        return self._client.ttl(key)

    def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Redis glob pattern (e.g., "price:*")

        Returns:
            Number of keys deleted
        """
        keys = self._client.keys(pattern)
        if keys:
            return self._client.delete(*keys)
        return 0

    def get_or_set(self, key: str, factory: callable, ttl: int = 300) -> Any:
        """Get from cache or compute and cache the value.

        Args:
            key: Cache key
            factory: Function to call if cache miss
            ttl: TTL for cached value

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl)
        return value

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit_rate, and total_keys
        """
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total if total > 0 else 0.0
        total_keys = len(self._client.keys('*'))
        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': hit_rate,
            'total_keys': total_keys
        }

    def health_check(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if Redis is responding
        """
        try:
            return self._client.ping()
        except redis.ConnectionError:
            return False


# Lazy singleton - don't instantiate at import time
def get_cache() -> CacheManager:
    """Get the singleton CacheManager instance."""
    return CacheManager()
