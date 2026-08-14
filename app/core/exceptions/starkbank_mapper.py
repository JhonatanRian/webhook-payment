import logging
from typing import Any

import starkbank

from app.core.exceptions.starkbank_exceptions import (
    StarkBankAuthenticationError,
    StarkBankIntegrationError,
    StarkBankNetworkError,
    StarkBankServerError,
    StarkBankValidationError,
)

logger = logging.getLogger(__name__)


def handle_starkbank_exception(err: Exception) -> StarkBankIntegrationError:
    """Translates generic Stark Bank SDK / StarkCore exceptions into typed domain exceptions."""
    logger.error(
        "Stark Bank SDK exception caught: %s (%s)",
        err,
        type(err).__name__,
        exc_info=True,
    )

    if isinstance(err, starkbank.error.InputErrors):
        extracted_details: list[dict[str, Any]] = []
        is_auth_error = False
        if hasattr(err, "errors"):
            for e in err.errors:
                code = getattr(e, "code", None)
                msg = getattr(e, "message", str(e))
                extracted_details.append({"code": code, "message": msg})
                if code in ("invalidCredentials", "invalidSignature", "unauthorized"):
                    is_auth_error = True

        if is_auth_error:
            return StarkBankAuthenticationError(
                message=(
                    "Stark Bank authentication failed: Provided digital signature "
                    "or Project ID does not check out."
                ),
                raw_error=err,
                details=extracted_details,
            )

        return StarkBankValidationError(
            message=f"Request rejected by Stark Bank API: {err}",
            raw_error=err,
            details=extracted_details,
        )

    if isinstance(err, starkbank.error.InvalidSignatureError):
        return StarkBankAuthenticationError(
            message=f"Invalid digital signature for Stark Bank: {err}",
            raw_error=err,
        )

    if isinstance(err, starkbank.error.InternalServerError):
        return StarkBankServerError(
            message="Stark Bank servers are temporarily unavailable.",
            raw_error=err,
        )

    if isinstance(err, (TimeoutError, ConnectionError)):
        return StarkBankNetworkError(
            message="Network connection failure or timeout reaching Stark Bank.",
            raw_error=err,
        )

    if isinstance(err, starkbank.error.StarkError):
        return StarkBankIntegrationError(
            message=f"Stark Bank SDK error: {err}",
            raw_error=err,
        )

    return StarkBankIntegrationError(
        message=f"Unexpected error during Stark Bank integration: {err}",
        raw_error=err,
    )
