from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from app.domain.enums import PaymentMethod, PaymentStatus
from app.domain.errors import InvalidStatusTransition

_ALLOWED_TRANSITIONS: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.PENDING: frozenset({PaymentStatus.SUCCEEDED, PaymentStatus.FAILED}),
    PaymentStatus.SUCCEEDED: frozenset({PaymentStatus.REFUNDED}),
    PaymentStatus.FAILED: frozenset(),
    PaymentStatus.REFUNDED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Tariff:
    id: str
    title: str
    price: int


@dataclass(frozen=True, slots=True)
class Payment:
    id: UUID
    status: PaymentStatus
    tariff_id: str
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: tuple[int, ...] | None
    email: str
    created_at: datetime
    idempotency_key: str | None = None

    def transition_to(self, new_status: PaymentStatus) -> Payment:
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidStatusTransition(
                f"Cannot move payment from {self.status.value} to {new_status.value}"
            )
        return replace(self, status=new_status)
