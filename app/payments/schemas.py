from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.domain.entities import Payment, Tariff
from app.domain.enums import PaymentMethod, PaymentStatus
from app.domain.errors import InvalidPromoCode
from app.domain.pricing import validate_promo_code


class PaymentCreateRequest(BaseModel):
    tariff_id: str = Field(min_length=1, max_length=32)
    email: EmailStr
    method: PaymentMethod
    installment_months: Literal[3, 6, 12] | None = None
    promo_code: str | None = Field(default=None, max_length=32)

    @field_validator("promo_code")
    @classmethod
    def validate_promo_code_field(cls, value: str | None) -> str | None:
        try:
            validate_promo_code(value)
        except InvalidPromoCode as error:
            raise ValueError("unknown promo code") from error
        return value

    @field_validator("installment_months", mode="before")
    @classmethod
    def validate_installment_months_field(
        cls, value: object, info: ValidationInfo
    ) -> object:
        method = info.data.get("method")
        if value is not None and method is not PaymentMethod.INSTALLMENT:
            raise ValueError(
                "installment_months is only allowed for installment payments"
            )
        return value

    @model_validator(mode="after")
    def validate_installment_fields(self) -> PaymentCreateRequest:
        if self.method is PaymentMethod.INSTALLMENT and self.installment_months is None:
            raise ValueError("installment_months is required for installment payments")
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: PaymentStatus
    tariff_id: str
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: EmailStr
    created_at: datetime

    @classmethod
    def from_entity(cls, payment: Payment) -> PaymentResponse:
        return cls(
            id=payment.id,
            status=payment.status,
            tariff_id=payment.tariff_id,
            amount=payment.amount,
            discount=payment.discount,
            method=payment.method,
            installment_months=payment.installment_months,
            schedule=list(payment.schedule) if payment.schedule is not None else None,
            email=payment.email,
            created_at=payment.created_at,
        )


class TariffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: int

    @classmethod
    def from_entity(cls, tariff: Tariff) -> TariffResponse:
        return cls(id=tariff.id, title=tariff.title, price=tariff.price)


class BankWebhookRequest(BaseModel):
    payment_id: UUID
    status: PaymentStatus
