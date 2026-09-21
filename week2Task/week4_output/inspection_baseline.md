# Inspection view — retriever `baseline`

hit-rate@3 = 11/12 | tally = {'PASS': 6, 'R': 1, 'G': 5, 'NIC': 0} | p50 retrieval = 4.55 ms

## Q01 — what is the default for retry_backoff_ms
- Gold: `v3-client::client-constructor-parameters::3-table` (also correct: `v3-client::client-send::6-table`, `v3-changelog::retry-defaults-changed::1`)
- Exact token: `retry_backoff_ms` (symbol)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-client::client-send::7` | v3 | 0.778 | 0.872 |  | The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call |
| 2 | `v2-client::client-request::5-table` | v2 | 0.676 | 0.789 |  | \| Parameter \| Type \| Default \| Required \| Description \| \|---\|---\|---\|---\|---\| \| url \| str \| — \ |
| 3 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.693 | 0.787 | also correct | The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery ti |

**Answer:** `The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call. [chunk:v3-client::client-send::7]`

**Label: R** — gold `v3-client::client-constructor-parameters::3-table` sits at rank 7 of 25; 3/3 of the top-3 contain `retry_backoff_ms`; top-3 = [v3-client::client-send::7, v2-client::client-request::5-table, v3-changelog::retry-defaults-changed::1]

## Q02 — how do I authenticate the client?
- Gold: `v3-client::authentication::1` (also correct: `v3-client::authentication::2-code`)
- Exact token: none

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v2-client::authentication::1` | v2 | 0.531 | 0.581 |  | Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing toke |
| 2 | `v3-client::authentication::1` | v3 | 0.513 | 0.563 | **GOLD** | Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must no |
| 3 | `v3-client::client::0` | v3 | 0.499 | 0.549 |  | The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry poli |

**Answer:** `I don't know based on the provided documents.`

**Label: G** — gold `v3-client::authentication::1` at rank 2 of top-3 containing ['ACME_API_TOKEN'], but answer lacks it — lexical-support gate refused (support=0.50 < 0.60)

## Q03 — what's the default heartbeat_interval_ms when streaming?
- Gold: `v3-streaming::client-stream::2-table`
- Exact token: `heartbeat_interval_ms` (symbol)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-streaming::client-stream::2-table` | v3 | 0.709 | 0.809 | **GOLD** | \| Parameter \| Type \| Default \| Required \| Description \| \|---\|---\|---\|---\|---\| \| url \| str \| — \ |
| 2 | `v3-streaming::streaming-responses::0` | v3 | 0.441 | 0.475 |  | Streaming delivers server-sent events (SSE) as they are produced instead of waiting for the full response body |
| 3 | `v3-streaming::reconnection::5` | v3 | 0.427 | 0.460 |  | If the stream drops, the SDK reconnects automatically with exponential backoff and replays events missed while |

**Answer:** `| heartbeat_interval_ms | int | 15000 | no | Interval between keep-alive heartbeat frames on the idle stream. | | | heartbeat_interval_ms | int | 15000 | no | Interval between keep-alive heartbeat frames on the idle stream [chunk:v3-streaming::client-stream::2-table]`

**Label: PASS** — correct chunk at rank 1; answer contains ['15000']

## Q04 — uploads keep failing with PayloadTooLargeError, what's the size limit?
- Gold: `v3-files::upload-parameters::1-table` (also correct: `v3-files::upload-parameters::2`)
- Exact token: `PayloadTooLargeError` (error class)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-files::upload-parameters::1-table` | v3 | 0.681 | 0.726 | **GOLD** | \| Parameter \| Type \| Default \| Required \| Description \| \|---\|---\|---\|---\|---\| \| file_path \| str  |
| 2 | `v2-uploads::upload-parameters::1-table` | v2 | 0.665 | 0.725 |  | \| Parameter \| Type \| Default \| Required \| Description \| \|---\|---\|---\|---\|---\| \| file_path \| str  |
| 3 | `v3-files::upload-parameters::2` | v3 | 0.685 | 0.715 | also correct | The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically  |

**Answer:** `I don't know based on the provided documents.`

**Label: G** — gold `v3-files::upload-parameters::1-table` at rank 1 of top-3 containing ['25'], but answer lacks it — lexical-support gate refused (support=0.33 < 0.60)

## Q05 — what does X-RateLimit-Remaining mean?
- Gold: `v3-ratelimits::headers::3`
- Exact token: `X-RateLimit-Remaining` (symbol (header))

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-ratelimits::headers::3` | v3 | 0.598 | 0.673 | **GOLD** | Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers describin |
| 2 | `v3-ratelimits::rate-limits::0` | v3 | 0.495 | 0.495 |  | Rate limits cap how many requests an account can make per minute. Limits are enforced per API token, not per I |
| 3 | `v2-errors::toomanyrequestserror::4` | v2 | 0.399 | 0.399 |  | In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute. |

**Answer:** `Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers describing your current budget. [chunk:v3-ratelimits::headers::3]`

**Label: PASS** — correct chunk at rank 1; answer contains ['X-RateLimit-Remaining']

## Q06 — got a 429 back, how long should I wait before retrying?
- Gold: `v3-errors::ratelimiterror::2` (also correct: `v3-ratelimits::handling-http-429::4`)
- Exact token: `429` (error code)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-ratelimits::handling-http-429::4` | v3 | 0.538 | 0.565 | also correct | On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header  |
| 2 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.500 | 0.527 |  | The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery ti |
| 3 | `v3-errors::ratelimiterror::2` | v3 | 0.456 | 0.525 | **GOLD** | When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_second |

**Answer:** `When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. [chunk:v3-errors::ratelimiterror::2]`

**Label: PASS** — correct chunk at rank 3; answer contains ['Retry-After']

## Q07 — paginate_auto is gone after upgrading, what do I use now?
- Gold: `v3-changelog::removed-apis::3` (also correct: `v2-pagination::paginate-auto::4`)
- Exact token: `paginate_auto` (symbol)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v2-pagination::paginate-auto::4` | v2 | 0.630 | 0.684 | also correct | `paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead. |
| 2 | `v2-pagination::paginate-auto::1` | v2 | 0.584 | 0.625 |  | `paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhaust |
| 3 | `v3-changelog::removed-apis::3` | v3 | 0.501 | 0.556 | **GOLD** | `Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor |

**Answer:** `I don't know based on the provided documents.`

**Label: G** — gold `v3-changelog::removed-apis::3` at rank 3 of top-3 containing ['list_after'], but answer lacks it — lexical-support gate refused (support=0.57 < 0.60)

## Q08 — default tolerance_seconds for webhook signature checks?
- Gold: `v3-webhooks::verification-parameters::3-table`
- Exact token: `tolerance_seconds` (symbol)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-webhooks::verification-parameters::4` | v3 | 0.521 | 0.564 |  | Deliveries older than `tolerance_seconds` fail verification; this protects you against replay attacks. |
| 2 | `v3-webhooks::verification-parameters::3-table` | v3 | 0.473 | 0.558 | **GOLD** | \| Parameter \| Type \| Default \| Required \| Description \| \|---\|---\|---\|---\|---\| \| tolerance_seconds |
| 3 | `v3-webhooks::signature-verification::2-code` | v3 | 0.513 | 0.556 |  | ```python from acme.webhooks import verify_signature verify_signature(     payload=raw_body,     signature_hea |

**Answer:** `| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. | | Parameter | Type | Default | Required | Description | |---|---|---|---|---| | tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale [chunk:v3-webhooks::verification-parameters::3-table]`

**Label: PASS** — correct chunk at rank 2; answer contains ['300']

## Q09 — can I share one client across threads?
- Gold: `v3-client::thread-safety::9`
- Exact token: none

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-client::thread-safety::9` | v3 | 0.744 | 0.851 | **GOLD** | A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per req |
| 2 | `v3-streaming::client-stream::1` | v3 | 0.319 | 0.341 |  | `Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server clo |
| 3 | `v3-client::client-send::5` | v3 | 0.295 | 0.317 |  | `Client.send()` performs a single HTTP request and returns a `Response`. |

**Answer:** `A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request. Share one instance across threads instead of constructing a client per request. [chunk:v3-client::thread-safety::9]`

**Label: PASS** — correct chunk at rank 1; answer contains ['thread-safe']

## Q10 — how do I resume an upload that got interrupted?
- Gold: `v3-files::resumable-uploads::4`
- Exact token: none

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-files::resumable-uploads::4` | v3 | 0.739 | 0.773 | **GOLD** | Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Clie |
| 2 | `v2-uploads::upload-parameters::1-table` | v2 | 0.384 | 0.401 |  | \| Parameter \| Type \| Default \| Required \| Description \| \|---\|---\|---\|---\|---\| \| file_path \| str  |
| 3 | `v2-uploads::file-uploads::0` | v2 | 0.380 | 0.396 |  | Uploads in SDK v2 go through `Client.upload_file()`. |

**Answer:** `Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Client.files.upload()`. [chunk:v3-files::resumable-uploads::4]`

**Label: PASS** — correct chunk at rank 1; answer contains ['upload_id']

## Q11 — timeout_s stopped working after the upgrade, what's the new option?
- Gold: `v3-changelog::timeout-units-renamed::2`
- Exact token: `timeout_s` (symbol)

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-changelog::timeout-units-renamed::2` | v3 | 0.610 | 0.670 | **GOLD** | Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default tim |
| 2 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.494 | 0.524 |  | The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery ti |
| 3 | `v2-errors::toomanyrequestserror::4` | v2 | 0.462 | 0.492 |  | In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute. |

**Answer:** `I don't know based on the provided documents.`

**Label: G** — gold `v3-changelog::timeout-units-renamed::2` at rank 1 of top-3 containing ['timeout_ms'], but answer lacks it — lexical-support gate refused (support=0.43 < 0.60)

## Q12 — how many times does a failed webhook delivery get retried?
- Gold: `v3-webhooks::retries::5`
- Exact token: none

| rank | chunk_id | ver | dense | final | gold? | text |
|---|---|---|---|---|---|---|
| 1 | `v3-webhooks::retries::5` | v3 | 0.662 | 0.707 | **GOLD** | Failed deliveries are retried up to five times over six hours with exponential backoff. An endpoint is disable |
| 2 | `v3-errors::ratelimiterror::2` | v3 | 0.506 | 0.521 |  | When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_second |
| 3 | `v3-ratelimits::handling-http-429::4` | v3 | 0.499 | 0.499 |  | On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header  |

**Answer:** `I don't know based on the provided documents.`

**Label: G** — gold `v3-webhooks::retries::5` at rank 1 of top-3 containing ['five times'], but answer lacks it — lexical-support gate refused (support=0.43 < 0.60)
