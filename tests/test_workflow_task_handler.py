from app.workers.workflow_task_handler import WorkflowTaskHandler


class FakeRuntime:
    def __init__(self):
        self.calls = []

    def execute_agent(self, agent_name, **kwargs):
        self.calls.append(
            {
                "agent_name": agent_name,
                "kwargs": kwargs,
            }
        )

        return {
            "result": "agent executed",
        }


def test_workflow_task_handler_executes_agent():
    runtime = FakeRuntime()

    handler = WorkflowTaskHandler(
        runtime,
        agent_name="research-agent",
    )

    result = handler.handle(
        step_name="research",
        inputs={
            "input": "distributed AI orchestration",
        },
    )

    assert result == {
        "result": "agent executed",
    }

    assert runtime.calls == [
        {
            "agent_name": "research-agent",
            "kwargs": {
                "inputs": {
                    "input": "distributed AI orchestration",
                },
                "step_name": "research",
            },
        }
    ]