import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions.domain_exceptions import (
    BusinessRuleViolationError,
    DuplicateEntityError,
    DuplicateEventError,
    EntityNotFoundError,
    WebhookSignatureError,
)
from app.core.exceptions.starkbank_exceptions import (
    StarkBankAuthenticationError,
    StarkBankIntegrationError,
    StarkBankNetworkError,
    StarkBankServerError,
    StarkBankValidationError,
)

logger = logging.getLogger("app.exceptions")


def _register_domain_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        logger.warning(
            "Entity not found: %s [Path: %s %s]",
            exc.message,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message},
        )

    @app.exception_handler(DuplicateEntityError)
    async def duplicate_entity_handler(request: Request, exc: DuplicateEntityError) -> JSONResponse:
        logger.warning(
            "Duplicate entity error: %s [Path: %s %s]",
            exc.message,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(DuplicateEventError)
    async def duplicate_event_handler(request: Request, exc: DuplicateEventError) -> JSONResponse:
        logger.info(
            "Duplicate event ignored for idempotency: %s [Path: %s %s]",
            exc.message,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": exc.message, "status": "ignored_duplicate"},
        )

    @app.exception_handler(WebhookSignatureError)
    async def webhook_signature_handler(
        request: Request, exc: WebhookSignatureError
    ) -> JSONResponse:
        logger.warning(
            "Webhook signature verification failed: %s [Path: %s %s]",
            exc.message,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

    @app.exception_handler(BusinessRuleViolationError)
    async def business_rule_handler(
        request: Request, exc: BusinessRuleViolationError
    ) -> JSONResponse:
        logger.warning(
            "Business rule violation: %s [Path: %s %s]",
            exc.message,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.message},
        )


def _register_starkbank_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarkBankAuthenticationError)
    async def stark_auth_handler(
        request: Request, exc: StarkBankAuthenticationError
    ) -> JSONResponse:
        logger.error(
            "Stark Bank authentication error: %s (code=%s) [Path: %s %s]",
            exc.message,
            exc.error_code,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "starkbank_authentication_failed",
                "detail": exc.message,
                "code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(StarkBankValidationError)
    async def stark_validation_handler(
        request: Request, exc: StarkBankValidationError
    ) -> JSONResponse:
        logger.warning(
            "Stark Bank API validation rejected request: %s (code=%s) [Path: %s %s]",
            exc.message,
            exc.error_code,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "starkbank_validation_failed",
                "detail": exc.message,
                "code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(StarkBankServerError)
    async def stark_server_handler(request: Request, exc: StarkBankServerError) -> JSONResponse:
        logger.error(
            "Stark Bank API upstream server error: %s (code=%s) [Path: %s %s]",
            exc.message,
            exc.error_code,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "starkbank_server_error",
                "detail": exc.message,
                "code": exc.error_code,
            },
        )

    @app.exception_handler(StarkBankNetworkError)
    async def stark_network_handler(request: Request, exc: StarkBankNetworkError) -> JSONResponse:
        logger.error(
            "Stark Bank network timeout error: %s (code=%s) [Path: %s %s]",
            exc.message,
            exc.error_code,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "error": "starkbank_network_timeout",
                "detail": exc.message,
                "code": exc.error_code,
            },
        )

    @app.exception_handler(StarkBankIntegrationError)
    async def stark_integration_handler(
        request: Request, exc: StarkBankIntegrationError
    ) -> JSONResponse:
        logger.error(
            "Stark Bank integration exception: %s (code=%s) [Path: %s %s]",
            exc.message,
            exc.error_code,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "starkbank_integration_error",
                "detail": exc.message,
                "code": exc.error_code,
            },
        )


def _register_fallback_handler(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled server exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )


def register_exception_handlers(app: FastAPI) -> None:
    _register_domain_handlers(app)
    _register_starkbank_handlers(app)
    _register_fallback_handler(app)
