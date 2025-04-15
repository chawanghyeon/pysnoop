# agents/logger_client.py
import asyncio
import json
from datetime import datetime
from core.textml.extractor import extract_numbers_from_text
from core.auth.session import generate_token

user_id = "alice"
token = generate_token(user_id)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8888


async def send_metrics(lines):
    reader, writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)

    for line in lines:
        results = extract_numbers_from_text(line)
        for context, value in results:
            message = {
                "type": "metric",
                "uri": f"/agent/{user_id}/{context or 'unknown'}",
                "ts": datetime.utcnow().isoformat() + "Z",
                "value": value,
                "token": token,
            }
            msg_json = json.dumps(message) + "\n"
            writer.write(msg_json.encode())
            await writer.drain()

            response = await reader.readline()
            print(f"[SERVER] {response.decode().strip()}")

    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    import fileinput

    print(">> Paste lines (Ctrl+D to end input):")
    lines = list(fileinput.input())
    asyncio.run(send_metrics(lines))
