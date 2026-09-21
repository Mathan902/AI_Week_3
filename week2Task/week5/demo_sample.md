# Demo-set sample (bonus)

`random.Random(20260921).sample(sorted(golden ids), 10)` = ['Q04', 'Q01', 'Q12', 'Q02', 'Q11', 'Q07', 'Q06', 'Q09', 'Q10', 'Q05']

## 01. `tr-eb756d46af` — uploads keep failing with PayloadTooLargeError, what's the size limit?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-files::upload-parameters::1-table` | v3 | 0.681 | 0.726 |
| 2 | `v2-uploads::upload-parameters::1-table` | v2 | 0.665 | 0.725 |
| 3 | `v3-files::upload-parameters::2` | v3 | 0.685 | 0.715 |

<details><summary>retrieved text</summary>

**#1 `v3-files::upload-parameters::1-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 25 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| part_size_mb | int | 5 | no | Size of each multipart chunk when uploading large files. |
```

**#2 `v2-uploads::upload-parameters::1-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |
```

**#3 `v3-files::upload-parameters::2`**

```
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 02. `tr-d898260ff2` — what is the default for retry_backoff_ms

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-client::client-send::7` | v3 | 0.778 | 0.872 |
| 2 | `v2-client::client-request::5-table` | v2 | 0.676 | 0.789 |
| 3 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.693 | 0.787 |

<details><summary>retrieved text</summary>

**#1 `v3-client::client-send::7`**

```
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.
```

**#2 `v2-client::client-request::5-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |
```

**#3 `v3-changelog::retry-defaults-changed::1`**

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

</details>

**Output:** `The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call. [chunk:v3-client::client-send::7]`

## 03. `tr-f4296b1de7` — how many times does a failed webhook delivery get retried?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-webhooks::retries::5` | v3 | 0.662 | 0.707 |
| 2 | `v3-errors::ratelimiterror::2` | v3 | 0.506 | 0.521 |
| 3 | `v3-ratelimits::handling-http-429::4` | v3 | 0.499 | 0.499 |

<details><summary>retrieved text</summary>

**#1 `v3-webhooks::retries::5`**

```
Failed deliveries are retried up to five times over six hours with exponential backoff. An endpoint is disabled after 20 consecutive failures.
```

**#2 `v3-errors::ratelimiterror::2`**

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

**#3 `v3-ratelimits::handling-http-429::4`**

```
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 04. `tr-b52c17cd99` — how do I authenticate the client?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-client::authentication::1` | v2 | 0.531 | 0.581 |
| 2 | `v3-client::authentication::1` | v3 | 0.513 | 0.563 |
| 3 | `v3-client::client::0` | v3 | 0.499 | 0.549 |

<details><summary>retrieved text</summary>

**#1 `v2-client::authentication::1`**

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.
```

**#2 `v3-client::authentication::1`**

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.
```

**#3 `v3-client::client::0`**

```
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy for every request your application sends.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 05. `tr-48b7c63837` — timeout_s stopped working after the upgrade, what's the new option?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-changelog::timeout-units-renamed::2` | v3 | 0.610 | 0.670 |
| 2 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.494 | 0.524 |
| 3 | `v2-errors::toomanyrequestserror::4` | v2 | 0.462 | 0.492 |

<details><summary>retrieved text</summary>

**#1 `v3-changelog::timeout-units-renamed::2`**

```
Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds (`timeout_ms=10000`).
```

**#2 `v3-changelog::retry-defaults-changed::1`**

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

**#3 `v2-errors::toomanyrequestserror::4`**

```
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 06. `tr-2e7bca4968` — paginate_auto is gone after upgrading, what do I use now?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v2-pagination::paginate-auto::4` | v2 | 0.630 | 0.684 |
| 2 | `v2-pagination::paginate-auto::1` | v2 | 0.584 | 0.625 |
| 3 | `v3-changelog::removed-apis::3` | v3 | 0.501 | 0.556 |

<details><summary>retrieved text</summary>

**#1 `v2-pagination::paginate-auto::4`**

```
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
```

**#2 `v2-pagination::paginate-auto::1`**

```
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.
```

**#3 `v3-changelog::removed-apis::3`**

```
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.
```

</details>

**Output:** `I don't know based on the provided documents.`

## 07. `tr-28b455d072` — got a 429 back, how long should I wait before retrying?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-ratelimits::handling-http-429::4` | v3 | 0.538 | 0.565 |
| 2 | `v3-changelog::retry-defaults-changed::1` | v3 | 0.500 | 0.527 |
| 3 | `v3-errors::ratelimiterror::2` | v3 | 0.456 | 0.525 |

<details><summary>retrieved text</summary>

**#1 `v3-ratelimits::handling-http-429::4`**

```
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
```

**#2 `v3-changelog::retry-defaults-changed::1`**

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

**#3 `v3-errors::ratelimiterror::2`**

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

</details>

**Output:** `When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. [chunk:v3-errors::ratelimiterror::2]`

## 08. `tr-f019715dc3` — can I share one client across threads?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-client::thread-safety::9` | v3 | 0.744 | 0.851 |
| 2 | `v3-streaming::client-stream::1` | v3 | 0.319 | 0.341 |
| 3 | `v3-client::client-send::5` | v3 | 0.295 | 0.317 |

<details><summary>retrieved text</summary>

**#1 `v3-client::thread-safety::9`**

```
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.
```

**#2 `v3-streaming::client-stream::1`**

```
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.
```

**#3 `v3-client::client-send::5`**

```
`Client.send()` performs a single HTTP request and returns a `Response`.
```

</details>

**Output:** `A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request. Share one instance across threads instead of constructing a client per request. [chunk:v3-client::thread-safety::9]`

## 09. `tr-6a26231079` — how do I resume an upload that got interrupted?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-files::resumable-uploads::4` | v3 | 0.739 | 0.773 |
| 2 | `v2-uploads::upload-parameters::1-table` | v2 | 0.384 | 0.401 |
| 3 | `v2-uploads::file-uploads::0` | v2 | 0.380 | 0.396 |

<details><summary>retrieved text</summary>

**#1 `v3-files::resumable-uploads::4`**

```
Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Client.files.upload()`.
```

**#2 `v2-uploads::upload-parameters::1-table`**

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |
```

**#3 `v2-uploads::file-uploads::0`**

```
Uploads in SDK v2 go through `Client.upload_file()`.
```

</details>

**Output:** `Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Client.files.upload()`. [chunk:v3-files::resumable-uploads::4]`

## 10. `tr-a495636510` — what does X-RateLimit-Remaining mean?

| rank | chunk_id | ver | dense | final |
|---|---|---|---|---|
| 1 | `v3-ratelimits::headers::3` | v3 | 0.598 | 0.673 |
| 2 | `v3-ratelimits::rate-limits::0` | v3 | 0.495 | 0.495 |
| 3 | `v2-errors::toomanyrequestserror::4` | v2 | 0.399 | 0.399 |

<details><summary>retrieved text</summary>

**#1 `v3-ratelimits::headers::3`**

```
Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers describing your current budget.
```

**#2 `v3-ratelimits::rate-limits::0`**

```
Rate limits cap how many requests an account can make per minute. Limits are enforced per API token, not per IP address.
```

**#3 `v2-errors::toomanyrequestserror::4`**

```
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.
```

</details>

**Output:** `Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers describing your current budget. [chunk:v3-ratelimits::headers::3]`
