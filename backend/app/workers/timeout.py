from dataclasses import dataclass


@dataclass(frozen=True)
class TimeoutPolicy:
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than 0.")

    def get_timeout(self) -> float:
        return self.timeout_seconds