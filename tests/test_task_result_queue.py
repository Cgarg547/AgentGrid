from app.workers.result_queue import TaskResultQueue


def test_task_result_queue_publishes_and_consumes_result():
    queue = TaskResultQueue(
        "agentgrid-test-task-results"
    )

    result = {
        "task_id": "task-result-123",
        "execution_id": "execution-result-123",
        "status": "completed",
        "result": {
            "answer": "worker completed task",
        },
    }

    queue.publish(result)

    consumed = queue.consume()

    assert consumed == result