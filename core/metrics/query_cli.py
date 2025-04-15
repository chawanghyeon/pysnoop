# core/metrics/query_cli.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.metrics import ascii_plot, datapoints
from datetime import datetime


def print_all(uri: str):
    values = datapoints.get(uri)
    if not values:
        print(f"[INFO] No data for URI: {uri}")
        return
    print(f"📊 All values for: {uri}")
    for ts, val in values:
        print(f"  {ts.isoformat()}  ->  {val}")


def print_latest(uri: str):
    result = datapoints.get_latest(uri)
    if not result:
        print(f"[INFO] No data for URI: {uri}")
        return
    ts, val = result
    print(f"🕒 Latest value for {uri}: {val} at {ts.isoformat()}")


def plot_ascii(uri: str):
    values = datapoints.get(uri)
    ascii_plot.plot_ascii(values)


def main():
    datapoints.init_db()
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python core/metrics/query_cli.py all /uri/path")
        print("  python core/metrics/query_cli.py latest /uri/path")
        print("  python core/metrics/query_cli.py plot /uri/path")
        return

    mode = sys.argv[1]
    uri = sys.argv[2]

    if mode == "all":
        print_all(uri)
    elif mode == "latest":
        print_latest(uri)
    elif mode == "plot":
        plot_ascii(uri)
    else:
        print("[ERROR] Unknown mode:", mode)


if __name__ == "__main__":
    main()
