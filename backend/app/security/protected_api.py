from __future__ import annotations

from fastapi import Depends

from app.models.api_key import APIKey
from app.security.rate_limit import require_rate_limit
from app.security.scope_auth import require_scope
from app.security.scopes import APIScope


def require_scope_with_rate_limit(scope: APIScope):
    scope_dependency = require_scope(scope)

    def dependency(
        api_key: APIKey = Depends(require_rate_limit),
    ) -> APIKey:
        return scope_dependency(api_key)

    return dependency