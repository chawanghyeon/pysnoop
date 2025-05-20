# agents/collectors/top_processes.py
from typing import List, Tuple

import psutil

from .base import BaseCollector, register_collector


@register_collector
class TopProcessCollector(BaseCollector):
    def collect(self) -> List[Tuple[str, float]]:
        procs_data = []
        try:
            # Get all processes first to allow cpu_percent to have a comparison interval
            # Calling cpu_percent() with no interval for the first time returns a meaningless 0.0.
            # Iterate once to "prime" it if necessary, or rely on psutil's internal handling.
            # For process_iter, it's generally okay.

            pids = psutil.pids()  # Get all PIDs
            for pid in pids:
                try:
                    p = psutil.Process(pid)
                    # Fetch all attributes at once to minimize race conditions
                    with p.oneshot():
                        p_info = p.as_dict(attrs=["pid", "name", "cpu_percent", "memory_percent"])

                    # Filter out processes with None cpu_percent (e.g. kernel tasks, just spawned)
                    if p_info.get("cpu_percent") is None:
                        continue
                    procs_data.append(p_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue  # Process died or restricted
                except Exception as e_proc:  # Error processing a single process
                    print(
                        f"[DEBUG][TopProcessCollector] Skipping process PID {pid} due to: {e_proc}"
                    )
                    pass

            sorted_procs = sorted(
                procs_data,
                key=lambda p_info: p_info.get("cpu_percent", 0.0)
                or 0.0,  # Handle None from as_dict if not filtered
                reverse=True,
            )

            metrics = []
            for p_info in sorted_procs[:5]:  # Top 5 CPU consumers
                pid_val = p_info.get("pid", "unknown_pid")
                name_val = p_info.get("name", "")

                # Sanitize name for metric URI
                clean_name = "".join(
                    c if c.isalnum() or c in ("-", "_", ".") else "_" for c in name_val
                ).strip("_")
                if not clean_name:
                    clean_name = f"pid_{pid_val}"
                # Truncate very long names
                clean_name = (clean_name[:30] + "..") if len(clean_name) > 32 else clean_name

                cpu_perc = p_info.get("cpu_percent")
                if cpu_perc is not None:
                    metrics.append(
                        (
                            f"top_cpu.{clean_name}.pid_{pid_val}.cpu_percent",
                            float(cpu_perc),
                        )
                    )

                mem_perc = p_info.get("memory_percent")
                if mem_perc is not None:
                    metrics.append(
                        (
                            f"top_mem.{clean_name}.pid_{pid_val}.mem_percent",
                            float(mem_perc),
                        )
                    )
            return metrics
        except Exception as e:
            print(f"[WARN][TopProcessCollector] Failed to collect top processes: {e}")
            return []
