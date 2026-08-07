"""Unit and API tests for auth endpoints, token exchange, /me, and capability authorization."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from company_profile.api.dependencies import RequestActor, require_capability
from company_profile.api.errors import ForbiddenError

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_exchange_endpoint(async_client: AsyncClient) -> None:
    """Verify POST /api/v1/auth/exchange with valid dev token."""
    response = await async_client.post(
        "/api/v1/auth/exchange", json={"token": "mock-token-researcher"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "researcher@example.com"


@pytest.mark.asyncio
async def test_auth_logout_endpoint(async_client: AsyncClient) -> None:
    """Verify POST /api/v1/auth/logout with active session."""
    headers = {"Authorization": "Bearer mock-token-researcher"}
    response = await async_client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_get_me_endpoint(async_client: AsyncClient) -> None:
    """Verify GET /api/v1/me returns current user details and workspace context."""
    headers = {"Authorization": "Bearer mock-token-researcher"}
    response = await async_client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["email"] == "researcher@example.com"


@pytest.mark.asyncio
async def test_update_me_endpoint(async_client: AsyncClient) -> None:
    """Verify PATCH /api/v1/me updates display_name and preferred_locale."""
    headers = {"Authorization": "Bearer mock-token-researcher"}
    response = await async_client.patch(
        "/api/v1/me",
        headers=headers,
        json={"display_name": "New Researcher Name", "preferred_locale": "en"},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["display_name"] == "New Researcher Name"
    assert res_data["data"]["preferred_locale"] == "en"


@pytest.mark.asyncio
async def test_require_capability_authorization() -> None:
    """Verify require_capability raises 403 ForbiddenError if capability missing."""
    dep = require_capability("policy:manage")
    actor = RequestActor(
        user_id="11111111-1111-4111-8111-111111111111",
        email="researcher@example.com",
        display_name="Researcher",
        preferred_locale="vi",
        status="active",
        active_workspace=None,
        workspaces=[],
        capabilities=["company:read"],
    )
    with pytest.raises(ForbiddenError):
        dep(actor)
