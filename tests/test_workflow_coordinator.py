import pytest

from app.core.redis import redis_client
from app.services.task_dispatcher import TaskDispatcher
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue
from app.workers.worker import Worker
from app.workers.idempotency import IdempotencyStore
from app.workflows.execution import WorkflowStatus
from app.workers.workflow_coordinator import WorkflowCoordinator
from app.workflows.execution import WorkflowExecution
from app.workflows.workflow import Workflow, WorkflowStep
from app.workflows.workflow_state import StepStatus

@pytest.fixture(autouse=True)
def clean_coordinator_redis_state():
    queue_names = [
        "agentgrid-test-worker-coordinator-task-v2",
        "agentgrid-test-worker-coordinator-result-v2",
        "agentgrid-test-distributed-workflow-task",
        "agentgrid-test-distributed-workflow-result",
    ]

    idempotency_prefixes = [
        "agentgrid-test-worker-coordinator-v2",
        "agentgrid-test-distributed-research-v2",
        "agentgrid-test-distributed-analysis-v2",
    ]

    for queue_name in queue_names:
        redis_client.delete(queue_name)

    for prefix in idempotency_prefixes:
        keys = redis_client.scan_iter(
            match=f"{prefix}:*"
        )

        for key in keys:
            redis_client.delete(key)

    yield

    for queue_name in queue_names:
        redis_client.delete(queue_name)

    for prefix in idempotency_prefixes:
        keys = redis_client.scan_iter(
            match=f"{prefix}:*"
        )

        for key in keys:
            redis_client.delete(key)

def test_coordinator_dispatches_ready_step():
    workflow = Workflow(
        name="test-workflow",
        description="Test workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            )
        ],
    )

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id="execution-coordinator-123",
    )

    task_queue = TaskDispatcher(
        TaskQueue("agentgrid-test-coordinator")
    )

    result_queue = TaskResultQueue(
        "agentgrid-test-coordinator-results"
    )

    coordinator = WorkflowCoordinator(
        dispatcher=task_queue,
        result_queue=result_queue,
    )

    dispatched = coordinator.dispatch_ready_steps(
        execution
    )

    assert dispatched == ["research"]

    assert execution.step_statuses["research"] == (
        StepStatus.RUNNING
    )

    task = TaskQueue(
        "agentgrid-test-coordinator"
    ).dequeue()

    assert task is not None
    assert task["execution_id"] == (
        "execution-coordinator-123"
    )
    assert task["step_name"] == "research"
    assert task["agent_name"] == "research-agent"


def test_coordinator_processes_completed_result():
    workflow = Workflow(
        name="test-workflow",
        description="Test workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            )
        ],
    )

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id="execution-result-123",
    )

    coordinator = WorkflowCoordinator(
        dispatcher=TaskDispatcher(
            TaskQueue("agentgrid-test-coordinator-results-task")
        ),
        result_queue=TaskResultQueue(
            "agentgrid-test-coordinator-results-result"
        ),
    )

    execution.mark_step_running("research")

    dispatched = coordinator.process_result(
        execution,
        {
            "task_id": "execution-result-123:research",
            "execution_id": "execution-result-123",
            "step_name": "research",
            "agent_name": "research-agent",
            "status": "completed",
            "attempt": 1,
            "result": {
                "findings": [
                    "AI orchestration",
                    "distributed workers",
                ]
            },
        },
    )

    assert dispatched == []

    assert execution.step_statuses["research"] == (
        StepStatus.COMPLETED
    )

    assert execution.step_results["research"] == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

def test_coordinator_dispatches_next_dependent_step():
    workflow = Workflow(
        name="test-workflow",
        description="Test workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            ),
            WorkflowStep(
                name="analysis",
                agent_name="analysis-agent",
                depends_on=["research"],
            ),
        ],
    )

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id="execution-dependency-123",
    )

    coordinator = WorkflowCoordinator(
        dispatcher=TaskDispatcher(
            TaskQueue("agentgrid-test-coordinator-dependency-task")
        ),
        result_queue=TaskResultQueue(
            "agentgrid-test-coordinator-dependency-result"
        ),
    )

    execution.mark_step_running("research")

    research_result = {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

    dispatched = coordinator.process_result(
        execution,
        {
            "task_id": "execution-dependency-123:research",
            "execution_id": "execution-dependency-123",
            "step_name": "research",
            "agent_name": "research-agent",
            "status": "completed",
            "attempt": 1,
            "result": research_result,
        },
    )

    assert dispatched == ["analysis"]

    assert execution.step_statuses["research"] == StepStatus.COMPLETED
    assert execution.step_results["research"] == research_result
    assert execution.step_statuses["analysis"] == StepStatus.RUNNING

def test_coordinator_enqueues_dependent_step_with_inputs():
    workflow = Workflow(
        name="test-workflow",
        description="Test workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            ),
            WorkflowStep(
                name="analysis",
                agent_name="analysis-agent",
                depends_on=["research"],
            ),
        ],
    )

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id="execution-queue-123",
    )

    task_queue = TaskQueue(
        "agentgrid-test-coordinator-dependent-task"
    )

    coordinator = WorkflowCoordinator(
        dispatcher=TaskDispatcher(task_queue),
        result_queue=TaskResultQueue(
            "agentgrid-test-coordinator-dependent-result"
        ),
    )

    execution.mark_step_running("research")

    research_result = {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

    coordinator.process_result(
        execution,
        {
            "task_id": "execution-queue-123:research",
            "execution_id": "execution-queue-123",
            "step_name": "research",
            "agent_name": "research-agent",
            "status": "completed",
            "attempt": 1,
            "result": research_result,
        },
    )

    task = task_queue.dequeue()

    assert task is not None
    assert task["task_id"] == "execution-queue-123:analysis"
    assert task["execution_id"] == "execution-queue-123"
    assert task["step_name"] == "analysis"
    assert task["agent_name"] == "analysis-agent"
    assert task["inputs"] == {
        "research": research_result,
    }


def test_worker_result_can_be_consumed_by_coordinator():
    workflow = Workflow(
        name="test-workflow",
        description="Test workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            ),
            WorkflowStep(
                name="analysis",
                agent_name="analysis-agent",
                depends_on=["research"],
            ),
        ],
    )

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id="execution-worker-coordinator-123",
    )

    task_queue = TaskQueue(
        "agentgrid-test-worker-coordinator-task-v2"
    )

    result_queue = TaskResultQueue(
        "agentgrid-test-worker-coordinator-result-v2"
    )

    coordinator = WorkflowCoordinator(
        dispatcher=TaskDispatcher(task_queue),
        result_queue=result_queue,
    )

    def research_handler(*, step_name, inputs):
        return {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ]
        }

    worker = Worker(
        queue=task_queue,
        agent_handlers={
            "research-agent": research_handler,
        },
        result_queue=result_queue,
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid-test-worker-coordinator-v2"
        ),
    )

    execution.mark_step_running("research")

    coordinator.dispatcher.dispatch(
        task_id="execution-worker-coordinator-123:research",
        execution_id="execution-worker-coordinator-123",
        step_name="research",
        agent_name="research-agent",
        inputs={},
    )

    worker_result = worker.process_one()

    assert worker_result is not None
    assert worker_result["status"] == "completed"

    published_result = result_queue.consume()

    assert published_result is not None
    assert published_result["execution_id"] == (
        "execution-worker-coordinator-123"
    )
    assert published_result["step_name"] == "research"
    assert published_result["agent_name"] == "research-agent"
    assert published_result["status"] == "completed"

    dispatched = coordinator.process_result(
        execution,
        published_result,
    )

    assert dispatched == ["analysis"]
    assert execution.step_statuses["research"] == StepStatus.COMPLETED
    assert execution.step_results["research"] == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }
    assert execution.step_statuses["analysis"] == StepStatus.RUNNING

def test_distributed_two_step_workflow():
    workflow = Workflow(
        name="distributed-research",
        description="Two-step distributed research workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            ),
            WorkflowStep(
                name="analysis",
                agent_name="analysis-agent",
                depends_on=["research"],
            ),
        ],
    )

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id="execution-distributed-123",
    )

    task_queue = TaskQueue(
        "agentgrid-test-distributed-workflow-task"
    )

    result_queue = TaskResultQueue(
        "agentgrid-test-distributed-workflow-result"
    )

    coordinator = WorkflowCoordinator(
        dispatcher=TaskDispatcher(task_queue),
        result_queue=result_queue,
    )

    research_idempotency = IdempotencyStore(
        key_prefix="agentgrid-test-distributed-research-v2"
    )

    analysis_idempotency = IdempotencyStore(
        key_prefix="agentgrid-test-distributed-analysis-v2"
    )

    def research_handler(*, step_name, inputs):
        return {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ]
        }

    def analysis_handler(*, step_name, inputs):
        research = inputs["research"]

        return {
            "analysis": (
                f"Analyzed {len(research['findings'])} findings."
            )
        }

    research_worker = Worker(
        queue=task_queue,
        agent_handlers={
            "research-agent": research_handler,
        },
        result_queue=result_queue,
        idempotency_store=research_idempotency,
    )

    analysis_worker = Worker(
        queue=task_queue,
        agent_handlers={
            "analysis-agent": analysis_handler,
        },
        result_queue=result_queue,
        idempotency_store=analysis_idempotency,
    )

    dispatched = coordinator.dispatch_ready_steps(execution)

    assert dispatched == ["research"]
    assert execution.step_statuses["research"] == StepStatus.RUNNING

    research_task = task_queue.dequeue()

    assert research_task is not None
    assert research_task["step_name"] == "research"
    assert research_task["agent_name"] == "research-agent"

    task_queue.enqueue(research_task)

    research_worker_result = research_worker.process_one()

    assert research_worker_result is not None
    assert research_worker_result["status"] == "completed"

    research_result = result_queue.consume()

    assert research_result is not None
    assert research_result["step_name"] == "research"

    dispatched = coordinator.process_result(
        execution,
        research_result,
    )

    assert dispatched == ["analysis"]
    assert execution.step_statuses["research"] == StepStatus.COMPLETED
    assert execution.step_statuses["analysis"] == StepStatus.RUNNING

    analysis_task = task_queue.dequeue()

    assert analysis_task is not None
    assert analysis_task["step_name"] == "analysis"
    assert analysis_task["agent_name"] == "analysis-agent"
    assert analysis_task["inputs"] == {
        "research": {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ]
        }
    }

    task_queue.enqueue(analysis_task)

    analysis_worker_result = analysis_worker.process_one()

    assert analysis_worker_result is not None
    assert analysis_worker_result["status"] == "completed"

    analysis_result = result_queue.consume()

    assert analysis_result is not None
    assert analysis_result["step_name"] == "analysis"

    coordinator.process_result(
        execution,
        analysis_result,
    )

    assert execution.step_statuses["research"] == StepStatus.COMPLETED
    assert execution.step_statuses["analysis"] == StepStatus.COMPLETED
    assert execution.status == WorkflowStatus.COMPLETED

    assert execution.step_results["analysis"] == {
        "analysis": "Analyzed 2 findings."
    }