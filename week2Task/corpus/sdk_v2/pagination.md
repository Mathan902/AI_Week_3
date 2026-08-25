# Acme SDK v2 — Pagination

page_id: v2-pagination
sdk_version: v2
page_type: reference

# Pagination

List endpoints in SDK v2 return full pages with automatic pagination helpers.

## paginate_auto()

`paginate_auto()` walks every page of a collection and yields items one by one until the collection is exhausted.

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| url | str | — | yes | List endpoint path relative to base_url. |
| page_size | int | 100 | no | Number of items requested per page. |

```python
for invoice in client.paginate_auto(url="/v2/invoices"):
    print(invoice.id)
```

`paginate_auto()` was removed in SDK v3; use explicit cursor pagination via `list_after()` instead.
