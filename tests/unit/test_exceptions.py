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


async def test_exception_handlers_http_mapping() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/not-found")
    async def raise_not_found(request: Request):
        raise EntityNotFoundError("User", "abc")

    @test_app.get("/duplicate-entity")
    async def raise_dup_entity(request: Request):
        raise DuplicateEntityError("User already exists")

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

        r3 = await client.get("/business-rule")
        assert r3.status_code == 422
        assert r3.json()["detail"] == "Negative balance"
