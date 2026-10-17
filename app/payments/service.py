from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.entities import Payment, Tariff
from app.domain.enums import PaymentMethod, PaymentStatus
from app.domain.errors import (
    InvalidStatusTransition,
    PaymentNotFound,
    TariffNotFound,
)
from app.domain.pricing import calculate_discount, create_installment_schedule
from app.domain.repositories import PaymentRepository, TariffRepository


@dataclass(frozen=True, slots=True)
class CreatePaymentCommand:
    tariff_id: str
    email: str
    method: PaymentMethod
    installment_months: int | None
    promo_code: str | None
    idempotency_key: str | None


@dataclass(frozen=True, slots=True)
class CreatePaymentResult:
    payment: Payment
    created: bool


class PaymentService:
    def __init__(
        self,
        tariff_repository: TariffRepository,
        payment_repository: PaymentRepository,
    ) -> None:
        self._tariffs = tariff_repository
        self._payments = payment_repository

    async def ensure_initial_data(self) -> None:
        await self._tariffs.ensure_defaults()

    async def list_tariffs(self) -> list[Tariff]:
        return await self._tariffs.list_all()

    async def create_payment(self, command: CreatePaymentCommand) -> CreatePaymentResult:
        if command.idempotency_key is not None:
            existing = await self._payments.get_by_idempotency_key(command.idempotency_key)
            if existing is not None:
                return CreatePaymentResult(payment=existing, created=False)

        tariff = await self._tariffs.get_by_id(command.tariff_id)
        if tariff is None:
            raise TariffNotFound(command.tariff_id)

        discount = calculate_discount(tariff.price, command.promo_code)
        amount = tariff.price - discount
        schedule = create_installment_schedule(amount, command.installment_months)
        payment = Payment(
            id=uuid4(),
            status=PaymentStatus.PENDING,
            tariff_id=tariff.id,
            amount=amount,
            discount=discount,
            method=command.method,
            installment_months=command.installment_months,
            schedule=schedule,
            email=str(command.email),
            created_at=datetime.now(UTC),
            idempotency_key=command.idempotency_key,
        )
        saved_payment, created = await self._payments.create(payment)
        return CreatePaymentResult(payment=saved_payment, created=created)

    async def get_payment(self, payment_id: UUID) -> Payment:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFound(payment_id)
        return payment

    async def list_payments(
        self, email: str | None, status: PaymentStatus | None
    ) -> list[Payment]:
        return await self._payments.list_by_filters(email=email, status=status)

    async def transition_payment(
        self, payment_id: UUID, new_status: PaymentStatus
    ) -> Payment:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFound(payment_id)

        payment.transition_to(new_status)
        updated_payment = await self._payments.update_status(
            payment_id=payment_id,
            expected_status=payment.status,
            new_status=new_status,
        )
        if updated_payment is None:
            current = await self._payments.get_by_id(payment_id)
            if current is None:
                raise PaymentNotFound(payment_id)
            raise InvalidStatusTransition(
                f"Payment {payment_id} changed concurrently to {current.status.value}"
            )
        return updated_payment
