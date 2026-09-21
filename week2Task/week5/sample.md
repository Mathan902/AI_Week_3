# Seeded random sample

`random.Random(20260921).sample(sorted(trace_ids), 20)` over 126 traces in `week5/traces.jsonl`.

## 01. `tr-e144a5320d` — what was the old default backoff

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.455 | 0.580 |
| 2 | `v2-client::client-request::5-table` | v2 | 0.386 | 0.461 |
| 3 | `v3-client::client-send::7` | v3 | 0.376 | 0.426 |

<details><summary>retrieved text</summary>

**#1 `v3-changelog::retry-defaults-changed::1`**

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

**#2 `v2-client::client-request::5-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |
```

**#3 `v3-client::client-send::7`**

```
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.
```

</details>

**Output:** `The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly. [chunk:v3-changelog::retry-defaults-changed::1]`

## 02. `tr-3e5524039d` — how do I send json in the body of a request

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-client::client-send::5` | v3 | 0.473 | 0.514 |
| 2 | `v2-client::client-request::6-code` | v2 | 0.459 | 0.473 |
| 3 | `v3-client::client-send::8-code` | v3 | 0.442 | 0.470 |

<details><summary>retrieved text</summary>

**#1 `v3-client::client-send::5`**

```
`Client.send()` performs a single HTTP request and returns a `Response`.
```

**#2 `v2-client::client-request::6-code`**

```
```python
response = client.request(url="/v2/invoices", method="POST")
```
```

**#3 `v3-client::client-send::8-code`**

```
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```
```

</details>

**Output:** ``Client.send()` performs a single HTTP request and returns a `Response`. [chunk:v3-client::client-send::5]`

## 03. `tr-0a8782a5ac` — what is retry_backoff_ms

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-client::client-send::7` | v3 | 0.779 | 0.869 |
| 2 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.697 | 0.787 |
| 3 | `v2-client::client-request::5-table` | v2 | 0.608 | 0.698 |

<details><summary>retrieved text</summary>

**#1 `v3-client::client-send::7`**

```
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.
```

**#2 `v3-changelog::retry-defaults-changed::1`**

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

**#3 `v2-client::client-request::5-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |
```

</details>

**Output:** `The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call. [chunk:v3-client::client-send::7]`

## 04. `tr-3002ea968a` — how long can I resume an upload for

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-files::resumable-uploads::4` | v3 | 0.735 | 0.772 |
| 2 | `v3-files::upload-parameters::2` | v3 | 0.460 | 0.479 |
| 3 | `v2-uploads::upload-parameters::1-table` | v2 | 0.401 | 0.420 |

<details><summary>retrieved text</summary>

**#1 `v3-files::resumable-uploads::4`**

```
Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Client.files.upload()`.
```

**#2 `v3-files::upload-parameters::2`**

```
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.
```

**#3 `v2-uploads::upload-parameters::1-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |
```

</details>

**Output:** `Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Client.files.upload()`. [chunk:v3-files::resumable-uploads::4]`

## 05. `tr-16cdcfb0f1` — paginate_auto example

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-pagination::paginate-auto::1` | v2 | 0.717 | 0.817 |
| 2 | `v2-pagination::paginate-auto::4` | v2 | 0.598 | 0.698 |
| 3 | `v2-pagination::paginate-auto::3-code` | v2 | 0.501 | 0.601 |

<details><summary>retrieved text</summary>

**#1 `v2-pagination::paginate-auto::1`**

```
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.
```

**#2 `v2-pagination::paginate-auto::4`**

```
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
```

**#3 `v2-pagination::paginate-auto::3-code`**

```
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```
```

</details>

**Output:** ``paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted. [chunk:v2-pagination::paginate-auto::1]`

## 06. `tr-d437a02c10` — how do I test webhooks locally

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-webhooks::webhooks::0` | v3 | 0.478 | 0.503 |
| 2 | `v3-webhooks::signature-verification::2-code` | v3 | 0.384 | 0.409 |
| 3 | `v2-client::authentication::1` | v2 | 0.230 | 0.230 |

<details><summary>retrieved text</summary>

**#1 `v3-webhooks::webhooks::0`**

```
Webhooks push Acme platform events to an HTTPS endpoint you control.
```

**#2 `v3-webhooks::signature-verification::2-code`**

```
```python
from acme.webhooks import verify_signature
verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```
```

**#3 `v2-client::authentication::1`**

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 07. `tr-0c614eb7d9` — create invoice example

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-pagination::paginate-auto::3-code` | v2 | 0.431 | 0.481 |
| 2 | `v2-client::client-request::6-code` | v2 | 0.402 | 0.402 |
| 3 | `v3-client::client-send::8-code` | v3 | 0.320 | 0.320 |

<details><summary>retrieved text</summary>

**#1 `v2-pagination::paginate-auto::3-code`**

```
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```
```

**#2 `v2-client::client-request::6-code`**

```
```python
response = client.request(url="/v2/invoices", method="POST")
```
```

**#3 `v3-client::client-send::8-code`**

```
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```
```

</details>

**Output:** `I don't know based on the provided documents.`

## 08. `tr-b533926bc3` — webhook retry schedule

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-ratelimits::handling-http-429::4` | v3 | 0.573 | 0.623 |
| 2 | `v3-errors::ratelimiterror::2` | v3 | 0.472 | 0.522 |
| 3 | `v2-errors::toomanyrequestserror::2` | v2 | 0.459 | 0.509 |

<details><summary>retrieved text</summary>

**#1 `v3-ratelimits::handling-http-429::4`**

```
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
```

**#2 `v3-errors::ratelimiterror::2`**

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

**#3 `v2-errors::toomanyrequestserror::2`**

```
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 09. `tr-2c606428b8` — list_after usage

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-changelog::removed-apis::3` | v3 | 0.430 | 0.530 |
| 2 | `v2-pagination::paginate-auto::4` | v2 | 0.348 | 0.448 |
| 3 | `v2-pagination::paginate-auto::2-table` | v2 | 0.312 | 0.362 |

<details><summary>retrieved text</summary>

**#1 `v3-changelog::removed-apis::3`**

```
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.
```

**#2 `v2-pagination::paginate-auto::4`**

```
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
```

**#3 `v2-pagination::paginate-auto::2-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | List endpoint path relative to base_url. |
| page_size | int | 100 | no | Number of items requested per page. |
```

</details>

**Output:** ``Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`. [chunk:v3-changelog::removed-apis::3]`

## 10. `tr-59ebac9e56` — what is part_size_mb

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-files::upload-parameters::2` | v3 | 0.506 | 0.626 |
| 2 | `v3-files::upload-parameters::1-table` | v3 | 0.456 | 0.546 |
| 3 | `v2-uploads::upload-parameters::2` | v2 | 0.388 | 0.478 |

<details><summary>retrieved text</summary>

**#1 `v3-files::upload-parameters::2`**

```
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.
```

**#2 `v3-files::upload-parameters::1-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 25 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| part_size_mb | int | 5 | no | Size of each multipart chunk when uploading large files. |
```

**#3 `v2-uploads::upload-parameters::2`**

```
The default maximum file size in v2 is 10 MB.
```

</details>

**Output:** `The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`. [chunk:v3-files::upload-parameters::2]`

## 11. `tr-4fc05e9928` — what attribute tells me how long to wait after rate limit

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-ratelimits::rate-limits::0` | v3 | 0.544 | 0.572 |
| 2 | `v3-errors::ratelimiterror::2` | v3 | 0.506 | 0.561 |
| 3 | `v2-errors::toomanyrequestserror::4` | v2 | 0.513 | 0.554 |

<details><summary>retrieved text</summary>

**#1 `v3-ratelimits::rate-limits::0`**

```
Rate limits cap how many requests an account can make per minute. Limits are enforced per API token, not per IP address.
```

**#2 `v3-errors::ratelimiterror::2`**

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

**#3 `v2-errors::toomanyrequestserror::4`**

```
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.
```

</details>

**Output:** `When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. [chunk:v3-errors::ratelimiterror::2]`

## 12. `tr-b67ebb71de` — how do I override backoff for a single request

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-client::client-request::5-table` | v2 | 0.628 | 0.678 |
| 2 | `v3-client::client-send::6-table` | v3 | 0.619 | 0.669 |
| 3 | `v3-client::client-send::7` | v3 | 0.575 | 0.641 |

<details><summary>retrieved text</summary>

**#1 `v2-client::client-request::5-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |
```

**#2 `v3-client::client-send::6-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |
```

**#3 `v3-client::client-send::7`**

```
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.
```

</details>

**Output:** `The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call. [chunk:v3-client::client-send::7]`

## 13. `tr-4e8ace72b2` — NotFoundError retryable?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-errors::error-class-table::1-table` | v2 | 0.573 | 0.723 |
| 2 | `v3-errors::error-class-table::1-table` | v3 | 0.538 | 0.688 |
| 3 | `v3-errors::disabling-automatic-error-retries::4` | v3 | 0.551 | 0.626 |

<details><summary>retrieved text</summary>

**#1 `v2-errors::error-class-table::1-table`**

```
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |
```

**#2 `v3-errors::error-class-table::1-table`**

```
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| PermissionDeniedError | Token lacks required scope | no |
| NotFoundError | Resource does not exist | no |
| RateLimitError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |
```

**#3 `v3-errors::disabling-automatic-error-retries::4`**

```
Automatic retries apply only to retryable errors listed in the table above. Passing `max_retries=0` when constructing the client disables them; the first failure is then raised directly to the caller.
```

</details>

**Output:** `Automatic retries apply only to retryable errors listed in the table above. Passing `max_retries=0` when constructing the client disables them; the first failure is then raised directly to the caller. Automatic retries apply only to retryable errors listed in the table above [chunk:v3-errors::disabling-automatic-error-retries::4]`

## 14. `tr-4da0dedb22` — what changed between v2 and v3

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-changelog::what-changed-in-v3::0` | v3 | 0.475 | 0.575 |
| 2 | `v2-uploads::upload-parameters::2` | v2 | 0.362 | 0.387 |
| 3 | `v3-files::file-uploads::0` | v3 | 0.261 | 0.286 |

<details><summary>retrieved text</summary>

**#1 `v3-changelog::what-changed-in-v3::0`**

```
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.
```

**#2 `v2-uploads::upload-parameters::2`**

```
The default maximum file size in v2 is 10 MB.
```

**#3 `v3-files::file-uploads::0`**

```
Uploads in SDK v3 go through `Client.files.upload()`.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 15. `tr-4fc7b3e2f0` — what happens if the stream disconnects

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-streaming::reconnection::5` | v3 | 0.623 | 0.698 |
| 2 | `v3-streaming::client-stream::1` | v3 | 0.625 | 0.675 |
| 3 | `v3-streaming::streaming-responses::0` | v3 | 0.445 | 0.470 |

<details><summary>retrieved text</summary>

**#1 `v3-streaming::reconnection::5`**

```
If the stream drops, the SDK reconnects automatically with exponential backoff and replays events missed while offline when the endpoint supports the `Last-Event-ID` header.
```

**#2 `v3-streaming::client-stream::1`**

```
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.
```

**#3 `v3-streaming::streaming-responses::0`**

```
Streaming delivers server-sent events (SSE) as they are produced instead of waiting for the full response body.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 16. `tr-eb85fc3c25` — AuthenticationError when creating client

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-client::authentication::1` | v2 | 0.638 | 0.713 |
| 2 | `v3-client::authentication::1` | v3 | 0.593 | 0.668 |
| 3 | `v3-client::authentication::2-code` | v3 | 0.388 | 0.425 |

<details><summary>retrieved text</summary>

**#1 `v2-client::authentication::1`**

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.
```

**#2 `v3-client::authentication::1`**

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.
```

**#3 `v3-client::authentication::2-code`**

```
```python
from acme import Client
client = Client()  # reads ACME_API_TOKEN
```
```

</details>

**Output:** `Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent. Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable [chunk:v2-client::authentication::1]`

## 17. `tr-4a0095b313` — v2 upload limit vs v3

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-files::upload-parameters::2` | v3 | 0.528 | 0.558 |
| 2 | `v2-uploads::upload-parameters::2` | v2 | 0.509 | 0.539 |
| 3 | `v3-files::file-uploads::0` | v3 | 0.475 | 0.535 |

<details><summary>retrieved text</summary>

**#1 `v3-files::upload-parameters::2`**

```
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.
```

**#2 `v2-uploads::upload-parameters::2`**

```
The default maximum file size in v2 is 10 MB.
```

**#3 `v3-files::file-uploads::0`**

```
Uploads in SDK v3 go through `Client.files.upload()`.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 18. `tr-b292e79be2` — how to verify webhook payload

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-webhooks::signature-verification::2-code` | v3 | 0.643 | 0.733 |
| 2 | `v3-webhooks::webhooks::0` | v3 | 0.513 | 0.543 |
| 3 | `v3-webhooks::signature-verification::1` | v3 | 0.476 | 0.536 |

<details><summary>retrieved text</summary>

**#1 `v3-webhooks::signature-verification::2-code`**

```
```python
from acme.webhooks import verify_signature
verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```
```

**#2 `v3-webhooks::webhooks::0`**

```
Webhooks push Acme platform events to an HTTPS endpoint you control.
```

**#3 `v3-webhooks::signature-verification::1`**

```
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```

</details>

**Output:** ````python from acme.webhooks import verify_signature verify_signature(     payload=raw_body,     signature_header=request.headers["X-Acme-Signature"],     secret=WEBHOOK_SIGNING_SECRET, ) ``` from acme.webhooks import verify_signature [chunk:v3-webhooks::signature-verification::2-code]`

## 19. `tr-16c2469574` — what scheme does verify_signature expect

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-webhooks::signature-verification::1` | v3 | 0.464 | 0.514 |
| 2 | `v3-webhooks::signature-verification::2-code` | v3 | 0.440 | 0.490 |
| 3 | `v3-webhooks::verification-parameters::3-table` | v3 | 0.415 | 0.465 |

<details><summary>retrieved text</summary>

**#1 `v3-webhooks::signature-verification::1`**

```
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```

**#2 `v3-webhooks::signature-verification::2-code`**

```
```python
from acme.webhooks import verify_signature
verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```
```

**#3 `v3-webhooks::verification-parameters::3-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. |
| scheme | str | "v3" | no | Signature scheme prefix expected in the header. |
```

</details>

**Output:** `from acme.webhooks import verify_signature verify_signature( [chunk:v3-webhooks::signature-verification::2-code]`

## 20. `tr-66dbda2dd0` — list of removed apis in v3

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-changelog::what-changed-in-v3::0` | v3 | 0.343 | 0.368 |
| 2 | `v2-pagination::pagination::0` | v2 | 0.300 | 0.350 |
| 3 | `v2-pagination::paginate-auto::4` | v2 | 0.242 | 0.342 |

<details><summary>retrieved text</summary>

**#1 `v3-changelog::what-changed-in-v3::0`**

```
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.
```

**#2 `v2-pagination::pagination::0`**

```
List endpoints in SDK v2 return full pages with automatic pagination helpers.
```

**#3 `v2-pagination::paginate-auto::4`**

```
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
```

</details>

**Output:** `I don't know based on the provided documents.`
