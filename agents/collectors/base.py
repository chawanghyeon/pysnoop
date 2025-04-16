# agents/collectors/base.py
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Type


class BaseCollector(ABC):
    registry: list[Any] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseCollector.registry.append(cls)

    @abstractmethod
    def collect(self) -> List[Tuple[str, float]]:
        pass


collector_registry: List[Type[BaseCollector]] = []


def register_collector(cls: Type[BaseCollector]):
    collector_registry.append(cls)
    return cls
