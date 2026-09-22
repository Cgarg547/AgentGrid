import json
from datetime import datetime
from typing import Any

from app.services.execution_event_repository import ExecutionEventRepository


class ExecutionMetrics:
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"

    def __init__(self, event_repository: ExecutionEventRepository):
        self.event_repository = event_repository

    def execution_metrics(
        self,
        execution_id: str,
    ) -> dict[str, Any]:
        events = self.event_repository.list_by_task(
            execution_id
        )

        completed_events = [
            event
            for event in events
            if event.event_type == self.WORKFLOW_COMPLETED
        ]

        failed_events = [
            event
            for event in events
            if event.event_type == self.WORKFLOW_FAILED
        ]

        terminal_events = completed_events + failed_events

        durations: list[float] = []

        for event in terminal_events:
            duration = self._duration_ms(
                self._event_data(event)
            )

            if duration is not None:
                durations.append(duration)

        status = "unknown"

        if completed_events:
            status = "completed"
        elif failed_events:
            status = "failed"

        step_count = sum(
            1
            for event in events
            if event.event_type
            in {
                self.STEP_COMPLETED,
                self.STEP_FAILED,
            }
        )

        return {
            "execution_id": execution_id,
            "status": status,
            "duration_ms": (
                durations[-1]
                if durations
                else None
            ),
            "step_count": step_count,
        }

    def step_metrics(
        self,
        execution_id: str,
    ) -> list[dict[str, Any]]:
        events = self.event_repository.list_by_task(
            execution_id
        )

        step_events = [
            event
            for event in events
            if event.event_type
            in {
                self.STEP_COMPLETED,
                self.STEP_FAILED,
            }
        ]

        metrics: list[dict[str, Any]] = []

        for event in step_events:
            data = self._event_data(event)

            metrics.append({
                "step_name": data.get("step_name"),
                "event_type": event.event_type,
                "duration_ms": self._duration_ms(data),
            })

        return metrics

    def aggregate_metrics(
        self,
        execution_ids: list[str] | None = None,
        workflow_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError(
                    "start_time must be earlier than or equal to end_time."
                )

        if execution_ids is None:
            execution_ids = self.event_repository.list_task_ids()

            execution_ids = [
                execution_id
                for execution_id in execution_ids
                if self._is_workflow_execution(
                    execution_id
                )
            ]

        if workflow_name is not None:
            filtered_execution_ids = []

            for execution_id in execution_ids:
                events = self.event_repository.list_by_task(
                    execution_id
                )

                matches_workflow = any(
                    event.event_type == self.WORKFLOW_STARTED
                    and self._event_data(event).get(
                        "workflow_name"
                    ) == workflow_name
                    for event in events
                )

                if matches_workflow:
                    filtered_execution_ids.append(
                        execution_id
                    )

            execution_ids = filtered_execution_ids

        if start_time is not None or end_time is not None:
            filtered_execution_ids = []

            for execution_id in execution_ids:
                events = self.event_repository.list_by_task(
                    execution_id
                )

                workflow_started_events = [
                    event
                    for event in events
                    if event.event_type
                    == self.WORKFLOW_STARTED
                ]

                if not workflow_started_events:
                    continue

                workflow_started_at = min(
                    event.timestamp
                    for event in workflow_started_events
                )

                if (
                    start_time is not None
                    and workflow_started_at < start_time
                ):
                    continue

                if (
                    end_time is not None
                    and workflow_started_at > end_time
                ):
                    continue

                filtered_execution_ids.append(
                    execution_id
                )

            execution_ids = filtered_execution_ids

        execution_results = [
            self.execution_metrics(execution_id)
            for execution_id in execution_ids
        ]

        total_executions = len(execution_results)

        completed = sum(
            result["status"] == "completed"
            for result in execution_results
        )

        failed = sum(
            result["status"] == "failed"
            for result in execution_results
        )

        unknown = sum(
            result["status"] == "unknown"
            for result in execution_results
        )

        durations = [
            result["duration_ms"]
            for result in execution_results
            if result["duration_ms"] is not None
        ]

        step_counts = [
            result["step_count"]
            for result in execution_results
        ]

        success_rate = (
            completed / total_executions
            if total_executions > 0
            else 0.0
        )

        average_duration_ms = (
            sum(durations) / len(durations)
            if durations
            else None
        )

        average_step_count = (
            sum(step_counts) / len(step_counts)
            if step_counts
            else 0.0
        )

        return {
            "total_executions": total_executions,
            "completed": completed,
            "failed": failed,
            "unknown": unknown,
            "success_rate": success_rate,
            "average_duration_ms": average_duration_ms,
            "average_step_count": average_step_count,
        }

    def _is_workflow_execution(
        self,
        execution_id: str,
    ) -> bool:
        events = self.event_repository.list_by_task(
            execution_id
        )

        return any(
            event.event_type == self.WORKFLOW_STARTED
            for event in events
        )

    @staticmethod
    def _event_data(
        event: Any,
    ) -> dict[str, Any]:
        data = event.data

        if isinstance(data, str):
            return json.loads(data)

        return data

    @staticmethod
    def _duration_ms(
        data: dict[str, Any],
    ) -> float | None:
        duration = data.get("duration_ms")

        if duration is None:
            return None

        return float(duration)