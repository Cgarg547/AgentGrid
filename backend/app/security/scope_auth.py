from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.database import SessionLocal
from app.models.api_key import APIKey
from app.security.api_key_auth import require_api_key
from app.security.scopes import APIScope
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.security_audit_repository import SecurityAuditRepository
from app.services.security_audit_service import SecurityAuditService


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)

security_audit_service = SecurityAuditService(
    SecurityAuditRepository(SessionLocal)
)


def require_scope(scope: APIScope):
    def dependency(
        api_key: APIKey = Depends(require_api_key),
    ) -> APIKey:
        if not api_key_service.has_scope(
            api_key,
            scope.value,
        ):
            security_audit_service.record_event(
                key_id=api_key.key_id,
                action="authorization",
                outcome="denied",
                metadata={
                    "required_scope": scope.value,
                    "reason": "missing_required_scope",
                },
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Missing required scope: "
                    f"{scope.value}"
                ),
            )

        security_audit_service.record_event(
            key_id=api_key.key_id,
            action="authorization",
            outcome="allowed",
            metadata={
                "required_scope": scope.value,
            },
        )

        return api_key

    return dependency