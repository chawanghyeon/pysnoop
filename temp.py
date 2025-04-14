import asyncio
import json


async def send_message():
    reader, writer = await asyncio.open_connection("127.0.0.1", 8888)

    message = {
        "type": "metric",
        "uri": "/app/server1/cpu",
        "ts": "2025-04-14T18:40:00Z",
        "value": 91.2,
    }
    writer.write((json.dumps(message) + "\n").encode())
    await writer.drain()

    response = await reader.readline()
    print(f"[SERVER RESPONSE] {response.decode().strip()}")

    writer.close()
    await writer.wait_closed()


asyncio.run(send_message())
