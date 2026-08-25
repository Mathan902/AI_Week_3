# Acme SDK v2 — Errors

page_id: v2-errors
sdk_version: v2
page_type: reference

# Error handling

All SDK exceptions inherit from `AcmeError`. API-level failures raise subclasses of `ApiError`.

## Error class table

| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

## TooManyRequestsError

When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.

```python
from acme.errors import TooManyRequestsError

try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.
