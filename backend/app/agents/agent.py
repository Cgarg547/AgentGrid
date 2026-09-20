from dataclasses import dataclass, field
from typing import List


@dataclass
class Agent:
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "allowed_tools": self.allowed_tools,
        }

    def can_use_tool(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools