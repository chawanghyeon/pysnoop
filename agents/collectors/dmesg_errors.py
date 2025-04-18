# agents/collectors/dmesg_errors.py
import subprocess
from typing import List, Tuple

from .base import BaseCollector


class DmesgErrorCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        try:
            output = subprocess.check_output(["dmesg", "--level=err"], text=True)
            return [("kernel.dmesg.errors", float(len(output.splitlines())))]
        except Exception:
            return []
