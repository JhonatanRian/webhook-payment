import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response access logging and correlation tracking."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id

        client_host = request.client.host if request.client else "unknown"
        start_time = time.perf_counter()

        logger.info(
            "--> HTTP %s %s [request_id=%s, client=%s]",
            request.method,
            request.url.path,
            request_id,
            client_host,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "<-- HTTP %s %s 500 Internal Server Error [%.2fms] [request_id=%s]: %s",
                request.method,
                request.url.path,
                duration_ms,
                request_id,
                exc,
                exc_info=True,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "An internal server error occurred."},
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id

        status_code = response.status_code
        if status_code < 400:
            logger.info(
                "<-- HTTP %s %s %d OK [%.2fms] [request_id=%s]",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                request_id,
            )
        elif status_code < 500:
            logger.warning(
                "<-- HTTP %s %s %d Client Error [%.2fms] [request_id=%s]",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                request_id,
            )
        else:
            logger.error(
                "<-- HTTP %s %s %d Server Error [%.2fms] [request_id=%s]",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                request_id,
            )

        if logger.isEnabledFor(logging.DEBUG):
            response_body_bytes = b""
            if hasattr(response, "body") and response.body:
                response_body_bytes = response.body
            elif hasattr(response, "body_iterator") and response.body_iterator is not None:
                body_chunks: list[bytes] = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk)
                response_body_bytes = b"".join(body_chunks)

                async def new_body_iterator():
                    for c in body_chunks:
                        yield c

                response.body_iterator = new_body_iterator()

            body_str = response_body_bytes.decode("utf-8", errors="replace")
            logger.debug(
                "<-- HTTP %s %s Response Payload [request_id=%s]: %s",
                request.method,
                request.url.path,
                request_id,
                body_str,
            )

        return response
