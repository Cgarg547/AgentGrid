from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models.workflow_schedule import WorkflowSchedule


class WorkflowScheduleRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, schedule: WorkflowSchedule) -> None:
        with self.session_factory() as session:
            existing = session.get(
                WorkflowSchedule,
                schedule.schedule_id,
            )

            if existing is None:
                session.add(schedule)
            else:
                existing.workflow_name = schedule.workflow_name
                existing.next_run_at = schedule.next_run_at
                existing.enabled = schedule.enabled
                existing.created_at = schedule.created_at

            session.commit()

    def get(self, schedule_id: str) -> WorkflowSchedule | None:
        with self.session_factory() as session:
            schedule = session.get(
                WorkflowSchedule,
                schedule_id,
            )

            if schedule is None:
                return None

            session.expunge(schedule)
            return schedule

    def list(
        self,
        enabled: bool | None = None,
    ) -> list[WorkflowSchedule]:
        with self.session_factory() as session:
            statement = select(WorkflowSchedule)

            if enabled is not None:
                statement = statement.where(
                    WorkflowSchedule.enabled == enabled
                )

            statement = statement.order_by(
                WorkflowSchedule.next_run_at.asc()
            )

            schedules = list(session.scalars(statement).all())

            for schedule in schedules:
                session.expunge(schedule)

            return schedules

    def list_due(
        self,
        now: datetime,
    ) -> list[WorkflowSchedule]:
        with self.session_factory() as session:
            statement = (
                select(WorkflowSchedule)
                .where(
                    WorkflowSchedule.enabled.is_(True),
                    WorkflowSchedule.next_run_at <= now,
                )
                .order_by(WorkflowSchedule.next_run_at.asc())
            )

            schedules = list(session.scalars(statement).all())

            for schedule in schedules:
                session.expunge(schedule)

            return schedules

    def claim_due(
        self,
        schedule_id: str,
        now: datetime,
        next_run_at: datetime,
    ) -> WorkflowSchedule | None:
        with self.session_factory() as session:
            statement = (
                select(WorkflowSchedule)
                .where(
                    WorkflowSchedule.schedule_id == schedule_id,
                    WorkflowSchedule.enabled.is_(True),
                    WorkflowSchedule.next_run_at <= now,
                )
                .with_for_update(skip_locked=True)
            )

            schedule = session.scalars(statement).first()

            if schedule is None:
                return None

            schedule.next_run_at = next_run_at

            session.commit()

            session.refresh(schedule)
            session.expunge(schedule)

            return schedule

    def delete(self, schedule_id: str) -> bool:
        with self.session_factory() as session:
            schedule = session.get(
                WorkflowSchedule,
                schedule_id,
            )

            if schedule is None:
                return False

            session.delete(schedule)
            session.commit()
            return True