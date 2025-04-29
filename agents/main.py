import argparse
import asyncio
import json
import signal
from datetime import datetime
from types import FrameType
from typing import Optional

from agents.collectors.base import collector_registry

# Interval between full metric sends (in seconds)
INTERVAL: int = 10

# Shutdown signal
shutdown_event = asyncio.Event()


def handle_exit(sig: int, frame: Optional[FrameType]) -> None:
    """
    Handle system signals (SIGINT, SIGTERM) and trigger graceful shutdown.
    """
    print("\n[INFO] Agent stopping...")
    shutdown_event.set()


# Register signal handlers
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def send_collected_metrics(host: str, port: int, user_id: str, token: str) -> None:
    """
    Connects to the server and sends collected metrics from all registered collectors.
    """
    ts: str = datetime.utcnow().isoformat() + "Z"

    try:
        reader, writer = await asyncio.open_connection(host, port)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    for CollectorClass in collector_registry:
        try:
            collector = CollectorClass()
            metrics = collector.collect()
            for uri, value in metrics:
                full_uri = f"/agent/{user_id}/{uri}"
                message = {
                    "type": "metric",
                    "uri": full_uri,
                    "ts": ts,
                    "value": value,
                    "token": token,
                }
                writer.write((json.dumps(message) + "\n").encode())
                await writer.drain()
                resp = await reader.readline()
                print(f"[SENT] {full_uri} = {value} [Response: {resp.decode().strip()}]")
        except Exception as e:
            print(f"[ERROR] {CollectorClass.__name__} failed: {e}")

    writer.close()
    await writer.wait_closed()


async def run_agent(args: argparse.Namespace) -> None:
    """
    Main agent loop that collects and sends metrics periodically.
    """
    while not shutdown_event.is_set():
        await send_collected_metrics(args.host, args.port, args.user_id, args.token)

        # Sleep in small chunks to respond quickly to shutdown
        sleep_time = 0
        while sleep_time < INTERVAL:
            if shutdown_event.is_set():
                break
            await asyncio.sleep(1)
            sleep_time += 1


def parse_args(argv=None) -> argparse.Namespace:
    """
    Parses command-line arguments required to run the agent.
    """
    parser = argparse.ArgumentParser(description="System Metrics Agent")
    parser.add_argument("--host", required=True, help="Server host (e.g. 127.0.0.1)")
    parser.add_argument("--port", type=int, required=True, help="Server port (e.g. 8888)")
    parser.add_argument("--user-id", required=True, help="Agent user ID")
    parser.add_argument("--token", required=True, help="Authentication token")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(run_agent(args))
    except KeyboardInterrupt:
        print("\n[INFO] Agent terminated by user.")
