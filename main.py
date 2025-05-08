# main.py (루트에 위치)
import argparse
import asyncio

from apps.server.main import run_server  # 서버 루프


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

    if args.mode == "server":
        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            print("\n[MAIN] KeyboardInterrupt received. Exiting...")
    else:
        from apps.agents.main import run_agent

        try:
            asyncio.run(run_agent())
        except KeyboardInterrupt:
            print("\n[MAIN] KeyboardInterrupt received. Exiting...")
