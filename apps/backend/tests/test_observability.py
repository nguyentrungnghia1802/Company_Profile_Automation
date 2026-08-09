"""Tests for observability endpoints (/health, /ready, /metrics) and MetricsCollector."""

from fastapi.testclient import TestClient

from company_profile.api.app import create_app
from company_profile.operations.metrics import MetricsCollector


def test_metrics_collector_prometheus_output() -> None:
    """Test MetricsCollector format and metrics counters."""
    collector = MetricsCollector.get_instance()
    collector.record_http_request("GET", "/api/v1/companies", 200)
    collector.record_job_execution("research", "completed")
    collector.record_ai_run("gemini", "success")

    output = collector.generate_prometheus_metrics()

    assert "# HELP vcps_http_requests_total" in output
    assert "# TYPE vcps_http_requests_total counter" in output
    assert 'vcps_http_requests_total{method="GET",path="/api/v1/companies",status="200"}' in output
    assert "# HELP vcps_confidence_score_avg" in output
    assert "vcps_confidence_score_avg" in output


def test_metrics_endpoint_http() -> None:
    """Test GET /api/v1/metrics HTTP endpoint."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "vcps_confidence_score_avg" in response.text
