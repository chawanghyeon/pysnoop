# apps/agents/collectors/uptime.py
import subprocess
from typing import Any, List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class UptimeCollector(BaseCollector):
    def collect(
        self,
    ) -> List[Tuple[str, Any]]:  # 반환 타입을 Any로 변경 또는 (str, str)
        try:
            output = subprocess.check_output(["uptime", "-p"], text=True, errors="ignore").strip()
            if output:
                # URI를 변경하고, 실제 output 문자열을 반환
                return [("system.uptime.description", output)]
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
