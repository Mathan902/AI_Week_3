# Acme SDK v3 — Streaming

page_id: v3-streaming
sdk_version: v3
page_type: reference

# Streaming responses

Streaming delivers server-sent events (SSE) as they are produced instead of waiting for the full response body.

## Client.stream()

`Client.stream()` returns an iterator of `StreamEvent` objects. The connection stays open until the server closes it or the iterator is closed by the caller.

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | Path of the streaming endpoint relative to base_url. |
| buffer_size_ms | int | 250 | no | Server-side buffering window in milliseconds before each event batch is flushed. |
| heartbeat_interval_ms | int | 15000 | no | Interval between keep-alive heartbeat frames on the idle stream. |

Lowering `buffer_size_ms` reduces end-to-end latency at the cost of more, smaller network writes.

```python
with client.stream(url="/v3/events") as events:
    for event in events:
        print(event.type, event.data)
```

## Reconnection

If the stream drops, the SDK reconnects automatically with exponential backoff and replays events missed while offline when the endpoint supports the `Last-Event-ID` header.
