from abc import ABC, abstractmethod


class BaseFeature(ABC):
    @abstractmethod
    def run(self):
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        pass
