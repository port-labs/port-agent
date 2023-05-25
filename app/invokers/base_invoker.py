from abc import ABC, abstractmethod


class BaseInvoker(ABC):
    @abstractmethod
    def invoke(self, message: dict, destination: dict):
        pass
