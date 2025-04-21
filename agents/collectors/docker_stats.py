import subprocess
from typing import List, Tuple

from .base import BaseCollector, register_collector


@register_collector
class DockerStatsCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        """
        Collects per-container metrics using 'docker stats --no-stream'.
        Returns:
            List of (uri_key, value) pairs.
        """
        metrics = []

        try:
            output = subprocess.check_output(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.Name}}::{{.CPUPerc}}::{{.MemPerc}}::{{.MemUsage}}",
                ],
                text=True,
            )

            for line in output.strip().splitlines():
                try:
                    name, cpu, mem, mem_usage = line.strip().split("::")
                    cpu_val = float(cpu.strip("%"))
                    mem_val = float(mem.strip("%"))

                    # Optional: Parse memory usage value (e.g., "210MiB / 3.84GiB")
                    usage_raw = mem_usage.split("/")[0].strip()
                    mem_usage_val = _parse_memory_value(usage_raw)

                    # Add metrics
                    metrics.append((f"docker.container.{name}.cpu_percent", cpu_val))
                    metrics.append((f"docker.container.{name}.mem_percent", mem_val))
                    metrics.append((f"docker.container.{name}.mem_usage_mb", mem_usage_val))
                except Exception as e:
                    print(f"[WARN] Failed to parse line: {line} ({e})")

        except Exception as e:
            print(f"[ERROR] DockerStatsCollector failed: {e}")

        return metrics


def _parse_memory_value(s: str) -> float:
    """
    Parses a string like '210MiB' or '3.84GiB' to megabytes as float.
    """
    s = s.strip().upper()
    if s.endswith("MIB"):
        return float(s[:-3])
    if s.endswith("GIB"):
        return float(s[:-3]) * 1024
    if s.endswith("KIB"):
        return float(s[:-3]) / 1024
    if s.endswith("B"):
        return float(s[:-1]) / 1024 / 1024
    return 0.0
