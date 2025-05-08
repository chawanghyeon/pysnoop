# agents/collectors/uptime.py
import subprocess
from typing import List, Tuple

from .base import BaseCollector


class UptimeCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        try:
            output = subprocess.check_output(["uptime", "-p"], text=True).strip()
            return [("system.uptime.length", float(len(output)))]
        except Exception:
            return []
