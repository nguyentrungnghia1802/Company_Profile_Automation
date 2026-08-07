"""Mock AuthProvider implementation for local development and testing."""

from __future__ import annotations


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


class MockAuthProvider:
    """Mock auth adapter that accepts dev tokens or returns a fixed actor."""

    def __init__(self, default_actor: MockActor | None = None) -> None:
        self.default_actor = default_actor or MockActor()

    async def verify_token(self, token: str) -> MockActor:
        """Verify bearer token or return mock actor."""
        if token == "invalid":
            raise ValueError("AUTH_INVALID_TOKEN")
        return self.default_actor
