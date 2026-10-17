"""SQLAlchemy persistence models for tariffs and payments."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TariffModel(Base):
    __tablename__ = "tariffs"
    __table_args__ = (CheckConstraint("price > 0", name="ck_tariffs_positive_price"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)


class PaymentModel(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_positive_amount"),
        CheckConstraint("discount >= 0", name="ck_payments_nonnegative_discount"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')",
            name="ck_payments_status",
        ),
        CheckConstraint(
            "method IN ('card', 'sbp', 'installment')",
            name="ck_payments_method",
        ),
        CheckConstraint(
            "(method = 'installment' AND installment_months IN (3, 6, 12) "
            "AND schedule IS NOT NULL) OR "
            "(method <> 'installment' AND installment_months IS NULL "
            "AND schedule IS NULL)",
            name="ck_payments_installment_fields",
        ),
        Index("ix_payments_email_created_at", "email", "created_at"),
        Index("ix_payments_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    tariff_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tariffs.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    installment_months: Mapped[int | None] = mapped_column(nullable=True)
    schedule: Mapped[list[int] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
