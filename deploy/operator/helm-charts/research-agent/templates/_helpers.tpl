{{- define "research-agent.name" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "research-agent.labels" -}}
app.kubernetes.io/name: {{ include "research-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: agent
app.kubernetes.io/part-of: research-platform
app.kubernetes.io/managed-by: research-agent-operator
{{- end -}}

{{- define "research-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "research-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
