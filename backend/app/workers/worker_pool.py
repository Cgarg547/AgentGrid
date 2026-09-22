import threading
import time
from typing import Any

from app.workers.worker import Worker


class WorkerPool:
    def __init__(
        self,
        workers: list[Worker],
        poll_interval: float = 0.1,
    ):
        if not workers:
            raise ValueError(
                "Worker pool must contain at least one worker."
            )

        if poll_interval <= 0:
            raise ValueError(
                "Poll interval must be greater than 0."
            )

        self.workers = workers
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def process_available_tasks(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        threads: list[threading.Thread] = []
        thread_results: list[dict[str, Any] | None] = [
            None
        ] * len(self.workers)

        def run_worker(
            index: int,
            worker: Worker,
        ) -> None:
            thread_results[index] = worker.process_one()

        for index, worker in enumerate(self.workers):
            thread = threading.Thread(
                target=run_worker,
                args=(index, worker),
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        for result in thread_results:
            if result is not None:
                results.append(result)

        return results

    def start(self) -> None:
        if self._threads:
            return

        self._stop_event.clear()

        for worker in self.workers:
            thread = threading.Thread(
                target=self._run_worker_loop,
                args=(worker,),
                daemon=True,
            )
            self._threads.append(thread)
            thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        for thread in self._threads:
            thread.join(timeout=2)

        for worker in self.workers:
            worker.stop()

        self._threads.clear()

    def _run_worker_loop(self, worker: Worker) -> None:
        while not self._stop_event.is_set():
            result = worker.process_one()

            if result is None:
                time.sleep(self.poll_interval)