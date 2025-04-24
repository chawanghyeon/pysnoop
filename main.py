# main.py (루트에 위치)
import argparse
import asyncio

from agents.main import parse_args as parse_agent_args  # Agent 실행기
from agents.main import run_agent
from server.main import run_server  # 서버 루프


def parse_main_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description="pysnoop main entry")
    parser.add_argument(
        "--mode",
        choices=["server", "agent"],
        required=True,
        help="Which mode to run: server or agent",
    )
    return parser.parse_known_args()


if __name__ == "__main__":
    args, unknown_args = parse_main_args()

    try:
        if args.mode == "server":
            asyncio.run(run_server())

        elif args.mode == "agent":
            # agent 전용 인자 파싱 (host, port, user_id, token)
            agent_args = parse_agent_args(unknown_args)
            asyncio.run(run_agent(agent_args))

    except KeyboardInterrupt:
        print("\n[MAIN] Shutdown requested by user.")
