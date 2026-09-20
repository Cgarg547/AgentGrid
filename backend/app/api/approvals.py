from fastapi import APIRouter, HTTPException

from app.agents.agent import Agent
from app.agents.executor import AgentExecutor
from app.models.approval_api import (
    ApprovalExecutionResponse,
    ApprovalResponse,
)
from app.security.approval_store import ApprovalStore
from app.tools.registry import ToolRegistry
from app.tools.tool import Tool


router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
)


approval_store = ApprovalStore()


def _create_executor() -> AgentExecutor:
    agent = Agent(
        name="researcher",
        description="Research agent",
        allowed_tools=["send_email"],
    )

    registry = ToolRegistry()

    registry.register(
        Tool(
            name="send_email",
            description="Send an email",
            handler=lambda **kwargs: {
                "message": "email sent",
                "arguments": kwargs,
            },
        )
    )

    return AgentExecutor(
        agent=agent,
        tool_registry=registry,
        approval_store=approval_store,
    )


executor = _create_executor()


def _to_response(request) -> dict:
    return request.describe()


@router.get(
    "/{request_id}",
    response_model=ApprovalResponse,
)
def get_approval(request_id: str):
    request = approval_store.get(request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Approval request "
                f"'{request_id}' not found."
            ),
        )

    return _to_response(request)


@router.post(
    "/{request_id}/approve",
    response_model=ApprovalExecutionResponse,
)
def approve_request(request_id: str):
    try:
        request = approval_store.approve(request_id)

        execution_result = (
            executor.execute_approved_request(
                request_id
            )
        )

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Approval request "
                f"'{request_id}' not found."
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        )

    return {
        **request.describe(),
        "execution_result": execution_result,
    }


@router.post(
    "/{request_id}/reject",
    response_model=ApprovalResponse,
)
def reject_request(request_id: str):
    try:
        request = approval_store.reject(request_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Approval request "
                f"'{request_id}' not found."
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return _to_response(request)