from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] | None = Field(
        default=None,
        description="Scopes to assign to the API key.",
    )


class APIKeyCreateResponse(BaseModel):
    key_id: str
    name: str
    api_key: str
    scopes: list[str]
    enabled: bool
    created_at: datetime


class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    scopes: list[str]
    enabled: bool
    created_at: datetime


class APIKeyListResponse(BaseModel):
    api_keys: list[APIKeyResponse]
    count: int


class APIKeyScopeUpdateRequest(BaseModel):
    scopes: list[str]