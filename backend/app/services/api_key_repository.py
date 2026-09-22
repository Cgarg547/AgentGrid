from __future__ import annotations

from sqlalchemy import select

from app.models.api_key import APIKey


class APIKeyRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, api_key: APIKey) -> None:
        with self.session_factory() as session:
            existing = session.get(APIKey, api_key.key_id)

            if existing is None:
                session.add(api_key)
            else:
                existing.key_hash = api_key.key_hash
                existing.name = api_key.name
                existing.scopes = api_key.scopes
                existing.enabled = api_key.enabled
                existing.created_at = api_key.created_at

            session.commit()

    def get(self, key_id: str) -> APIKey | None:
        with self.session_factory() as session:
            api_key = session.get(APIKey, key_id)

            if api_key is None:
                return None

            session.expunge(api_key)
            return api_key

    def get_by_hash(self, key_hash: str) -> APIKey | None:
        with self.session_factory() as session:
            statement = select(APIKey).where(
                APIKey.key_hash == key_hash
            )

            api_key = session.scalars(statement).first()

            if api_key is None:
                return None

            session.expunge(api_key)
            return api_key

    def list(
        self,
        enabled: bool | None = None,
    ) -> list[APIKey]:
        with self.session_factory() as session:
            statement = select(APIKey)

            if enabled is not None:
                statement = statement.where(
                    APIKey.enabled == enabled
                )

            statement = statement.order_by(
                APIKey.created_at.asc()
            )

            api_keys = list(
                session.scalars(statement).all()
            )

            for api_key in api_keys:
                session.expunge(api_key)

            return api_keys

    def delete(self, key_id: str) -> bool:
        with self.session_factory() as session:
            api_key = session.get(APIKey, key_id)

            if api_key is None:
                return False

            session.delete(api_key)
            session.commit()
            return True