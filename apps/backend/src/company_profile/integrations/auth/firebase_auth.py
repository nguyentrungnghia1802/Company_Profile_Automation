"""Firebase / Identity Platform AuthProvider adapter (OD-001 placeholder)."""

from __future__ import annotations

from company_profile.integrations.auth.protocol import AuthProvider, AuthSubjectContext


class FirebaseAuthAdapter(AuthProvider):
    """Production Firebase / Identity Platform token verification adapter."""

    def __init__(self, project_id: str = "") -> None:
        self.project_id = project_id

    async def verify_token(self, token: str) -> AuthSubjectContext:
        """Verify Firebase ID token placeholder."""
        if not token or token == "invalid":
            raise ValueError("AUTH_INVALID_TOKEN")

        return AuthSubjectContext(
            auth_provider="firebase",
            auth_subject=f"firebase_sub_{token[:10]}",
            email="user@firebase.example.com",
            display_name="Firebase User",
            preferred_locale="vi",
        )
