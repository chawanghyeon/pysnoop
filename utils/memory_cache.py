# server/utils/memory_cache.py

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class MetricCache:
    """
    MetricCache stores the latest value and timestamp for each URI.
    Provides thread-safe updates and TTL-based expiration.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        """
        Initialize the metric cache.

        Args:
            ttl_seconds (int): Time in seconds before a metric expires.
        """
        self._cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock: asyncio.Lock = asyncio.Lock()
        self._ttl = timedelta(seconds=ttl_seconds)

    async def update(self, uri: str, value: Any, ts: datetime) -> None:
        """
        Update the cache with a new metric value for a specific URI.

        Args:
            uri (str): The URI path.
            value (Any): The metric value.
            ts (datetime): The timestamp of the metric.
        """
        async with self._lock:
            self._cache[uri] = {"timestamp": ts, "value": value}

    async def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """
        Take a safe snapshot copy of the current metric cache,
        removing expired entries.

        Returns:
            dict: A copy of the current URI -> {timestamp, value} mapping.
        """
        async with self._lock:
            now = datetime.utcnow()
            expired_uris = [
                uri
                for uri, info in self._cache.items()
                if now - info.get("timestamp", now) > self._ttl
            ]

            # Remove expired entries
            for uri in expired_uris:
                del self._cache[uri]

            return dict(self._cache)

    async def get_metric(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest metric for a specific URI if not expired.

        Args:
            uri (str): The URI to look up.

        Returns:
            dict | None: Metric data or None if expired or not found.
        """
        async with self._lock:
            now = datetime.utcnow()
            info = self._cache.get(uri)
            if info and (now - info.get("timestamp", now)) <= self._ttl:
                return info
            return None

    async def clear(self) -> None:
        """
        Clear the entire metric cache.
        """
        async with self._lock:
            self._cache.clear()
