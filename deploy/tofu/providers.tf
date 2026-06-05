# Point at your k3s (or any) cluster via its kubeconfig. On a k3s node this is
# usually /etc/rancher/k3s/k3s.yaml.
provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context != "" ? var.kube_context : null
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context != "" ? var.kube_context : null
  }
}
