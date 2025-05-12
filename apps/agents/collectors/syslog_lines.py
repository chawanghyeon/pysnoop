# agents/collectors/syslog_lines.py
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class SyslogLineLengthCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        # Common log paths, agent might need configuration for this
        log_paths_to_try = ["/var/log/syslog", "/var/log/messages"]
        log_path_found = None

        for p in log_paths_to_try:
            if os.path.exists(p) and os.access(p, os.R_OK):
                log_path_found = p
                break

        if not log_path_found:
            # print("[DEBUG][SyslogCollector] No accessible syslog file found.")
            return []

        metrics = []
        try:
            # Using 'tail -n10'. Ensure agent has permissions.
            # errors='ignore' to prevent issues with non-UTF8 characters in logs if any.
            process = subprocess.run(
                ["tail", "-n10", log_path_found],
                capture_output=True,
                text=True,
                check=False,
                errors="ignore",
            )
            if process.returncode != 0:
                # tail can return non-zero if file is smaller than N lines, but still output content.  # noqa
                # However, if stderr has content, it's likely a more serious error.
                if process.stderr:
                    print(
                        f"[WARN][SyslogCollector] 'tail' command for {log_path_found} reported errors: {process.stderr.strip()}"  # noqa
                    )
                # If there's output despite non-zero return, process it. Otherwise, return empty.
                if not process.stdout:
                    return []

            lines = process.stdout.strip().splitlines()
            for i, line in enumerate(lines):
                metrics.append(
                    (
                        f"log.system.{Path(log_path_found).name}.line{i}.length",
                        float(len(line)),
                    )
                )
        except FileNotFoundError:
            print("[WARN][SyslogCollector] 'tail' command not found.")
        except Exception as e:
            print(f"[WARN][SyslogCollector] Error processing {log_path_found}: {e}")
        return metrics
