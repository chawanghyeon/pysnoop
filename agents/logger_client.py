# agents/logger_client.py
import asyncio
import json
from datetime import datetime
from agents.collectors.base import collector_registry


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8888
user_id = "agent01"
token = "your_token_here"


async def send_collected_metrics():
    ts = datetime.utcnow().isoformat() + "Z"
    reader, writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)

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
                print(f"[SENT] {full_uri} = {value} [{resp.decode().strip()}]")
        except Exception as e:
            print(f"[ERROR] {CollectorClass.__name__}: {e}")

    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(send_collected_metrics())
