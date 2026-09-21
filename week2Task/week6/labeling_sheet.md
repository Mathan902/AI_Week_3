# Blind labelling sheet: 25 answers, one binary criterion

**Criterion: DIRECTLY ANSWERS.** This is the same wording the judge gets (`week6/judge_v1.txt`).

- **PASS**: a developer who asked this could act on the answer alone. It states the specific fact, value, behaviour or usage they asked for, and that is correct according to the documentation shown.
- **FAIL**: it quotes nearby text that doesn't answer the question, answers a different question, or says "I don't know" when the documentation shown contains the answer.
- "I don't know" is PASS only if the documentation shown really does not contain the answer.
- If the question names no version, the developer is on SDK v3.
- **Ignore** code formatting/parsing, endpoint validity, version labelling, deprecation notes, repetition and citation format. Assertions check those in code.

The cases are in a shuffled order and don't show their failure mode. No judge output exists yet.

**How to label:** put `"PASS"` or `"FAIL"` in each `label` field of `week6/labels_25.json` (the `note` field is optional). Then run `.venv/bin/python week6_eval.py lock-labels`.

---

## 1. `E22`: what changed between v2 and v3

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-changelog::what-changed-in-v3::0`** (SDK v3)

```
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.
```

**[2] `v2-uploads::upload-parameters::2`** (SDK v2)

```
The default maximum file size in v2 is 10 MB.
```

**[3] `v3-files::file-uploads::0`** (SDK v3)

```
Uploads in SDK v3 go through `Client.files.upload()`.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 2. `E18`: how do I authenticate the client?

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-client::authentication::1`** (SDK v2)

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. A missing token raises `AuthenticationError` before any network request is sent.
```

**[2] `v3-client::authentication::1`** (SDK v3)

```
Create the client with an API token supplied through the `ACME_API_TOKEN` environment variable. Tokens must not be committed to source control. A missing token raises `AuthenticationError` before any network request is sent.
```

**[3] `v3-client::client::0`** (SDK v3)

```
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy for every request your application sends.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 3. `E09`: TooManyRequestsError how to get the retry delay

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-errors::toomanyrequestserror::4`** (SDK v2)

```
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.
```

**[2] `v2-errors::toomanyrequestserror::3-code`** (SDK v2)

```
```python
from acme.errors import TooManyRequestsError
try:
    client.request(url="/v2/invoices")
except TooManyRequestsError as exc:
    delay = exc.response.headers["Retry-After"]
```
```

**[3] `v2-errors::toomanyrequestserror::2`** (SDK v2)

```
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.
```

</details>

**Answer:**

```text
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves. [chunk:v2-errors::toomanyrequestserror::2]
```

Label: ____

---

## 4. `E02`: how to verify webhook payload

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-webhooks::signature-verification::2-code`** (SDK v3)

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

**[2] `v3-webhooks::webhooks::0`** (SDK v3)

```
Webhooks push Acme platform events to an HTTPS endpoint you control.
```

**[3] `v3-webhooks::signature-verification::1`** (SDK v3)

```
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```

</details>

**Answer:**

```text
```python from acme.webhooks import verify_signature verify_signature(     payload=raw_body,     signature_header=request.headers["X-Acme-Signature"],     secret=WEBHOOK_SIGNING_SECRET, ) ``` from acme.webhooks import verify_signature [chunk:v3-webhooks::signature-verification::2-code]
```

Label: ____

---

## 5. `E07`: client.request example

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-client::client-request::4`** (SDK v2)

```
`Client.request()` performs a single HTTP request and returns a response object.
```

**[2] `v3-client::client-send::5`** (SDK v3)

```
`Client.send()` performs a single HTTP request and returns a `Response`.
```

**[3] `v2-client::client-request::6-code`** (SDK v2)

```
```python
response = client.request(url="/v2/invoices", method="POST")
```
```

</details>

**Answer:**

```text
response = client.request(url="/v2/invoices", method="POST") ```python response = client.request(url="/v2/invoices", method="POST") ``` [chunk:v2-client::client-request::6-code]
```

Label: ____

---

## 6. `E04`: verify_signature parameters

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-webhooks::verification-parameters::3-table`** (SDK v3)

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. |
| scheme | str | "v3" | no | Signature scheme prefix expected in the header. |
```

**[2] `v3-webhooks::signature-verification::2-code`** (SDK v3)

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

**[3] `v3-webhooks::signature-verification::1`** (SDK v3)

```
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```

</details>

**Answer:**

```text
from acme.webhooks import verify_signature verify_signature( [chunk:v3-webhooks::signature-verification::2-code]
```

Label: ____

---

## 7. `E15`: what happens if the stream disconnects

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-streaming::reconnection::5`** (SDK v3)

```
If the stream drops, the SDK reconnects automatically with exponential backoff and replays events missed while offline when the endpoint supports the `Last-Event-ID` header.
```

**[2] `v3-streaming::client-stream::1`** (SDK v3)

```
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.
```

**[3] `v3-streaming::streaming-responses::0`** (SDK v3)

```
Streaming delivers server-sent events (SSE) as they are produced instead of waiting for the full response body.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 8. `E12`: NotFoundError retryable?

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-errors::error-class-table::1-table`** (SDK v2)

```
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| NotFoundError | Resource does not exist | no |
| TooManyRequestsError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |
```

**[2] `v3-errors::error-class-table::1-table`** (SDK v3)

```
| Exception | Raised when | Retryable |
|---|---|---|
| AuthenticationError | Token missing or invalid | no |
| PermissionDeniedError | Token lacks required scope | no |
| NotFoundError | Resource does not exist | no |
| RateLimitError | HTTP 429 returned by the API | yes, after delay |
| ServerError | HTTP 5xx returned by the API | yes |
```

**[3] `v3-errors::disabling-automatic-error-retries::4`** (SDK v3)

```
Automatic retries apply only to retryable errors listed in the table above. Passing `max_retries=0` when constructing the client disables them; the first failure is then raised directly to the caller.
```

</details>

**Answer:**

```text
Automatic retries apply only to retryable errors listed in the table above. Passing `max_retries=0` when constructing the client disables them; the first failure is then raised directly to the caller. Automatic retries apply only to retryable errors listed in the table above [chunk:v3-errors::disabling-automatic-error-retries::4]
```

Label: ____

---

## 9. `E21`: list of removed apis in v3

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-changelog::what-changed-in-v3::0`** (SDK v3)

```
This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.
```

**[2] `v2-pagination::pagination::0`** (SDK v2)

```
List endpoints in SDK v2 return full pages with automatic pagination helpers.
```

**[3] `v2-pagination::paginate-auto::4`** (SDK v2)

```
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 10. `E11`: what is part_size_mb

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-files::upload-parameters::2`** (SDK v3)

```
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.
```

**[2] `v3-files::upload-parameters::1-table`** (SDK v3)

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 25 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| part_size_mb | int | 5 | no | Size of each multipart chunk when uploading large files. |
```

**[3] `v2-uploads::upload-parameters::2`** (SDK v2)

```
The default maximum file size in v2 is 10 MB.
```

</details>

**Answer:**

```text
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`. [chunk:v3-files::upload-parameters::2]
```

Label: ____

---

## 11. `E23`: what attribute tells me how long to wait after rate limit

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-ratelimits::rate-limits::0`** (SDK v3)

```
Rate limits cap how many requests an account can make per minute. Limits are enforced per API token, not per IP address.
```

**[2] `v3-errors::ratelimiterror::2`** (SDK v3)

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

**[3] `v2-errors::toomanyrequestserror::4`** (SDK v2)

```
In v3 this exception was renamed to `RateLimitError` and gained the `retry_after_seconds` attribute.
```

</details>

**Answer:**

```text
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again. [chunk:v3-errors::ratelimiterror::2]
```

Label: ____

---

## 12. `E14`: what is retry_backoff_ms

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-client::client-send::7`** (SDK v3)

```
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.
```

**[2] `v3-changelog::retry-defaults-changed::1`** (SDK v3)

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

**[3] `v2-client::client-request::5-table`** (SDK v2)

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |
```

</details>

**Answer:**

```text
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call. [chunk:v3-client::client-send::7]
```

Label: ____

---

## 13. `E01`: what scheme does verify_signature expect

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-webhooks::signature-verification::1`** (SDK v3)

```
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```

**[2] `v3-webhooks::signature-verification::2-code`** (SDK v3)

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

**[3] `v3-webhooks::verification-parameters::3-table`** (SDK v3)

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| tolerance_seconds | int | 300 | no | Maximum allowed age of a delivery before it is rejected as stale. |
| scheme | str | "v3" | no | Signature scheme prefix expected in the header. |
```

</details>

**Answer:**

```text
from acme.webhooks import verify_signature verify_signature( [chunk:v3-webhooks::signature-verification::2-code]
```

Label: ____

---

## 14. `E08`: upload_file is not an attribute of Client

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-uploads::upload-parameters::3-code`** (SDK v2)

```
```python
client.upload_file(file_path="report.pdf")
```
```

**[2] `v2-uploads::file-uploads::0`** (SDK v2)

```
Uploads in SDK v2 go through `Client.upload_file()`.
```

**[3] `v3-files::file-uploads::0`** (SDK v3)

```
Uploads in SDK v3 go through `Client.files.upload()`.
```

</details>

**Answer:**

```text
client.upload_file(file_path="report.pdf") ```python client.upload_file(file_path="report.pdf") ``` [chunk:v2-uploads::upload-parameters::3-code]
```

Label: ____

---

## 15. `E13`: how do I send json in the body of a request

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-client::client-send::5`** (SDK v3)

```
`Client.send()` performs a single HTTP request and returns a `Response`.
```

**[2] `v2-client::client-request::6-code`** (SDK v2)

```
```python
response = client.request(url="/v2/invoices", method="POST")
```
```

**[3] `v3-client::client-send::8-code`** (SDK v3)

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

**Answer:**

```text
`Client.send()` performs a single HTTP request and returns a `Response`. [chunk:v3-client::client-send::5]
```

Label: ____

---

## 16. `E05`: hw to verify webhok signature

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-webhooks::signature-verification::2-code`** (SDK v3)

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

**[2] `v3-webhooks::signature-verification::1`** (SDK v3)

```
Every delivery includes an `X-Acme-Signature` header containing an HMAC-SHA256 signature of the raw request body, keyed with your endpoint's signing secret. Verify the signature before trusting a payload.
```

**[3] `v3-webhooks::webhooks::0`** (SDK v3)

```
Webhooks push Acme platform events to an HTTPS endpoint you control.
```

</details>

**Answer:**

```text
from acme.webhooks import verify_signature verify_signature( [chunk:v3-webhooks::signature-verification::2-code]
```

Label: ____

---

## 17. `E17`: create invoice example

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-pagination::paginate-auto::3-code`** (SDK v2)

```
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```
```

**[2] `v2-client::client-request::6-code`** (SDK v2)

```
```python
response = client.request(url="/v2/invoices", method="POST")
```
```

**[3] `v3-client::client-send::8-code`** (SDK v3)

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

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 18. `E25`: is the client thread safe

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-client::thread-safety::9`** (SDK v3)

```
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request.
```

**[2] `v3-streaming::client-stream::1`** (SDK v3)

```
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.
```

**[3] `v3-client::client::0`** (SDK v3)

```
The `Client` is the entry point of the Acme SDK. It manages authentication, connection pooling, and retry policy for every request your application sends.
```

</details>

**Answer:**

```text
A `Client` instance is thread-safe. Share one instance across threads instead of constructing a client per request. A `Client` instance is thread-safe [chunk:v3-client::thread-safety::9]
```

Label: ____

---

## 19. `E16`: v2 upload limit vs v3

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-files::upload-parameters::2`** (SDK v3)

```
The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.
```

**[2] `v2-uploads::upload-parameters::2`** (SDK v2)

```
The default maximum file size in v2 is 10 MB.
```

**[3] `v3-files::file-uploads::0`** (SDK v3)

```
Uploads in SDK v3 go through `Client.files.upload()`.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 20. `E24`: what was the old default backoff

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-changelog::retry-defaults-changed::1`** (SDK v3)

```
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.
```

**[2] `v2-client::client-request::5-table`** (SDK v2)

```
| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path relative to the configured base_url. |
| method | str | "GET" | no | HTTP verb to use for the request. |
| retry_backoff_ms | int | 2000 | no | Overrides the client-level backoff delay for this request only. |
```

**[3] `v3-client::client-send::7`** (SDK v3)

```
The per-request `retry_backoff_ms` parameter overrides the value given in the constructor for that single call.
```

</details>

**Answer:**

```text
The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly. [chunk:v3-changelog::retry-defaults-changed::1]
```

Label: ____

---

## 21. `E03`: how do I stream events

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-streaming::streaming-responses::0`** (SDK v3)

```
Streaming delivers server-sent events (SSE) as they are produced instead of waiting for the full response body.
```

**[2] `v3-streaming::client-stream::4-code`** (SDK v3)

```
```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```
```

**[3] `v3-streaming::client-stream::1`** (SDK v3)

```
`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.
```

</details>

**Answer:**

```text
with client.stream(url="/v3/events") as events: ```python with client.stream(url="/v3/events") as events:     for event in events:         print(event.type, event.data) ``` [chunk:v3-streaming::client-stream::4-code]
```

Label: ____

---

## 22. `E19`: how many failures before my webhook is turned off

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-webhooks::retries::5`** (SDK v3)

```
Failed deliveries are retried up to five times over six hours with exponential backoff. An endpoint is disabled after 20 consecutive failures.
```

**[2] `v3-errors::ratelimiterror::2`** (SDK v3)

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

**[3] `v3-ratelimits::handling-http-429::4`** (SDK v3)

```
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 23. `E20`: webhook retry schedule

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v3-ratelimits::handling-http-429::4`** (SDK v3)

```
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
```

**[2] `v3-errors::ratelimiterror::2`** (SDK v3)

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

**[3] `v2-errors::toomanyrequestserror::2`** (SDK v2)

```
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.
```

</details>

**Answer:**

```text
I don't know based on the provided documents.
```

Label: ____

---

## 24. `E06`: paginate_auto example

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-pagination::paginate-auto::1`** (SDK v2)

```
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.
```

**[2] `v2-pagination::paginate-auto::4`** (SDK v2)

```
`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
```

**[3] `v2-pagination::paginate-auto::3-code`** (SDK v2)

```
```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```
```

</details>

**Answer:**

```text
`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted. [chunk:v2-pagination::paginate-auto::1]
```

Label: ____

---

## 25. `E10`: does the sdk automatically retry 429s

<details><summary>documentation shown (top 3 retrieved)</summary>

**[1] `v2-errors::toomanyrequestserror::2`** (SDK v2)

```
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves.
```

**[2] `v3-ratelimits::handling-http-429::4`** (SDK v3)

```
On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
```

**[3] `v3-errors::ratelimiterror::2`** (SDK v3)

```
When the service returns HTTP 429 the SDK raises `RateLimitError`. The exception carries a `retry_after_seconds` attribute parsed from the server's `Retry-After` header, so callers can wait exactly as long as the server asks before trying again.
```

</details>

**Answer:**

```text
When the service returns HTTP 429 in SDK v2 the SDK raises `TooManyRequestsError`. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves. The exception does not expose a parsed retry delay; callers must read the raw `Retry-After` header from the attached response object themselves. [chunk:v2-errors::toomanyrequestserror::2]
```

Label: ____
