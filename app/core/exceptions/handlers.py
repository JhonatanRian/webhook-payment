from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions.domain_exceptions import (
    BusinessRuleViolationError,
    DuplicateEntityError,
    DuplicateEventError,
    EntityNotFoundError,
    WebhookSignatureError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message},
        )

    @app.exception_handler(DuplicateEntityError)
    async def duplicate_entity_handler(request: Request, exc: DuplicateEntityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(DuplicateEventError)
    async def duplicate_event_handler(request: Request, exc: DuplicateEventError) -> JSONResponse:
        # Idempotency response: return 200 OK so webhook sender doesn't retry unnecessarily
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": exc.message, "status": "ignored_duplicate"},
        )

    @app.exception_handler(WebhookSignatureError)
    async def webhook_signature_handler(
        request: Request, exc: WebhookSignatureError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

    @app.exception_handler(BusinessRuleViolationError)
    async def business_rule_handler(
        request: Request, exc: BusinessRuleViolationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.message},
        )
