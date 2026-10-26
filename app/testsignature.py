import hashlib
import hmac

# body = b'{"payment_id":"ВСТАВЬТЕ_ID_ПЛАТЕЖА","status":"succeeded"}'
# secret = b"ВСТАВЬТЕ_WEBHOOK_SECRET_ИЗ_.env"

body = b'{\n  "payment_id": "dc4221ef-d1b7-4483-b55b-79ea44059d62",\n  "status": "succeeded"\n}'
secret = b"local-development-secret"

print(hmac.new(secret, body, hashlib.sha256).hexdigest())


# import hashlib
# import hmac
# import urllib.request
#
# secret = "local-development-secret".encode()
# body = b'{"payment_id":"0a87f40e-52f0-446f-979d-0270a7f4ccb6","status":"succeeded"}'
# signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
#
# request = urllib.request.Request(
#     "http://127.0.0.1:8000/webhooks/bank",
#     data=body,
#     headers={
#         "Content-Type": "application/json",
#         "X-Signature": signature,
#     },
#     method="POST",
# )
#
# with urllib.request.urlopen(request) as response:
#     print(response.status, response.read().decode())