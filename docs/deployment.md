# Deployment

From a laptop to a Kubernetes cluster with an operator. Pick the level you
need; each builds on the one before.

## 1. Local (no container)

```bash
make install
make run            # API + control panel on http://localhost:8080
```

Or the CLI: `make cli` (interactive) or `make cli Q="Research ..."`.

## 2. Container image (Cloud Native Buildpacks)

No Dockerfile: the [Paketo](https://paketo.io) Python buildpack reads
`requirements.txt`, `project.toml` and `Procfile`.

```bash
make image          # pack build research-deep-agent:latest
```

Run it with docker compose (reads `.env`):

```bash
cp .env.example .env   # fill in keys
docker compose up      # http://localhost:8080
```

The `web` process runs the FastAPI server; the `agent` process runs the CLI
(used by the Kubernetes Job).

## 3. Kubernetes (plain manifests)

```bash
cp deploy/k8s/secret.example.yaml deploy/k8s/secret.yaml   # fill in keys
make k8s-deploy                                            # kubectl apply -k deploy/k8s
```

You get a Deployment (2 replicas, liveness `/healthz`, readiness `/readyz`,
resource requests, hardened securityContext), a Service, and your Secret. A
one-off run is available as `deploy/k8s/job.yaml`.

## 4. Kubernetes (the operator)

A Helm-based operator (built with the
[Operator SDK](https://github.com/operator-framework/operator-sdk)) reconciles
a `ResearchAgent` custom resource into the Deployment, Service and optional
HPA.

```bash
# Build and push the operator image (from deploy/operator):
#   docker build -t <registry>/research-agent-operator:latest .
#   docker push  <registry>/research-agent-operator:latest
make operator-deploy        # installs CRD + RBAC + manager
kubectl apply -f deploy/operator/config/samples/research_v1alpha1_researchagent.yaml
```

Manage instances declaratively:

```yaml
apiVersion: research.agennext.ai/v1alpha1
kind: ResearchAgent
spec:
  replicaCount: 3
  model: "anthropic:claude-sonnet-4-5"
  autoscaling: { enabled: true, minReplicas: 2, maxReplicas: 6 }
```

The chart is publishable to [Artifact Hub](https://artifacthub.io): see
`deploy/operator/helm-charts/artifacthub-repo.yml` and the
`artifacthub.io/*` annotations in `Chart.yaml`.

## 5. Infrastructure as code (OpenTofu)

Provision the whole thing declaratively with
[OpenTofu](https://opentofu.org) instead of `kubectl`. It creates the
namespace, the keys Secret, the Helm release, and a Traefik ingress (k3s).

```bash
cd deploy/tofu
cp terraform.tfvars.example terraform.tfvars   # kubeconfig path + API keys
tofu init && tofu apply
```

It uses the same Helm chart as the operator, so all three paths (kubectl,
operator, OpenTofu) stay consistent. See `deploy/tofu/README.md`. On a k3s
node, point `kubeconfig_path` at `/etc/rancher/k3s/k3s.yaml` and import the
image into containerd first.

## 6. GitOps (Flux)

Reconcile the agent from Git with [Flux](https://fluxcd.io): a `GitRepository`
tracks `main` and a `HelmRelease` installs the chart with the signed GHCR
image. Bump a value, push to `main`, and the cluster updates itself. Provide
secrets via SOPS / External Secrets (never commit keys). See
`deploy/flux/README.md`.

## Day-2 operations

### Cost — OpenCost
Workloads set CPU/memory **requests**, which is what
[OpenCost](https://github.com/opencost/opencost) uses to allocate spend, and
carry `app.kubernetes.io/part-of: research-platform` so cost rolls up per
product. Install OpenCost in the cluster and filter by that label to see the
agent's cost.

### Logs — Kubetail
All processes log to stdout. Stream and search logs across replicas with
[Kubetail](https://github.com/kubetail-org/kubetail), grouping on
`app.kubernetes.io/name=research-deep-agent`.

### Resilience — Chaos Mesh
`deploy/chaos/` holds [Chaos Mesh](https://github.com/chaos-mesh/chaos-mesh)
experiments: `pod-kill` (recovery), `network-delay` (slow upstream APIs),
`cpu-stress` (limits + HPA). Apply with `make chaos`.

### Feature flags — OpenFeature
Toggles go through [OpenFeature](https://openfeature.dev). Out of the box an
environment-backed provider reads `OF_*` variables; point it at flagd in
`research_agent/flags.py` for a central control plane. Current flags:

| Flag | Env var | Effect |
| --- | --- | --- |
| `research.enable_critique` | `OF_RESEARCH_ENABLE_CRITIQUE` | include the critique pack |
| `research.enabled_packs` | `OF_RESEARCH_ENABLED_PACKS` | restrict to listed packs (csv) |

## Interfaces

- **Control panel** — served at `/`, a natural-language chat UI with live
  streaming. See [ui-mockup](ui-mockup.md).
- **Real-time API** — `POST /research/stream` streams progress as
  [CloudEvents](https://github.com/cloudevents/spec) over SSE.
- **A2UI** — `POST /research/a2ui` emits [A2UI](https://a2ui.org) surface
  messages so an A2UI client can render results natively.
- **Component catalog** — the chat UI components live in `ui/` and are
  explorable in [Storybook](https://storybook.js.org) (`make storybook`).
