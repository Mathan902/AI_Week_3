# Acme SDK v3 — Webhooks

page_id: v3-webhooks
sdk_version: v3
page_type: reference

# Webhooks

Webhooks push Acme platform events to an HTTPS endpoint you control.

## Signature verification

Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.

```python
from acme.webhooks import verify_signature

verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```

## Verification parameters

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. |
| scheme | str | "v3" | no | Signature scheme prefix expected in the header. |

Deliveries older than `tolerance_seconds` fail verification; this protects you against replay attacks.

## Retries

Failed deliveries are retried up to five times over six hours with exponential backoff. An endpoint is disabled after 20 consecutive failures.
