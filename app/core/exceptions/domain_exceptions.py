from app.core.exceptions.base import BaseError


class DomainError(BaseError):
    """Base exception class for domain business rule errors."""

    pass


class EntityNotFoundError(DomainError):
    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(f"{entity_name} with id {entity_id} not found.")


class DuplicateEntityError(DomainError):
    def __init__(self, message: str = "Entity already exists.") -> None:
        super().__init__(message)


class BusinessRuleViolationError(DomainError):
    def __init__(self, message: str = "Business rule violation.") -> None:
        super().__init__(message)


class WebhookSignatureError(DomainError):
    def __init__(self, message: str = "Invalid webhook digital signature.") -> None:
        super().__init__(message)


class DuplicateEventError(DomainError):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Webhook event with id '{event_id}' has already been processed.")
