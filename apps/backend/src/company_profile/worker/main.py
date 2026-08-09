"""Worker process entrypoint with graceful shutdown."""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING

import structlog

from company_profile.config.settings import Settings, get_settings
from company_profile.worker.runner import WorkerRunner

if TYPE_CHECKING:
    from types import FrameType

logger = structlog.get_logger(__name__)

_shutdown_event = asyncio.Event()


def _handle_signal(signum: int, _frame: FrameType | None) -> None:
    """Handle termination signals for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    logger.info("shutdown_signal_received", signal=sig_name)
    _shutdown_event.set()


async def run_worker() -> None:
    """Start the durable PostgreSQL task runner and stop it gracefully."""
    logger.info("worker_starting")

    _shutdown_event.clear()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _shutdown_event.set)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, _handle_signal)

    settings = get_settings()
    runner = build_worker(settings)
    runner_task = asyncio.create_task(runner.start())
    logger.info("worker_ready", status="polling_for_jobs", worker_id=runner.worker_id)

    try:
        await _shutdown_event.wait()
    finally:
        logger.info("worker_shutting_down")
        runner.stop()
        await runner_task


def build_worker(settings: Settings | None = None) -> WorkerRunner:
    """Create the production worker from environment-backed settings."""
    config = settings or get_settings()
    return WorkerRunner(
        worker_id=config.worker_id,
        poll_interval=float(config.worker_poll_interval),
        batch_size=config.worker_batch_size,
        lease_seconds=config.worker_claim_lease_seconds,
    )


def main() -> None:
    """CLI entrypoint for the worker process."""
    # On Windows, signal handlers via loop.add_signal_handler are not supported,
    # so fall back to signal.signal for SIGINT (SIGTERM not available on Windows).
    if sys.platform == "win32":
        signal.signal(signal.SIGINT, _handle_signal)

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker_interrupted")


if __name__ == "__main__":
    main()
