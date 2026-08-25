# Acme SDK v3 — Client

page_id: v3-client
sdk_version: v3
page_type: reference

# Client

The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy for every request your application sends.

## Authentication

Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.

```python
from acme import Client

client = Client()  # reads ACME_API_TOKEN
```

## Client constructor parameters

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_ms | int | 10000 | no | Per-request timeout in milliseconds. |
| max_retries | int | 3 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 500 | no | Base delay in milliseconds for exponential backoff between retries. |

Setting `max_retries=0` at construction time disables all automatic retries; the client will then surface transport errors immediately.

## Client.send()

`Client.send()` performs a single HTTP request and returns a `Response`.

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.

```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

## Thread safety

A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.
