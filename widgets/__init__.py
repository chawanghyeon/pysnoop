# widgets/__init__.py

"""Exports all widgets for easier importing."""

from .current_time_widget import CurrentTimeWidget
from .dmesg_errors_widget import DmesgErrorsWidget
from .docker_stats_widget import DockerStatsWidget
from .system_info_widget import SystemInfoWidget
from .top_processes_widget import TopProcessesWidget
from .uptime_widget import UptimeWidget

__all__ = [
    "CurrentTimeWidget",
    "DmesgErrorsWidget",
    "DockerStatsWidget",
    "SystemInfoWidget",
    "TopProcessesWidget",
    "UptimeWidget",
]
