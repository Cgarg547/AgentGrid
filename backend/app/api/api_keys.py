from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import SessionLocal
from app.models.api_key import APIKey
from app.models.api_key_api import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    APIKeyScopeUpdateRequest,
)
from app.security.scope_auth import require_scope
from app.security.scopes import APIScope
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"],
)


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def _to_response(api_key: APIKey) -> APIKeyResponse:
    return APIKeyResponse(
        key_id=api_key.key_id,
        name=api_key.name,
        scopes=api_key_service.get_scopes(api_key),
        enabled=api_key.enabled,
        created_at=api_key.created_at,
    )


@router.post(
    "",
    response_model=APIKeyCreateResponse,
)
def create_api_key(
    request: APIKeyCreateRequest,
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    api_key, raw_key = api_key_service.create_api_key(
        request.name,
        scopes=request.scopes,
    )

    return APIKeyCreateResponse(
        key_id=api_key.key_id,
        name=api_key.name,
        api_key=raw_key,
        scopes=api_key_service.get_scopes(api_key),
        enabled=api_key.enabled,
        created_at=api_key.created_at,
    )


@router.get(
    "",
    response_model=APIKeyListResponse,
)
def list_api_keys(
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    api_keys = api_key_service.list_api_keys()

    return APIKeyListResponse(
        api_keys=[
            _to_response(api_key)
            for api_key in api_keys
        ],
        count=len(api_keys),
    )


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
)
def get_api_key(
    key_id: str,
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    api_key = api_key_service.get_api_key(key_id)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    return _to_response(api_key)


@router.put(
    "/{key_id}/scopes",
    response_model=APIKeyResponse,
)
def update_api_key_scopes(
    key_id: str,
    request: APIKeyScopeUpdateRequest,
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    if not api_key_service.set_scopes(
        key_id,
        request.scopes,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    api_key = api_key_service.get_api_key(key_id)

    return _to_response(api_key)


@router.post(
    "/{key_id}/enable",
    response_model=APIKeyResponse,
)
def enable_api_key(
    key_id: str,
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    if not api_key_service.enable_api_key(key_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    api_key = api_key_service.get_api_key(key_id)

    return _to_response(api_key)


@router.post(
    "/{key_id}/disable",
    response_model=APIKeyResponse,
)
def disable_api_key(
    key_id: str,
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    if not api_key_service.disable_api_key(key_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    api_key = api_key_service.get_api_key(key_id)

    return _to_response(api_key)


@router.delete(
    "/{key_id}",
)
def delete_api_key(
    key_id: str,
    _current_api_key=Depends(
        require_scope(
            APIScope.API_KEYS_MANAGE
        )
    ),
):
    if not api_key_service.delete_api_key(key_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    return {
        "deleted": True,
        "key_id": key_id,
    }