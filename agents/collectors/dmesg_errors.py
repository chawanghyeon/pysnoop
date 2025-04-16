# agents/collectors/dmesg_errors.py
import subprocess
from .base import BaseCollector


class DmesgErrorCollector(BaseCollector):
    def collect(self):
        try:
            output = subprocess.check_output(["dmesg", "--level=err"], text=True)
            return [("kernel.dmesg.errors", float(len(output.splitlines())))]
        except:
            return []
