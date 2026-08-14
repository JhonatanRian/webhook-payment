from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.exceptions.domain_exceptions import (
    BusinessRuleViolationError,
    DuplicateEntityError,
    DuplicateEventError,
    EntityNotFoundError,
    WebhookSignatureError,
)
from app.core.exceptions.handlers import register_exception_handlers
from app.core.exceptions.starkbank_exceptions import (
    StarkBankAuthenticationError,
    StarkBankIntegrationError,
    StarkBankNetworkError,
    StarkBankServerError,
    StarkBankValidationError,
)


def test_domain_exception_messages() -> None:
    not_found = EntityNotFoundError("Invoice", "123")
    assert "Invoice with id 123 not found" in not_found.message

    dup_entity = DuplicateEntityError("Duplicate invoice")
    assert dup_entity.message == "Duplicate invoice"

    dup_event = DuplicateEventError("evt_99")
    assert "evt_99" in dup_event.message
    assert dup_event.event_id == "evt_99"

    sig_err = WebhookSignatureError("Bad signature")
    assert sig_err.message == "Bad signature"

    rule_err = BusinessRuleViolationError("Invalid state")
    assert rule_err.message == "Invalid state"


async def test_domain_exception_handlers_http_mapping() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/not-found")
    async def raise_not_found(request: Request):
        raise EntityNotFoundError("User", "abc")

    @test_app.get("/duplicate-entity")
    async def raise_dup_entity(request: Request):
        raise DuplicateEntityError("User already exists")

    @test_app.get("/duplicate-event")
    async def raise_dup_event(request: Request):
        raise DuplicateEventError("evt_123")

    @test_app.get("/webhook-signature")
    async def raise_webhook_sig(request: Request):
        raise WebhookSignatureError("Invalid sig")

    @test_app.get("/business-rule")
    async def raise_business_rule(request: Request):
        raise BusinessRuleViolationError("Negative balance")

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/not-found")
        assert r1.status_code == 404
        assert r1.json()["detail"] == "User with id abc not found."

        r2 = await client.get("/duplicate-entity")
        assert r2.status_code == 409
        assert r2.json()["detail"] == "User already exists"

        r3 = await client.get("/duplicate-event")
        assert r3.status_code == 200
        assert r3.json()["status"] == "ignored_duplicate"

        r4 = await client.get("/webhook-signature")
        assert r4.status_code == 400
        assert r4.json()["detail"] == "Invalid sig"

        r5 = await client.get("/business-rule")
        assert r5.status_code == 422
        assert r5.json()["detail"] == "Negative balance"


async def test_starkbank_exception_handlers_http_mapping() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/stark-auth")
    async def raise_stark_auth(request: Request):
        raise StarkBankAuthenticationError("Auth error")

    @test_app.get("/stark-validation")
    async def raise_stark_val(request: Request):
        raise StarkBankValidationError("Validation error")

    @test_app.get("/stark-server")
    async def raise_stark_server(request: Request):
        raise StarkBankServerError("Server error")

    @test_app.get("/stark-network")
    async def raise_stark_net(request: Request):
        raise StarkBankNetworkError("Network error")

    @test_app.get("/stark-integration")
    async def raise_stark_integ(request: Request):
        raise StarkBankIntegrationError("Integ error")

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r6 = await client.get("/stark-auth")
        assert r6.status_code == 401
        assert r6.json()["error"] == "starkbank_authentication_failed"

        r7 = await client.get("/stark-validation")
        assert r7.status_code == 422
        assert r7.json()["error"] == "starkbank_validation_failed"

        r8 = await client.get("/stark-server")
        assert r8.status_code == 502
        assert r8.json()["error"] == "starkbank_server_error"

        r9 = await client.get("/stark-network")
        assert r9.status_code == 504
        assert r9.json()["error"] == "starkbank_network_timeout"

        r10 = await client.get("/stark-integration")
        assert r10.status_code == 500
        assert r10.json()["error"] == "starkbank_integration_error"


async def test_fallback_unhandled_exception_handler() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/unhandled")
    async def raise_unhandled(request: Request):
        raise ValueError("Critical unexpected error")

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/unhandled")
        assert r.status_code == 500
        assert r.json() == {"detail": "An internal server error occurred."}
