# core/app/main.py
import asyncio
from core.utils.message import parse_message, MessageParseError
from core.metrics.datapoints import MetricStorage
from core.fs.tree import URITree
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8888


uri_tree = URITree()
metric_storage = MetricStorage()


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
            uri = msg["uri"]
            ts = datetime.fromisoformat(msg["ts"].replace("Z", "+00:00"))
            value = msg["value"]

            if not uri_tree.exists(uri):
                uri_tree.insert_uri(uri)
                print(f"[NEW URI] Registered {uri}")

            # 저장
            metric_storage.insert(uri, ts, value)
            print(f"[SAVED] {uri} @ {ts} = {value}")

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
