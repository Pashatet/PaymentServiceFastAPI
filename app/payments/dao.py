from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.catalog import DEFAULT_TARIFFS
from app.domain.entities import Payment, Tariff
from app.domain.enums import PaymentMethod, PaymentStatus
from app.domain.repositories import PaymentRepository, TariffRepository
from app.payments.models import PaymentModel, TariffModel


def _to_tariff(model: TariffModel) -> Tariff:
    return Tariff(id=model.id, title=model.title, price=model.price)


def _to_payment(model: PaymentModel) -> Payment:
    return Payment(
        id=model.id,
        status=PaymentStatus(model.status),
        tariff_id=model.tariff_id,
        amount=model.amount,
        discount=model.discount,
        method=PaymentMethod(model.method),
        installment_months=model.installment_months,
        schedule=tuple(model.schedule) if model.schedule is not None else None,
        email=model.email,
        created_at=model.created_at,
        idempotency_key=model.idempotency_key,
    )


class SqlAlchemyTariffRepository(TariffRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_defaults(self) -> None:
        rows = (await self._session.scalars(select(TariffModel.id))).all()
        existing_ids = set(rows)
        missing = [tariff for tariff in DEFAULT_TARIFFS if tariff.id not in existing_ids]
        if missing:
            self._session.add_all(
                [
                    TariffModel(id=item.id, title=item.title, price=item.price)
                    for item in missing
                ]
            )
            try:
                await self._session.commit()
            except IntegrityError:
                # Two app workers can start at once; the primary key makes seeding safe.
                await self._session.rollback()

    async def list_all(self) -> list[Tariff]:
        result = await self._session.scalars(
            select(TariffModel).order_by(TariffModel.price.asc())
        )
        return [_to_tariff(model) for model in result.all()]

    async def get_by_id(self, tariff_id: str) -> Tariff | None:
        model = await self._session.get(TariffModel, tariff_id)
        return _to_tariff(model) if model is not None else None


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        model = await self._session.get(PaymentModel, payment_id)
        return _to_payment(model) if model is not None else None

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        model = await self._session.scalar(
            select(PaymentModel).where(PaymentModel.idempotency_key == key)
        )
        return _to_payment(model) if model is not None else None

    async def create(self, payment: Payment) -> tuple[Payment, bool]:
        model = PaymentModel(
            id=payment.id,
            status=payment.status.value,
            tariff_id=payment.tariff_id,
            amount=payment.amount,
            discount=payment.discount,
            method=payment.method.value,
            installment_months=payment.installment_months,
            schedule=list(payment.schedule) if payment.schedule is not None else None,
            email=payment.email,
            created_at=payment.created_at,
            idempotency_key=payment.idempotency_key,
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            if payment.idempotency_key is not None:
                existing = await self.get_by_idempotency_key(payment.idempotency_key)
                if existing is not None:
                    return existing, False
            raise
        await self._session.refresh(model)
        return _to_payment(model), True

    async def list_by_filters(
        self, email: str | None, status: PaymentStatus | None
    ) -> list[Payment]:
        query = select(PaymentModel).order_by(PaymentModel.created_at.desc())
        if email is not None:
            query = query.where(PaymentModel.email == email)
        if status is not None:
            query = query.where(PaymentModel.status == status.value)
        result = await self._session.scalars(query)
        return [_to_payment(model) for model in result.all()]

    async def update_status(
        self,
        payment_id: UUID,
        expected_status: PaymentStatus,
        new_status: PaymentStatus,
    ) -> Payment | None:
        statement = (
            update(PaymentModel)
            .where(
                PaymentModel.id == payment_id,
                PaymentModel.status == expected_status.value,
            )
            .values(status=new_status.value)
            .returning(PaymentModel)
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        await self._session.commit()
        return _to_payment(model) if model is not None else None
