from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db, init_db


async def test_init_db() -> None:
    await init_db()


async def test_init_db_handles_already_exists() -> None:
    op_err = OperationalError("CREATE TABLE ...", {}, Exception("table already exists"))
    mock_conn = AsyncMock()
    mock_conn.run_sync.side_effect = op_err

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_ctx.__aexit__.return_value = None

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx

    with patch("app.infra.db.session.engine", mock_engine):
        # Should not raise exception
        await init_db()


async def test_init_db_raises_other_operational_error() -> None:
    op_err = OperationalError("CREATE TABLE ...", {}, Exception("disk full"))
    mock_conn = AsyncMock()
    mock_conn.run_sync.side_effect = op_err

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_ctx.__aexit__.return_value = None

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx

    with patch("app.infra.db.session.engine", mock_engine):
        with pytest.raises(OperationalError):
            await init_db()


async def test_get_db_generator() -> None:
    gen = get_db()
    session = await anext(gen)
    assert isinstance(session, AsyncSession)
    await gen.aclose()
