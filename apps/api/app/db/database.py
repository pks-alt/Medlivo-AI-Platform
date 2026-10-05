from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

from app.core.settings import settings


_pool: AsyncConnectionPool | None = None


async def open_database() -> None:
    global _pool
    if not settings.database_url:
        return

    _pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        open=False,
    )
    await _pool.open()
    await _pool.wait()


async def close_database() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def connection():
    if _pool is None:
        raise RuntimeError("Database pool is not configured.")
    async with _pool.connection() as conn:
        yield conn


def database_configured() -> bool:
    return _pool is not None
