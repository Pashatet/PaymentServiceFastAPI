"""Errors raised by payment domain rules."""


class DomainError(Exception):
    """Base class for expected business errors."""


class TariffNotFound(DomainError):
    def __init__(self, tariff_id: str) -> None:
        self.tariff_id = tariff_id
        super().__init__(f"Tariff {tariff_id!r} was not found")


class PaymentNotFound(DomainError):
    def __init__(self, payment_id: object) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id!r} was not found")


class InvalidPromoCode(DomainError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Unknown promo code: {code}")


class InvalidStatusTransition(DomainError):
    """Raised when a payment status transition is not allowed."""


class InvalidWebhookSignature(DomainError):
    """Raised when the bank webhook signature is missing or incorrect."""
