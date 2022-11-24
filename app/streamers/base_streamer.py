from abc import ABC, abstractmethod


class BaseStreamer(ABC):
    @abstractmethod
    def stream(self) -> None:
        pass
