import argparse
import asyncio
import json
import signal
from datetime import datetime
from types import FrameType
from typing import Optional

from agents.collectors.base import collector_registry

# Interval between metric sends (in seconds)
INTERVAL: int = 10

# Shutdown flag
should_exit: bool = False


def handle_exit(sig: int, frame: Optional[FrameType]) -> None:
    """
    Handle system signals (SIGINT, SIGTERM) and trigger graceful shutdown.

    Args:
        sig: The signal number received.
        frame: Current stack frame (not used).
    """
    global should_exit
    should_exit = True
    print("\n[INFO] Agent stopping...")


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def send_collected_metrics(host: str, port: int, user_id: str, token: str) -> None:
    """
    Connects to the server and sends collected metrics from all registered collectors.

    Args:
        host: Target server hostname or IP.
        port: Target server port number.
        user_id: Identifier for the agent or user.
        token: Authentication token.

    Returns:
        None
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

    Args:
        args: Parsed command-line arguments (includes host, port, user_id, token).

    Returns:
        None
    """
    while not should_exit:
        await send_collected_metrics(args.host, args.port, args.user_id, args.token)
        await asyncio.sleep(INTERVAL)


def parse_args(argv=None) -> argparse.Namespace:
    """
    Parses command-line arguments required to run the agent.
    Args:
        argv (list): Optional list of arguments, used when invoked from outside.
    Returns:
        argparse.Namespace: Parsed arguments with host, port, user_id, and token.
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
