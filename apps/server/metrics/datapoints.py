# apps/server/metrics/datapoints.py
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# LogWriter와 동일한 로그 디렉토리 구조를 가정합니다.
# LogWriter의 기본 로그 디렉토리는 프로젝트 루트의 'logs' 폴더입니다.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = _PROJECT_ROOT / "logs"


def get_log_path_for_date(dt: datetime) -> Path:
    """지정된 날짜에 해당하는 로그 파일 경로를 반환합니다."""
    date_str = dt.strftime("%Y%m%d")
    return LOG_DIR / f"metrics-{date_str}.jsonl"


def init_db():
    """
    데이터베이스 초기화 (여기서는 로그 디렉토리 존재 여부 확인 정도로 단순화).
    실제 DB를 사용한다면 여기서 연결 및 테이블 생성을 수행합니다.
    """
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO][datapoints] Log directory initialized/checked: {LOG_DIR}")


def _parse_log_entry(line: str) -> Optional[Dict[str, Any]]:
    """JSONL 로그 라인을 파싱하고 datetime 객체로 변환합니다."""
    try:
        entry = json.loads(line)
        # 'ts' 필드를 datetime 객체로 변환
        if "ts" in entry and isinstance(entry["ts"], str):
            # ISO 형식을 UTC로 파싱
            dt_obj = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
            # 만약 timezone 정보가 없다면 UTC로 가정
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            entry["ts_datetime"] = dt_obj
        return entry
    except json.JSONDecodeError:
        return None
    except Exception:  # 날짜 변환 오류 등
        return None


def get_all_entries_from_log(log_file: Path) -> List[Dict[str, Any]]:
    """지정된 로그 파일에서 모든 유효한 항목을 읽어옵니다."""
    entries: list[Any] = []
    if not log_file.exists():
        return entries
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_log_entry(line)
            if parsed:
                entries.append(parsed)
    return entries


def get(uri: str, date_str: Optional[str] = None) -> List[Tuple[datetime, float]]:
    """
    지정된 URI에 대한 모든 데이터 포인트를 반환합니다.
    date_str (YYYYMMDD)이 제공되면 해당 날짜의 로그만 조회, 아니면 오늘 날짜의 로그를 조회합니다.
    """
    values: List[Tuple[datetime, float]] = []
    target_date = datetime.now(timezone.utc)
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"[WARN][datapoints] Invalid date format: {date_str}. Using today.")

    log_file_path = get_log_path_for_date(target_date)

    if not log_file_path.exists():
        print(
            f"[INFO][datapoints] Log file not found for date {target_date.strftime('%Y%m%d')}: {log_file_path}"  # noqa
        )
        return values

    print(f"[INFO][datapoints] Querying URI '{uri}' from log file: {log_file_path}")
    all_entries = get_all_entries_from_log(log_file_path)

    for entry in all_entries:
        if (
            entry.get("uri") == uri
            and "ts_datetime" in entry
            and isinstance(entry.get("value"), (int, float))
        ):
            values.append((entry["ts_datetime"], float(entry["value"])))

    # 시간 순으로 정렬 (오래된 것이 먼저)
    values.sort(key=lambda x: x[0])
    print(f"[INFO][datapoints] Found {len(values)} entries for URI '{uri}' in {log_file_path}")
    return values


def get_latest(uri: str, date_str: Optional[str] = None) -> Optional[Tuple[datetime, float]]:
    """
    지정된 URI에 대한 최신 데이터 포인트를 반환합니다.
    """
    all_values = get(uri, date_str)
    if not all_values:
        return None
    return all_values[-1]  # 정렬되어 있으므로 마지막 항목이 최신


# query_cli.py 에서 사용하는 함수들을 위해 datapoints.py에 있어야 합니다.
# ascii_plot.py는 별도로 query_cli.py 에서 import 하고 있으므로 여기서는 불필요합니다.

if __name__ == "__main__":
    # 테스트용 코드
    init_db()
    print("Testing datapoints.py module...")
    # 테스트를 위해서는 실제 로그 파일이 필요합니다.
    # 예시: 오늘 날짜의 로그 파일에 있는 /agent/user-1/system.cpu.core0 에 대한 데이터 조회
    # today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    # test_uri = "/agent/user-1/system.cpu.core0"

    # print(f"\nGetting all data for URI: {test_uri} (today)")
    # data = get(test_uri)
    # if data:
    #     for ts, val in data:
    #         print(f"  {ts.isoformat()} -> {val}")
    # else:
    #     print("  No data found.")

    # print(f"\nGetting latest data for URI: {test_uri} (today)")
    # latest_data = get_latest(test_uri)
    # if latest_data:
    #     ts, val = latest_data
    #     print(f"  {ts.isoformat()} -> {val}")
    # else:
    #     print("  No latest data found.")
    pass
