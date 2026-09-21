from app.services.task_dispatcher import TaskDispatcher
from app.workers.queue import TaskQueue
from app.workers.worker import Worker
from app.workers.idempotency import IdempotencyStore

def test_dispatched_workflow_task_is_executed_by_worker():
    queue = TaskQueue("agentgrid-test-worker-execution")

    def research_handler(*, step_name, inputs):
        return {
            "step_name": step_name,
            "answer": f"Processed: {inputs['input']}",
        }

    dispatcher = TaskDispatcher(queue)

    dispatcher.dispatch(
        task_id="task-worker-123",
        execution_id="execution-worker-123",
        step_name="research",
        agent_name="research-agent",
        inputs={
            "input": "Explain distributed AI orchestration",
        },
    )

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": research_handler,
        },
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid:test:worker-execution"
        ),
    )

    result = worker.process_one()

    assert result is not None
    assert result["task_id"] == "task-worker-123"
    assert result["execution_id"] == "execution-worker-123"
    assert result["step_name"] == "research"
    assert result["agent_name"] == "research-agent"
    assert result["status"] == "completed"

    assert result["result"] == {
        "step_name": "research",
        "answer": "Processed: Explain distributed AI orchestration",
    }