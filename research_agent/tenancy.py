"""Multi-tenancy for the Research deep agent.

Lets one deployment serve many tenants (customers / orgs) with isolation of:

- credentials: each tenant can bring its own model key and data-tool API keys,
  so tenant A's research never uses tenant B's keys;
- model: each tenant can run a different model;
- agent instance: built and cached per tenant.

Isolation is request-scoped via a ContextVar, so it is safe under concurrent
serving: the server enters a tenant scope for the duration of a request, tools
resolve credentials from that scope, and nothing leaks between tenants.

Tenant configuration comes from (first match wins):

1. A JSON registry file at ``TENANTS_CONFIG``:
       {
         "acme":  {"model": "anthropic:claude-sonnet-4-5",
                    "keys": {"ANTHROPIC_API_KEY": "...", "TAVILY_API_KEY": "..."}},
         "beta":  {"keys": {"ANTHROPIC_API_KEY": "..."}}
       }
2. Per-tenant environment variables, e.g. ``TENANT_ACME_MODEL`` and
   ``TENANT_ACME_TAVILY_API_KEY``.
3. The process environment (the implicit "default" tenant), preserving
   single-tenant behaviour when no tenancy is configured.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache

DEFAULT_TENANT = "default"

# The credentials of the tenant handling the current request. Empty means
# "fall back to the process environment".
_current_creds: ContextVar[dict] = ContextVar("tenant_creds", default={})
_current_tenant: ContextVar[str] = ContextVar("tenant_id", default=DEFAULT_TENANT)


@dataclass
class TenantConfig:
    tenant_id: str
    model: str | None = None
    keys: dict = field(default_factory=dict)


def _safe(name: str) -> str:
    return name.upper().replace("-", "_")


@lru_cache(maxsize=1)
def _registry() -> dict:
    path = os.environ.get("TENANTS_CONFIG")
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return {}


def load_tenant(tenant_id: str | None) -> TenantConfig:
    """Resolve a tenant's configuration. Unknown tenants fall back to env."""
    tid = tenant_id or DEFAULT_TENANT

    reg = _registry().get(tid, {})
    if reg:
        return TenantConfig(
            tenant_id=tid,
            model=reg.get("model"),
            keys=dict(reg.get("keys", {})),
        )

    # Per-tenant env vars: TENANT_<ID>_<KEY>.
    if tid != DEFAULT_TENANT:
        prefix = f"TENANT_{_safe(tid)}_"
        keys = {
            k[len(prefix):]: v
            for k, v in os.environ.items()
            if k.startswith(prefix) and k != f"{prefix}MODEL"
        }
        if keys or f"{prefix}MODEL" in os.environ:
            return TenantConfig(
                tenant_id=tid,
                model=os.environ.get(f"{prefix}MODEL"),
                keys=keys,
            )

    # Default tenant: use the process environment implicitly.
    return TenantConfig(tenant_id=tid)


def get_credential(env_var: str) -> str | None:
    """Resolve a credential for the current tenant, falling back to env.

    Tools call this instead of reading ``os.environ`` directly, so the same
    process can serve different tenants with different keys.
    """
    creds = _current_creds.get()
    if env_var in creds:
        return creds[env_var]
    return os.environ.get(env_var)


def current_tenant_id() -> str:
    return _current_tenant.get()


@contextmanager
def tenant_scope(config: TenantConfig):
    """Bind a tenant's credentials for the duration of a request."""
    tok_creds = _current_creds.set(dict(config.keys))
    tok_id = _current_tenant.set(config.tenant_id)
    try:
        yield config
    finally:
        _current_creds.reset(tok_creds)
        _current_tenant.reset(tok_id)
