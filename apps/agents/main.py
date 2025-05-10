# apps/agents/main.py
import asyncio
import hashlib
import hmac
import json
import os
import signal
import ssl
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import List, Optional, Tuple

from agents.collectors.base import collector_registry
from dotenv import load_dotenv

# Load .env
load_dotenv()

AGENT_HOST = os.environ.get("AGENT_HOST", "localhost")
AGENT_PORT = int(os.environ.get("AGENT_PORT", "8888"))
AGENT_USER_ID = os.environ.get("AGENT_USER_ID", "")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")
AGENT_SECRET = os.environ.get("AGENT_SECRET", "")
AGENT_INTERVAL = int(os.environ.get("AGENT_INTERVAL", "10"))

# Server certificate handling
DEFAULT_CERT_FILENAME = "server_cert.pem"
_AGENT_DIR = Path(__file__).resolve().parent
SERVER_CERT_PATH_STR = os.environ.get("SERVER_CERT_PATH")

# Mypy Fix: SERVER_CERT_PATH can be Path or None
SERVER_CERT_PATH: Optional[Path] = None

if SERVER_CERT_PATH_STR:
    SERVER_CERT_PATH = Path(SERVER_CERT_PATH_STR)
else:
    search_paths = [
        _AGENT_DIR / DEFAULT_CERT_FILENAME,
        _AGENT_DIR / "ssl" / DEFAULT_CERT_FILENAME,
        Path.cwd() / DEFAULT_CERT_FILENAME,
        Path.cwd() / "ssl" / DEFAULT_CERT_FILENAME,
    ]
    # Mypy is happy now as SERVER_CERT_PATH is Optional[Path]
    SERVER_CERT_PATH = next((p for p in search_paths if p.exists()), None)


AGENT_ALLOW_INSECURE_SSL = os.environ.get("AGENT_ALLOW_INSECURE_SSL", "false").lower() == "true"


if not all([AGENT_USER_ID, AGENT_TOKEN, AGENT_SECRET]):
    raise ValueError(
        "CRITICAL: AGENT_USER_ID, AGENT_TOKEN, or AGENT_SECRET is not "
        "configured. Please set them in .env or environment variables."
    )


def sign_message(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


shutdown_event = asyncio.Event()


def handle_exit(sig: int, frame: Optional[FrameType]) -> None:
    # Flake8 F541 fix: Regular string
    print(f"\n[INFO] Signal {sig} received. Agent stopping...")
    shutdown_event.set()


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def send_collected_metrics() -> None:
    ts_batch_start: str = datetime.utcnow().isoformat() + "Z"
    reader = None
    writer = None

    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        server_hostname_for_ssl = AGENT_HOST

        if SERVER_CERT_PATH and SERVER_CERT_PATH.exists():
            try:
                ssl_context.load_verify_locations(cafile=str(SERVER_CERT_PATH))
                # Flake8 E501 fix: Shorten line
                print(f"[INFO] Using server certificate for verification: " f"{SERVER_CERT_PATH}")
            except ssl.SSLError as e:
                # Flake8 E501 fix: Shorten line
                print(
                    f"[ERROR] Failed to load server certificate from " f"{SERVER_CERT_PATH}: {e}."
                )
                if not AGENT_ALLOW_INSECURE_SSL:
                    # Flake8 F541 fix: Regular string
                    # Flake8 E501 fix: Shorten line
                    print(
                        "[ERROR] Secure connection impossible. Set "
                        "AGENT_ALLOW_INSECURE_SSL=true to proceed "
                        "insecurely (NOT RECOMMENDED)."
                    )
                    return
                # Flake8 F541 fix: Regular string
                # Flake8 E501 fix: Shorten line
                print(
                    "[WARN] Proceeding with insecure SSL context "
                    "(no verify, no hostname check) due to cert load error."
                )
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        elif AGENT_ALLOW_INSECURE_SSL:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            # Flake8 E501 fix: Shorten line
            print(
                "[WARN] Server certificate not found or specified. "
                "AGENT_ALLOW_INSECURE_SSL is true. Using insecure SSL "
                "context."
            )
        else:
            # Flake8 E501 fix: Shorten line
            cert_path_info = str(SERVER_CERT_PATH) if SERVER_CERT_PATH else "various locations"
            print(
                "[ERROR] Server certificate not found or specified "
                f"(tried {cert_path_info}). Secure connection cannot be "
                "established. Set SERVER_CERT_PATH or "
                "AGENT_ALLOW_INSECURE_SSL=true (NOT RECOMMENDED)."
            )
            return

        # Flake8 E501 fix: Shorten line
        print(
            f"[INFO] Attempting to connect to {AGENT_HOST}:{AGENT_PORT} "
            f"(SSL server_hostname: '{server_hostname_for_ssl}')"
        )
        reader, writer = await asyncio.open_connection(
            AGENT_HOST,
            AGENT_PORT,
            ssl=ssl_context,
            server_hostname=(
                server_hostname_for_ssl if ssl_context.verify_mode != ssl.CERT_NONE else None
            ),
        )
        print(f"[INFO] Successfully connected to server " f"{AGENT_HOST}:{AGENT_PORT}")

    except ssl.SSLCertVerificationError as e:
        # Flake8 E501 fix: Shorten line
        cert_path_display = str(SERVER_CERT_PATH) if SERVER_CERT_PATH else "configured path"
        print(
            f"[ERROR] SSL Certificate Verification Error: {e}. "
            f"Ensure AGENT_HOST ('{AGENT_HOST}') matches the "
            f"certificate's hostname and the cert at "
            f"'{cert_path_display}' is correct for the server."
        )
        return
    except ConnectionRefusedError:
        # Flake8 E501 fix: Shorten line
        print(
            f"[ERROR] Connection refused by server {AGENT_HOST}:{AGENT_PORT}. "
            f"Is the server running and accessible?"
        )
        return
    except Exception as e:
        print(f"[ERROR] Connection failed to {AGENT_HOST}:{AGENT_PORT}: {e}")
        return

    active_collectors = [CollectorClass() for CollectorClass in collector_registry]
    metrics_collected_this_run: List[Tuple[str, float]] = []

    for collector_instance in active_collectors:
        collector_name = type(collector_instance).__name__
        try:
            current_metrics = collector_instance.collect()
            if current_metrics:
                metrics_collected_this_run.extend(current_metrics)
        except Exception as e_coll:
            print(f"[ERROR] Collector {collector_name} " f"failed during .collect(): {e_coll}")

    if not metrics_collected_this_run:
        # Flake8 F541 fix: Regular string
        print("[INFO] No metrics collected in this interval.")

    for uri_suffix, value in metrics_collected_this_run:
        if shutdown_event.is_set():
            # Flake8 F541 fix: Regular string
            print("[INFO] Shutdown initiated, stopping metric send.")
            break
        try:
            if not isinstance(value, (int, float)):
                # Flake8 E501 fix: Shorten line
                print(
                    f"[WARN] Metric value for URI suffix '{uri_suffix}' "
                    f"is not a number: {value} (type: {type(value)}). "
                    f"Skipping."
                )
                continue

            full_uri = f"/agent/{AGENT_USER_ID}/{uri_suffix}"
            message_to_sign = {
                "type": "metric",
                "uri": full_uri,
                "ts": ts_batch_start,
                "value": value,
                "token": AGENT_TOKEN,
            }

            payload_str = json.dumps(message_to_sign, separators=(",", ":"), sort_keys=True)
            signature = sign_message(AGENT_SECRET, payload_str)

            message_to_send = message_to_sign.copy()
            message_to_send["signature"] = signature

            writer.write((json.dumps(message_to_send) + "\n").encode())
            await writer.drain()

            resp_data = await reader.readline()
            response = resp_data.decode().strip()

            if response != "ACK":
                print(f"[ERROR] Server did not ACK metric {full_uri}. " f"Response: {response}")
            else:
                print(f"[SENT] {full_uri} = {value} [Response: {response}]")

        except ConnectionError as e_conn_send:
            # Flake8 E501 fix: Shorten line
            print(
                f"[ERROR] Connection error during metric send for "
                f"'{uri_suffix}': {e_conn_send}. Aborting current batch."
            )
            break
        except Exception as e_send:
            print(f"[ERROR] Failed to send metric for " f"'{uri_suffix}': {e_send}")

    if writer and not writer.is_closing():
        # Flake8 F541 fix: Regular string
        print("[INFO] Closing connection to server.")
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e_close:
            print(f"[ERROR] Error while closing writer: {e_close}")


async def run_agent() -> None:
    # Flake8 E501 fix: Shorten line
    print(
        f"[INFO] Agent starting. User: {AGENT_USER_ID}. "
        f"Target: {AGENT_HOST}:{AGENT_PORT}. Interval: {AGENT_INTERVAL}s."
    )
    if SERVER_CERT_PATH and SERVER_CERT_PATH.exists():
        # Flake8 E501 fix: Shorten line
        print(f"[INFO] Will use server certificate for SSL verification: " f"{SERVER_CERT_PATH}")
    elif AGENT_ALLOW_INSECURE_SSL:
        # Flake8 F541 fix: Regular string
        # Flake8 E501 fix: Shorten line
        print(
            "[WARN] Server certificate not found/specified. "
            "AGENT_ALLOW_INSECURE_SSL is true. SSL connections "
            "will be insecure."
        )
    else:
        # Flake8 F541 fix: Regular string
        # Flake8 E501 fix: Shorten line
        print(
            "[WARN] Server certificate not found/specified. "
            "AGENT_ALLOW_INSECURE_SSL is false. SSL connections may fail "
            "if server uses self-signed cert."
        )

    while not shutdown_event.is_set():
        await send_collected_metrics()

        if shutdown_event.is_set():
            break

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=AGENT_INTERVAL)
            if shutdown_event.is_set():
                break
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"[ERROR] Unexpected error in agent sleep loop: {e}")
            break

    # Flake8 F541 fix: Regular string
    print("[INFO] Agent run loop finished.")


if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        # Flake8 E501 fix: Shorten line
        print(
            "\n[INFO] Agent terminated by user (KeyboardInterrupt). "
            "Ensure shutdown_event is set if not already."
        )
        if not shutdown_event.is_set():
            shutdown_event.set()
    except Exception as e_main:
        print(f"[CRITICAL] Agent main execution failed: {e_main}")
    finally:
        # Flake8 F541 fix: Regular string
        print("[INFO] Agent shutdown sequence complete.")
