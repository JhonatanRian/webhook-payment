import pytest
import starkbank
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions.handlers import register_exception_handlers
from app.core.exceptions.starkbank_exceptions import (
    StarkBankAuthenticationError,
    StarkBankIntegrationError,
    StarkBankNetworkError,
    StarkBankServerError,
    StarkBankValidationError,
)
from app.core.exceptions.starkbank_mapper import handle_starkbank_exception


def test_handle_invalid_credentials_input_error() -> None:
    # Simulate StarkBank InputErrors with invalidCredentials code
    err_dict = {"code": "invalidCredentials", "message": "Signature does not check out."}
    input_err = starkbank.error.InputErrors([err_dict])

    result = handle_starkbank_exception(input_err)

    assert isinstance(result, StarkBankAuthenticationError)
    assert result.error_code == "invalid_credentials"
    assert len(result.details) == 1
    assert result.details[0]["code"] == "invalidCredentials"


def test_handle_validation_input_error() -> None:
    err_dict = {"code": "invalidTaxId", "message": "Tax ID is invalid."}
    input_err = starkbank.error.InputErrors([err_dict])

    result = handle_starkbank_exception(input_err)

    assert isinstance(result, StarkBankValidationError)
    assert result.error_code == "validation_error"
    assert len(result.details) == 1
    assert result.details[0]["code"] == "invalidTaxId"


def test_handle_internal_server_error() -> None:
    server_err = starkbank.error.InternalServerError("StarkBank 500 internal server error")

    result = handle_starkbank_exception(server_err)

    assert isinstance(result, StarkBankServerError)
    assert result.error_code == "server_error"


def test_handle_invalid_signature_error() -> None:
    sig_err = starkbank.error.InvalidSignatureError("Bad signature")

    result = handle_starkbank_exception(sig_err)

    assert isinstance(result, StarkBankAuthenticationError)
    assert result.error_code == "invalid_credentials"


def test_handle_network_timeout_error() -> None:
    timeout_err = TimeoutError("Connection timed out")

    result = handle_starkbank_exception(timeout_err)

    assert isinstance(result, StarkBankNetworkError)
    assert result.error_code == "network_error"


def test_handle_generic_stark_error() -> None:
    generic_err = starkbank.error.StarkError("Unknown SDK issue")

    result = handle_starkbank_exception(generic_err)

    assert isinstance(result, StarkBankIntegrationError)
    assert result.error_code == "starkbank_error"


@pytest.mark.asyncio
async def test_fastapi_exception_handlers_formatting() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test-auth-error")
    async def route_auth_error() -> None:
        err_dict = {"code": "invalidCredentials", "message": "Signature failure"}
        raw_err = starkbank.error.InputErrors([err_dict])
        raise handle_starkbank_exception(raw_err)

    @app.get("/test-validation-error")
    async def route_val_error() -> None:
        err_dict = {"code": "invalidAmount", "message": "Amount must be positive"}
        raw_err = starkbank.error.InputErrors([err_dict])
        raise handle_starkbank_exception(raw_err)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Test Auth error endpoint -> should return 401
        res_auth = await client.get("/test-auth-error")
        assert res_auth.status_code == 401
        body_auth = res_auth.json()
        assert body_auth["error"] == "starkbank_authentication_failed"
        assert body_auth["code"] == "invalid_credentials"

        # Test Validation error endpoint -> should return 422
        res_val = await client.get("/test-validation-error")
        assert res_val.status_code == 422
        body_val = res_val.json()
        assert body_val["error"] == "starkbank_validation_failed"
        assert body_val["code"] == "validation_error"
