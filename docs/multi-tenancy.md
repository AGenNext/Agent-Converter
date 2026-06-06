# Multi-tenancy

One deployment can serve many tenants (customers / orgs) with isolation of
credentials, model choice, and agent instance. Isolation is request-scoped via
a `ContextVar`, so it is safe under concurrent serving (`research_agent/tenancy.py`).

## How a request picks a tenant

Send the `X-Tenant-ID` header. If omitted, the `default` tenant is used (which
falls back to the process environment, preserving single-tenant behaviour).

```bash
curl -s localhost:8080/research \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: acme' \
  -d '{"question": "Research Fund X for our seed round."}'
```

The same header works on `/research`, `/research/stream` and `/research/a2ui`.

## What is isolated

- **Credentials** — tools resolve every API key through `get_credential()`,
  which reads the current tenant's keys first and falls back to the process
  env. Tenant A's research never uses tenant B's keys.
- **Model** — each tenant can run a different model.
- **Agent instance** — built once per tenant and cached.

## Configuring tenants

Two sources (first match wins), then the process env as the default tenant.

### 1. A JSON registry

Point `TENANTS_CONFIG` at a file:

```json
{
  "acme": {
    "model": "anthropic:claude-sonnet-4-5",
    "keys": {
      "ANTHROPIC_API_KEY": "sk-ant-acme...",
      "TAVILY_API_KEY": "tvly-acme..."
    }
  },
  "beta": {
    "keys": { "ANTHROPIC_API_KEY": "sk-ant-beta..." }
  }
}
```

In Kubernetes, mount this from a Secret and set `TENANTS_CONFIG` to its path.

### 2. Per-tenant environment variables

`TENANT_<ID>_<KEY>`, for example:

```
TENANT_ACME_MODEL=anthropic:claude-sonnet-4-5
TENANT_ACME_ANTHROPIC_API_KEY=sk-ant-acme...
TENANT_ACME_TAVILY_API_KEY=tvly-acme...
```

## Notes

- Missing a tenant's key degrades to a gap for that tool, never to
  fabrication, exactly as in single-tenant mode.
- The deep agent's virtual filesystem scratchpad is per-invocation, so there is
  no cross-request state to leak between tenants.
- The CLI and MCP server run as the default tenant; multi-tenancy is an
  HTTP-API feature.
