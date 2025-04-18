# agents/collectors/psutil_metrics.py
from typing import List, Tuple

import psutil

from .base import BaseCollector, register_collector


@register_collector
class PsutilMetricsCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        data = []
        for i, usage in enumerate(psutil.cpu_percent(percpu=True)):
            data.append((f"system.cpu.core{i}", usage))
        mem = psutil.virtual_memory()
        data.append(("system.memory.used_percent", mem.percent))
        return data
