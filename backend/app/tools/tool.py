from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    permissions: list[str] = field(default_factory=list)

    def execute(self, **kwargs: Any) -> Any:
        return self.handler(**kwargs)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
        }