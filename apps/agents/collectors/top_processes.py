# agents/collectors/top_processes.py
from typing import List, Tuple

import psutil

from .base import BaseCollector


class TopProcessCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        procs = sorted(
            psutil.process_iter(attrs=["pid", "name", "cpu_percent"]),
            key=lambda p: p.info["cpu_percent"],
            reverse=True,
        )
        return [
            (f"top.cpu.{p.info['pid']}_{p.info['name']}", p.info["cpu_percent"]) for p in procs[:5]
        ]
