{{- define "inference-gateway.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "inference-gateway.admissionName" -}}
{{- .Values.admission.serviceName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "inference-gateway.guardrailName" -}}
{{- .Values.guardrails.serviceName | trunc 63 | trimSuffix "-" -}}
{{- end -}}
