"""Transaction helper for async database sessions."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transactional(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Execute operations inside an explicit database transaction.

    Commits on successful block completion, rolls back on exception.
    """
    if session.in_transaction():
        yield session
    else:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
