variable "kubeconfig_path" {
  description = "Path to the kubeconfig for the target cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context to use (empty = current context)."
  type        = string
  default     = ""
}

variable "namespace" {
  description = "Namespace to deploy into."
  type        = string
  default     = "research-agent"
}

variable "image_repository" {
  description = "Container image repository (must be pullable by the cluster)."
  type        = string
  default     = "research-deep-agent"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "replica_count" {
  type    = number
  default = 2
}

variable "model" {
  description = "Model id passed as RESEARCH_AGENT_MODEL."
  type        = string
  default     = "anthropic:claude-sonnet-4-5"
}

variable "service_port" {
  type    = number
  default = 80
}

variable "api_keys" {
  description = <<-EOT
    API keys written into the research-agent-secrets Secret. Provide at least
    ANTHROPIC_API_KEY; add the data-tool keys you have. Missing keys degrade to
    gaps, never fabrication.
  EOT
  type        = map(string)
  sensitive   = true
  # Example (set real values in terraform.tfvars):
  # {
  #   ANTHROPIC_API_KEY = "sk-ant-..."
  #   TAVILY_API_KEY    = "tvly-..."
  # }
}

variable "enable_ingress" {
  description = "Create a Traefik ingress (k3s default) at the node IP."
  type        = bool
  default     = true
}

variable "ingress_host" {
  description = "Optional host for the ingress (empty = match any / node IP)."
  type        = string
  default     = ""
}
