# collectors/uptime.py
import re  # 정규표현식을 사용한 파싱을 위해 추가
import subprocess
from typing import Any, List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class UptimeCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, Any]]:
        try:
            # '-p' 옵션 없이 'uptime' 명령어 실행
            output = subprocess.check_output(["uptime"], text=True, errors="ignore").strip()

            # uptime 명령어 출력 예시:
            # "10:23:45 up 5 days,  1:22,  2 users,  load average: 0.00, 0.01, 0.05"
            # "10:23:45 up 10 min,  2 users,  load average: 0.00, 0.01, 0.05"
            # "10:23:45 up  1:22,  2 users,  load average: 0.00, 0.01, 0.05" (날짜 정보 없음)

            if "up " in output:
                # "up " 이후의 문자열 추출
                uptime_info_part = output.split("up ", 1)[1].strip()

                # "user" 또는 "users" 앞부분, 혹은 "load average" 앞부분까지 추출 (가동 시간 부분)
                # 정규표현식을 사용하여 더 정확하게 가동 시간 부분을 추출합니다.
                match = re.search(r"(.*?)(?:,\s*\d+\s*users?|,?\s*load average:)", uptime_info_part)
                if match:
                    parsed_uptime = match.group(1).strip().rstrip(",")  # 마지막 쉼표 제거
                    return [("system.uptime.description", f"Up {parsed_uptime}")]
                else:
                    # 정규표현식 매칭 실패 시, 단순 분할로 일부 정보 반환 (예: "5 days" 또는 "10 min")
                    # 또는 전체 uptime_info_part 반환도 고려 가능
                    first_segment = uptime_info_part.split(",")[0].strip()
                    return [("system.uptime.description", f"Up {first_segment}")]

            elif (
                output
            ):  # "up " 문자열이 없더라도 출력이 있다면 그대로 반환 (예상치 못한 형식 대비)
                return [("system.uptime.description", output)]

            return []  # 의미있는 출력이 없는 경우

        except FileNotFoundError:
            return [("system.uptime.description", "Uptime: 'uptime' 명령어 없음")]
        except subprocess.CalledProcessError as e:
            error_message = "Uptime: 명령어 실행 실패"
            # 실제 오류 메시지(stderr)가 있다면 추가 (너무 길지 않게)
            if e.stderr and len(e.stderr) < 100:  # 너무 긴 오류 메시지 방지
                error_message += f" ({e.stderr.strip()})"
            elif e.output and len(e.output) < 100:
                error_message += f" ({e.output.strip()})"
            return [("system.uptime.description", error_message)]
        except Exception as exc:  # 다른 예기치 않은 오류
            # print(f"[WARN][UptimeCollector] Unexpected error: {exc}") # 직접 print 대신
            return [
                (
                    "system.uptime.description",
                    f"Uptime: 알 수 없는 오류 ({type(exc).__name__})",
                )
            ]
