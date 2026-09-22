from datetime import datetime, timedelta, timezone

from app.models.workflow_schedule import WorkflowSchedule
from app.services.workflow_schedule_repository import WorkflowScheduleRepository
from app.services.workflow_schedule_service import WorkflowScheduleService
from app.services.workflow_scheduler import WorkflowScheduler


def test_create_and_get_schedule():
    class FakeRepository:
        def __init__(self):
            self.schedules = {}

        def save(self, schedule):
            self.schedules[schedule.schedule_id] = schedule

        def get(self, schedule_id):
            return self.schedules.get(schedule_id)

    repository = FakeRepository()
    service = WorkflowScheduleService(repository)

    next_run_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    schedule = service.create_schedule(
        workflow_name="research-pipeline",
        next_run_at=next_run_at,
    )

    stored = service.get_schedule(schedule.schedule_id)

    assert stored is not None
    assert stored.schedule_id == schedule.schedule_id
    assert stored.workflow_name == "research-pipeline"
    assert stored.enabled is True


def test_list_due_schedules():
    class FakeRepository:
        def __init__(self):
            self.schedules = []

        def save(self, schedule):
            self.schedules.append(schedule)

        def get(self, schedule_id):
            for schedule in self.schedules:
                if schedule.schedule_id == schedule_id:
                    return schedule
            return None

        def list_due(self, now):
            return [
                schedule
                for schedule in self.schedules
                if schedule.enabled and schedule.next_run_at <= now
            ]

    repository = FakeRepository()
    service = WorkflowScheduleService(repository)

    now = datetime.now(timezone.utc)

    due_schedule = service.create_schedule(
        workflow_name="research-pipeline",
        next_run_at=now - timedelta(minutes=1),
    )

    future_schedule = service.create_schedule(
        workflow_name="research-pipeline",
        next_run_at=now + timedelta(minutes=10),
    )

    due = service.list_due_schedules(now)

    assert len(due) == 1
    assert due[0].schedule_id == due_schedule.schedule_id
    assert due[0].schedule_id != future_schedule.schedule_id


def test_enable_and_disable_schedule():
    class FakeRepository:
        def __init__(self):
            self.schedules = {}

        def save(self, schedule):
            self.schedules[schedule.schedule_id] = schedule

        def get(self, schedule_id):
            return self.schedules.get(schedule_id)

    repository = FakeRepository()
    service = WorkflowScheduleService(repository)

    schedule = service.create_schedule(
        workflow_name="research-pipeline",
        next_run_at=datetime.now(timezone.utc),
    )

    assert schedule.enabled is True

    assert service.disable_schedule(schedule.schedule_id) is True
    assert service.get_schedule(schedule.schedule_id).enabled is False

    assert service.enable_schedule(schedule.schedule_id) is True
    assert service.get_schedule(schedule.schedule_id).enabled is True


def test_scheduler_runs_due_schedule_once():
    class FakeRepository:
        def __init__(self):
            self.schedules = {}

        def save(self, schedule):
            self.schedules[schedule.schedule_id] = schedule

        def list_due(self, now):
            return [
                schedule
                for schedule in self.schedules.values()
                if schedule.enabled and schedule.next_run_at <= now
            ]

        def claim_due(self, schedule_id, now, next_run_at):
            schedule = self.schedules.get(schedule_id)

            if schedule is None:
                return None

            if not schedule.enabled or schedule.next_run_at > now:
                return None

            schedule.next_run_at = next_run_at
            return schedule

    class FakeExecution:
        def __init__(self, execution_id):
            self.execution_id = execution_id

    repository = FakeRepository()

    now = datetime.now(timezone.utc)

    schedule = WorkflowSchedule(
        schedule_id="schedule-1",
        workflow_name="research-pipeline",
        next_run_at=now - timedelta(minutes=1),
        enabled=True,
        created_at=now,
    )

    repository.save(schedule)

    calls = []

    def fake_executor(workflow_name):
        calls.append(workflow_name)
        return FakeExecution("execution-1")

    scheduler = WorkflowScheduler(
        repository=repository,
        workflow_executor=fake_executor,
    )

    first_result = scheduler.run_once(now)
    second_result = scheduler.run_once(now)

    assert len(first_result) == 1
    assert len(second_result) == 0

    assert calls == ["research-pipeline"]

    assert first_result[0]["schedule_id"] == "schedule-1"
    assert first_result[0]["workflow_name"] == "research-pipeline"
    assert first_result[0]["execution_id"] == "execution-1"

    assert repository.schedules["schedule-1"].next_run_at > now