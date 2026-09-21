from app.services.task_dispatcher import TaskDispatcher
from app.workers.queue import TaskQueue


def test_task_dispatcher_enqueues_workflow_task():
    queue = TaskQueue(
        "agentgrid-test-dispatcher"
    )

    dispatcher = TaskDispatcher(queue)

    dispatcher.dispatch(
        task_id="task-123",
        execution_id="execution-123",
        step_name="research",
        agent_name="research-agent",
        inputs={
            "input": "Research AI orchestration",
        },
    )

    task = queue.dequeue()

    assert task == {
        "task_id": "task-123",
        "execution_id": "execution-123",
        "step_name": "research",
        "agent_name": "research-agent",
        "inputs": {
            "input": "Research AI orchestration",
        },
    }