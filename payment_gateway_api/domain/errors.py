"""Domain errors, translated to HTTP only at the edge (infrastructure/api)."""


class BankUnavailableError(Exception):
    """The single bank call failed (FR-13). `cause` is for logs only, never for the merchant."""

    def __init__(self, cause: str) -> None:
        super().__init__(cause)
        self.cause = cause
