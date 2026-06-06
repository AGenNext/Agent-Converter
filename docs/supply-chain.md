# Supply chain security

How this project manages dependency risk, generates a Software Bill of
Materials (SBOM), and signs its release artifacts.

## Dependency audit

Python dependencies are audited with [pip-audit](https://github.com/pypa/pip-audit):

```bash
pip-audit
```

At the time of writing, the resolved runtime dependencies are clean. The web
stack is on current versions (fastapi, starlette, urllib3, requests, anyio).
Keep `pip-audit` in CI so regressions surface on every change.

### A note on the Dependabot alert

GitHub Dependabot also scans the manifests. If it flags an advisory that
`pip-audit` does not reproduce against the resolved tree, it is usually a
transitive package in a dev-only toolchain (for example the Storybook / Vite
chain under `ui/`, which has no runtime role). Triage: confirm whether the
package is a runtime or dev dependency, bump it if a fix exists, and record the
decision. Never silently dismiss a runtime advisory.

## SBOM

We publish CycloneDX SBOMs so consumers can inspect exactly what ships.

- Python: generated with [cyclonedx-bom](https://github.com/CycloneDX/cyclonedx-python).
- JavaScript (the `ui/` component library): generated with `npm sbom` /
  cyclonedx-npm.

Generate locally:

```bash
# Python (from the installed environment)
pip install cyclonedx-bom
cyclonedx-py environment -o sbom/python.cdx.json

# JavaScript
cd ui && npm install && npm sbom --sbom-format cyclonedx > ../sbom/ui.cdx.json
```

A snapshot lives in `sbom/`. CI regenerates it on every push
(`.github/workflows/sbom.yml`) and uploads it as a build artifact.

## Signing (cosign / Sigstore)

Release container images are signed with [cosign](https://github.com/sigstore/cosign)
using keyless signing (Sigstore + GitHub OIDC), and the SBOM is attached as a
signed attestation. See `.github/workflows/release.yml`.

Verify a pulled image:

```bash
cosign verify \
  --certificate-identity-regexp 'https://github.com/AGenNext/Agent-Converter/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/agennext/agent-converter:<tag>

# Verify the SBOM attestation
cosign verify-attestation --type cyclonedx \
  --certificate-identity-regexp 'https://github.com/AGenNext/Agent-Converter/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/agennext/agent-converter:<tag>
```

Keyless signing means no long-lived keys to manage: the signature is tied to
the workflow identity and recorded in the public Rekor transparency log.

## Build provenance

- The image is built with Cloud Native Buildpacks (no hand-written Dockerfile
  for the app), which produces a reproducible, SBOM-friendly image.
- Dependencies are declared with minimum versions in `requirements.txt` /
  `pyproject.toml`. For fully reproducible builds, add a lockfile (pip-tools or
  uv) and have CI install from it.

## CI hardening

- **Least privilege**: every workflow declares minimal `permissions`; the Pages
  build job is `contents: read`, and only the deploy job gets `pages: write` /
  `id-token: write`.
- **No mutable-tag third-party Actions**: release tooling (pack, cosign) is
  installed inline at pinned versions, with cosign verified against its
  published checksums and pack verifiable via `PACK_SHA256`. Only GitHub-owned
  `actions/*` are used via `uses:`.
- **`persist-credentials: false`** on checkout so the `GITHUB_TOKEN` is not
  left on disk for later steps.
- **Immutable image refs**: the release signs the image by digest, not tag.
- **Dependabot** (`.github/dependabot.yml`) keeps pip, npm and github-actions
  dependencies patched.

See also [SECURITY.md](../SECURITY.md).

## Practices

- Keep `pip-audit` and SBOM generation in CI.
- Review Dependabot PRs promptly; prefer the smallest bump that clears the
  advisory.
- Never add a dependency that fabricates data into the agent's tool results
  (see the anti-patterns in the spec); a compromised data source must degrade
  to a gap, not a confident wrong answer.
