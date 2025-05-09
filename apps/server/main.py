# apps/server/main.py
# flake8: noqa
import asyncio
import json
import os
import ssl
from datetime import datetime  # Ensure datetime is imported directly if used for type hints
from pathlib import Path

from server.auth.session import verify_hmac_signature, verify_token
from server.utils.gen_cert import generate_self_signed_cert
from server.utils.log_writer import LogWriter
from server.utils.memory_cache import MetricCache
from server.utils.message import MessageParseError, parse_message

# 서버 설정
HOST = os.environ.get("SERVER_HOST", "127.0.0.1")  # Make HOST configurable
PORT = int(os.environ.get("SERVER_PORT", "8888"))  # Make PORT configurable

# TLS 인증서 경로
CERT_PATH = Path(os.environ.get("SSL_CERT_PATH", "ssl/cert.pem"))
KEY_PATH = Path(os.environ.get("SSL_KEY_PATH", "ssl/key.pem"))

# 인스턴스 초기화
log_writer = LogWriter()
metric_cache = MetricCache()


def clear_screen():
    """Clears the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    클라이언트 연결을 처리하고, 수신된 메트릭을 파일과 메모리에 저장하는 비동기 함수
    """
    addr = writer.get_extra_info("peername")
    print(f"[CONNECTED] {addr}")
    log_writer.start()  # Ensure log writer is started if not already

    try:
        while True:
            try:
                data = await reader.readline()
            except ConnectionResetError:
                print(f"[INFO] Connection reset by {addr} while reading line.")
                break
            except asyncio.exceptions.IncompleteReadError:
                print(f"[INFO] Incomplete read from {addr}, client likely closed connection.")
                break

            if not data:
                print(f"[INFO] No data from {addr}, client closed connection.")
                break

            raw = data.decode().strip()
            if not raw:  # Skip empty lines if any sent
                continue

            try:
                msg_original = parse_message(raw)  # Contains signature
                msg_for_verification = msg_original.copy()  # Work on a copy for verification

                token = msg_for_verification.get("token")
                signature_from_msg = msg_for_verification.pop("signature", None)

                if not token or not signature_from_msg:
                    writer.write(b"ERROR: Missing token or signature\n")
                    await writer.drain()
                    continue

                user_id = verify_token(token)
                if not user_id:
                    writer.write(b"ERROR: Invalid or expired token\n")
                    await writer.drain()
                    continue

                # Payload for HMAC verification is the JSON of the message *without* the signature field
                payload_to_verify_str = json.dumps(
                    msg_for_verification, separators=(",", ":"), sort_keys=True
                )
                if not verify_hmac_signature(token, payload_to_verify_str, signature_from_msg):
                    writer.write(b"ERROR: Invalid signature\n")
                    await writer.drain()
                    continue

                # Use original parsed message (msg_original) for further processing
                # as msg_for_verification had signature popped.
                uri = msg_original["uri"]
                ts = msg_original["ts_datetime"]  # Use the datetime object from parse_message
                value = msg_original["value"]

                log_entry = {
                    "ts": ts.isoformat(),
                    "uri": uri,
                    "value": value,
                    "user_id": user_id,
                }
                await log_writer.append(log_entry)
                await metric_cache.update(uri, value, ts)

                print(f"[{user_id}] {uri} @ {ts.isoformat()} = {value}")
                writer.write(b"ACK\n")

            except MessageParseError as e:
                print(f"[WARN] Message parsing error from {addr}: {e}")
                writer.write(f"ERROR: {e}\n".encode())
            except Exception as e:
                print(f"[ERROR] Unexpected error processing message from {addr}: {e}")
                writer.write(b"ERROR: Internal server error\n")

            await writer.drain()

    except asyncio.exceptions.IncompleteReadError:
        print(f"[INFO] Client {addr} closed connection abruptly (incomplete read).")
    except ConnectionResetError:
        print(f"[INFO] Connection reset by peer {addr}")
    except Exception as e:
        print(f"[ERROR] Unhandled connection error from {addr}: {e}")
    finally:
        print(f"[DISCONNECTED] {addr}")
        if writer and not writer.is_closing():
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e_close:
                print(f"[ERROR] Error during writer close for {addr}: {e_close}")


async def dashboard_loop(shutdown_event: asyncio.Event):
    """
    주기적으로 메모리 캐시를 콘솔에 출력하는 대시보드 루프
    """
    try:
        while not shutdown_event.is_set():
            clear_screen()
            snapshot = await metric_cache.snapshot()

            print(f"--- Server Dashboard ({datetime.now().isoformat()}) ---")
            print(f"{'URI':60} | {'VALUE':>10} | {'TIMESTAMP'}")
            print("-" * 90)

            sorted_snapshot = sorted(snapshot.items())

            for uri, info in sorted_snapshot:
                value = info.get("value", "N/A")
                ts_obj = info.get("timestamp")
                ts_str = ts_obj.isoformat() if isinstance(ts_obj, datetime) else str(ts_obj)
                print(f"{uri:60} | {str(value):>10} | {ts_str}")

            print("-" * 90)
            print(f"Total cached metrics: {len(snapshot)}")

            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass  # Normal loop for sleep
    except asyncio.CancelledError:
        print("[INFO] Dashboard loop cancelled.")
    except Exception as e:
        print(f"[ERROR] Dashboard loop crashed: {e}")


async def run_server():
    """
    TLS 기반 TCP 서버 + 대시보드 + 로그 저장기 실행
    """
    # Determine hostname for certificate generation
    # If HOST is '0.0.0.0' or '127.0.0.1', use 'localhost' for cert.
    # Otherwise, use the specified HOST.
    cert_hostname = "localhost" if HOST in ("127.0.0.1", "0.0.0.0") else HOST
    if not CERT_PATH.exists() or not KEY_PATH.exists():
        print(
            f"[TLS] Certificates ({CERT_PATH}, {KEY_PATH}) not found. Generating self-signed certificate for hostname: '{cert_hostname}'"
        )
        try:
            generate_self_signed_cert(str(CERT_PATH), str(KEY_PATH), hostname=cert_hostname)
        except Exception as e_cert:
            print(f"[ERROR] Failed to generate self-signed certificate: {e_cert}")
            return

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    try:
        ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
    except FileNotFoundError:
        print(f"[ERROR] SSL certificate or key file not found. Searched: {CERT_PATH}, {KEY_PATH}")
        return
    except ssl.SSLError as e:
        print(
            f"[ERROR] SSL error loading certificate chain: {e}. Ensure certificate and key are valid and match."
        )
        return

    # log_writer.start() # Moved to handle_client to start on first connection, or start here if always needed.
    # Starting it here is fine as well, ensures it's running before first client.
    log_writer.start()

    server = None
    shutdown_event = asyncio.Event()  # Event for coordinating shutdown

    try:
        server = await asyncio.start_server(handle_client, HOST, PORT, ssl=ssl_context)
        addr = server.sockets[0].getsockname()
        print(f"[SECURE SERVER] Serving on {addr} (TLS enabled for hostname: '{cert_hostname}')")

        dashboard_task = asyncio.create_task(dashboard_loop(shutdown_event))

        # Keep server running until explicitly stopped or an error
        await server.serve_forever()

    except OSError as e:
        print(f"[ERROR] Could not start server on {HOST}:{PORT}: {e} (Port already in use?)")
    except asyncio.CancelledError:
        print("[INFO] Server task cancelled.")  # Should be part of graceful shutdown
    except Exception as e:
        print(f"[ERROR] Unexpected error in run_server: {e}")
    finally:
        print("[SERVER] Initiating shutdown sequence...")
        shutdown_event.set()  # Signal dashboard and other tasks to stop

        if "dashboard_task" in locals() and not dashboard_task.done():
            try:
                await asyncio.wait_for(dashboard_task, timeout=5)  # Give dashboard time to finish
            except asyncio.TimeoutError:
                print("[WARN] Dashboard task did not finish in time, cancelling.")
                dashboard_task.cancel()
            except asyncio.CancelledError:
                print("[INFO] Dashboard task was cancelled.")  # Expected if cancelled by timeout
            except Exception as e_dash_fin:
                print(f"[ERROR] Exception during dashboard task finalization: {e_dash_fin}")

        if server:
            server.close()
            try:
                await server.wait_closed()
                print("[INFO] Server has been closed.")
            except Exception as e_server_close:
                print(f"[ERROR] Error during server.wait_closed(): {e_server_close}")

        # Ensure log writer queue is processed (optional, depends on how critical pending logs are)
        if log_writer.task and not log_writer.queue.empty():
            print(f"[INFO] Waiting for log writer to flush {log_writer.queue.qsize()} items...")
            try:
                await asyncio.wait_for(log_writer.queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                print("[WARN] Log writer did not flush all items in time.")
            except Exception as e_log_join:
                print(f"[ERROR] Error waiting for log queue to join: {e_log_join}")

        print("[SERVER] Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n[INFO] Server process interrupted by user (KeyboardInterrupt).")
    finally:
        print("[INFO] Main execution finished.")
