from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.services.workflow_schedule_repository import (
    WorkflowScheduleRepository,
)


class WorkflowScheduler:
    def __init__(
        self,
        repository: WorkflowScheduleRepository,
        workflow_executor: Callable[..., Any],
    ):
        self.repository = repository
        self.workflow_executor = workflow_executor

    def run_once(
        self,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if now is None:
            now = datetime.now(timezone.utc)

        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        due_schedules = self.repository.list_due(now)

        results: list[dict[str, Any]] = []

        for schedule in due_schedules:
            next_run_at = self._next_run_at(
                schedule.next_run_at,
                now,
            )

            claimed_schedule = self.repository.claim_due(
                schedule_id=schedule.schedule_id,
                now=now,
                next_run_at=next_run_at,
            )

            if claimed_schedule is None:
                continue

            execution = self.workflow_executor(
                claimed_schedule.workflow_name,
            )

            results.append(
                {
                    "schedule_id": claimed_schedule.schedule_id,
                    "workflow_name": claimed_schedule.workflow_name,
                    "execution_id": execution.execution_id,
                    "next_run_at": claimed_schedule.next_run_at,
                }
            )

        return results

    @staticmethod
    def _next_run_at(
        current_run_at: datetime,
        now: datetime,
    ) -> datetime:
        if current_run_at.tzinfo is None:
            current_run_at = current_run_at.replace(
                tzinfo=timezone.utc
            )

        next_run_at = current_run_at + timedelta(minutes=5)

        while next_run_at <= now:
            next_run_at += timedelta(minutes=5)

        return next_run_at