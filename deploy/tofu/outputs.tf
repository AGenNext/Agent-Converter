output "namespace" {
  value = kubernetes_namespace.this.metadata[0].name
}

output "release_name" {
  value = helm_release.research_agent.name
}

output "service" {
  description = "In-cluster service address."
  value       = "${helm_release.research_agent.name}.${kubernetes_namespace.this.metadata[0].name}.svc:${var.service_port}"
}

output "ingress_enabled" {
  value = var.enable_ingress
}
