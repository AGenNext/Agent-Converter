#!/usr/bin/env bash
# Sign a built image and attach its SBOM with cosign (keyless, Sigstore).
#
# Prereqs: cosign (https://docs.sigstore.dev/cosign/installation), an image
# pushed by digest, and a CycloneDX SBOM. For keyless signing you authenticate
# interactively (or via an OIDC provider in CI).
#
# Usage:
#   ./scripts/sign-image.sh ghcr.io/agennext/agent-converter:1.0.0
set -euo pipefail

IMAGE="${1:?usage: sign-image.sh <image[:tag]>}"

# Pin to a digest so the signature covers exact bytes, not a mutable tag.
if command -v crane >/dev/null 2>&1; then
  REF="$(crane digest "$IMAGE" --full-ref)"
else
  echo "crane not found; signing the tag (install crane to pin a digest)." >&2
  REF="$IMAGE"
fi

echo "Generating SBOM..."
cyclonedx-py environment -o sbom.cdx.json

echo "Signing $REF ..."
cosign sign --yes "$REF"

echo "Attesting SBOM for $REF ..."
cosign attest --yes --type cyclonedx --predicate sbom.cdx.json "$REF"

echo "Done. Verify with:"
echo "  cosign verify --certificate-oidc-issuer https://token.actions.githubusercontent.com \\"
echo "    --certificate-identity-regexp 'https://github.com/AGenNext/Agent-Converter/.*' $REF"
