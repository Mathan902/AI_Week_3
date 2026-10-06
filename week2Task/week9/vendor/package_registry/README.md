# package-registry MCP server (vendored)

Maintainer: Acme DevRel (devrel-tools team). Vendored from their internal repo at 0.4.1 on 2026-10-05; not
written or reviewed by the docs-assistant team before this week.

Exposes version metadata, release dates and deprecation notices for any package name.

| Env var | Meaning |
|---|---|
| `REGISTRY_URL` | upstream registry API. If unset, the server serves `REGISTRY_SNAPSHOT` offline. |
| `REGISTRY_TOKEN` | bearer token sent to `REGISTRY_URL` (read scope is enough; DevRel issues publish-scoped ones by default). |
| `REGISTRY_SNAPSHOT` | path to an offline JSON snapshot. |
| `REGISTRY_ACCESS_LOG` | where every tool call is appended (default `~/.cache/package-registry-mcp/access.log`). |
