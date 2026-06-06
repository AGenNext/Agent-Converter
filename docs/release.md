# Release process

The repository is released via GitHub Actions. Cutting a `v*` tag builds the
image with Cloud Native Buildpacks, pushes it to GHCR, generates a CycloneDX
SBOM, and signs both with cosign keyless (`.github/workflows/release.yml`).

## CI/CD overview

| Workflow | Trigger | Does |
| --- | --- | --- |
| `ci.yml` | push to main, PRs | pyflakes + pytest (3.10–3.12) + JS syntax |
| `codeql` | push, PRs | security scanning (default setup) |
| `sbom.yml` | push, PRs | CycloneDX SBOMs + pip-audit |
| `pages.yml` | push to main | publish the static UI showcase to GitHub Pages |
| `release.yml` | `v*` tag | build → GHCR → SBOM → cosign sign + attest |

## Release checklist

1. **Green CI**: `ci.yml`, CodeQL and `sbom.yml` all passing on the PR.
2. **No open security alerts** that are in scope (triage Dependabot; runtime
   `pip-audit` clean).
3. **Version bumped** consistently: `pyproject.toml`, `server.py` (`version`
   and `/api/info`), and `deploy/operator/helm-charts/research-agent/Chart.yaml`.
4. **CHANGELOG.md** updated with the new version and date.
5. **Docs** reflect any new behaviour.
6. **Merge** the PR to `main`.
7. **Tag**: `git tag v1.0.0 && git push origin v1.0.0` (or run `release.yml`
   via workflow_dispatch).
8. **Verify publish**: the image appears at
   `ghcr.io/agennext/agent-converter:v1.0.0` and the signature verifies:
   ```bash
   cosign verify \
     --certificate-oidc-issuer https://token.actions.githubusercontent.com \
     --certificate-identity-regexp 'https://github.com/AGenNext/Agent-Converter/.*' \
     ghcr.io/agennext/agent-converter:v1.0.0
   ```
9. **GitHub Release**: create the release from the tag, paste the CHANGELOG
   section, attach the SBOM artifact.

## Notes

- The release workflow needs GHCR package write (granted via the workflow's
  `packages: write`) and `id-token: write` for keyless signing. No long-lived
  secrets are required.
- Pin/bump the tool versions in `release.yml` (`PACK_VERSION`, `COSIGN_VERSION`)
  as needed; cosign is verified against its published checksums.
