"""Worker process entrypoint with graceful shutdown."""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING

import structlog

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
    """Main worker loop — claims and executes research job steps.

    This is a placeholder for Phase 3 (P3-006+). Currently it just
    starts, logs readiness, and waits for shutdown.
    """
    logger.info("worker_starting")

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown_event.set)

    logger.info("worker_ready", status="waiting_for_jobs")

    # Wait for shutdown signal
    await _shutdown_event.wait()

    logger.info("worker_shutting_down")
    # Future: wait for in-flight steps to finish within grace period


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
