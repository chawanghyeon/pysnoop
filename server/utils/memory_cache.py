# server/utils/memory_cache.py

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional


class MetricCache:
    """
    MetricCache stores the latest value and timestamp for each URI.
    Provides thread-safe updates and snapshot views for real-time dashboards.
    """

    def __init__(self) -> None:
        """
        Initialize an empty metric cache with asyncio lock.
        """
        self._cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock: asyncio.Lock = asyncio.Lock()

    async def update(self, uri: str, value: Any, ts: datetime) -> None:
        """
        Update the cache with a new metric value for a specific URI.

        Args:
            uri (str): The URI path (e.g., "host1/cpu/usage").
            value (Any): The metric value (e.g., 25.3).
            ts (datetime): Timestamp when the metric was collected.
        """
        async with self._lock:
            self._cache[uri] = {"timestamp": ts, "value": value}

    async def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """
        Take a safe snapshot copy of the current metric cache.

        Returns:
            dict: A copy of the current URI -> {timestamp, value} mapping.
        """
        async with self._lock:
            return dict(self._cache)

    async def get_metric(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest metric for a specific URI.

        Args:
            uri (str): The URI to look up.

        Returns:
            dict | None: The metric data or None if not found.
        """
        async with self._lock:
            return self._cache.get(uri)

    async def clear(self) -> None:
        """
        Clear the entire metric cache (useful for testing or resets).
        """
        async with self._lock:
            self._cache.clear()
