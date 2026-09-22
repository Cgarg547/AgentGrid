from datetime import datetime

from pydantic import BaseModel


class SecurityAuditEventResponse(BaseModel):
    event_id: str
    key_id: str | None
    action: str
    resource: str | None
    endpoint: str | None
    outcome: str
    timestamp: datetime
    metadata: dict


class SecurityAuditEventListResponse(BaseModel):
    events: list[SecurityAuditEventResponse]