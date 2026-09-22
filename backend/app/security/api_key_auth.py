from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import SessionLocal
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService

bearer_scheme = HTTPBearer(auto_error=False)

api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = api_key_service.authenticate(credentials.credentials)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key