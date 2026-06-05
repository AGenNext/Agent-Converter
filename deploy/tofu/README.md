# OpenTofu deployment

Provision the Research deep agent on a Kubernetes cluster (k3s or any other)
with [OpenTofu](https://opentofu.org). It creates a namespace, a Secret with
your API keys, deploys the in-repo Helm chart, and (on k3s) a Traefik ingress.

## Prerequisites

- OpenTofu >= 1.6 (`tofu`).
- A kubeconfig for the target cluster. On a k3s node that is
  `/etc/rancher/k3s/k3s.yaml`.
- The image available to the cluster. Build it with Cloud Native Buildpacks
  (`make image`) and push to a registry the node can pull, or import it into
  k3s containerd:
  ```bash
  docker save research-deep-agent:latest | sudo k3s ctr images import -
  ```

## Use

```bash
cd deploy/tofu
cp terraform.tfvars.example terraform.tfvars   # fill in keys + kubeconfig path
tofu init
tofu plan
tofu apply
```

Outputs include the namespace, the Helm release name, and the in-cluster
service address. With ingress enabled, the agent is reachable at the node IP
(`http://<node-ip>/`).

## Notes

- This uses the same Helm chart as the operator
  (`../operator/helm-charts/research-agent`), so OpenTofu and the operator stay
  consistent.
- `api_keys` is a sensitive variable; keep `terraform.tfvars` out of version
  control (it is gitignored) or supply values via `TF_VAR_*` / a secrets
  backend.
- For multi-tenancy, add `TENANTS_CONFIG` (mounted from a Secret) and per-tenant
  keys; see `../../docs/multi-tenancy.md`.
- This is infrastructure-as-code only. Running `tofu apply` is the action that
  touches your cluster; nothing is deployed until you do.
