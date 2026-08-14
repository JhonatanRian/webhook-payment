import logging
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions.domain_exceptions import EntityNotFoundError
from app.core.exceptions.handlers import register_exception_handlers
from app.core.middleware import RequestLoggingMiddleware
from app.core.middleware import logger as middleware_logger


@pytest.mark.asyncio
async def test_middleware_request_id_generation_and_header() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ping": "pong"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/ping")
        assert res.status_code == 200
        assert "X-Request-ID" in res.headers
        assert len(res.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_middleware_preserves_provided_request_id() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ping": "pong"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        custom_id = "req_custom_12345"
        res = await client.get("/ping", headers={"X-Request-ID": custom_id})
        assert res.status_code == 200
        assert res.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_middleware_handled_domain_exception_logging() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    @app.get("/item")
    async def get_item() -> None:
        raise EntityNotFoundError("Item", "123")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/item")
        assert res.status_code == 404
        assert res.json() == {"detail": "Item with id 123 not found."}
        assert "X-Request-ID" in res.headers


@pytest.mark.asyncio
async def test_middleware_unhandled_exception_logging() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    @app.get("/bug")
    async def bug() -> None:
        raise RuntimeError("Unexpected failure!")

    # raise_app_exceptions=False simulates standard ASGI server behavior for 500 error responses
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/bug")
        assert res.status_code == 500
        assert res.json() == {"detail": "An internal server error occurred."}
        assert "X-Request-ID" in res.headers


@pytest.mark.asyncio
async def test_middleware_debug_level_response_body_logging() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/data")
    async def data() -> dict[str, str]:
        return {"status": "ok", "message": "hello world"}

    transport = ASGITransport(app=app)
    original_level = middleware_logger.level
    try:
        middleware_logger.setLevel(logging.DEBUG)
        with patch.object(middleware_logger, "debug") as mock_debug:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.get("/data")
                assert res.status_code == 200
                assert res.json() == {"status": "ok", "message": "hello world"}
                assert mock_debug.called
                debug_args = [call.args for call in mock_debug.call_args_list]
                body_logged = any(
                    "Response Payload" in arg[0] or "hello world" in str(arg) for arg in debug_args
                )
                assert body_logged
    finally:
        middleware_logger.setLevel(original_level)
