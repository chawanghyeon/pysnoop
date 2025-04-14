# core/metrics/datapoints.py
from collections import defaultdict
from datetime import datetime
from typing import List, Tuple


class MetricStorage:
    def __init__(self):
        # key: URI 문자열, value: list of (timestamp, value)
        self._store = defaultdict(list)

    def insert(self, uri: str, ts: datetime, value: float):
        self._store[uri].append((ts, value))

    def get(self, uri: str) -> List[Tuple[datetime, float]]:
        return self._store.get(uri, [])

    def get_latest(self, uri: str) -> Tuple[datetime, float] | None:
        if self._store[uri]:
            return self._store[uri][-1]
        return None
