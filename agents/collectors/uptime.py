# agents/collectors/uptime.py
import subprocess

from .base import BaseCollector


class UptimeCollector(BaseCollector):
    def collect(self):
        try:
            output = subprocess.check_output(["uptime", "-p"], text=True).strip()
            return [("system.uptime.length", float(len(output)))]
        except Exception:
            return []
