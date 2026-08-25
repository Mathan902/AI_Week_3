# Acme SDK v3 — Errors

page_id: v3-errors
sdk_version: v3
page_type: reference

# Error handling

All SDK exceptions inherit from `AcmeError`. Transport failures raise `TransportError`; API-level failures raise subclasses of `ApiError`.

## Error class table

| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| PermissionDeniedError | Token lacks required scope | no |
| NotFoundError | Resource does not exist | no |
| RateLimitError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

## RateLimitError

When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.

```python
from acme.errors import RateLimitError

try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

## Disabling automatic error retries

Automatic retries apply only to retryable errors listed in the table above. Passing `max_retries=0` when constructing the client disables them; the first failure is then raised directly to the caller.
