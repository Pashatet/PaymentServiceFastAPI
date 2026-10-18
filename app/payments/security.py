import hashlib
import hmac

from fastapi import Request

from app.domain.errors import InvalidWebhookSignature


async def verify_webhook_signature(
    request: Request,
    signature: str | None,
) -> None:
    if signature is None:
        raise InvalidWebhookSignature("Missing X-Signature header")

    secret = request.app.state.settings.webhook_secret.get_secret_value().encode("utf-8")
    body = await request.body()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature.strip().lower(), expected):
        raise InvalidWebhookSignature("Invalid X-Signature header")
