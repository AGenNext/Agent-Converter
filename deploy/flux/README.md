# Flux GitOps

Deploy and continuously reconcile the Research deep agent with
[Flux](https://fluxcd.io). Flux watches this repository and keeps the cluster in
sync with the manifests here, using the signed image published to GHCR.

## What's here

- `gitrepository.yaml` — a Flux `GitRepository` tracking `main`.
- `helmrelease.yaml` — a `HelmRelease` that installs the in-repo Helm chart
  (`deploy/operator/helm-charts/research-agent`) with the GHCR image.

## Bootstrap

```bash
# Install Flux into the cluster (once):
flux bootstrap github \
  --owner=AGenNext --repository=Agent-Converter \
  --branch=main --path=deploy/flux

# Or, on an existing Flux install, just apply the source + release:
kubectl apply -f deploy/flux/gitrepository.yaml
kubectl apply -f deploy/flux/helmrelease.yaml
```

Flux then reconciles on its interval; bump `image.tag` (or any value) in
`helmrelease.yaml`, push to `main`, and the cluster updates automatically.

## Secrets

Do **not** commit plaintext API keys. Provide `research-agent-secrets` via one
of:

- **SOPS**: encrypt a Secret with `sops` and let Flux's `kustomize-controller`
  decrypt it (the standard Flux secrets workflow).
- **External Secrets Operator**: sync from Vault / a cloud secret manager.
- Or create it out of band: `kubectl -n research-agent create secret generic
  research-agent-secrets --from-literal=ANTHROPIC_API_KEY=...`.

## Why GitOps here

The release pipeline signs the image (cosign) and the chart is the same one the
operator and OpenTofu use, so Git is the single source of truth: a reviewed,
audited commit is the only way the running deployment changes.
