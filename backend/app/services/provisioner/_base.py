from abc import ABC, abstractmethod

class ProvisionerBase(ABC):
    @abstractmethod
    def fetch_current(self, user_email: str) -> dict:
        ...

    @abstractmethod
    def apply(self, user_email: str, plan: list[dict]) -> list[dict]:
        ...
