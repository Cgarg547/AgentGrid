from typing import Any, TypedDict


class AgentGraphState(TypedDict, total=False):
    input: str
    research: dict[str, Any]
    analysis: dict[str, Any]
    report: dict[str, Any]