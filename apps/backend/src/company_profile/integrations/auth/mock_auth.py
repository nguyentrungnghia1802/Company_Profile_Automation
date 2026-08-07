"""Mock AuthProvider implementation for local development and testing."""

from __future__ import annotations

from company_profile.integrations.auth.protocol import AuthProvider, AuthSubjectContext


class MockActor:
    """Mock authenticated actor context."""

    def __init__(
        self,
        user_id: str = "usr_dev_001",
        email: str = "dev@example.com",
        workspace_id: str = "ws_dev_001",
        role: str = "researcher",
        capabilities: list[str] | None = None,
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.workspace_id = workspace_id
        self.role = role
        self.capabilities = capabilities or ["read_company", "create_research_job"]


class MockAuthProvider(AuthProvider):
    """Mock auth adapter supporting deterministic development tokens."""

    def __init__(
        self,
        default_actor: MockActor | None = None,
        default_subject: AuthSubjectContext | None = None,
    ) -> None:
        self.default_actor = default_actor or MockActor()
        if default_actor:
            self.default_subject = AuthSubjectContext(
                auth_provider="mock",
                auth_subject=default_actor.user_id,
                email=default_actor.email,
                display_name="Mock User",
                preferred_locale="vi",
            )
        else:
            self.default_subject = default_subject or AuthSubjectContext(
                auth_provider="mock",
                auth_subject="sub_dev_researcher_001",
                email="researcher@example.com",
                display_name="Dev Researcher",
                preferred_locale="vi",
            )

    async def verify_token(self, token: str) -> AuthSubjectContext:
        """Verify dev token and return subject identity context."""
        if token == "invalid" or token == "mock-token-invalid":
            raise ValueError("AUTH_INVALID_TOKEN")

        if token == "mock-token-admin":
            return AuthSubjectContext(
                auth_provider="mock",
                auth_subject="sub_dev_admin_001",
                email="admin@example.com",
                display_name="Dev Admin",
                preferred_locale="vi",
            )

        if token == "mock-token-reviewer":
            return AuthSubjectContext(
                auth_provider="mock",
                auth_subject="sub_dev_reviewer_001",
                email="reviewer@example.com",
                display_name="Dev Reviewer",
                preferred_locale="vi",
            )

        if token == "mock-token-researcher":
            return AuthSubjectContext(
                auth_provider="mock",
                auth_subject="sub_dev_researcher_001",
                email="researcher@example.com",
                display_name="Dev Researcher",
                preferred_locale="vi",
            )

        return self.default_subject
