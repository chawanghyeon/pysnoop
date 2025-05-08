import asyncio
import hashlib
import hmac
import json
import os
import signal
from datetime import datetime
from types import FrameType
from typing import Optional

from agents.collectors.base import collector_registry
from dotenv import load_dotenv

# ✅ Load .env
load_dotenv()

AGENT_HOST = os.environ.get("AGENT_HOST", "")
AGENT_PORT = int(os.environ.get("AGENT_PORT", "8888"))
AGENT_USER_ID = os.environ.get("AGENT_USER_ID", "")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")
AGENT_SECRET = os.environ.get("AGENT_SECRET", "")

# 필수값 검증
if not all([AGENT_HOST, AGENT_USER_ID, AGENT_TOKEN, AGENT_SECRET]):
    raise ValueError("AGENT_HOST, AGENT_USER_ID, AGENT_TOKEN, AGENT_SECRET must be set in .env")


def sign_message(secret: str, payload: str) -> str:
    """
    HMAC 서명을 생성하는 함수
    """
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


# 메트릭 전송 간격 (초)
INTERVAL: int = 10

# 종료 이벤트
shutdown_event = asyncio.Event()


def handle_exit(sig: int, frame: Optional[FrameType]) -> None:
    """
    SIGINT 또는 SIGTERM 시 graceful shutdown 처리
    """
    print("\n[INFO] Agent stopping...")
    shutdown_event.set()


# 종료 시그널 등록
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def send_collected_metrics() -> None:
    """
    서버에 연결하여 등록된 수집기로부터 메트릭을 수집 후 전송
    """
    ts: str = datetime.utcnow().isoformat() + "Z"

    try:
        reader, writer = await asyncio.open_connection(AGENT_HOST, AGENT_PORT)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    for CollectorClass in collector_registry:
        try:
            collector = CollectorClass()
            metrics = collector.collect()
            for uri, value in metrics:
                full_uri = f"/agent/{AGENT_USER_ID}/{uri}"
                message = {
                    "type": "metric",
                    "uri": full_uri,
                    "ts": ts,
                    "value": value,
                    "token": AGENT_TOKEN,
                }

                # HMAC 서명 추가
                payload_str = json.dumps(message, separators=(",", ":"), sort_keys=True)
                signature = sign_message(AGENT_SECRET, payload_str)
                message["signature"] = signature

                # 전송
                writer.write((json.dumps(message) + "\n").encode())
                await writer.drain()

                # 응답
                resp = await reader.readline()
                print(f"[SENT] {full_uri} = {value} [Response: {resp.decode().strip()}]")

        except Exception as e:
            print(f"[ERROR] {CollectorClass.__name__} failed: {e}")

    writer.close()
    await writer.wait_closed()


async def run_agent() -> None:
    """
    주기적으로 메트릭을 수집하고 서버로 전송하는 Agent 루프
    """
    while not shutdown_event.is_set():
        await send_collected_metrics()

        sleep_time = 0
        while sleep_time < INTERVAL:
            if shutdown_event.is_set():
                break
            await asyncio.sleep(1)
            sleep_time += 1


if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\n[INFO] Agent terminated by user.")
