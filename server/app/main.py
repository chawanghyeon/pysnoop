# core/app/main.py
import asyncio
from datetime import datetime

from server.auth.session import verify_token
from server.fs.tree import URITree
from server.metrics import datapoints
from server.utils.message import MessageParseError, parse_message

HOST = "127.0.0.1"
PORT = 8888


uri_tree = URITree()
datapoints.init_db()


async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"[CONNECTED] {addr}")

    while True:
        data = await reader.readline()
        if not data:
            break

        raw = data.decode().strip()
        try:
            msg = parse_message(raw)

            token = msg.get("token")
            user_id = verify_token(token)
            if not user_id:
                writer.write(b"ERROR: Invalid or expired token\n")
                await writer.drain()
                continue

            uri = msg["uri"]
            ts = datetime.fromisoformat(msg["ts"].replace("Z", "+00:00"))
            value = msg["value"]

            if not uri_tree.exists(uri):
                uri_tree.insert_uri(uri)
                print(f"[NEW URI] Registered {uri}")

            datapoints.insert(uri, ts, value)
            print(f"[{user_id}] {uri} @ {ts} = {value}")
            writer.write(b"ACK\n")

        except MessageParseError as e:
            writer.write(f"ERROR: {e}\n".encode())

        await writer.drain()

    writer.close()
    await writer.wait_closed()


async def run_server():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"[SERVER] Serving on {addr}")

    async with server:
        await server.serve_forever()
