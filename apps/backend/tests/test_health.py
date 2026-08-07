"""Tests for health and readiness endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from company_profile.api.app import create_app

app = create_app()
client = TestClient(app)


def test_health_returns_ok() -> None:
    """Health endpoint returns 200 with status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_ready_returns_ok() -> None:
    """Readiness endpoint returns 200 with checks."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]
