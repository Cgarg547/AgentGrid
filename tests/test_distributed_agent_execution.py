from app.runtime import AgentGridRuntime
from app.services.task_dispatcher import TaskDispatcher
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.workflow_task_handler import WorkflowTaskHandler
from app.workers.worker import Worker


def test_distributed_worker_executes_real_agent():
    queue = TaskQueue("agentgrid-test-distributed-agent")

    runtime = AgentGridRuntime()

    workflow_handler = WorkflowTaskHandler(
        runtime,
        agent_name="research-agent",
    )

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": workflow_handler.handle,
        },
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid:test:distributed-agent-v2"
        ),
    )

    dispatcher = TaskDispatcher(queue)

    dispatcher.dispatch(
        task_id="distributed-task-123",
        execution_id="distributed-execution-123",
        step_name="research",
        agent_name="research-agent",
        inputs={
            "input": "Explain distributed AI orchestration",
        },
    )

    result = worker.process_one()

    assert result is not None

    assert result["task_id"] == "distributed-task-123"
    assert result["execution_id"] == "distributed-execution-123"
    assert result["step_name"] == "research"
    assert result["agent_name"] == "research-agent"
    assert result["status"] == "completed"

    assert result["result"] == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }