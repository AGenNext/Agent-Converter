"""Tools for the Research deep agent.

Two kinds of tools live here:

1. Live integrations that have a public API and are cheap to wire:
   - tavily_search   (Tavily, web research)        -> needs TAVILY_API_KEY
   - web_search      (Tavily, lighter web search)  -> needs TAVILY_API_KEY
   - web_fetch       (read a URL)                   -> no key needed
   - perplexity_verify (Perplexity chat API)        -> needs PERPLEXITY_API_KEY
   - apollo_enrich   (Apollo.io people enrichment)  -> needs APOLLO_API_KEY

2. Stubs for premium data sources that need an enterprise contract. They are
   real LangChain tools with the right signature, but until you drop in the
   vendor SDK / endpoint they return a clear "not configured" message instead
   of fabricating data (the spec forbids fabrication). Search for
   `# TODO(builder)` to find each integration point.

Every tool degrades gracefully: if a key is missing it returns a short string
saying so, rather than raising, so the agent can record a gap and move on.
"""

from __future__ import annotations

import json
import os

import requests
from langchain_core.tools import tool

# Lazy import so the package still imports without the optional dependency.
try:  # pragma: no cover - exercised only when tavily is installed
    from tavily import TavilyClient
except Exception:  # pragma: no cover
    TavilyClient = None


_REQUEST_TIMEOUT = 30


def _missing(env_var: str, vendor: str) -> str:
    return (
        f"[{vendor} not configured] Set {env_var} to enable this tool. "
        "Returning no data so the agent records a gap rather than guessing."
    )


# ---------------------------------------------------------------------------
# Live integrations
# ---------------------------------------------------------------------------


@tool
def tavily_search(query: str, max_results: int = 5, topic: str = "general") -> str:
    """Deep web research across many sources via Tavily.

    Use as the primary general research tool: market reports, news, articles,
    company and investor context. `topic` may be "general", "news" or
    "finance". Returns a synthesised answer plus the top source results.
    """
    key = os.environ.get("TAVILY_API_KEY")
    if not key or TavilyClient is None:
        return _missing("TAVILY_API_KEY", "Tavily")
    client = TavilyClient(api_key=key)
    resp = client.search(
        query,
        max_results=max_results,
        topic=topic if topic in {"general", "news", "finance"} else "general",
        include_answer=True,
    )
    return json.dumps(resp, indent=2, default=str)


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Targeted web search for a specific gap or follow-up query.

    Lighter than `tavily_search`: use it to chase a named fact, a person's
    recent activity, a government statistic, or a single article. Returns the
    top results with titles, URLs and snippets.
    """
    key = os.environ.get("TAVILY_API_KEY")
    if not key or TavilyClient is None:
        return _missing("TAVILY_API_KEY", "Tavily (web_search)")
    client = TavilyClient(api_key=key)
    resp = client.search(query, max_results=max_results, search_depth="basic")
    results = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
        }
        for r in resp.get("results", [])
    ]
    return json.dumps(results, indent=2, default=str)


@tool
def web_fetch(url: str) -> str:
    """Fetch and return the readable text of a specific web page.

    Use after a search to read an article, blog post, filing, or a company's
    own pages. Returns up to ~12k characters of extracted text.
    """
    try:
        resp = requests.get(
            url,
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": "ResearchDeepAgent/1.0 (+research)"},
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return f"[web_fetch failed for {url}] {exc}"

    text = resp.text
    # Best-effort HTML -> text if BeautifulSoup is available; otherwise raw.
    try:  # pragma: no cover - optional dependency
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = "\n".join(
            line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
        )
    except Exception:  # pragma: no cover
        pass
    return text[:12000]


@tool
def perplexity_verify(claim_or_query: str) -> str:
    """Cross-check a fact with Perplexity as a FINAL verification layer.

    The spec mandates: never use this as the sole source. Use it to confirm
    key figures (fund size, market size, a person's role), surface
    contradictions, and catch anything missed. Returns Perplexity's answer
    with citations.
    """
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        return _missing("PERPLEXITY_API_KEY", "Perplexity")
    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            timeout=_REQUEST_TIMEOUT,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.environ.get("PERPLEXITY_MODEL", "sonar"),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Verify the user's claim against current sources. "
                            "State whether it is supported, contradicted, or "
                            "unverifiable, and cite sources. Be concise."
                        ),
                    },
                    {"role": "user", "content": claim_or_query},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return f"[perplexity_verify failed] {exc}"

    msg = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    citations = data.get("citations", [])
    out = {"verification": msg, "citations": citations}
    return json.dumps(out, indent=2, default=str)


@tool
def apollo_enrich(name: str = "", domain: str = "", email: str = "") -> str:
    """Enrich a person via Apollo.io: role, company, location, work history.

    Provide a name plus the company `domain` (best match), or an `email`.
    Only returns what Apollo holds. Never invent contact details; if Apollo
    returns nothing, record a gap.
    """
    key = os.environ.get("APOLLO_API_KEY")
    if not key:
        return _missing("APOLLO_API_KEY", "Apollo.io")
    try:
        resp = requests.post(
            "https://api.apollo.io/v1/people/match",
            timeout=_REQUEST_TIMEOUT,
            headers={"Content-Type": "application/json", "X-Api-Key": key},
            json={
                k: v
                for k, v in {
                    "name": name,
                    "domain": domain,
                    "email": email,
                }.items()
                if v
            },
        )
        resp.raise_for_status()
        person = resp.json().get("person")
    except Exception as exc:  # noqa: BLE001
        return f"[apollo_enrich failed] {exc}"

    if not person:
        return "[apollo_enrich] No match found. Record this as a gap."
    keep = {
        k: person.get(k)
        for k in (
            "name",
            "title",
            "headline",
            "organization_name",
            "city",
            "state",
            "country",
            "linkedin_url",
            "employment_history",
        )
    }
    return json.dumps(keep, indent=2, default=str)


# ---------------------------------------------------------------------------
# Premium data source stubs (enterprise contracts required)
# ---------------------------------------------------------------------------


@tool
def pitchbook_search(query: str, entity_type: str = "any") -> str:
    """Structured fund / company / deal data from PitchBook Premium.

    `entity_type` is "fund", "company", "deal", "person", or "any". Returns
    fund or company overview, funding history, investors, portfolio, deal
    history and team bios.
    """
    key = os.environ.get("PITCHBOOK_API_KEY")
    if not key:
        return _missing("PITCHBOOK_API_KEY", "PitchBook")
    # TODO(builder): call the PitchBook API / data feed here and map the
    # response to a compact JSON summary. Do not fabricate on error: return a
    # message so the agent records a gap.
    return _missing("PITCHBOOK_API_KEY", "PitchBook")


@tool
def factset_query(query: str) -> str:
    """Financial and market data from FactSet (public company metrics, sector
    performance, benchmarks).
    """
    key = os.environ.get("FACTSET_API_KEY")
    if not key:
        return _missing("FACTSET_API_KEY", "FactSet")
    # TODO(builder): call the FactSet AI-Ready Data API and summarise.
    return _missing("FACTSET_API_KEY", "FactSet")


@tool
def harmonic_lookup(company: str) -> str:
    """Company intelligence and growth signals from Harmonic."""
    key = os.environ.get("HARMONIC_API_KEY")
    if not key:
        return _missing("HARMONIC_API_KEY", "Harmonic")
    # TODO(builder): call the Harmonic API and summarise signals.
    return _missing("HARMONIC_API_KEY", "Harmonic")


@tool
def clay_enrich(target: str, kind: str = "company") -> str:
    """Company or people enrichment and signals from Clay.

    `kind` is "company" or "person".
    """
    key = os.environ.get("CLAY_API_KEY")
    if not key:
        return _missing("CLAY_API_KEY", "Clay")
    # TODO(builder): call the Clay enrichment API / table webhook and
    # summarise.
    return _missing("CLAY_API_KEY", "Clay")


# Exported in the order the spec tends to reach for them.
ALL_TOOLS = [
    pitchbook_search,
    factset_query,
    harmonic_lookup,
    clay_enrich,
    apollo_enrich,
    tavily_search,
    web_search,
    web_fetch,
    perplexity_verify,
]
