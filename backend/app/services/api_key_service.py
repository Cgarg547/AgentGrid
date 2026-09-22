from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from app.models.api_key import APIKey
from app.services.api_key_repository import APIKeyRepository


class APIKeyService:
    DEFAULT_SCOPES = [
        "workflows:read",
        "workflows:execute",
        "executions:read",
        "executions:control",
        "workers:read",
    ]
    
    def __init__(self, repository: APIKeyRepository):
        self.repository = repository

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(
            raw_key.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _serialize_scopes(scopes: list[str]) -> str:
        return ",".join(
            sorted(set(scopes))
        )

    @staticmethod
    def _deserialize_scopes(scopes: str) -> list[str]:
        if not scopes:
            return []

        return [
            scope
            for scope in scopes.split(",")
            if scope
        ]

    def create_api_key(
        self,
        name: str,
        scopes: list[str] | None = None,
    ) -> tuple[APIKey, str]:
        raw_key = f"ag_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)

        api_key = APIKey(
            key_id=str(uuid4()),
            key_hash=key_hash,
            name=name,
            scopes=self._serialize_scopes(
                self.DEFAULT_SCOPES
                if scopes is None
                else scopes
            ),
            enabled=True,
            created_at=datetime.now(timezone.utc),
        )

        key_id = api_key.key_id

        self.repository.save(api_key)

        stored_api_key = self.repository.get(key_id)

        if stored_api_key is None:
            raise RuntimeError(
                f"Failed to retrieve created API key '{key_id}'."
            )

        return stored_api_key, raw_key

    def authenticate(
        self,
        raw_key: str,
    ) -> APIKey | None:
        key_hash = self._hash_key(raw_key)

        api_key = self.repository.get_by_hash(
            key_hash
        )

        if api_key is None:
            return None

        if not api_key.enabled:
            return None

        return api_key

    def get_api_key(
        self,
        key_id: str,
    ) -> APIKey | None:
        return self.repository.get(key_id)

    def list_api_keys(
        self,
        enabled: bool | None = None,
    ) -> list[APIKey]:
        return self.repository.list(
            enabled=enabled
        )

    def get_scopes(
        self,
        api_key: APIKey,
    ) -> list[str]:
        return self._deserialize_scopes(
            api_key.scopes
        )

    def has_scope(
        self,
        api_key: APIKey,
        scope: str,
    ) -> bool:
        return scope in self.get_scopes(api_key)

    def set_scopes(
        self,
        key_id: str,
        scopes: list[str],
    ) -> bool:
        api_key = self.repository.get(key_id)

        if api_key is None:
            return False

        api_key.scopes = self._serialize_scopes(
            scopes
        )

        self.repository.save(api_key)

        return True

    def enable_api_key(
        self,
        key_id: str,
    ) -> bool:
        api_key = self.repository.get(key_id)

        if api_key is None:
            return False

        api_key.enabled = True

        self.repository.save(api_key)

        return True

    def disable_api_key(
        self,
        key_id: str,
    ) -> bool:
        api_key = self.repository.get(key_id)

        if api_key is None:
            return False

        api_key.enabled = False

        self.repository.save(api_key)

        return True

    def delete_api_key(
        self,
        key_id: str,
    ) -> bool:
        return self.repository.delete(key_id)