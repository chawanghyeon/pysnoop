# agents/collectors/dmesg_errors.py
import subprocess
from typing import List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class DmesgErrorCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        try:
            # dmesg often requires root/sudo privileges.
            output = subprocess.check_output(["dmesg", "--level=err"], text=True, errors="ignore")
            return [("kernel.dmesg.errors", float(len(output.splitlines())))]
        except FileNotFoundError:
            print("[WARN][DmesgErrorCollector] 'dmesg' command not found.")
            return []
        except subprocess.CalledProcessError as e:
            # This might indicate permission issues or no errors found if dmesg returns non-zero.
            # Some dmesg versions might return non-zero if no messages of the given level exist.
            # Check e.returncode and e.output if necessary. For now, assume it's an error.
            print(
                f"[WARN][DmesgErrorCollector] 'dmesg' command failed (permissions? or no messages?): {e.returncode} {e.stderr or e.output}"  # noqa
            )
            return []
        except Exception as e:
            print(f"[WARN][DmesgErrorCollector] Unexpected error: {e}")
            return []
