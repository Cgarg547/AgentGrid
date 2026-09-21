import pytest

from app.core.redis import redis_client
from app.runtime import AgentGridRuntime
from app.workflows.workflow_state import StepStatus

@pytest.fixture(autouse=True)
def clean_distributed_runtime_queues():
    redis_client.delete(
        "agentgrid:workflow:tasks",
        "agentgrid:workflow:results",
    )

    yield

    redis_client.delete(
        "agentgrid:workflow:tasks",
        "agentgrid:workflow:results",
    )

def test_runtime_starts_distributed_workflow():
    runtime = AgentGridRuntime()

    runtime.distributed_task_queue = runtime.distributed_task_queue

    execution = runtime.execute_workflow_distributed(
        workflow_name="research-pipeline",
        inputs={
            "topic": "AI orchestration",
        },
    )

    assert execution is not None

    assert execution.step_statuses["research"] == (
        StepStatus.RUNNING
    )

    task = runtime.distributed_task_queue.dequeue()

    assert task is not None

    assert task["execution_id"] == execution.execution_id
    assert task["step_name"] == "research"
    assert task["agent_name"] == "research-agent"
    assert task["inputs"] == {
        "topic": "AI orchestration",
    }

def test_runtime_distributed_worker_executes_research():
    runtime = AgentGridRuntime()

    execution = runtime.execute_workflow_distributed(
        workflow_name="research-pipeline",
        inputs={
            "topic": "AI orchestration",
        },
    )

    task = runtime.distributed_task_queue.dequeue()

    assert task is not None
    assert task["execution_id"] == execution.execution_id
    assert task["step_name"] == "research"
    assert task["agent_name"] == "research-agent"

    from app.workers.worker import Worker
    from app.workers.idempotency import IdempotencyStore

    worker = Worker(
        queue=runtime.distributed_task_queue,
        agent_handlers={
            "research-agent": (
                lambda *, step_name, inputs:
                runtime.execute_agent(
                    "research-agent",
                    step_name=step_name,
                    inputs=inputs,
                )
            )
        },
        result_queue=runtime.distributed_result_queue,
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid-test-runtime-worker-v1"
        ),
    )

    runtime.distributed_task_queue.enqueue(task)

    worker_result = worker.process_one()

    assert worker_result is not None
    assert worker_result["status"] == "completed"
    assert worker_result["execution_id"] == execution.execution_id
    assert worker_result["step_name"] == "research"

    published_result = (
        runtime.distributed_result_queue.consume()
    )

    assert published_result is not None
    assert published_result["execution_id"] == (
        execution.execution_id
    )
    assert published_result["step_name"] == "research"
    assert published_result["agent_name"] == "research-agent"
    assert published_result["status"] == "completed"
    assert published_result["result"] == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

def test_runtime_distributed_workflow_advances_to_reports():
    runtime = AgentGridRuntime()

    execution = runtime.execute_workflow_distributed(
        workflow_name="research-pipeline",
        inputs={
            "topic": "AI orchestration",
        },
    )

    from app.workers.worker import Worker
    from app.workers.idempotency import IdempotencyStore

    research_worker = Worker(
        queue=runtime.distributed_task_queue,
        agent_handlers={
            "research-agent": (
                lambda *, step_name, inputs:
                runtime.execute_agent(
                    "research-agent",
                    step_name=step_name,
                    inputs=inputs,
                )
            )
        },
        result_queue=runtime.distributed_result_queue,
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid-test-runtime-e2e-research-v1"
        ),
    )

    research_task = runtime.distributed_task_queue.dequeue()

    assert research_task is not None
    assert research_task["step_name"] == "research"

    runtime.distributed_task_queue.enqueue(research_task)

    research_worker_result = research_worker.process_one()

    assert research_worker_result is not None
    assert research_worker_result["status"] == "completed"

    research_result = (
        runtime.distributed_result_queue.consume()
    )

    assert research_result is not None
    assert research_result["execution_id"] == execution.execution_id
    assert research_result["step_name"] == "research"

    dispatched = runtime.distributed_workflow_executor.process_result(
        execution,
        research_result,
    )

    assert dispatched is execution
    assert execution.step_statuses["research"].value == "completed"
    assert execution.step_statuses["analysis"].value == "running"

    analysis_worker = Worker(
        queue=runtime.distributed_task_queue,
        agent_handlers={
            "analysis-agent": (
                lambda *, step_name, inputs:
                runtime.execute_agent(
                    "analysis-agent",
                    step_name=step_name,
                    inputs=inputs,
                )
            )
        },
        result_queue=runtime.distributed_result_queue,
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid-test-runtime-e2e-analysis-v1"
        ),
    )

    analysis_task = runtime.distributed_task_queue.dequeue()

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

    runtime.distributed_task_queue.enqueue(analysis_task)

    analysis_worker_result = analysis_worker.process_one()

    assert analysis_worker_result is not None
    assert analysis_worker_result["status"] == "completed"

    analysis_result = (
        runtime.distributed_result_queue.consume()
    )

    assert analysis_result is not None
    assert analysis_result["execution_id"] == execution.execution_id
    assert analysis_result["step_name"] == "analysis"
    assert analysis_result["agent_name"] == "analysis-agent"

    runtime.distributed_workflow_executor.process_result(
        execution,
        analysis_result,
    )

    assert execution.step_statuses["research"].value == "completed"
    assert execution.step_statuses["analysis"].value == "completed"
    assert execution.step_statuses["report"].value == "running"

    assert execution.status.value == "running"

    report_task = runtime.distributed_task_queue.dequeue()

    assert report_task is not None
    assert report_task["execution_id"] == execution.execution_id
    assert report_task["step_name"] == "report"
    assert report_task["agent_name"] == "writer-agent"
    assert report_task["inputs"] == {
        "analysis": {
            "analysis": "Analyzed 2 findings."
        }
    }

    writer_worker = Worker(
        queue=runtime.distributed_task_queue,
        agent_handlers={
            "writer-agent": (
                lambda *, step_name, inputs:
                runtime.execute_agent(
                    "writer-agent",
                    step_name=step_name,
                    inputs=inputs,
                )
            )
        },
        result_queue=runtime.distributed_result_queue,
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid-test-runtime-e2e-writer-v1"
        ),
    )

    runtime.distributed_task_queue.enqueue(report_task)

    writer_worker_result = writer_worker.process_one()

    assert writer_worker_result is not None
    assert writer_worker_result["status"] == "completed"
    assert writer_worker_result["execution_id"] == execution.execution_id
    assert writer_worker_result["step_name"] == "report"
    assert writer_worker_result["agent_name"] == "writer-agent"

    report_result = (
        runtime.distributed_result_queue.consume()
    )

    assert report_result is not None
    assert report_result["execution_id"] == execution.execution_id
    assert report_result["step_name"] == "report"
    assert report_result["agent_name"] == "writer-agent"
    assert report_result["status"] == "completed"
    assert report_result["result"] == {
        "report": "Analyzed 2 findings."
    }

    runtime.distributed_workflow_executor.process_result(
        execution,
        report_result,
    )

    assert execution.step_statuses["research"].value == "completed"
    assert execution.step_statuses["analysis"].value == "completed"
    assert execution.step_statuses["report"].value == "completed"

    assert execution.status.value == "completed"

    assert execution.step_results["report"] == {
        "report": "Analyzed 2 findings."
    }