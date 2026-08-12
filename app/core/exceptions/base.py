class BaseError(Exception):
    """Base exception class for all application errors."""

    def __init__(self, message: str = "An application error occurred.") -> None:
        self.message = message
        super().__init__(self.message)
