from __future__ import annotations

import threading
import time

from app.services.workflow_scheduler import WorkflowScheduler


class WorkflowSchedulerLoop:
    def __init__(
        self,
        scheduler: WorkflowScheduler,
        interval_seconds: float = 5.0,
    ):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than 0.")

        self.scheduler = scheduler
        self.interval_seconds = interval_seconds

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    def start(self) -> None:
        if self.is_running:
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="agentgrid-workflow-scheduler",
            daemon=True,
        )

        self._thread.start()

    def stop(self) -> None:
        if not self.is_running:
            return

        self._stop_event.set()

        if self._thread is not threading.current_thread():
            self._thread.join(
                timeout=self.interval_seconds + 1
            )

        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.scheduler.run_once()
            except Exception:
                # Keep the scheduler loop alive if one scheduling
                # cycle fails. Detailed logging will be added later.
                pass

            self._stop_event.wait(
                timeout=self.interval_seconds
            )