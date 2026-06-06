# Changelog

All notable changes to this project are documented here. The format is loosely
based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-06-06

First release. Converts the Research Agent build specification (v1.0) into a
runnable LangChain deep agent, plus interfaces, deployment, and supply-chain
tooling around it.

### Agent
- LangChain `deepagents` orchestrator implementing the spec's research process,
  critical-thinking layer, evidence categories, confidence tags, source
  hierarchy, output standards and anti-patterns.
- Source-pack sub-agents: investor, people, market, company, technical, sales,
  general, plus a `critique` stress-test pack.
- Tools: live Tavily, web search/fetch, Perplexity, Apollo; honest stubs for
  PitchBook, FactSet, Harmonic, Clay (degrade to gaps, never fabricate).
- Vendor-neutral, **local-first** model selection: defaults to a local Ollama
  model with no keys, uses a cloud provider when its key is present, fully
  configurable via `RESEARCH_AGENT_MODEL` / `LOCAL_MODEL` / per request.
- Multi-tenancy with per-tenant credentials and model, isolated per request.
- OpenFeature feature flags (toggle the critique pack and enabled packs).

### Interfaces
- CLI (`main.py`).
- FastAPI HTTP API with OpenAPI docs (`/docs`, `/redoc`).
- Real-time streaming as CloudEvents over SSE (`/research/stream`).
- A2UI surface streaming (`/research/a2ui`) with a real in-browser A2UI client.
- MCP server exposing `research` / `research_pack` tools.
- Built-in control panel with a step-by-step onboarding wizard and a Storybook
  component kit (`ui/`).

### Deployment
- OCI image via Cloud Native Buildpacks; docker-compose.
- Kubernetes manifests, a Helm-based operator with a `ResearchAgent` CRD,
  k3s overlay, and OpenTofu module.
- Day-2: OpenCost labels, Kubetail-friendly logs, Chaos Mesh experiments.
- GitHub Pages static showcase.

### Security & supply chain
- Non-root, read-only-rootfs container; least-privilege CI; no mutable-tag
  third-party Actions.
- CycloneDX SBOMs, `pip-audit`, Dependabot.
- cosign keyless image signing and SBOM attestation on release.
- Fixed CodeQL findings: exception-info exposure, client-side request forgery,
  unpinned Actions.

[1.0.0]: https://github.com/AGenNext/Agent-Converter/releases/tag/v1.0.0
