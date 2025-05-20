# globals.py

"""Global state management for the application."""

from typing import List, Optional

from collectors.base import BaseCollector
from utils.log_writer import LogWriter

_instantiated_collectors_cache: List[BaseCollector] = []
_log_writer_instance_cache: Optional[LogWriter] = None


def get_instantiated_collectors() -> List[BaseCollector]:
    """Returns the cached list of instantiated collectors."""
    return _instantiated_collectors_cache


def set_instantiated_collectors(collectors: List[BaseCollector]) -> None:
    """Sets the cached list of instantiated collectors."""
    global _instantiated_collectors_cache
    _instantiated_collectors_cache = collectors


def get_log_writer_instance() -> Optional[LogWriter]:
    """Returns the cached LogWriter instance."""
    return _log_writer_instance_cache


def set_log_writer_instance(log_writer: Optional[LogWriter]) -> None:
    """Sets the cached LogWriter instance."""
    global _log_writer_instance_cache
    _log_writer_instance_cache = log_writer
