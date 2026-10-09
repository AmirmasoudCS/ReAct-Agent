
class Message:
    """A message stored in the agent's internal conversation history."""

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content