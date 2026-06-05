resource "kubernetes_namespace" "this" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "research-platform"
    }
  }
}

# API keys for the agent. Tools resolve these (or degrade to gaps).
resource "kubernetes_secret" "keys" {
  metadata {
    name      = "research-agent-secrets"
    namespace = kubernetes_namespace.this.metadata[0].name
  }
  type = "Opaque"
  data = var.api_keys
}

# Deploy the agent using the in-repo Helm chart (the same one the operator
# reconciles), so OpenTofu and the operator stay consistent.
resource "helm_release" "research_agent" {
  name      = "research-agent"
  namespace = kubernetes_namespace.this.metadata[0].name
  chart     = "${path.module}/../operator/helm-charts/research-agent"

  set {
    name  = "replicaCount"
    value = tostring(var.replica_count)
  }
  set {
    name  = "image.repository"
    value = var.image_repository
  }
  set {
    name  = "image.tag"
    value = var.image_tag
  }
  set {
    name  = "model"
    value = var.model
  }
  set {
    name  = "secretName"
    value = kubernetes_secret.keys.metadata[0].name
  }
  set {
    name  = "service.port"
    value = tostring(var.service_port)
  }

  depends_on = [kubernetes_secret.keys]
}

# k3s ships Traefik; expose the service at the node IP.
resource "kubernetes_ingress_v1" "this" {
  count = var.enable_ingress ? 1 : 0

  metadata {
    name      = "research-deep-agent"
    namespace = kubernetes_namespace.this.metadata[0].name
    annotations = {
      "traefik.ingress.kubernetes.io/router.entrypoints" = "web"
    }
  }

  spec {
    rule {
      host = var.ingress_host != "" ? var.ingress_host : null
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = helm_release.research_agent.name
              port {
                number = var.service_port
              }
            }
          }
        }
      }
    }
  }

  depends_on = [helm_release.research_agent]
}
