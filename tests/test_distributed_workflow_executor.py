from app.core.database import SessionLocal
from app.services.distributed_workflow_executor import (
    DistributedWorkflowExecutor,
)
from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
from app.services.task_dispatcher import TaskDispatcher
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue
from app.workflows.execution import WorkflowExecution
from app.workflows.workflow import Workflow, WorkflowStep
from app.workflows.workflow_state import StepStatus


def test_distributed_executor_starts_workflow():
    workflow = Workflow(
        name="test-workflow",
        description="Test distributed workflow",
        steps=[
            WorkflowStep(
                name="research",
                agent_name="research-agent",
            ),
        ],
    )

    task_queue = TaskQueue(
        "agentgrid-test-distributed-executor-task"
    )

    result_queue = TaskResultQueue(
        "agentgrid-test-distributed-executor-result"
    )

    execution_repository = PostgresExecutionRepository(
        SessionLocal
    )

    executor = DistributedWorkflowExecutor(
        dispatcher=TaskDispatcher(task_queue),
        result_queue=result_queue,
        execution_repository=execution_repository,
    )

    execution = executor.start(
        workflow,
        inputs={
            "topic": "AI orchestration",
        },
    )

    assert isinstance(execution, WorkflowExecution)
    assert execution.step_statuses["research"] == StepStatus.RUNNING

    task = task_queue.dequeue()

    assert task is not None
    assert task["execution_id"] == execution.execution_id
    assert task["step_name"] == "research"
    assert task["agent_name"] == "research-agent"
    assert task["inputs"] == {
        "topic": "AI orchestration",
    }

    persisted_execution = execution_repository.get(
        execution.execution_id
    )

    assert persisted_execution is not None
    assert persisted_execution.execution_id == execution.execution_id
    assert persisted_execution.workflow_name == "test-workflow"
    assert persisted_execution.status == execution.status.value
    assert persisted_execution.step_statuses["research"] == "running"


def test_distributed_executor_processes_result_and_dispatches_next_step():
    workflow = Workflow(
        name="test-workflow",
        description="Test distributed workflow",
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

    task_queue = TaskQueue(
        "agentgrid-test-distributed-executor-result-task-v3"
    )

    result_queue = TaskResultQueue(
        "agentgrid-test-distributed-executor-result-result-v3"
    )

    execution_repository = PostgresExecutionRepository(
        SessionLocal
    )

    executor = DistributedWorkflowExecutor(
        dispatcher=TaskDispatcher(task_queue),
        result_queue=result_queue,
        execution_repository=execution_repository,
    )

    execution = executor.start(workflow)
    initial_task = task_queue.dequeue()

    assert initial_task is not None
    assert initial_task["execution_id"] == execution.execution_id
    assert initial_task["step_name"] == "research"
    assert initial_task["agent_name"] == "research-agent"

    research_result = {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

    updated_execution = executor.process_result(
        execution,
        {
            "task_id": f"{execution.execution_id}:research",
            "execution_id": execution.execution_id,
            "step_name": "research",
            "agent_name": "research-agent",
            "status": "completed",
            "attempt": 1,
            "result": research_result,
        },
    )

    assert updated_execution is execution

    assert execution.step_statuses["research"] == StepStatus.COMPLETED

    assert execution.step_results["research"] == research_result

    assert execution.step_statuses["analysis"] == StepStatus.RUNNING

    analysis_task = task_queue.dequeue()

    assert analysis_task is not None
    assert analysis_task["execution_id"] == execution.execution_id
    assert analysis_task["step_name"] == "analysis"
    assert analysis_task["agent_name"] == "analysis-agent"
    assert analysis_task["inputs"] == {
        "research": research_result,
    }

    persisted_execution = execution_repository.get(
        execution.execution_id
    )

    assert persisted_execution is not None
    assert persisted_execution.execution_id == execution.execution_id
    assert persisted_execution.workflow_name == "test-workflow"
    assert persisted_execution.step_statuses["research"] == "completed"
    assert persisted_execution.step_statuses["analysis"] == "running"
    assert persisted_execution.step_results["research"] == research_result