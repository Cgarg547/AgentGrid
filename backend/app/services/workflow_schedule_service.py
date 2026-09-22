from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.workflow_schedule import WorkflowSchedule
from app.services.workflow_schedule_repository import WorkflowScheduleRepository


class WorkflowScheduleService:
    def __init__(self, repository: WorkflowScheduleRepository):
        self.repository = repository

    def create_schedule(
        self,
        workflow_name: str,
        next_run_at: datetime,
    ) -> WorkflowSchedule:
        if next_run_at.tzinfo is None:
            next_run_at = next_run_at.replace(tzinfo=timezone.utc)

        schedule = WorkflowSchedule(
            schedule_id=str(uuid4()),
            workflow_name=workflow_name,
            next_run_at=next_run_at,
            enabled=True,
            created_at=datetime.now(timezone.utc),
        )

        schedule_id = schedule.schedule_id
        self.repository.save(schedule)

        stored_schedule = self.repository.get(schedule_id)

        if stored_schedule is None:
            raise RuntimeError(
                f"Failed to retrieve created schedule '{schedule_id}'."
            )

        return stored_schedule

    def get_schedule(
        self,
        schedule_id: str,
    ) -> WorkflowSchedule | None:
        return self.repository.get(schedule_id)

    def list_schedules(
        self,
        enabled: bool | None = None,
    ) -> list[WorkflowSchedule]:
        return self.repository.list(enabled=enabled)

    def list_due_schedules(
        self,
        now: datetime | None = None,
    ) -> list[WorkflowSchedule]:
        if now is None:
            now = datetime.now(timezone.utc)

        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        return self.repository.list_due(now)

    def enable_schedule(self, schedule_id: str) -> bool:
        schedule = self.repository.get(schedule_id)

        if schedule is None:
            return False

        schedule.enabled = True
        self.repository.save(schedule)
        return True

    def disable_schedule(self, schedule_id: str) -> bool:
        schedule = self.repository.get(schedule_id)

        if schedule is None:
            return False

        schedule.enabled = False
        self.repository.save(schedule)
        return True

    def delete_schedule(self, schedule_id: str) -> bool:
        return self.repository.delete(schedule_id)