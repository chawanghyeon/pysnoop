# collectors/dmesg_errors.py
import subprocess
from typing import List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class DmesgErrorCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        try:
            # dmesg 명령어는 종종 루트 권한이 필요합니다.
            # stderr=subprocess.DEVNULL 추가하여 stderr 출력을 화면에 표시하지 않도록 시도
            output = subprocess.check_output(
                ["sudo", "dmesg", "--level=err"],
                text=True,
                errors="ignore",
                stderr=subprocess.DEVNULL,  # <--- 이 부분을 추가합니다.
            )
            return [("kernel.dmesg.errors", float(len(output.splitlines())))]
        except FileNotFoundError:
            return [("kernel.dmesg.errors", -2.0)]
        except (
            subprocess.CalledProcessError
        ):  # stderr가 DEVNULL로 갔으므로 e.stderr은 비어있을 수 있습니다.
            return [("kernel.dmesg.errors", -1.0)]
        except Exception:
            return [("kernel.dmesg.errors", -3.0)]
