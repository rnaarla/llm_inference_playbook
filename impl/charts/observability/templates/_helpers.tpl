{{- define "inference-observability.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "inference-observability.labels" -}}
app.kubernetes.io/name: {{ include "inference-observability.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
inference.platform/environment: {{ .Values.global.environmentName | quote }}
{{- end -}}

{{- define "inference-observability.otelName" -}}
{{- printf "%s-otel" (include "inference-observability.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
