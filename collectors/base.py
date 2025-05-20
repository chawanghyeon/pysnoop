# apps/collectors/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Type, Union  # Added Union, Dict


class BaseCollector(ABC):
    registry: list[Any] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @abstractmethod
    def collect(self) -> Union[List[Tuple[str, Any]], List[Dict[str, Any]]]:
        pass


collector_registry: List[Type[BaseCollector]] = []


def register_collector(cls: Type[BaseCollector]):
    collector_registry.append(cls)
    return cls
