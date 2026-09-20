from app.agents.agent import Agent


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        if agent.name in self._agents:
            raise ValueError(
                f"Agent '{agent.name}' is already registered."
            )

        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        agent = self._agents.get(name)

        if agent is None:
            raise KeyError(
                f"Agent '{name}' is not registered."
            )

        return agent

    def list(self) -> list[Agent]:
        return list(self._agents.values())