# apps/agents/collectors/uptime.py
import subprocess
from typing import List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class UptimeCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        try:
            # 'uptime -p' output: "up 2 weeks, 4 days, 13 hours, 25 minutes"
            # Consider parsing 'uptime' (no -p) for seconds for a more standard metric.
            # Example: `uptime_output = subprocess.check_output(["uptime"], text=True).strip()`
            # Then parse `uptime_output`. For now, keeping original logic but renaming metric.
            output = subprocess.check_output(["uptime", "-p"], text=True, errors="ignore").strip()
            if output:
                return [("system.uptime.description_length", float(len(output)))]
            return []
        except FileNotFoundError:
            print("[WARN][UptimeCollector] 'uptime' command not found.")
            return []
        except subprocess.CalledProcessError as e:
            print(f"[WARN][UptimeCollector] 'uptime' command failed: {e}")
            return []
        except Exception as e:
            print(f"[WARN][UptimeCollector] Unexpected error: {e}")
            return []
