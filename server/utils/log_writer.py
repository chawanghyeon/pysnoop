# server/utils/log_writer.py

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class LogWriter:
    """
    비동기 큐를 기반으로 로그 데이터를 .jsonl 파일로 저장하는 클래스.

    로그는 프로젝트 루트의 logs 디렉토리에 날짜별로 저장되며,
    append() 메서드로 큐에 저장 요청을 보내고, 내부적으로 write loop에서 처리된다.
    """

    def __init__(self, log_dir: Path | None = None):
        """
        로그 저장 디렉토리를 초기화하고 큐를 생성한다.

        Args:
            log_dir (Path | None): 로그 파일이 저장될 디렉토리 (기본값: 프로젝트 루트/logs)
        """
        # 로그 파일을 저장할 디렉토리 설정 (기본: 프로젝트 루트의 logs 폴더)
        if log_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent  # 프로젝트 루트 계산
            log_dir = base_dir / "logs"

        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)  # 디렉토리 없으면 생성
        self.queue: asyncio.Queue = asyncio.Queue()  # 로그 저장 요청을 담는 비동기 큐
        self.task = None  # 백그라운드 쓰기 태스크 (한 번만 실행됨)

    def get_log_path(self) -> str:
        """
        오늘 날짜 기준의 로그 파일 경로를 생성한다.

        Returns:
            str: 날짜별 로그 파일의 전체 경로 (e.g., logs/metrics-20250422.jsonl)
        """
        date_str = datetime.now().strftime("%Y%m%d")
        return str(self.log_dir / f"metrics-{date_str}.jsonl")

    async def append(self, entry: Dict):
        """
        로그 entry를 큐에 추가한다.

        Args:
            entry (Dict): 저장할 로그 데이터 (예: {"ts": ..., "uri": ..., "value": ..., "user_id": ...})
        """
        await self.queue.put(entry)

    async def _write_loop(self):
        """
        내부적으로 실행되는 백그라운드 루프.
        큐에서 로그 요청을 받아 파일에 순차적으로 저장한다.
        """
        while True:
            entry = await self.queue.get()
            try:
                with open(self.get_log_path(), "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                # 파일 저장 중 예외 발생 시 콘솔에 출력
                print(f"[LOG ERROR] Failed to write log: {e}")
            finally:
                self.queue.task_done()  # 큐 작업 완료 처리

    def start(self):
        """
        로그 쓰기 루프를 백그라운드 태스크로 실행한다.
        중복 실행되지 않도록 첫 호출 시에만 태스크를 시작한다.
        """
        if not self.task:
            self.task = asyncio.create_task(self._write_loop())
