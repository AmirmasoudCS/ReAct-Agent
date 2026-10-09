
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """Interface that every agent tool must implement."""

    name: str
    description: str

    @abstractmethod
    def execute(self, tool_input: str) -> str:
        """Execute the tool and return its result as a string."""
        raise NotImplementedError

    def get_description(self) -> str:
        """Return the tool's description for the LLM."""
        return f"{self.name}: {self.description}"