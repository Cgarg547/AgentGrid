from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import SessionLocal
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.security_audit_repository import SecurityAuditRepository
from app.services.security_audit_service import SecurityAuditService


bearer_scheme = HTTPBearer(auto_error=False)

api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)

security_audit_service = SecurityAuditService(
    SecurityAuditRepository(SessionLocal)
)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    if credentials is None:
        security_audit_service.record_event(
            key_id=None,
            action="authentication",
            outcome="denied",
            metadata={
                "reason": "missing_api_key",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        security_audit_service.record_event(
            key_id=None,
            action="authentication",
            outcome="denied",
            metadata={
                "reason": "invalid_authentication_scheme",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = api_key_service.authenticate(
        credentials.credentials
    )

    if api_key is None:
        security_audit_service.record_event(
            key_id=None,
            action="authentication",
            outcome="denied",
            metadata={
                "reason": "invalid_or_disabled_api_key",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    security_audit_service.record_event(
        key_id=api_key.key_id,
        action="authentication",
        outcome="allowed",
    )

    return api_key