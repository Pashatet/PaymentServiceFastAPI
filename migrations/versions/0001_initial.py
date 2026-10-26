"""Create the initial payment service schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("price > 0", name="ck_tariffs_positive_price"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("tariff_id", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("discount", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("installment_months", sa.Integer(), nullable=True),
        sa.Column("schedule", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_payments_positive_amount"),
        sa.CheckConstraint("discount >= 0", name="ck_payments_nonnegative_discount"),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')",
            name="ck_payments_status",
        ),
        sa.CheckConstraint(
            "method IN ('card', 'sbp', 'installment')",
            name="ck_payments_method",
        ),
        sa.CheckConstraint(
            "(method = 'installment' AND installment_months IN (3, 6, 12) "
            "AND schedule IS NOT NULL) OR "
            "(method <> 'installment' AND installment_months IS NULL "
            "AND schedule IS NULL)",
            name="ck_payments_installment_fields",
        ),
        sa.ForeignKeyConstraint(
            ["tariff_id"], ["tariffs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_payments_email_created_at", "payments", ["email", "created_at"]
    )
    op.create_index("ix_payments_status", "payments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_email_created_at", table_name="payments")
    op.drop_table("payments")
    op.drop_table("tariffs")
