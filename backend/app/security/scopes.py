from enum import StrEnum


class APIScope(StrEnum):
    WORKFLOWS_READ = "workflows:read"
    WORKFLOWS_EXECUTE = "workflows:execute"
    EXECUTIONS_READ = "executions:read"
    EXECUTIONS_CONTROL = "executions:control"
    WORKERS_READ = "workers:read"
    API_KEYS_MANAGE = "api_keys:manage"