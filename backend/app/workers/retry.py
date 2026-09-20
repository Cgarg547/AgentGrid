from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts

    def get_delay(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("Attempt must be at least 1.")

        return self.base_delay * (2 ** (attempt - 1))