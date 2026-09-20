from dataclasses import dataclass
from enum import Enum


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class ToolPolicy:
    tool_name: str
    allowed: bool = True
    require_approval: bool = False

    def evaluate(self) -> PolicyDecision:
        if not self.allowed:
            return PolicyDecision.DENY

        if self.require_approval:
            return PolicyDecision.REQUIRE_APPROVAL

        return PolicyDecision.ALLOW