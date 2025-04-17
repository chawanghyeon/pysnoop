# run_server.py
import asyncio

from server.app.main import run_server

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n[SERVER] Shutdown requested by user")
