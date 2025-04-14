# core/utils/message.py
import json
from datetime import datetime


class MessageParseError(Exception):
    pass


def parse_message(raw_line: str) -> dict:
    try:
        msg = json.loads(raw_line)
        # 필수 필드 확인
        if not all(k in msg for k in ("type", "uri", "ts", "value")):
            raise MessageParseError("Missing required fields")
        # 타입 확인
        if not isinstance(msg["value"], (int, float)):
            raise MessageParseError("Value must be numeric")
        # 타임스탬프 검증
        datetime.fromisoformat(msg["ts"].replace("Z", "+00:00"))
        return msg
    except (json.JSONDecodeError, ValueError) as e:
        raise MessageParseError(f"Invalid message: {e}")
