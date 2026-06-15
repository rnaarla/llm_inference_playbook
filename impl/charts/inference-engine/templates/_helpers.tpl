{{- define "inference-engine.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "inference-engine.labels" -}}
app: {{ include "inference-engine.name" . }}
platform/profile: {{ .Values.profile | quote }}
{{- end -}}
