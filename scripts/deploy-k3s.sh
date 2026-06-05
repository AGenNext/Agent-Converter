#!/usr/bin/env bash
# Deploy the Research deep agent to a k3s cluster.
#
# Prereqs:
#   - kubectl configured for the target cluster (export KUBECONFIG=...), or run
#     this on the k3s node where /etc/rancher/k3s/k3s.yaml exists.
#   - The image must be available to the cluster. Either push it to a registry
#     the node can pull, or import it into k3s containerd:
#       pack build research-deep-agent:latest
#       docker save research-deep-agent:latest | sudo k3s ctr images import -
#   - deploy/k8s/secret.yaml created from secret.example.yaml with your keys.
#
# Usage:
#   ./scripts/deploy-k3s.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f deploy/k8s/secret.yaml ]; then
  echo "Missing deploy/k8s/secret.yaml. Copy secret.example.yaml and fill it in." >&2
  exit 1
fi

echo "Applying k3s overlay..."
kubectl apply -k deploy/k3s

echo "Waiting for rollout..."
kubectl rollout status deploy/research-deep-agent --timeout=180s

NODE_IP="$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')"
echo "Done. The agent should be reachable via the Traefik ingress at:"
echo "  http://${NODE_IP}/"
