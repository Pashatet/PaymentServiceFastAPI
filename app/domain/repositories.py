from typing import Protocol
from uuid import UUID

from app.domain.entities import Payment, Tariff
from app.domain.enums import PaymentStatus


class TariffRepository(Protocol):
    async def ensure_defaults(self) -> None: ...

    async def list_all(self) -> list[Tariff]: ...

    async def get_by_id(self, tariff_id: str) -> Tariff | None: ...


class PaymentRepository(Protocol):
    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...

    async def get_by_idempotency_key(self, key: str) -> Payment | None: ...

    async def create(self, payment: Payment) -> tuple[Payment, bool]: ...

    async def list_by_filters(
        self, email: str | None, status: PaymentStatus | None
    ) -> list[Payment]: ...

    async def update_status(
        self,
        payment_id: UUID,
        expected_status: PaymentStatus,
        new_status: PaymentStatus,
    ) -> Payment | None: ...
