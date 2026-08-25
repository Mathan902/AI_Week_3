# Acme SDK v2 — Client

page_id: v2-client
sdk_version: v2
page_type: reference

# Client

The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy.

## Authentication

Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

## Client constructor parameters

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_s | float | 30 | no | Per-request timeout in seconds. |
| max_retries | int | 5 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 2000 | no | Base delay in milliseconds for exponential backoff between retries. |

Setting `max_retries=0` disables all automatic retries.

## Client.request()

`Client.request()` performs a single HTTP request and returns a response object.

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |

```python
response = client.request(url="/v2/invoices", method="POST")
```
