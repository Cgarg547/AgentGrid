from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts