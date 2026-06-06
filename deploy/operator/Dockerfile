# Helm-based operator image. Built on the operator-sdk Helm operator base,
# which runs the Helm reconciler against the chart per watches.yaml.
FROM quay.io/operator-framework/helm-operator:v1.34.1

ENV HOME=/opt/helm
COPY watches.yaml ${HOME}/watches.yaml
COPY helm-charts ${HOME}/helm-charts

WORKDIR ${HOME}
