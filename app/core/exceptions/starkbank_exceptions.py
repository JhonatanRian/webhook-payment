from typing import Any

from app.core.exceptions.base import BaseError


class StarkBankIntegrationError(BaseError):
    """Base exception for all Stark Bank SDK integration errors."""

    def __init__(
        self,
        message: str = "An error occurred while communicating with Stark Bank API.",
        error_code: str | None = None,
        raw_error: Exception | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.error_code = error_code or "starkbank_error"
        self.raw_error = raw_error
        self.details = details or []
        super().__init__(message)


class StarkBankAuthenticationError(StarkBankIntegrationError):
    """Raised when authentication fails (invalid project ID, signature, or private key)."""

    def __init__(
        self,
        message: str = (
            "Stark Bank authentication failed: Provided digital signature "
            "or Project ID does not check out."
        ),
        raw_error: Exception | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="invalid_credentials",
            raw_error=raw_error,
            details=details,
        )


class StarkBankValidationError(StarkBankIntegrationError):
    """Raised when request payload or parameters are rejected by Stark Bank."""

    def __init__(
        self,
        message: str = "Invalid request parameters rejected by Stark Bank API.",
        raw_error: Exception | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="validation_error",
            raw_error=raw_error,
            details=details,
        )


class StarkBankServerError(StarkBankIntegrationError):
    """Raised when Stark Bank servers respond with 5xx internal server errors."""

    def __init__(
        self,
        message: str = "Stark Bank internal server error. Please try again later.",
        raw_error: Exception | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="server_error",
            raw_error=raw_error,
        )


class StarkBankNetworkError(StarkBankIntegrationError):
    """Raised when network connection or request times out while reaching Stark Bank API."""

    def __init__(
        self,
        message: str = "Network connection failure or timeout reaching Stark Bank API.",
        raw_error: Exception | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="network_error",
            raw_error=raw_error,
        )
