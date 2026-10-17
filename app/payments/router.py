from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Query, Response
from fastapi.exceptions import RequestValidationError
from pydantic import EmailStr

from app.domain.enums import PaymentStatus
from app.domain.errors import InvalidPromoCode
from app.payments.dependencies import PaymentServiceDep
from app.payments.schemas import (
    BankWebhookRequest,
    PaymentCreateRequest,
    PaymentResponse,
    TariffResponse,
)
from app.payments.security import verify_webhook_signature
from app.payments.service import CreatePaymentCommand

router = APIRouter()


@router.get("/tariffs", response_model=list[TariffResponse], tags=["tariffs"])
async def list_tariffs(service: PaymentServiceDep) -> list[TariffResponse]:
    tariffs = await service.list_tariffs()
    return [TariffResponse.from_entity(tariff) for tariff in tariffs]


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=201,
    tags=["payments"],
)
async def create_payment(
    payload: PaymentCreateRequest,
    response: Response,
    service: PaymentServiceDep,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ] = None,
) -> PaymentResponse:
    command = CreatePaymentCommand(
        tariff_id=payload.tariff_id,
        email=str(payload.email),
        method=payload.method,
        installment_months=payload.installment_months,
        promo_code=payload.promo_code,
        idempotency_key=idempotency_key,
    )
    try:
        result = await service.create_payment(command)
    except InvalidPromoCode as error:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "promo_code"),
                    "msg": "Value error, unknown promo code",
                    "input": error.code,
                    "ctx": {"error": "unknown promo code"},
                }
            ]
        ) from error

    if not result.created:
        response.status_code = 200
    return PaymentResponse.from_entity(result.payment)


@router.get("/payments", response_model=list[PaymentResponse], tags=["payments"])
async def list_payments(
    service: PaymentServiceDep,
    email: Annotated[EmailStr | None, Query()] = None,
    status: Annotated[PaymentStatus | None, Query()] = None,
) -> list[PaymentResponse]:
    payments = await service.list_payments(
        email=str(email) if email is not None else None,
        status=status,
    )
    return [PaymentResponse.from_entity(payment) for payment in payments]


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=["payments"],
)
async def get_payment(
    payment_id: Annotated[UUID, Path()],
    service: PaymentServiceDep,
) -> PaymentResponse:
    payment = await service.get_payment(payment_id)
    return PaymentResponse.from_entity(payment)


@router.post(
    "/webhooks/bank",
    dependencies=[Depends(verify_webhook_signature)],
    tags=["webhooks"],
)
async def bank_webhook(
    payload: BankWebhookRequest,
    service: PaymentServiceDep,
) -> dict[str, str]:
    await service.transition_payment(payload.payment_id, payload.status)
    return {"result": "ok"}
