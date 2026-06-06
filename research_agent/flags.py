"""Feature flags via OpenFeature (https://github.com/open-feature/spec).

The agent reads its toggles through the vendor-neutral OpenFeature API, so the
backing provider can be swapped without touching agent code. By default it uses
a zero-infrastructure provider that reads flags from environment variables, so
flags work out of the box (including inside a container). In production, point
OpenFeature at flagd or any other provider in one place (see `configure`).

Flag naming: an env-backed flag `research.enable_critique` is read from the
environment variable `OF_RESEARCH_ENABLE_CRITIQUE` (uppercased, dots and dashes
to underscores, `OF_` prefix). Booleans accept 1/0, true/false, yes/no, on/off.

Flags currently consulted:
- research.enable_critique   (bool, default true)  include the critique pack
- research.enabled_packs     (object/list, default []) if non-empty, only these
                             pack names are attached (others are dropped)
"""

from __future__ import annotations

import os
from typing import Sequence

from openfeature import api
from openfeature.flag_evaluation import FlagResolutionDetails, Reason
from openfeature.provider import AbstractProvider
from openfeature.provider.metadata import Metadata

_PREFIX = "OF_"
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _env_name(flag_key: str) -> str:
    safe = flag_key.upper().replace(".", "_").replace("-", "_")
    return f"{_PREFIX}{safe}"


class EnvironmentProvider(AbstractProvider):
    """An OpenFeature provider that resolves flags from environment variables.

    Deliberately tiny: it needs no network, no sidecar and no config file, so
    the agent has working flags by default. Swap it for flagd in production.
    """

    def get_metadata(self) -> Metadata:
        return Metadata(name="EnvironmentProvider")

    def _raw(self, flag_key: str):
        return os.environ.get(_env_name(flag_key))

    def resolve_boolean_details(self, flag_key, default_value, evaluation_context=None):
        raw = self._raw(flag_key)
        if raw is None:
            return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)
        low = raw.strip().lower()
        if low in _TRUE:
            return FlagResolutionDetails(value=True, reason=Reason.STATIC)
        if low in _FALSE:
            return FlagResolutionDetails(value=False, reason=Reason.STATIC)
        return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)

    def resolve_string_details(self, flag_key, default_value, evaluation_context=None):
        raw = self._raw(flag_key)
        if raw is None:
            return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)
        return FlagResolutionDetails(value=raw, reason=Reason.STATIC)

    def resolve_integer_details(self, flag_key, default_value, evaluation_context=None):
        raw = self._raw(flag_key)
        if raw is None:
            return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)
        try:
            return FlagResolutionDetails(value=int(raw), reason=Reason.STATIC)
        except ValueError:
            return FlagResolutionDetails(value=default_value, reason=Reason.ERROR)

    def resolve_float_details(self, flag_key, default_value, evaluation_context=None):
        raw = self._raw(flag_key)
        if raw is None:
            return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)
        try:
            return FlagResolutionDetails(value=float(raw), reason=Reason.STATIC)
        except ValueError:
            return FlagResolutionDetails(value=default_value, reason=Reason.ERROR)

    def resolve_object_details(self, flag_key, default_value, evaluation_context=None):
        raw = self._raw(flag_key)
        if raw is None:
            return FlagResolutionDetails(value=default_value, reason=Reason.DEFAULT)
        # Comma-separated list, e.g. OF_RESEARCH_ENABLED_PACKS="investor,people".
        items = [x.strip() for x in raw.split(",") if x.strip()]
        return FlagResolutionDetails(value=items, reason=Reason.STATIC)


_configured = False


def configure() -> None:
    """Register the default provider once.

    To use flagd or another provider instead, set the provider here (for
    example via the OpenFeature flagd provider package) before building the
    agent. This is the single integration point.
    """
    global _configured
    if _configured:
        return
    api.set_provider(EnvironmentProvider())
    _configured = True


def _client():
    configure()
    return api.get_client()


def is_enabled(flag_key: str, default: bool = True) -> bool:
    return _client().get_boolean_value(flag_key, default)


def get_list(flag_key: str, default: Sequence[str] | None = None) -> list:
    value = _client().get_object_value(flag_key, list(default or []))
    return list(value) if value else []
