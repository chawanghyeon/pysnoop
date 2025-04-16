# agents/collectors/syslog_lines.py
import os, subprocess
from .base import BaseCollector


class SyslogLineLengthCollector(BaseCollector):
    def collect(self):
        log_path = "/var/log/syslog"
        metrics = []
        if os.path.exists(log_path):
            try:
                lines = subprocess.check_output(
                    ["tail", "-n10", log_path], text=True
                ).splitlines()
                for i, line in enumerate(lines):
                    metrics.append((f"log.syslog.line{i}.length", float(len(line))))
            except:
                pass
        return metrics
