# apps/collectors/top_processes.py (수정됨)
from typing import Any, Dict, List  # Tuple 대신 Dict, Any 임포트

import psutil

from .base import BaseCollector, register_collector


@register_collector
class TopProcessCollector(BaseCollector):
    # 반환 타입을 List[Dict[str, Any]]로 변경
    def collect(self) -> List[Dict[str, Any]]:
        procs_data: List[Dict[str, Any]] = []  # 타입 명시
        try:
            pids = psutil.pids()
            for pid_val in pids:
                try:
                    p = psutil.Process(pid_val)
                    # 필요한 속성들을 한 번에 가져옵니다.
                    with p.oneshot():
                        p_info_dict = p.as_dict(
                            attrs=["pid", "name", "cpu_percent", "memory_percent"]
                        )

                    # cpu_percent가 None인 프로세스(예: 커널 작업, 방금 생성된 프로세스)는 제외합니다.
                    if p_info_dict.get("cpu_percent") is None:
                        continue
                    procs_data.append(p_info_dict)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue  # 프로세스가 죽었거나 접근이 제한된 경우
                except Exception as e_proc:
                    print(f"[DEBUG][TopProcessCollector] PID {pid_val} 처리 중 오류: {e_proc}")
                    pass  # 개별 프로세스 오류는 건너뜁니다.

            # CPU 사용량 기준으로 정렬합니다.
            sorted_procs = sorted(
                procs_data,
                key=lambda p_info_item: p_info_item.get("cpu_percent", 0.0) or 0.0,
                reverse=True,
            )

            # 상위 10개 프로세스 정보를 반환합니다 (TopProcessesWidget에서 10개를 사용).
            return sorted_procs[:10]

        except Exception as e:
            print(f"[WARN][TopProcessCollector] 상위 프로세스 수집 실패: {e}")
            return []
