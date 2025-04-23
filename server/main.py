# core/app/main.py

import asyncio
from datetime import datetime

from server.auth.session import verify_token  # 토큰 검증 유틸
from server.fs.tree import URITree  # URI 등록 및 탐색 트리
from server.utils.log_writer import LogWriter  # 비동기 로그 저장기
from server.utils.message import MessageParseError, parse_message  # 메시지 파싱 유틸

# 서버 호스트 및 포트 설정
HOST = "127.0.0.1"
PORT = 8888

# 로그 저장기 및 URI 트리 인스턴스 초기화
log_writer = LogWriter()
uri_tree = URITree()


async def handle_client(reader, writer):
    """
    클라이언트의 연결을 처리하고, 메트릭 메시지를 수신하여
    URI 등록, 토큰 검증, 로그 저장까지 수행하는 비동기 함수.

    Args:
        reader (StreamReader): 클라이언트에서 오는 데이터 스트림
        writer (StreamWriter): 클라이언트에게 응답을 보내는 스트림
    """
    addr = writer.get_extra_info("peername")
    print(f"[CONNECTED] {addr}")

    while True:
        data = await reader.readline()
        if not data:
            break  # 연결 종료

        raw = data.decode().strip()
        try:
            msg = parse_message(raw)  # 문자열 메시지를 dict로 파싱

            token = msg.get("token")
            user_id = verify_token(token)  # 토큰 검증
            if not user_id:
                writer.write(b"ERROR: Invalid or expired token\n")
                await writer.drain()
                continue  # 인증 실패시 무시

            uri = msg["uri"]
            ts = datetime.fromisoformat(msg["ts"].replace("Z", "+00:00"))
            value = msg["value"]

            # 새로운 URI인 경우 트리에 등록
            if not uri_tree.exists(uri):
                uri_tree.insert_uri(uri)
                print(f"[NEW URI] Registered {uri}")

            # 수신 로그 출력
            print(f"[{user_id}] {uri} @ {ts} = {value}")

            # 로그를 비동기 큐에 저장 요청
            await log_writer.append({"ts": ts, "uri": uri, "value": value, "user_id": user_id})

            writer.write(b"ACK\n")

        except MessageParseError as e:
            writer.write(f"ERROR: {e}\n".encode())

        await writer.drain()

    writer.close()
    await writer.wait_closed()


async def run_server():
    """
    TCP 서버를 시작하고, 클라이언트 핸들러 및 로그 쓰기 루프를 실행하는 메인 함수.
    """
    log_writer.start()  # 로그 쓰기 루프 시작

    # TCP 서버 바인딩 및 핸들러 등록
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"[SERVER] Serving on {addr}")

    # 서버 영구 실행
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n[SERVER] Shutdown requested by user")
