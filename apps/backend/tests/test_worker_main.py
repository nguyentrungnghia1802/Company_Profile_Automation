"""Worker entrypoint regression tests."""

from company_profile.config.settings import Settings
from company_profile.modules.research.pipeline import ResearchPipelineError
from company_profile.worker.main import build_worker
from company_profile.worker.runner import WorkerRunner


def test_build_worker_uses_runtime_settings() -> None:
    """The container worker is configured to claim durable research tasks."""
    runner = build_worker(
        Settings(
            worker_id="worker-test",
            worker_poll_interval=7,
            worker_batch_size=3,
            worker_claim_lease_seconds=42,
        )
    )

    assert runner.worker_id == "worker-test"
    assert runner.poll_interval == 7.0
    assert runner.batch_size == 3
    assert runner.lease_seconds == 42


def test_worker_persists_safe_step_error_codes() -> None:
    """Raw exception text never becomes a task-facing provider payload."""
    assert (
        WorkerRunner.safe_task_error("source_fetch", ValueError("secret upstream response"))
        == "TASK_STEP_FAILED:source_fetch:VALUEERROR"
    )
    assert (
        WorkerRunner.safe_task_error(
            "entity_resolution", ResearchPipelineError("COMPANY_NOT_FOUND")
        )
        == "TASK_STEP_FAILED:entity_resolution:COMPANY_NOT_FOUND"
    )
