from app.domain.errors import InvalidPromoCode

PROMO_CODE = "KVITTO10"
PROMO_DISCOUNT_PERCENT = 10


def calculate_discount(price: int, promo_code: str | None) -> int:
    if promo_code is None or not promo_code.strip():
        return 0

    normalized_code = promo_code.strip().upper()
    if normalized_code != PROMO_CODE:
        raise InvalidPromoCode(promo_code)

    return price * PROMO_DISCOUNT_PERCENT // 100


def create_installment_schedule(
    amount: int, installment_months: int | None
) -> tuple[int, ...] | None:
    if installment_months is None:
        return None

    base_amount, remainder = divmod(amount, installment_months)
    return tuple(
        base_amount + (1 if month_index < remainder else 0)
        for month_index in range(installment_months)
    )
