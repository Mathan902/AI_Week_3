# Blind labelling sheet: run `r2_b` (33 integrated-system answers)

**Criterion: DIRECTLY ANSWERS** (the Week 6 wording, unchanged, `week6/judge_v2.txt`).

- PASS: a developer on the stated SDK version could act on this answer alone; it states the fact, value, behaviour or usage they asked for, correct according to the documentation shown.
- FAIL: quotes nearby text that doesn't answer, answers a different question, or says it can't answer when the documentation shown contains the answer. A decline is PASS only if the docs shown really lack it.
- Ignore code formatting, version labels, deprecation notes, citations: assertions check those.

Shuffled order; modes hidden; no judge output exists for this run yet.

---

## 1. `C10`: what is the maximum upload size
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-uploads::upload-parameters::1-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |

[2] v2-uploads::upload-parameters::2 (SDK v2)
The default maximum file size in v2 is 10 MB.

[3] v2-uploads::file-uploads::0 (SDK v2)
Uploads in SDK v2 go through `Client.upload_file()`.

[4] check_deprecation({"symbol": "Client.upload_file", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "Client.upload_file", "status": "renamed", "kind": "replaced (not in changelog)", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.files.upload()", "replacement_path": "/v3/files", "note": "v2 uploads go through `Client.upload_file()`; v3 uploads go through `Client.files.upload()`. The v3 changelog does not list this change.", "source": "v3-files::file-uploads::0", "for_caller": "works on 2.4; replaced (not in changelog) in 3.0: when upgrading use Client.files.upload()"}

[5] check_deprecation({"symbol": "PayloadTooLargeError", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "PayloadTooLargeError", "sdk_version": "v2", "status": "not_in_changelog"}

[6] check_deprecation({"symbol": "max_file_size_mb", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "max_file_size_mb", "sdk_version": "v2", "status": "not_in_changelog"}

[7] symbol_exists({"symbol": "Client.upload_file", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.upload_file", "params": ["file_path", "max_file_size_mb", "mime_type"], "exists_in_v3": false}

[8] symbol_exists({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v3": true}

[9] check_deprecation({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "Client", "sdk_version": "v2", "status": "not_in_changelog"}
```
</details>

**Answer:**

```text
In SDK v2 the default maximum upload size is 10 MB. You can change it with `max_file_size_mb` on `Client.upload_file()`, and larger files raise `PayloadTooLargeError`. The v2 docs I retrieved don't cover the `Client()` constructor arguments, so the example uses it with no arguments.

```python
from acme import Client

client = Client()
client.upload_file("big.bin", max_file_size_mb=50)
```

Version notes (SDK 2.4):
- `Client.upload_file()` works on 2.4, but was replaced (not in changelog) in 3.0. When you upgrade, use Client.files.upload().

Sources:
- [SDK v2 2.0-2.9] [v2-uploads::upload-parameters::1-table](corpus/sdk_v2/uploads.md#upload-parameters)
- [SDK v2 2.0-2.9] [v2-uploads::upload-parameters::2](corpus/sdk_v2/uploads.md#upload-parameters)
- [SDK v2 2.0-2.9] [v2-uploads::file-uploads::0](corpus/sdk_v2/uploads.md#file-uploads)

Code checked against the SDK v2 symbol table: pass (3 symbols).
```

---

## 2. `C04`: how do I upload a file
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-uploads::upload-parameters::1-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |

[2] v2-uploads::file-uploads::0 (SDK v2)
Uploads in SDK v2 go through `Client.upload_file()`.

[3] v2-uploads::upload-parameters::3-code (SDK v2)
```python
client.upload_file(file_path="report.pdf")
```

[4] symbol_exists({"symbol": "Client.upload_file", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.upload_file", "params": ["file_path", "max_file_size_mb", "mime_type"], "exists_in_v3": false}

[5] check_deprecation({"symbol": "Client.upload_file", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "Client.upload_file", "status": "renamed", "kind": "replaced (not in changelog)", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.files.upload()", "replacement_path": "/v3/files", "note": "v2 uploads go through `Client.upload_file()`; v3 uploads go through `Client.files.upload()`. The v3 changelog does not list this change.", "source": "v3-files::file-uploads::0", "for_caller": "works on 2.4; replaced (not in changelog) in 3.0: when upgrading use Client.files.upload()"}

[6] symbol_exists({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v3": true}

[7] check_deprecation({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "Client", "sdk_version": "v2", "status": "not_in_changelog"}

[8] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[9] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.

[10] v2-client::client::0 (SDK v2)
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy.
```
</details>

**Answer:**

```text
In SDK 2.4 you upload a file with `Client.upload_file()`, which still works on 2.4 but is replaced by `Client.files.upload()` in 3.0, so plan that change before upgrading. The client reads its API token from the `ACME_API_TOKEN` environment variable.

```python
from acme import Client

client = Client()
client.upload_file(file_path="report.pdf")
```

Version notes (SDK 2.4):
- `Client.upload_file()` works on 2.4, but was replaced (not in changelog) in 3.0. When you upgrade, use Client.files.upload().

Sources:
- [SDK v2 2.0-2.9] [v2-uploads::upload-parameters::3-code](corpus/sdk_v2/uploads.md#upload-parameters)
- [SDK v2 2.0-2.9] [v2-uploads::file-uploads::0](corpus/sdk_v2/uploads.md#file-uploads)
- [SDK v2 2.0-2.9] [v2-uploads::upload-parameters::1-table](corpus/sdk_v2/uploads.md#upload-parameters)
- [SDK v2 2.0-2.9] [v2-client::authentication::1](corpus/sdk_v2/client.md#authentication)
- [SDK v2 2.0-2.9] [v2-client::client::0](corpus/sdk_v2/client.md#client)

Code checked against the SDK v2 symbol table: pass (3 symbols).
```

---

## 3. `C26`: migrate my paginate_auto loop to 3.0
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "paginate_auto", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "paginate_auto", "exists_in_v2": true, "changelog": "removed in 3.0; use list_after() (explicit cursor pagination)"}

[2] check_deprecation({"symbol": "paginate_auto", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "paginate_auto", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "list_after() (explicit cursor pagination)", "replacement_path": "/v3/invoices", "note": "`paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use list_after() (explicit cursor pagination)"}

[3] symbol_exists({"symbol": "list_after", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.list_after", "params": ["cursor", "url"], "exists_in_v2": false}

[4] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[5] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

[6] v3-streaming::client-stream::4-code (SDK v3)
```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

[7] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[8] v3-streaming::client-stream::4-code (SDK v3)
```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

[9] v3-streaming::client-stream::1 (SDK v3)
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.

[10] get_openapi_spec({"path": "/v3/invoices"}) (SDK v3)
{"path": "/v3/invoices", "sdk_version": "v3", "operations": {"get": {"operationId": "listInvoices", "summary": "List invoices with explicit cursor pagination.", "parameters": [{"name": "cursor", "in": "query", "required": false, "schema": {"type": "string"}, "description": "Cursor from the previous page; omit for the first page."}, {"name": "page_size", "in": "query", "required": false, "schema": {"type": "integer", "default": 100}}], "x-sdk-call": "cursor = None\nwhile True:\n    page = client.list_after(url=\"/v3/invoices\", cursor=cursor)\n    for invoice in page.items:\n        print(invoice.id)\n    cursor = page.next_cursor\n    if cursor is None:\n        break"}, "post": {"operationId": "createInvoice", "summary": "Create an invoice.", "requestBody": {"required": true, "content": {"application/json": {"schema": {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]}}}}, "x-sdk-call": "response = client.send(url=\"/v3/invoices\", method=\"POST\", body={\"amount\": 4200})\nprint(response.status_code)"}}}
```
</details>

**Answer:**

```text
`paginate_auto()` no longer exists in SDK 3.0. Replace it with explicit cursor pagination using `client.list_after(url=..., cursor=...)`, which takes the cursor from the previous page and returns `page.items` and `page.next_cursor`. The loop below assumes you already have a `client` object from your app, since I did not retrieve the v3 client constructor.

```python
cursor = None
while True:
    page = client.list_after(url="/v3/invoices", cursor=cursor)
    for invoice in page.items:
        print(invoice.id)
    cursor = page.next_cursor
    if cursor is None:
        break
```

Version notes (SDK 2.4):
- `paginate_auto()` no longer exists in 3.0 (removed). Use list_after() (explicit cursor pagination).

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::removed-apis::3](corpus/sdk_v3/changelog.md#removed-apis)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 4. `C05`: how do I handle a 429 and find out how long to wait
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[2] v2-errors::toomanyrequestserror::2 (SDK v2)
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.

[3] v2-errors::error-class-table::1-table (SDK v2)
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

[4] symbol_exists({"symbol": "TooManyRequestsError", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme.errors import TooManyRequestsError", "exists_in_v3": false}

[5] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[6] v2-errors::toomanyrequestserror::2 (SDK v2)
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.

[7] v2-errors::error-class-table::1-table (SDK v2)
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

[8] check_deprecation({"symbol": "TooManyRequestsError", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "TooManyRequestsError", "status": "renamed", "kind": "renamed", "changed_in": "3.0", "deprecated_in": null, "replacement": "RateLimitError (carries retry_after_seconds)", "replacement_path": null, "note": "In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.", "source": "v2-errors::toomanyrequestserror::4", "for_caller": "works on 2.4; renamed in 3.0: when upgrading use RateLimitError (carries retry_after_seconds)"}

[9] symbol_exists({"symbol": "client.request", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.request", "params": ["method", "retry_backoff_ms", "url"], "exists_in_v3": false}

[10] check_deprecation({"symbol": "client.request", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "Client.request", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.send()", "replacement_path": null, "note": "`Client.request()` was removed; use `Client.send()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use Client.send()"}

[11] check_deprecation({"symbol": "TooManyRequestsError.response.headers", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "TooManyRequestsError.response.headers", "sdk_version": "v2", "status": "not_in_changelog"}
```
</details>

**Answer:**

```text
On SDK v2.4, a 429 raises `TooManyRequestsError`, which does not parse the delay. Read the raw `Retry-After` header from `exc.response.headers`. Note that `client.request()` and `TooManyRequestsError` change in 3.0 (`Client.send()` and `RateLimitError`, which carries `retry_after_seconds`), so plan for that when upgrading.

```python
import time
from acme.errors import TooManyRequestsError

try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
    time.sleep(int(delay))  # Retry-After is usually seconds; it can also be an HTTP date, which this does not handle
```

Version notes (SDK 2.4):
- `Client.request()` works on 2.4, but was removed in 3.0. When you upgrade, use Client.send().
- `TooManyRequestsError` works on 2.4, but was renamed in 3.0. When you upgrade, use RateLimitError (carries retry_after_seconds).

Sources:
- [SDK v2 2.0-2.9] [v2-errors::toomanyrequestserror::2](corpus/sdk_v2/errors.md#toomanyrequestserror)
- [SDK v2 2.0-2.9] [v2-errors::toomanyrequestserror::3-code](corpus/sdk_v2/errors.md#toomanyrequestserror)
- [SDK v2 2.0-2.9] [v2-errors::error-class-table::1-table](corpus/sdk_v2/errors.md#error-class-table)
- [SDK v2 2.0-2.9] [v2-errors::toomanyrequestserror::4](corpus/sdk_v2/errors.md#toomanyrequestserror)

Code checked against the SDK v2 symbol table: pass (2 symbols).
```

---

## 5. `C07`: how do I stream events
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[2] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[3] v2-client::client::0 (SDK v2)
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy.

[4] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[5] v2-pagination::paginate-auto::1 (SDK v2)
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.

[6] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[7] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[8] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[9] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.
```
</details>

**Answer:**

```text
The v2 docs don't cover this: I searched the SDK 2.4 docs three ways and found nothing on streaming or event consumption. Check the v2 changelog or the Client reference for your version, or tell me which event source or endpoint you're calling so I can search again.
```

---

## 6. `C20`: what is the free tier rate limit
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-ratelimits::limit-tiers::2 (SDK v3)
The free tier allows 60 requests per minute with a burst allowance of 10 requests.

[2] v3-ratelimits::limit-tiers::1-table (SDK v3)
| Tier | Requests per minute | Burst allowance |
|---|---|---|
| Free | 60 | 10 |
| Team | 600 | 100 |
| Enterprise | 6000 | custom |

[3] v3-ratelimits::rate-limits::0 (SDK v3)
Rate limits cap how many requests an account can make per minute. Limits are enforced per API token, not per IP address.
```
</details>

**Answer:**

```text
The free tier allows 60 requests per minute, with a burst allowance of 10 requests. Limits are enforced per API token, not per IP address.

Sources:
- [SDK v3 3.0-3.2] [v3-ratelimits::limit-tiers::2](corpus/sdk_v3/ratelimits.md#limit-tiers)
- [SDK v3 3.0-3.2] [v3-ratelimits::limit-tiers::1-table](corpus/sdk_v3/ratelimits.md#limit-tiers)
- [SDK v3 3.0-3.2] [v3-ratelimits::rate-limits::0](corpus/sdk_v3/ratelimits.md#rate-limits)
```

---

## 7. `C29`: does the SDK support GraphQL?
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-streaming::client-stream::2-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path of the streaming endpoint relative to base_url. |
| buffer_size_ms | int | 250 | no | Server-side buffering window in milliseconds before each event batch is flushed. |
| heartbeat_interval_ms | int | 15000 | no | Interval between keep-alive heartbeat frames on the idle stream. |

[2] v3-ratelimits::limit-tiers::1-table (SDK v3)
| Tier | Requests per minute | Burst allowance |
|---|---|---|
| Free | 60 | 10 |
| Team | 600 | 100 |
| Enterprise | 6000 | custom |

[3] v3-client::thread-safety::9 (SDK v3)
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.

[4] v3-ratelimits::limit-tiers::1-table (SDK v3)
| Tier | Requests per minute | Burst allowance |
|---|---|---|
| Free | 60 | 10 |
| Team | 600 | 100 |
| Enterprise | 6000 | custom |

[5] v3-streaming::client-stream::2-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path of the streaming endpoint relative to base_url. |
| buffer_size_ms | int | 250 | no | Server-side buffering window in milliseconds before each event batch is flushed. |
| heartbeat_interval_ms | int | 15000 | no | Interval between keep-alive heartbeat frames on the idle stream. |

[6] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.
```
</details>

**Answer:**

```text
The v3 docs don't cover this: searches of the SDK 3.0 documentation for GraphQL returned no relevant content, so I can't confirm whether the SDK supports GraphQL. Check with the Acme team or the full v3 docs before assuming either way.
```

---

## 8. `C14`: Client(timeout_s=30) raises TypeError
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "timeout_s", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "timeout_s", "exists_in_v2": true, "changelog": "renamed in 3.0; use timeout_ms (milliseconds; default 10000)"}

[2] check_deprecation({"symbol": "timeout_s", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "timeout_s", "status": "renamed", "kind": "renamed", "changed_in": "3.0", "deprecated_in": null, "replacement": "timeout_ms (milliseconds; default 10000)", "replacement_path": null, "note": "Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds.", "source": "v3-changelog::timeout-units-renamed::2", "for_caller": "renamed in 3.0: `timeout_s` no longer exists on 3.0; use timeout_ms (milliseconds; default 10000)"}

[3] symbol_exists({"symbol": "timeout_ms", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "Client constructor parameter", "symbol": "timeout_ms", "exists_in_v2": false}
```
</details>

**Answer:**

```text
`timeout_s` no longer exists in SDK 3.0, so `Client(timeout_s=30)` raises TypeError. Use `timeout_ms` instead, which takes milliseconds: `Client(timeout_ms=30000)` is the 30-second equivalent. The 3.0 default also dropped from 30 seconds to 10 seconds (10000 ms), so set it explicitly if you relied on the old default.

```python
client = Client(timeout_ms=30000)
```

Version notes (SDK 3.0):
- `timeout_s()` no longer exists in 3.0 (renamed). Use timeout_ms (milliseconds; default 10000).

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::timeout-units-renamed::2](corpus/sdk_v3/changelog.md#timeout-units-renamed)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 9. `C32`: connecting with ACME_API_TOKEN=[REDACTED:api_key] and our proxy at [REDACTED:connection_string] - how do I change base_url?
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[2] v3-webhooks::webhooks::0 (SDK v3)
Webhooks push Acme platform events to an HTTPS endpoint you control.

[3] v3-client::authentication::1 (SDK v3)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.

[4] symbol_exists({"symbol": "base_url", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "Client constructor parameter", "symbol": "base_url", "exists_in_v2": true}

[5] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[6] v3-client::authentication::1 (SDK v3)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.

[7] v3-client::thread-safety::9 (SDK v3)
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.

[8] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[9] v3-client::client-constructor-parameters::3-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_ms | int | 10000 | no | Per-request timeout in milliseconds. |
| max_retries | int | 3 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 500 | no | Base delay in milliseconds for exponential backoff between retries. |

[10] v3-changelog::timeout-units-renamed::2 (SDK v3)
Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds (`timeout_ms=10000`).

[11] check_deprecation({"symbol": "base_url", "sdk_version": "3.0"}) (SDK v3)
{"symbol": "base_url", "sdk_version": "v3", "status": "not_in_changelog"}

[12] symbol_exists({"symbol": "Client", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v2": true}

[13] check_deprecation({"symbol": "Client", "sdk_version": "3.0"}) (SDK v3)
{"symbol": "Client", "sdk_version": "v3", "status": "not_in_changelog"}
```
</details>

**Answer:**

```text
Pass your proxy's root URL as `base_url` to the `Client` constructor in v3; it replaces the default `https://api.acme.dev`. Your API token is still read from the `ACME_API_TOKEN` environment variable, so you don't pass it in code.

```python
from acme import Client

# Replace with your proxy's root URL (the redacted value from your setup).
client = Client(base_url="https://YOUR-PROXY-HOST")
```

Sources:
- [SDK v3 3.0-3.2] [v3-client::client-constructor-parameters::3-table](corpus/sdk_v3/client.md#client-constructor-parameters)
- [SDK v3 3.0-3.2] [v3-client::authentication::1](corpus/sdk_v3/client.md#authentication)

Code checked against the SDK v3 symbol table: pass (2 symbols).
```

---

## 10. `C08`: how do I verify a webhook signature
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[2] v2-uploads::upload-parameters::1-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |

[3] v2-errors::error-class-table::1-table (SDK v2)
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

[4] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[5] v2-errors::error-class-table::1-table (SDK v2)
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

[6] v2-errors::toomanyrequestserror::2 (SDK v2)
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.

[7] symbol_exists({"symbol": "verify_signature", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": false, "symbol": "verify_signature", "exists_in_v3": true}

[8] v2-errors::toomanyrequestserror::2 (SDK v2)
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.

[9] v2-errors::error-class-table::1-table (SDK v2)
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

[10] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.
```
</details>

**Answer:**

```text
The v2 docs don't cover this. Searches of the SDK 2.4 docs found nothing on webhook signature verification, and `verify_signature` does not exist in SDK 2.4; it exists only in v3, so upgrading to v3 is the path to that helper.
```

---

## 11. `C01`: how do I paginate through all invoices
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-pagination::paginate-auto::3-code (SDK v2)
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```

[2] v2-pagination::paginate-auto::1 (SDK v2)
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.

[3] v2-pagination::paginate-auto::4 (SDK v2)
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.

[4] symbol_exists({"symbol": "paginate_auto", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.paginate_auto", "params": ["page_size", "url"], "exists_in_v3": false}

[5] check_deprecation({"symbol": "paginate_auto", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "paginate_auto", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "list_after() (explicit cursor pagination)", "replacement_path": "/v3/invoices", "note": "`paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use list_after() (explicit cursor pagination)"}
```
</details>

**Answer:**

```text
In SDK v2, `client.paginate_auto()` walks every page of a collection and yields items one at a time, so you can loop over all invoices directly. This method is removed in SDK 3.0, where you must use explicit cursor pagination with `list_after()` instead.

```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```

Version notes (SDK 2.4):
- `paginate_auto()` works on 2.4, but was removed in 3.0. When you upgrade, use list_after() (explicit cursor pagination).

Sources:
- [SDK v2 2.0-2.9] [v2-pagination::paginate-auto::3-code](corpus/sdk_v2/pagination.md#paginate-auto)
- [SDK v2 2.0-2.9] [v2-pagination::paginate-auto::1](corpus/sdk_v2/pagination.md#paginate-auto)
- [SDK v2 2.0-2.9] [v2-pagination::paginate-auto::4](corpus/sdk_v2/pagination.md#paginate-auto)

Code checked against the SDK v2 symbol table: pass (1 symbols).
```

---

## 12. `C23`: client.paginate_auto(url="/v2/invoices") is slow, how do I change the page size?
(Resolved: SDK 2.x.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "client.paginate_auto", "sdk_version": "2.x"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.paginate_auto", "params": ["page_size", "url"], "exists_in_v3": false}

[2] v2-pagination::paginate-auto::1 (SDK v2)
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.

[3] v2-pagination::paginate-auto::2-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | List endpoint path relative to base_url. |
| page_size | int | 100 | no | Number of items requested per page. |

[4] v2-pagination::paginate-auto::4 (SDK v2)
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.

[5] check_deprecation({"symbol": "Client.paginate_auto", "sdk_version": "2.x"}) (SDK v2)
{"sdk_version": "v2", "symbol": "paginate_auto", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "list_after() (explicit cursor pagination)", "replacement_path": "/v3/invoices", "note": "`paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.x; removed in 3.0: when upgrading use list_after() (explicit cursor pagination)"}

[6] check_deprecation({"symbol": "page_size", "sdk_version": "2.x"}) (SDK v2)
{"symbol": "page_size", "sdk_version": "v2", "status": "not_in_changelog"}

[7] symbol_exists({"symbol": "Client", "sdk_version": "2.x"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v3": true}

[8] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[9] v2-pagination::paginate-auto::2-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | List endpoint path relative to base_url. |
| page_size | int | 100 | no | Number of items requested per page. |

[10] v2-client::client-request::5-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |

[11] check_deprecation({"symbol": "Client", "sdk_version": "2.x"}) (SDK v2)
{"symbol": "Client", "sdk_version": "v2", "status": "not_in_changelog"}

[12] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.

[13] v2-client::client::0 (SDK v2)
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy.

[14] v2-client::client-request::6-code (SDK v2)
```python
response = client.request(url="/v2/invoices", method="POST")
```
```
</details>

**Answer:**

```text
I don't know based on the provided documents.
```

---

## 13. `C16`: client.upload_file() raises AttributeError
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "client.upload_file", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "client.upload_file", "exists_in_v2": true, "changelog": "replaced (not in changelog) in 3.0; use Client.files.upload()"}

[2] symbol_exists({"symbol": "files.upload", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.files.upload", "params": ["file_path", "max_file_size_mb", "part_size_mb"], "exists_in_v2": false}

[3] check_deprecation({"symbol": "client.upload_file", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "Client.upload_file", "status": "renamed", "kind": "replaced (not in changelog)", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.files.upload()", "replacement_path": "/v3/files", "note": "v2 uploads go through `Client.upload_file()`; v3 uploads go through `Client.files.upload()`. The v3 changelog does not list this change.", "source": "v3-files::file-uploads::0", "for_caller": "replaced (not in changelog) in 3.0: `Client.upload_file` no longer exists on 3.0; use Client.files.upload()"}

[4] v3-files::upload-parameters::3-code (SDK v3)
```python
client.files.upload(file_path="dataset.csv", max_file_size_mb=25)
```

[5] v3-files::file-uploads::0 (SDK v3)
Uploads in SDK v3 go through `Client.files.upload()`.

[6] v3-files::upload-parameters::1-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 25 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| part_size_mb | int | 5 | no | Size of each multipart chunk when uploading large files. |

[7] v3-files::file-uploads::0 (SDK v3)
Uploads in SDK v3 go through `Client.files.upload()`.

[8] v3-client::thread-safety::9 (SDK v3)
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.

[9] v3-changelog::what-changed-in-v3::0 (SDK v3)
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.

[10] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[11] v3-client::authentication::1 (SDK v3)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.

[12] v3-client::thread-safety::9 (SDK v3)
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.

[13] symbol_exists({"symbol": "Client", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v2": true}

[14] v3-client::authentication::1 (SDK v3)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.

[15] v3-client::authentication::2-code (SDK v3)
```python
from acme import Client
client = Client()  # reads ACME_API_TOKEN
```

[16] v3-client::client-constructor-parameters::3-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_ms | int | 10000 | no | Per-request timeout in milliseconds. |
| max_retries | int | 3 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 500 | no | Base delay in milliseconds for exponential backoff between retries. |
```
</details>

**Answer:**

```text
I don't know based on the provided documents.
```

---

## 14. `C31`: my token [REDACTED:acme_token] gives AuthenticationError on 2.4, how should I pass the token?
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[2] v2-errors::error-class-table::1-table (SDK v2)
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |

[3] v2-errors::error-handling::0 (SDK v2)
All SDK exceptions inherit from `AcmeError`. API-level failures raise subclasses of `ApiError`.

[4] check_deprecation({"symbol": "AuthenticationError", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "AuthenticationError", "sdk_version": "v2", "status": "not_in_changelog"}

[5] check_deprecation({"symbol": "ACME_API_TOKEN", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "ACME_API_TOKEN", "sdk_version": "v2", "status": "not_in_changelog"}
```
</details>

**Answer:**

```text
On SDK v2, supply the token through the `ACME_API_TOKEN` environment variable, set before you create the client. `AuthenticationError` is raised before any request is sent when the token is missing, and also when the token is invalid, so check that the variable is set in the same shell or process that runs your code. The v2 docs don't show a code sample for passing the token as a constructor argument.

Sources:
- [SDK v2 2.0-2.9] [v2-client::authentication::1](corpus/sdk_v2/client.md#authentication)
- [SDK v2 2.0-2.9] [v2-errors::error-class-table::1-table](corpus/sdk_v2/errors.md#error-class-table)
```

---

## 15. `C28`: AttributeError: 'Client' object has no attribute 'query'
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "client.query", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "client.query", "exists_in_v2": false}

[2] v3-client::thread-safety::9 (SDK v3)
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.

[3] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[4] v3-client::client-send::5 (SDK v3)
`Client.send()` performs a single HTTP request and returns a `Response`.

[5] check_deprecation({"symbol": "client.query", "sdk_version": "3.0"}) (SDK v3)
{"symbol": "client.query", "sdk_version": "v3", "status": "not_in_changelog"}

[6] symbol_exists({"symbol": "client.send", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.send", "params": ["body", "headers", "method", "retry_backoff_ms", "url"], "exists_in_v2": false}

[7] v3-client::client-send::5 (SDK v3)
`Client.send()` performs a single HTTP request and returns a `Response`.

[8] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[9] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[10] check_deprecation({"symbol": "client.request", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "Client.request", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.send()", "replacement_path": null, "note": "`Client.request()` was removed; use `Client.send()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "removed in 3.0: `Client.request` no longer exists on 3.0; use Client.send()"}
```
</details>

**Answer:**

```text
`client.query` doesn't exist in SDK v3 (or v2), so this AttributeError is expected; the v3 docs don't describe a `query` method. To make a request on v3, use `Client.send()`, which replaces the removed `Client.request()`.

```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

Version notes (SDK 3.0):
- `Client.request()` no longer exists in 3.0 (removed). Use Client.send().
- The default changed in 3.0: The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3. Set retry_backoff_ms=2000 explicitly to keep the v2 behaviour.

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::removed-apis::3](corpus/sdk_v3/changelog.md#removed-apis)
- [SDK v3 3.0-3.2] [v3-client::client-send::5](corpus/sdk_v3/client.md#client-send)
- [SDK v3 3.0-3.2] [v3-client::client-send::6-table](corpus/sdk_v3/client.md#client-send)
- [SDK v3 3.0-3.2] [v3-client::client-send::8-code](corpus/sdk_v3/client.md#client-send)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 16. `C18`: how do I verify a webhook signature
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-webhooks::signature-verification::2-code (SDK v3)
```python
from acme.webhooks import verify_signature
verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```

[2] v3-webhooks::signature-verification::1 (SDK v3)
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.

[3] v3-webhooks::webhooks::0 (SDK v3)
Webhooks push Acme platform events to an HTTPS endpoint you control.

[4] symbol_exists({"symbol": "verify_signature", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "function", "symbol": "acme.webhooks.verify_signature", "params": ["payload", "scheme", "secret", "signature_header", "tolerance_seconds"], "exists_in_v2": false}
```
</details>

**Answer:**

```text
Verify the `X-Acme-Signature` header against the raw request body before you trust the payload, using `verify_signature` from `acme.webhooks` with your endpoint's signing secret. Pass the raw bytes of the body, not parsed JSON, because the signature is an HMAC-SHA256 over the exact body.

```python
from acme.webhooks import verify_signature

verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```

Sources:
- [SDK v3 3.0-3.2] [v3-webhooks::signature-verification::2-code](corpus/sdk_v3/webhooks.md#signature-verification)
- [SDK v3 3.0-3.2] [v3-webhooks::signature-verification::1](corpus/sdk_v3/webhooks.md#signature-verification)

Code checked against the SDK v3 symbol table: pass (2 symbols).
```

---

## 17. `C02`: how do I send a POST request to create an invoice
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-client::client-request::6-code (SDK v2)
```python
response = client.request(url="/v2/invoices", method="POST")
```

[2] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[3] v2-pagination::paginate-auto::3-code (SDK v2)
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```

[4] symbol_exists({"symbol": "client.request", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.request", "params": ["method", "retry_backoff_ms", "url"], "exists_in_v3": false}

[5] check_deprecation({"symbol": "client.request", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "Client.request", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.send()", "replacement_path": null, "note": "`Client.request()` was removed; use `Client.send()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use Client.send()"}

[6] v2-client::client-request::6-code (SDK v2)
```python
response = client.request(url="/v2/invoices", method="POST")
```

[7] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.

[8] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[9] v2-client::client-request::6-code (SDK v2)
```python
response = client.request(url="/v2/invoices", method="POST")
```

[10] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.

[11] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[12] v2-uploads::file-uploads::0 (SDK v2)
Uploads in SDK v2 go through `Client.upload_file()`.

[13] v2-errors::toomanyrequestserror::2 (SDK v2)
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.

[14] v2-uploads::upload-parameters::1-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |
```
</details>

**Answer:**

```text
The v2 docs don't cover this. They show `client.request(url="/v2/invoices", method="POST")` for a POST, but no parameter for sending a JSON body, so I can't give you a verified way to create an invoice on SDK 2.4. Also, `Client.request()` was removed in 3.0; on v3 the replacement is `Client.send()`.

Version notes (SDK 2.4):
- `Client.request()` works on 2.4, but was removed in 3.0. When you upgrade, use Client.send().

Sources:
- [SDK v2 2.0-2.9] [v2-client::client-request::6-code](corpus/sdk_v2/client.md#client-request)
- [SDK v2 2.0-2.9] [v2-client::client-request::4](corpus/sdk_v2/client.md#client-request)
```

---

## 18. `C03`: set the request timeout to 60 seconds
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-client::client-constructor-parameters::2-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_s | float | 30 | no | Per-request timeout in seconds. |
| max_retries | int | 5 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 2000 | no | Base delay in milliseconds for exponential backoff between retries. |

[2] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[3] v2-client::client-request::5-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |

[4] symbol_exists({"symbol": "timeout_s", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "Client constructor parameter", "symbol": "timeout_s", "exists_in_v3": false}

[5] check_deprecation({"symbol": "timeout_s", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "timeout_s", "status": "renamed", "kind": "renamed", "changed_in": "3.0", "deprecated_in": null, "replacement": "timeout_ms (milliseconds; default 10000)", "replacement_path": null, "note": "Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds.", "source": "v3-changelog::timeout-units-renamed::2", "for_caller": "works on 2.4; renamed in 3.0: when upgrading use timeout_ms (milliseconds; default 10000)"}

[6] check_deprecation({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "Client", "sdk_version": "v2", "status": "not_in_changelog"}

[7] symbol_exists({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v3": true}
```
</details>

**Answer:**

```text
On SDK 2.4, pass `timeout_s=60` to the `Client` constructor. This is a per-request timeout in seconds (the v2 default is 30). The option is renamed to `timeout_ms` in 3.0, where durations are in milliseconds and the default is 10000, so the value will need to change when you upgrade.

```python
from acme import Client

client = Client(timeout_s=60)
```

Version notes (SDK 2.4):
- `timeout_s()` works on 2.4, but was renamed in 3.0. When you upgrade, use timeout_ms (milliseconds; default 10000).

Sources:
- [SDK v2 2.0-2.9] [v2-client::client-constructor-parameters::2-table](corpus/sdk_v2/client.md#client-constructor-parameters)

Code checked against the SDK v2 symbol table: pass (2 symbols).
```

---

## 19. `C12`: how do I use client.request() to POST an invoice?
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "client.request", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "client.request", "exists_in_v2": true, "changelog": "removed in 3.0; use Client.send()"}

[2] check_deprecation({"symbol": "client.request", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "Client.request", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.send()", "replacement_path": null, "note": "`Client.request()` was removed; use `Client.send()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "removed in 3.0: `Client.request` no longer exists on 3.0; use Client.send()"}

[3] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[4] v3-client::client-send::5 (SDK v3)
`Client.send()` performs a single HTTP request and returns a `Response`.

[5] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```
```
</details>

**Answer:**

```text
`client.request()` no longer exists in SDK 3.0. Use `client.send()` instead, passing `method="POST"` and the invoice data as `body`. Your existing client setup stays the same.

```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

Version notes (SDK 3.0):
- `Client.request()` no longer exists in 3.0 (removed). Use Client.send().
- The default changed in 3.0: The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3. Set retry_backoff_ms=2000 explicitly to keep the v2 behaviour.

Sources:
- [SDK v3 3.0-3.2] [v3-client::client-send::8-code](corpus/sdk_v3/client.md#client-send)
- [SDK v3 3.0-3.2] [v3-client::client-send::5](corpus/sdk_v3/client.md#client-send)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 20. `C27`: how do I use client.batch() to send several requests at once
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "client.batch", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": false, "symbol": "client.batch", "exists_in_v3": false}

[2] check_deprecation({"symbol": "client.batch", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "client.batch", "sdk_version": "v2", "status": "not_in_changelog"}

[3] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.

[4] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[5] v2-client::client-request::6-code (SDK v2)
```python
response = client.request(url="/v2/invoices", method="POST")
```

[6] check_deprecation({"symbol": "client.request", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "Client.request", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.send()", "replacement_path": null, "note": "`Client.request()` was removed; use `Client.send()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use Client.send()"}
```
</details>

**Answer:**

```text
`client.batch()` does not exist in SDK v2.4 (or in v3). The v2 docs don't cover sending several requests at once. The documented v2 call is `Client.request()`, which sends one HTTP request per call, and it is removed in 3.0 (use `Client.send()` after upgrading).

Version notes (SDK 2.4):
- `Client.request()` works on 2.4, but was removed in 3.0. When you upgrade, use Client.send().

Sources:
- [SDK v2 2.0-2.9] [v2-client::client-request::4](corpus/sdk_v2/client.md#client-request)
- [SDK v2 2.0-2.9] [v2-client::client-request::6-code](corpus/sdk_v2/client.md#client-request)
```

---

## 21. `C25`: I'm upgrading from 2.4 to 3.0. How do I rewrite client.request(url="/v2/invoices", method="POST")?
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "client.request", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "client.request", "exists_in_v2": true, "changelog": "removed in 3.0; use Client.send()"}

[2] symbol_exists({"symbol": "Client.send", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.send", "params": ["body", "headers", "method", "retry_backoff_ms", "url"], "exists_in_v2": false}

[3] check_deprecation({"symbol": "client.request", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "Client.request", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "Client.send()", "replacement_path": null, "note": "`Client.request()` was removed; use `Client.send()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use Client.send()"}

[4] v3-client::client-send::5 (SDK v3)
`Client.send()` performs a single HTTP request and returns a `Response`.

[5] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[6] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[7] get_openapi_spec({"path": "/v3/invoices"}) (SDK v3)
{"path": "/v3/invoices", "sdk_version": "v3", "operations": {"get": {"operationId": "listInvoices", "summary": "List invoices with explicit cursor pagination.", "parameters": [{"name": "cursor", "in": "query", "required": false, "schema": {"type": "string"}, "description": "Cursor from the previous page; omit for the first page."}, {"name": "page_size", "in": "query", "required": false, "schema": {"type": "integer", "default": 100}}], "x-sdk-call": "cursor = None\nwhile True:\n    page = client.list_after(url=\"/v3/invoices\", cursor=cursor)\n    for invoice in page.items:\n        print(invoice.id)\n    cursor = page.next_cursor\n    if cursor is None:\n        break"}, "post": {"operationId": "createInvoice", "summary": "Create an invoice.", "requestBody": {"required": true, "content": {"application/json": {"schema": {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]}}}}, "x-sdk-call": "response = client.send(url=\"/v3/invoices\", method=\"POST\", body={\"amount\": 4200})\nprint(response.status_code)"}}}
```
</details>

**Answer:**

```text
`client.request()` no longer exists in SDK 3.0; use `Client.send()` instead. The v3 invoices endpoint is `/v3/invoices` (not `/v2/invoices`), and the POST requires a JSON body with an integer `amount`, so pass `body={"amount": ...}` with the amount you need.

```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
)
print(response.status_code)
```

Version notes (SDK 2.4):
- `Client.request()` no longer exists in 3.0 (removed). Use Client.send().

Sources:
- [SDK v3 3.0-3.2] [v3-client::client-send::8-code](corpus/sdk_v3/client.md#client-send)
- [SDK v3 3.0-3.2] [v3-client::client-send::6-table](corpus/sdk_v3/client.md#client-send)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 22. `C24`: how do I upload a file
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-files::upload-parameters::1-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 25 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| part_size_mb | int | 5 | no | Size of each multipart chunk when uploading large files. |

[2] v3-files::file-uploads::0 (SDK v3)
Uploads in SDK v3 go through `Client.files.upload()`.

[3] v3-files::upload-parameters::3-code (SDK v3)
```python
client.files.upload(file_path="dataset.csv", max_file_size_mb=25)
```

[4] symbol_exists({"symbol": "Client", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v2": true}

[5] check_deprecation({"symbol": "files.upload", "sdk_version": "2.9"}) (SDK v3)
{"symbol": "files.upload", "sdk_version": "v3", "status": "not_in_changelog"}

[6] v3-client::authentication::1 (SDK v3)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.

[7] v3-client::thread-safety::9 (SDK v3)
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.

[8] v3-client::client::0 (SDK v3)
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy for every request your application sends.

[9] check_deprecation({"symbol": "Client", "sdk_version": "3.0"}) (SDK v3)
{"symbol": "Client", "sdk_version": "v3", "status": "not_in_changelog"}

[10] symbol_exists({"symbol": "files.upload", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.files.upload", "params": ["file_path", "max_file_size_mb", "part_size_mb"], "exists_in_v2": false}

[11] check_deprecation({"symbol": "files.upload", "sdk_version": "3.0"}) (SDK v3)
{"symbol": "files.upload", "sdk_version": "v3", "status": "not_in_changelog"}

[12] v3-files::file-uploads::0 (SDK v3)
Uploads in SDK v3 go through `Client.files.upload()`.

[13] v3-files::upload-parameters::3-code (SDK v3)
```python
client.files.upload(file_path="dataset.csv", max_file_size_mb=25)
```

[14] v3-client::client-send::5 (SDK v3)
`Client.send()` performs a single HTTP request and returns a `Response`.
```
</details>

**Answer:**

```text
I don't know based on the provided documents.
```

---

## 23. `C13`: paginate_auto example
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "paginate_auto", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "paginate_auto", "exists_in_v2": true, "changelog": "removed in 3.0; use list_after() (explicit cursor pagination)"}

[2] symbol_exists({"symbol": "list_after", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.list_after", "params": ["cursor", "url"], "exists_in_v2": false}

[3] check_deprecation({"symbol": "paginate_auto", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "paginate_auto", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "list_after() (explicit cursor pagination)", "replacement_path": "/v3/invoices", "note": "`paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "removed in 3.0: `paginate_auto` no longer exists on 3.0; use list_after() (explicit cursor pagination)"}

[4] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[5] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

[6] v3-streaming::client-stream::4-code (SDK v3)
```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

[7] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[8] v3-streaming::client-stream::4-code (SDK v3)
```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

[9] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[10] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[11] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

[12] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[13] get_openapi_spec({"path": "/v3/invoices"}) (SDK v3)
{"path": "/v3/invoices", "sdk_version": "v3", "operations": {"get": {"operationId": "listInvoices", "summary": "List invoices with explicit cursor pagination.", "parameters": [{"name": "cursor", "in": "query", "required": false, "schema": {"type": "string"}, "description": "Cursor from the previous page; omit for the first page."}, {"name": "page_size", "in": "query", "required": false, "schema": {"type": "integer", "default": 100}}], "x-sdk-call": "cursor = None\nwhile True:\n    page = client.list_after(url=\"/v3/invoices\", cursor=cursor)\n    for invoice in page.items:\n        print(invoice.id)\n    cursor = page.next_cursor\n    if cursor is None:\n        break"}, "post": {"operationId": "createInvoice", "summary": "Create an invoice.", "requestBody": {"required": true, "content": {"application/json": {"schema": {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]}}}}, "x-sdk-call": "response = client.send(url=\"/v3/invoices\", method=\"POST\", body={\"amount\": 4200})\nprint(response.status_code)"}}}
```
</details>

**Answer:**

```text
`paginate_auto()` no longer exists in SDK 3.0. Use `client.list_after(url=..., cursor=...)` and loop on `next_cursor` until it is `None`. The example below assumes `client` is already constructed.

```python
cursor = None
while True:
    page = client.list_after(url="/v3/invoices", cursor=cursor)
    for invoice in page.items:
        print(invoice.id)
    cursor = page.next_cursor
    if cursor is None:
        break
```

Version notes (SDK 3.0):
- `paginate_auto()` no longer exists in 3.0 (removed). Use list_after() (explicit cursor pagination).

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::removed-apis::3](corpus/sdk_v3/changelog.md#removed-apis)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 24. `C30`: what's new in SDK v4?
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-changelog::what-changed-in-v3::0 (SDK v3)
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.

[2] v3-files::file-uploads::0 (SDK v3)
Uploads in SDK v3 go through `Client.files.upload()`.

[3] v3-changelog::timeout-units-renamed::2 (SDK v3)
Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds (`timeout_ms=10000`).

[4] v3-changelog::what-changed-in-v3::0 (SDK v3)
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.

[5] v3-files::file-uploads::0 (SDK v3)
Uploads in SDK v3 go through `Client.files.upload()`.

[6] v3-changelog::timeout-units-renamed::2 (SDK v3)
Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds (`timeout_ms=10000`).

[7] check_deprecation({"symbol": "timeout_s", "sdk_version": "2.9"}) (SDK v3)
{"sdk_version": "v3", "symbol": "timeout_s", "status": "renamed", "kind": "renamed", "changed_in": "3.0", "deprecated_in": null, "replacement": "timeout_ms (milliseconds; default 10000)", "replacement_path": null, "note": "Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds.", "source": "v3-changelog::timeout-units-renamed::2", "for_caller": "renamed in 3.0: `timeout_s` no longer exists on 3.0; use timeout_ms (milliseconds; default 10000)"}
```
</details>

**Answer:**

```text
SDK 4.x has no published docs, so I can't tell you what's new in it. The latest published version is v3, and its changelog lists the changes from v2: the `timeout_s` constructor option is now `timeout_ms` (all durations are milliseconds, default 10000), and file uploads go through `Client.files.upload()`. The v3 docs don't cover anything changed in v4.

Version notes (SDK 3.0):
- There are no docs for SDK 4.x. The latest published version is 3.0-3.2; this answer is for 3.0.
- `timeout_s()` no longer exists in 3.0 (renamed). Use timeout_ms (milliseconds; default 10000).

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::what-changed-in-v3::0](corpus/sdk_v3/changelog.md#what-changed-in-v3)
- [SDK v3 3.0-3.2] [v3-changelog::timeout-units-renamed::2](corpus/sdk_v3/changelog.md#timeout-units-renamed)
- [SDK v3 3.0-3.2] [v3-files::file-uploads::0](corpus/sdk_v3/files.md#file-uploads)
```

---

## 25. `C19`: what is the default retry backoff
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-changelog::retry-defaults-changed::1 (SDK v3)
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.

[2] v3-client::client-send::7 (SDK v3)
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.

[3] v3-client::client-send::6-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| headers | dict | {} | no | Additional request headers merged over the defaults. |
| body | dict \| None | None | no | JSON-serializable request body. Ignored for GET requests. |
| retry_backoff_ms | int | 500 | no | Overrides the client-level backoff delay for this request only. |

[4] check_deprecation({"symbol": "retry_backoff_ms", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "retry_backoff_ms", "status": "default_changed", "kind": "default changed", "changed_in": "3.0", "deprecated_in": null, "replacement": "set retry_backoff_ms=2000 explicitly to keep the v2 behaviour", "replacement_path": null, "note": "The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3.", "source": "v3-changelog::retry-defaults-changed::1", "for_caller": "default changed in 3.0: set retry_backoff_ms=2000 explicitly to keep the v2 behaviour"}
```
</details>

**Answer:**

```text
The default retry backoff in SDK v3 is 500 ms, reduced from 2000 ms in v2. To keep the v2 delay, set `retry_backoff_ms=2000` explicitly.

Version notes (SDK 3.0):
- The default changed in 3.0: The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3. Set retry_backoff_ms=2000 explicitly to keep the v2 behaviour.

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::retry-defaults-changed::1](corpus/sdk_v3/changelog.md#retry-defaults-changed)
- [SDK v3 3.0-3.2] [v3-client::client-send::6-table](corpus/sdk_v3/client.md#client-send)
```

---

## 26. `C21`: I'm on 2.4 - how do I iterate every invoice?
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-pagination::paginate-auto::3-code (SDK v2)
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```

[2] v2-pagination::paginate-auto::1 (SDK v2)
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.

[3] v2-pagination::pagination::0 (SDK v2)
List endpoints in SDK v2 return full pages with automatic pagination helpers.

[4] symbol_exists({"symbol": "client.paginate_auto", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "client method", "symbol": "Client.paginate_auto", "params": ["page_size", "url"], "exists_in_v3": false}

[5] check_deprecation({"symbol": "client.paginate_auto", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "paginate_auto", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "list_after() (explicit cursor pagination)", "replacement_path": "/v3/invoices", "note": "`paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "works on 2.4; removed in 3.0: when upgrading use list_after() (explicit cursor pagination)"}

[6] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[7] v2-client::client-request::6-code (SDK v2)
```python
response = client.request(url="/v2/invoices", method="POST")
```

[8] v2-client::client-request::4 (SDK v2)
`Client.request()` performs a single HTTP request and returns a response object.

[9] symbol_exists({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v3": true}

[10] check_deprecation({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "Client", "sdk_version": "v2", "status": "not_in_changelog"}

[11] v2-client::authentication::1 (SDK v2)
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.

[12] v2-client::client::0 (SDK v2)
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy.

[13] v2-errors::toomanyrequestserror::3-code (SDK v2)
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```

[14] v2-pagination::paginate-auto::3-code (SDK v2)
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```

[15] v2-pagination::paginate-auto::4 (SDK v2)
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.

[16] v2-pagination::paginate-auto::1 (SDK v2)
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.
```
</details>

**Answer:**

```text
I don't know based on the provided documents.
```

---

## 27. `C17`: how do I stream events
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-streaming::streaming-responses::0 (SDK v3)
Streaming delivers server-sent events (SSE) as they are produced instead of waiting for the full response body.

[2] v3-streaming::client-stream::4-code (SDK v3)
```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

[3] v3-streaming::client-stream::1 (SDK v3)
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.

[4] symbol_exists({"symbol": "Client.stream", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.stream", "params": ["buffer_size_ms", "heartbeat_interval_ms", "url"], "exists_in_v2": false}
```
</details>

**Answer:**

```text
Use `Client.stream()` with a v3 endpoint URL and iterate over the returned `StreamEvent` objects. The connection stays open until the server closes it or you close the iterator, so the `with` block handles cleanup. The snippet assumes you already have a `client`; `Client.stream()` also accepts `buffer_size_ms` and `heartbeat_interval_ms`.

```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

Sources:
- [SDK v3 3.0-3.2] [v3-streaming::streaming-responses::0](corpus/sdk_v3/streaming.md#streaming-responses)
- [SDK v3 3.0-3.2] [v3-streaming::client-stream::4-code](corpus/sdk_v3/streaming.md#client-stream)
- [SDK v3 3.0-3.2] [v3-streaming::client-stream::1](corpus/sdk_v3/streaming.md#client-stream)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 28. `C11`: how do I paginate through all invoices
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[2] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[3] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

[4] symbol_exists({"symbol": "list_after", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "client method", "symbol": "Client.list_after", "params": ["cursor", "url"], "exists_in_v2": false}

[5] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[6] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

[7] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[8] v3-changelog::removed-apis::3 (SDK v3)
`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.

[9] v3-client::client-send::8-code (SDK v3)
```python
response = client.send(
    url="/v3/invoices",
    method="POST",
    body={"amount": 4200},
    retry_backoff_ms=500,
)
print(response.status_code)
```

[10] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

[11] get_openapi_spec({"path": "/v3/invoices"}) (SDK v3)
{"path": "/v3/invoices", "sdk_version": "v3", "operations": {"get": {"operationId": "listInvoices", "summary": "List invoices with explicit cursor pagination.", "parameters": [{"name": "cursor", "in": "query", "required": false, "schema": {"type": "string"}, "description": "Cursor from the previous page; omit for the first page."}, {"name": "page_size", "in": "query", "required": false, "schema": {"type": "integer", "default": 100}}], "x-sdk-call": "cursor = None\nwhile True:\n    page = client.list_after(url=\"/v3/invoices\", cursor=cursor)\n    for invoice in page.items:\n        print(invoice.id)\n    cursor = page.next_cursor\n    if cursor is None:\n        break"}, "post": {"operationId": "createInvoice", "summary": "Create an invoice.", "requestBody": {"required": true, "content": {"application/json": {"schema": {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]}}}}, "x-sdk-call": "response = client.send(url=\"/v3/invoices\", method=\"POST\", body={\"amount\": 4200})\nprint(response.status_code)"}}}

[12] check_deprecation({"symbol": "paginate_auto", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "paginate_auto", "status": "removed", "kind": "removed", "changed_in": "3.0", "deprecated_in": null, "replacement": "list_after() (explicit cursor pagination)", "replacement_path": "/v3/invoices", "note": "`paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.", "source": "v3-changelog::removed-apis::3", "for_caller": "removed in 3.0: `paginate_auto` no longer exists on 3.0; use list_after() (explicit cursor pagination)"}
```
</details>

**Answer:**

```text
`paginate_auto()` was removed in SDK 3.0. To page through all invoices, call `client.list_after(url="/v3/invoices", cursor=cursor)` in a loop, starting with `cursor=None` and stopping when `page.next_cursor` is None. The example assumes you already have a `client`.

```python
cursor = None
while True:
    page = client.list_after(url="/v3/invoices", cursor=cursor)
    for invoice in page.items:
        print(invoice.id)
    cursor = page.next_cursor
    if cursor is None:
        break
```

Version notes (SDK 3.0):
- `paginate_auto()` no longer exists in 3.0 (removed). Use list_after() (explicit cursor pagination).

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::removed-apis::3](corpus/sdk_v3/changelog.md#removed-apis)

Code checked against the SDK v3 symbol table: pass (1 symbols).
```

---

## 29. `C15`: how do I catch TooManyRequestsError
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "TooManyRequestsError", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": false, "symbol": "TooManyRequestsError", "exists_in_v2": true, "changelog": "renamed in 3.0; use RateLimitError (carries retry_after_seconds)"}

[2] check_deprecation({"symbol": "TooManyRequestsError", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "TooManyRequestsError", "status": "renamed", "kind": "renamed", "changed_in": "3.0", "deprecated_in": null, "replacement": "RateLimitError (carries retry_after_seconds)", "replacement_path": null, "note": "In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.", "source": "v2-errors::toomanyrequestserror::4", "for_caller": "renamed in 3.0: `TooManyRequestsError` no longer exists on 3.0; use RateLimitError (carries retry_after_seconds)"}

[3] symbol_exists({"symbol": "RateLimitError", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "import", "symbol": "from acme.errors import RateLimitError", "exists_in_v2": false}

[4] v3-ratelimits::handling-http-429::4 (SDK v3)
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.

[5] v3-errors::ratelimiterror::2 (SDK v3)
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.

[6] v3-errors::ratelimiterror::3-code (SDK v3)
```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```
```
</details>

**Answer:**

```text
`TooManyRequestsError` no longer exists in SDK 3.0; it was renamed to `RateLimitError`, which the SDK raises on HTTP 429. Catch `RateLimitError` and read `retry_after_seconds` to see how long the server asked you to wait.

```python
from acme.errors import RateLimitError
try:
    client.send(url="/v3/invoices")
except RateLimitError as exc:
    print(f"wait {exc.retry_after_seconds}s")
```

Version notes (SDK 3.0):
- `TooManyRequestsError` no longer exists in 3.0 (renamed). Use RateLimitError (carries retry_after_seconds).

Sources:
- [SDK v3 3.0-3.2] [v3-errors::ratelimiterror::3-code](corpus/sdk_v3/errors.md#ratelimiterror)
- [SDK v3 3.0-3.2] [v3-errors::ratelimiterror::2](corpus/sdk_v3/errors.md#ratelimiterror)
- [SDK v3 3.0-3.2] [v3-ratelimits::handling-http-429::4](corpus/sdk_v3/ratelimits.md#handling-http-429)

Code checked against the SDK v3 symbol table: pass (2 symbols).
```

---

## 30. `C06`: what is the default retry backoff
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-client::client-request::5-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |

[2] v2-client::client-constructor-parameters::2-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_s | float | 30 | no | Per-request timeout in seconds. |
| max_retries | int | 5 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 2000 | no | Base delay in milliseconds for exponential backoff between retries. |

[3] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[4] check_deprecation({"symbol": "retry_backoff_ms", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "symbol": "retry_backoff_ms", "status": "default_changed", "kind": "default changed", "changed_in": "3.0", "deprecated_in": null, "replacement": "set retry_backoff_ms=2000 explicitly to keep the v2 behaviour", "replacement_path": null, "note": "The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3.", "source": "v3-changelog::retry-defaults-changed::1", "for_caller": "works on 2.4; default changed in 3.0: when upgrading use set retry_backoff_ms=2000 explicitly to keep the v2 behaviour"}

[5] symbol_exists({"symbol": "retry_backoff_ms", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "Client constructor parameter", "symbol": "retry_backoff_ms", "exists_in_v3": true}
```
</details>

**Answer:**

```text
In SDK v2 the default retry backoff is 2000 ms, set by the `retry_backoff_ms` client constructor option. It is the base delay for exponential backoff between retries. In v3.0 the default drops to 500 ms, so set `retry_backoff_ms=2000` explicitly before upgrading if you want to keep the v2 behaviour.

Version notes (SDK 2.4):
- `retry_backoff_ms()` works on 2.4, but was default changed in 3.0. When you upgrade, use set retry_backoff_ms=2000 explicitly to keep the v2 behaviour.

Sources:
- [SDK v2 2.0-2.9] [v2-client::client-constructor-parameters::2-table](corpus/sdk_v2/client.md#client-constructor-parameters)
- [SDK v2 2.0-2.9] [v2-client::client-request::5-table](corpus/sdk_v2/client.md#client-request)
```

---

## 31. `C22`: we're on acme 3.0, set the timeout to 2 minutes
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] symbol_exists({"symbol": "timeout_ms", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "Client constructor parameter", "symbol": "timeout_ms", "exists_in_v2": false}

[2] v3-changelog::timeout-units-renamed::2 (SDK v3)
Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds (`timeout_ms=10000`).

[3] v3-client::client-send::7 (SDK v3)
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.

[4] v3-errors::ratelimiterror::2 (SDK v3)
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.

[5] check_deprecation({"symbol": "timeout_s", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "symbol": "timeout_s", "status": "renamed", "kind": "renamed", "changed_in": "3.0", "deprecated_in": null, "replacement": "timeout_ms (milliseconds; default 10000)", "replacement_path": null, "note": "Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds.", "source": "v3-changelog::timeout-units-renamed::2", "for_caller": "renamed in 3.0: `timeout_s` no longer exists on 3.0; use timeout_ms (milliseconds; default 10000)"}

[6] symbol_exists({"symbol": "Client", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v2": true}
```
</details>

**Answer:**

```text
`timeout_s` no longer exists in SDK 3.0. Set the timeout with the `timeout_ms` constructor option instead, in milliseconds, so 2 minutes is `timeout_ms=120000`. The 3.0 default also dropped from 30 seconds to 10 seconds, so set it explicitly if you rely on a longer default.

```python
from acme import Client

client = Client(timeout_ms=120000)
```

Version notes (SDK 3.0):
- `timeout_s()` no longer exists in 3.0 (renamed). Use timeout_ms (milliseconds; default 10000).

Sources:
- [SDK v3 3.0-3.2] [v3-changelog::timeout-units-renamed::2](corpus/sdk_v3/changelog.md#timeout-units-renamed)

Code checked against the SDK v3 symbol table: pass (2 symbols).
```

---

## 32. `C09`: how do I turn off automatic retries
(The caller's installed SDK version, sent by their IDE: 2.4.)
(Resolved: SDK 2.4.)

<details><summary>documentation shown</summary>

```
[1] v2-client::client-constructor-parameters::3 (SDK v2)
Setting `max_retries=0` disables all automatic retries.

[2] v2-client::client-constructor-parameters::2-table (SDK v2)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| base_url | str | https://api.acme.dev | no | Root URL of the Acme API. |
| timeout_s | float | 30 | no | Per-request timeout in seconds. |
| max_retries | int | 5 | no | Automatic retries per request. Set to 0 to disable retries entirely. |
| retry_backoff_ms | int | 2000 | no | Base delay in milliseconds for exponential backoff between retries. |

[3] v2-errors::toomanyrequestserror::4 (SDK v2)
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.

[4] symbol_exists({"symbol": "max_retries", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "Client constructor parameter", "symbol": "max_retries", "exists_in_v3": true}

[5] check_deprecation({"symbol": "max_retries", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "max_retries", "sdk_version": "v2", "status": "not_in_changelog"}

[6] symbol_exists({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"sdk_version": "v2", "exists": true, "kind": "import", "symbol": "from acme import Client", "exists_in_v3": true}

[7] check_deprecation({"symbol": "Client", "sdk_version": "2.4"}) (SDK v2)
{"symbol": "Client", "sdk_version": "v2", "status": "not_in_changelog"}
```
</details>

**Answer:**

```text
Pass `max_retries=0` to the `Client` constructor in SDK v2. The default is 5 automatic retries per request, and setting it to 0 disables retries entirely.

```python
from acme import Client

client = Client(max_retries=0)
```

Sources:
- [SDK v2 2.0-2.9] [v2-client::client-constructor-parameters::3](corpus/sdk_v2/client.md#client-constructor-parameters)
- [SDK v2 2.0-2.9] [v2-client::client-constructor-parameters::2-table](corpus/sdk_v2/client.md#client-constructor-parameters)

Code checked against the SDK v2 symbol table: pass (2 symbols).
```

---

## 33. `C33`: load the webhook signing secret from an environment variable and verify the signature
(The caller's installed SDK version, sent by their IDE: 3.0.)
(Resolved: SDK 3.0.)

<details><summary>documentation shown</summary>

```
[1] v3-webhooks::signature-verification::2-code (SDK v3)
```python
from acme.webhooks import verify_signature
verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```

[2] v3-webhooks::signature-verification::1 (SDK v3)
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.

[3] v3-webhooks::webhooks::0 (SDK v3)
Webhooks push Acme platform events to an HTTPS endpoint you control.

[4] symbol_exists({"symbol": "verify_signature", "sdk_version": "3.0"}) (SDK v3)
{"sdk_version": "v3", "exists": true, "kind": "function", "symbol": "acme.webhooks.verify_signature", "params": ["payload", "scheme", "secret", "signature_header", "tolerance_seconds"], "exists_in_v2": false}

[5] v3-webhooks::verification-parameters::3-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. |
| scheme | str | "v3" | no | Signature scheme prefix expected in the header. |

[6] v3-webhooks::verification-parameters::4 (SDK v3)
Deliveries older than `tolerance_seconds` fail verification; this protects you against replay attacks.

[7] v3-webhooks::signature-verification::1 (SDK v3)
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.

[8] v3-webhooks::verification-parameters::3-table (SDK v3)
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. |
| scheme | str | "v3" | no | Signature scheme prefix expected in the header. |

[9] v3-webhooks::signature-verification::2-code (SDK v3)
```python
from acme.webhooks import verify_signature
verify_signature(
    payload=raw_body,
    signature_header=request.headers["X-Acme-Signature"],
    secret=WEBHOOK_SIGNING_SECRET,
)
```

[10] v3-webhooks::signature-verification::1 (SDK v3)
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```
</details>

**Answer:**

```text
Read the signing secret with os.environ and pass it to acme.webhooks.verify_signature along with the raw request body and the X-Acme-Signature header. The v3 docs don't say which exception verify_signature raises on an invalid or stale signature, so check the error handling before relying on it.

```python
import os
from acme.webhooks import verify_signature

WEBHOOK_SIGNING_SECRET = os.environ["WEBHOOK_SIGNING_SECRET"]

def handle_webhook(raw_body, headers):
    verify_signature(
        payload=raw_body,
        signature_header=headers["X-Acme-Signature"],
        secret=WEBHOOK_SIGNING_SECRET,
    )
```

Sources:
- [SDK v3 3.0-3.2] [v3-webhooks::signature-verification::2-code](corpus/sdk_v3/webhooks.md#signature-verification)
- [SDK v3 3.0-3.2] [v3-webhooks::signature-verification::1](corpus/sdk_v3/webhooks.md#signature-verification)
- [SDK v3 3.0-3.2] [v3-webhooks::verification-parameters::3-table](corpus/sdk_v3/webhooks.md#verification-parameters)
- [SDK v3 3.0-3.2] [v3-webhooks::verification-parameters::4](corpus/sdk_v3/webhooks.md#verification-parameters)

Code checked against the SDK v3 symbol table: pass (2 symbols).
```
