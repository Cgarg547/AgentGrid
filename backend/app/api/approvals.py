from fastapi import APIRouter, Depends, HTTPException

from app.models.approval_api import (
    ApprovalExecutionResponse,
    ApprovalResponse,
)
from app.runtime import AgentGridRuntime
from app.security.approval_store import ApprovalStore
from app.security.protected_api import require_scope_with_rate_limit
from app.security.scopes import APIScope


router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
)


runtime = AgentGridRuntime()
approval_store = runtime.approval_store
executor = runtime.get_approval_executor()


def _to_response(request):
    return request.describe()


@router.get(
    "/{request_id}",
    response_model=ApprovalResponse,
)
def get_approval(
    request_id: str,
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),
):
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
def approve_request(
    request_id: str,
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_CONTROL
        )
    ),
):
    try:
        request = approval_store.approve(
            request_id
        )

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
def reject_request(
    request_id: str,
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_CONTROL
        )
    ),
):
    try:
        request = approval_store.reject(
            request_id
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

    return _to_response(request)