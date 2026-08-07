"""AuthProvider protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class AuthSubjectContext(BaseModel):
    """Subject context returned by AuthProvider token verification."""

    auth_provider: str
    auth_subject: str
    email: str | None = None
    display_name: str
    preferred_locale: str = "vi"

    @property
    def user_id(self) -> str:
        """Alias for auth_subject for actor compatibility."""
        return self.auth_subject


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for external authentication identity verification adapters."""

    async def verify_token(self, token: str) -> AuthSubjectContext:
        """Verify bearer token or ID token and return subject identity context."""
        ...
