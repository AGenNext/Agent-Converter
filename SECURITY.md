# Security policy

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories
("Report a vulnerability" on the Security tab) rather than opening a public
issue. We aim to acknowledge within a few business days.

## Supply-chain posture

- **Dependency audits** run in CI (`pip-audit`) and via Dependabot (pip, npm,
  github-actions) — see `.github/dependabot.yml`.
- **SBOMs** (CycloneDX) are generated for the Python app and the UI library and
  uploaded as build artifacts (`.github/workflows/sbom.yml`). A snapshot lives
  in `sbom/`.
- **Signed releases**: container images are built with Cloud Native Buildpacks,
  pinned to an immutable digest, and signed with cosign keyless (Sigstore +
  GitHub OIDC). The SBOM is attached as a signed attestation
  (`.github/workflows/release.yml`). Verify with the commands in
  [docs/supply-chain.md](docs/supply-chain.md).
- **Hardened CI**: workflows use least-privilege `permissions`,
  `persist-credentials: false`, no mutable-tag third-party Actions (tooling is
  installed at pinned versions with checksum verification), and the GHCR token
  is the short-lived `GITHUB_TOKEN`.

## Runtime hardening

- The container runs as non-root with a read-only root filesystem, all
  capabilities dropped, and `allowPrivilegeEscalation: false`.
- Secrets are provided via environment / Kubernetes Secrets, never baked into
  the image.
- The service never leaks exception detail to clients; errors are logged
  server-side and returned generically.

## Agent-specific safety

Per the agent's anti-patterns, a missing or compromised data source degrades to
a reported gap, never to a fabricated, confident answer. Tool results are
treated as untrusted and triangulated across sources.
