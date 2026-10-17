from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.payments.dao import (
    SqlAlchemyPaymentRepository,
    SqlAlchemyTariffRepository,
)
from app.payments.service import PaymentService

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_payment_service(session: SessionDep) -> PaymentService:
    return PaymentService(
        tariff_repository=SqlAlchemyTariffRepository(session),
        payment_repository=SqlAlchemyPaymentRepository(session),
    )


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
