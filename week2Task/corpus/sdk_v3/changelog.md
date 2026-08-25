# Acme SDK v3 — Changelog (v3.0)

page_id: v3-changelog
sdk_version: v3
page_type: changelog

# What changed in v3

This page lists behavioral changes between SDK v2 and SDK v3. Read it before migrating.

## Retry defaults changed

The default retry backoff delay was reduced from 2000 ms in v2 to 500 ms in v3, cutting worst-case recovery time after a transient failure. Code that relied on the old default should set `retry_backoff_ms=2000` explicitly.

## Timeout units renamed

Constructor option `timeout_s` is now `timeout_ms`; all durations in the SDK are milliseconds. The default timeout dropped from 30 seconds to 10 seconds (`timeout_ms=10000`).

## Removed APIs

`Client.request()` was removed; use `Client.send()`. `paginate_auto()` was removed in favor of explicit cursor pagination via `list_after()`.
