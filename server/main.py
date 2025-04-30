import argparse
import asyncio
import json
import os
import ssl
from datetime import datetime
from pathlib import Path

from server.auth.session import verify_hmac_signature, verify_token
from server.utils.gen_cert import generate_self_signed_cert
from server.utils.log_writer import LogWriter
from server.utils.memory_cache import MetricCache
from server.utils.message import MessageParseError, parse_message

# 서버 설정
HOST = "127.0.0.1"
PORT = 8888

# TLS 인증서 경로
CERT_PATH = Path("ssl/cert.pem")
KEY_PATH = Path("ssl/key.pem")

# 인스턴스 초기화
log_writer = LogWriter()
metric_cache = MetricCache()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    클라이언트 연결을 처리하고, 수신된 메트릭을 파일과 메모리에 저장하는 비동기 함수
    """
    addr = writer.get_extra_info("peername")
    print(f"[CONNECTED] {addr}")

    try:
        while True:
            data = await reader.readline()
            if not data:
                break

            raw = data.decode().strip()
            try:
                msg = parse_message(raw)
                token = msg.get("token")
                signature = msg.pop("signature", None)

                if not token or not signature:
                    writer.write(b"ERROR: Missing token or signature\n")
                    await writer.drain()
                    continue

                # 토큰 유효성 검증
                user_id = verify_token(token)
                if not user_id:
                    writer.write(b"ERROR: Invalid or expired token\n")
                    await writer.drain()
                    continue

                # HMAC 서명 검증
                raw_payload = json.dumps(msg, separators=(",", ":"), sort_keys=True)
                if not verify_hmac_signature(token, raw_payload, signature):
                    writer.write(b"ERROR: Invalid signature\n")
                    await writer.drain()
                    continue

                # 파싱된 메트릭 정보 처리
                uri = msg["uri"]
                ts = datetime.fromisoformat(msg["ts"].replace("Z", "+00:00"))
                value = msg["value"]

                # 로그 파일 기록
                await log_writer.append({"ts": ts, "uri": uri, "value": value, "user_id": user_id})

                # 메모리 캐시 업데이트
                await metric_cache.update(uri, value, ts)

                print(f"[{user_id}] {uri} @ {ts} = {value}")
                writer.write(b"ACK\n")

            except MessageParseError as e:
                writer.write(f"ERROR: {e}\n".encode())

            await writer.drain()

    except Exception as e:
        print(f"[ERROR] Connection error from {addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def dashboard_loop():
    """
    주기적으로 메모리 캐시를 콘솔에 출력하는 대시보드 루프
    """
    while True:
        os.system("clear")  # Windows는 "cls"
        snapshot = await metric_cache.snapshot()

        print(f"{'URI':60} | {'VALUE':>10} | {'TIMESTAMP'}")
        print("-" * 90)

        for uri, info in snapshot.items():
            value = info.get("value")
            ts = info.get("timestamp")
            print(f"{uri:60} | {value:10} | {ts}")

        await asyncio.sleep(2)


async def run_server():
    """
    TLS 기반 TCP 서버 + 대시보드 + 로그 저장기 실행
    """
    if not CERT_PATH.exists() or not KEY_PATH.exists():
        print("[TLS] 인증서가 없어 자동 생성합니다.")
        generate_self_signed_cert(CERT_PATH, KEY_PATH)

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=str(CERT_PATH), keyfile=str(KEY_PATH))

    log_writer.start()

    server = await asyncio.start_server(handle_client, HOST, PORT, ssl=ssl_context)
    addr = server.sockets[0].getsockname()
    print(f"[SECURE SERVER] Serving on {addr} (TLS enabled)")

    # 서버와 대시보드를 각각 Task로 실행
    server_task = asyncio.create_task(server.serve_forever())
    dashboard_task = asyncio.create_task(dashboard_loop())

    try:
        await asyncio.gather(server_task, dashboard_task)
    except asyncio.CancelledError:
        print("[SERVER] Shutdown requested, cleaning up...")
    finally:
        server.close()
        await server.wait_closed()
        dashboard_task.cancel()
        try:
            await dashboard_task
        except asyncio.CancelledError:
            pass
        print("[SERVER] Clean shutdown complete.")


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description="pysnoop main entry")
    parser.add_argument(
        "--mode",
        choices=["server", "agent"],
        required=True,
        help="Which mode to run: server or agent",
    )
    return parser.parse_known_args()
