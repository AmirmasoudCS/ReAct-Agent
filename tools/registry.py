
from tools.base import BaseTool


class ToolRegistry:
    """Stores available tools and provides a common way to execute them."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool by its name."""

        if not tool.name:
            raise ValueError("Tool name cannot be empty.")

        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Return a registered tool, or None if it doesn't exist."""

        return self._tools.get(name)

    def get_descriptions(self) -> str:
        """Return descriptions of all registered tools."""

        return "\n".join(
            tool.get_description()
            for tool in self._tools.values()
        )

    def execute(self, name: str, tool_input: str) -> str:
        """Execute a tool by name and return its result."""

        tool = self.get(name)

        if tool is None:
            return f"Error: tool '{name}' does not exist."

        try:
            return tool.execute(tool_input)
        except Exception:
            return f"Error: tool '{name}' failed during execution."