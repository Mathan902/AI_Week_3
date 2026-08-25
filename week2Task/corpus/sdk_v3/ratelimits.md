# Acme SDK v3 — Rate limits

page_id: v3-ratelimits
sdk_version: v3
page_type: guide

# Rate limits

Rate limits cap how many requests an account can make per minute. Limits are enforced per API token, not per IP address.

## Limit tiers

| Tier | Requests per minute | Burst allowance |
|---|---|---|
| Free | 60 | 10 |
| Team | 600 | 100 |
| Enterprise | 6000 | custom |

The free tier allows 60 requests per minute with a burst allowance of 10 requests.

## Headers

Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers describing your current budget.

## Handling HTTP 429

On HTTP 429, wait for the duration given by `Retry-After`. The SDK's built-in retry policy honors this header automatically; see the Errors page for `RateLimitError`.
