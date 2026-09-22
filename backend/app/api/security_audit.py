from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.database import SessionLocal
from app.models.api_key import APIKey
from app.models.security_audit_api import (
    SecurityAuditEventListResponse,
    SecurityAuditEventResponse,
)
from app.security.protected_api import require_scope_with_rate_limit
from app.security.scopes import APIScope
from app.services.security_audit_repository import SecurityAuditRepository
from app.security.rate_limit import require_rate_limit


router = APIRouter(
    prefix="/security/audit",
    tags=["security-audit"],
)


security_audit_repository = SecurityAuditRepository(SessionLocal)


@router.get(
    "",
    response_model=SecurityAuditEventListResponse,
)
def list_security_audit_events(
    key_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    api_key: APIKey = Depends(
        require_scope_with_rate_limit(APIScope.API_KEYS_MANAGE)
    ),
):
    events = security_audit_repository.list(
        key_id=key_id,
        action=action,
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
    )

    return SecurityAuditEventListResponse(
        events=[
            SecurityAuditEventResponse(
                event_id=event.event_id,
                key_id=event.key_id,
                action=event.action,
                resource=event.resource,
                endpoint=event.endpoint,
                outcome=event.outcome,
                timestamp=event.timestamp,
                metadata=(
                    security_audit_repository.deserialize_metadata(
                        event.metadata_json
                    )
                ),
            )
            for event in events
        ]
    )