import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tariffs_are_available_on_startup(client: AsyncClient) -> None:
    response = await client.get("/tariffs")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "basic", "title": "Basic", "price": 990_000},
        {"id": "standard", "title": "Standard", "price": 1_990_000},
        {"id": "premium", "title": "Premium", "price": 2_990_000},
    ]


@pytest.mark.asyncio
async def test_promo_discount_is_integer_and_case_insensitive(
    client: AsyncClient,
) -> None:
    plain = await client.post(
        "/payments",
        json={"tariff_id": "standard", "email": "plain@example.com", "method": "card"},
    )
    discounted = await client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "promo@example.com",
            "method": "sbp",
            "promo_code": "kvittO10",
        },
    )

    assert plain.status_code == 201
    assert plain.json()["amount"] == 1_990_000
    assert plain.json()["discount"] == 0
    assert discounted.status_code == 201
    assert discounted.json()["discount"] == 199_000
    assert discounted.json()["amount"] == 1_791_000

    invalid = await client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "invalid@example.com",
            "method": "card",
            "promo_code": "UNKNOWN",
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"][0]["loc"] == ["body", "promo_code"]


@pytest.mark.asyncio
@pytest.mark.parametrize("months", [3, 6, 12])
async def test_installment_schedule_has_no_lost_kopecks(client: AsyncClient, months: int) -> None:
    response = await client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": f"months{months}@example.com",
            "method": "installment",
            "installment_months": months,
        },
    )

    assert response.status_code == 201
    payment = response.json()
    quotient, remainder = divmod(payment["amount"], months)
    expected = [quotient + 1] * remainder + [quotient] * (months - remainder)
    assert payment["schedule"] == expected
    assert sum(payment["schedule"]) == payment["amount"]


@pytest.mark.asyncio
async def test_same_idempotency_key_returns_existing_payment(
    client: AsyncClient,
) -> None:
    payload = {
        "tariff_id": "basic",
        "email": "same@example.com",
        "method": "card",
    }
    headers = {"Idempotency-Key": "order-42"}
    first = await client.post("/payments", json=payload, headers=headers)
    retry = await client.post("/payments", json=payload, headers=headers)
    listed = await client.get("/payments", params={"email": "same@example.com"})

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_invalid_status_transition_returns_409_without_changing_payment(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/payments",
        json={"tariff_id": "basic", "email": "status@example.com", "method": "card"},
    )
    payment_id = created.json()["id"]
    body = json.dumps(
        {"payment_id": payment_id, "status": "refunded"},
        separators=(",", ":"),
    ).encode()
    response = await client.post(
        "/webhooks/bank",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": _signature(body),
        },
    )
    current = await client.get(f"/payments/{payment_id}")

    assert response.status_code == 409
    assert response.json() == {"error": "invalid_transition"}
    assert current.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_missing_payment_returns_404(client: AsyncClient) -> None:
    response = await client.get("/payments/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webhook_missing_payment_returns_404_before_signature_check(
    client: AsyncClient,
) -> None:
    body = json.dumps(
        {
            "payment_id": "00000000-0000-0000-0000-000000000000",
            "status": "succeeded",
        },
        separators=(",", ":"),
    ).encode()
    response = await client.post(
        "/webhooks/bank",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 404
    assert response.json()["detail"].startswith("Payment UUID(")


@pytest.mark.asyncio
async def test_webhook_requires_valid_signature_and_changes_status(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/payments",
        json={"tariff_id": "basic", "email": "bank@example.com", "method": "card"},
    )
    payment_id = created.json()["id"]
    body = json.dumps(
        {"payment_id": payment_id, "status": "succeeded"},
        separators=(",", ":"),
    ).encode()
    invalid = await client.post(
        "/webhooks/bank",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "bad"},
    )
    accepted = await client.post(
        "/webhooks/bank",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": _signature(body),
        },
    )

    assert invalid.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json() == {"result": "ok"}
    assert (await client.get(f"/payments/{payment_id}")).json()["status"] == "succeeded"


@pytest.mark.asyncio
async def test_list_filters_by_email_and_status(client: AsyncClient) -> None:
    await client.post(
        "/payments",
        json={"tariff_id": "basic", "email": "filter@example.com", "method": "card"},
    )
    await client.post(
        "/payments",
        json={"tariff_id": "basic", "email": "other@example.com", "method": "card"},
    )

    response = await client.get(
        "/payments",
        params={"email": "filter@example.com", "status": "pending"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "filter@example.com"


def _signature(body: bytes) -> str:
    return hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_allowed_status_transitions_cover_failure_and_refund(
    client: AsyncClient,
) -> None:
    failed_payment = await client.post(
        "/payments",
        json={"tariff_id": "basic", "email": "failed@example.com", "method": "card"},
    )
    refunded_payment = await client.post(
        "/payments",
        json={"tariff_id": "basic", "email": "refund@example.com", "method": "card"},
    )

    async def send_status(payment_id: str, status: str):
        body = json.dumps(
            {"payment_id": payment_id, "status": status}, separators=(",", ":")
        ).encode()
        return await client.post(
            "/webhooks/bank",
            content=body,
            headers={"Content-Type": "application/json", "X-Signature": _signature(body)},
        )

    failed = await send_status(failed_payment.json()["id"], "failed")
    failed_retry = await send_status(failed_payment.json()["id"], "succeeded")
    succeeded = await send_status(refunded_payment.json()["id"], "succeeded")
    refunded = await send_status(refunded_payment.json()["id"], "refunded")

    assert failed.status_code == 200
    assert failed_retry.status_code == 409
    assert succeeded.status_code == 200
    assert refunded.status_code == 200
    assert (await client.get(f"/payments/{failed_payment.json()['id']}")).json()[
        "status"
    ] == "failed"
    assert (await client.get(f"/payments/{refunded_payment.json()['id']}")).json()[
        "status"
    ] == "refunded"
