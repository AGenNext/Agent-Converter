#!/usr/bin/env bash
# Build an OCI image for the Research deep agent with Cloud Native Buildpacks.
# No Dockerfile needed: the Paketo Python buildpack reads requirements.txt,
# project.toml and Procfile.
#
# Prereqs: pack (https://buildpacks.io/docs/install-pack/) and a container
# runtime (Docker or a compatible daemon).
#
# Usage:
#   ./scripts/build-image.sh [IMAGE_NAME]
# Example:
#   ./scripts/build-image.sh ghcr.io/agennext/research-deep-agent:1.0.0
set -euo pipefail

IMAGE="${1:-research-deep-agent:latest}"
BUILDER="${BUILDER:-paketobuildpacks/builder-jammy-base}"

echo "Building ${IMAGE} with builder ${BUILDER}..."
pack build "${IMAGE}" \
  --builder "${BUILDER}" \
  --default-process web

echo
echo "Done. Run it with:"
echo "  docker run --rm -p 8080:8080 \\"
echo "    -e ANTHROPIC_API_KEY -e TAVILY_API_KEY \\"
echo "    ${IMAGE}"
