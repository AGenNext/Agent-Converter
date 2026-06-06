# Configuration

All configuration is via environment variables, read from `.env` (copy
`.env.example`). The agent runs on whatever subset you provide.

## Model (vendor-neutral, local-first)

The agent runs on any LangChain-supported provider and resolves its default
model with this precedence:

1. `RESEARCH_AGENT_MODEL` (an explicit `provider:model` id) — always wins.
2. A recognised cloud key: `ANTHROPIC_API_KEY` → Claude, `OPENAI_API_KEY` →
   GPT, `GOOGLE_API_KEY` → Gemini.
3. `LOCAL_MODEL`, else the local default `ollama:tinyllama`.

So with **no keys set it runs fully locally** via Ollama, and adding a cloud key
(or `RESEARCH_AGENT_MODEL`) switches it to a hosted model.

| Variable | Purpose |
| --- | --- |
| `RESEARCH_AGENT_MODEL` | Force a specific model, `provider:model` format |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` | Use that cloud provider's default |
| `LOCAL_MODEL` | Override the local default (e.g. `ollama:llama3.1`) |

### Run fully local (Ollama)

```bash
# install Ollama (https://ollama.com), then:
ollama pull tinyllama        # or a tool-capable model: ollama pull llama3.1
pip install -r requirements.txt
python main.py "Research ..."   # no API keys needed
```

Caveat: small models such as `tinyllama` often cannot drive the multi-tool
agent loop reliably. For real research use a tool-capable local model
(`LOCAL_MODEL=ollama:llama3.1`) or a cloud key.

You can also pass a model directly in code, which takes precedence over the
env var:

```python
from research_agent import build_agent
agent = build_agent(model="anthropic:claude-sonnet-4-5")
# or a LangChain chat model instance
```

To use a non-Anthropic model, set `RESEARCH_AGENT_MODEL` (e.g.
`openai:gpt-...`) and provide that provider's key plus its LangChain
integration package.

## Data tools

Each key is optional. Without it, the matching tool returns a
"not configured" message and the agent records a gap instead of fabricating.

| Variable | Tool | Status |
| --- | --- | --- |
| `TAVILY_API_KEY` | `tavily_search`, `web_search` | Live |
| `PERPLEXITY_API_KEY` | `perplexity_verify` | Live |
| `PERPLEXITY_MODEL` | `perplexity_verify` (default `sonar`) | Live |
| `APOLLO_API_KEY` | `apollo_enrich` | Live |
| `PITCHBOOK_API_KEY` | `pitchbook_search` | Stub — wire in `tools.py` |
| `FACTSET_API_KEY` | `factset_query` | Stub — wire in `tools.py` |
| `HARMONIC_API_KEY` | `harmonic_lookup` | Stub — wire in `tools.py` |
| `CLAY_API_KEY` | `clay_enrich` | Stub — wire in `tools.py` |

`web_fetch` needs no key.

## Minimal viable setup

The agent is useful with just two keys:

```
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
```

Add `PERPLEXITY_API_KEY` for the verification layer and `APOLLO_API_KEY` for
people research. Wire the premium stubs when you have those contracts (see
[extending](extending.md)).

## Where keys are loaded

`tools.py` reads keys from the environment at call time via `os.environ`. Load
`.env` into the environment yourself (for example with `python-dotenv`) before
building the agent, or export the variables in your shell. `.env` is
gitignored; never commit real keys.
