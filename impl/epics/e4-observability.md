# E4 — Observability

## Objective

Prove the inference observability stack in a real environment:

- kube-prometheus-stack scrapes engine, gateway, admission, scheduler, and DCGM metrics
- Grafana sidecar loads the inference platform dashboard
- PrometheusRule objects encode the E4 starter alerts and route to runbooks
- OpenTelemetry collector accepts gateway and engine traces and exports to the configured backend
- per-tenant and priority-class metrics stay bounded by the gateway/admission label policy

## Required configuration

Populate observability values from:

- `impl/config/env.example.yaml`
- `impl/charts/observability/values.yaml`
- `impl/observability/values-kube-prometheus-stack.yaml`

Minimum E4 values:

| Field / env var | Purpose |
|---|---|
| `OBSERVABILITY_NAMESPACE` | Namespace where Prometheus, Grafana, and OTel run |
| `PROMETHEUS_STACK_RELEASE` | Helm release name for kube-prometheus-stack |
| `INFERENCE_OBSERVABILITY_RELEASE` | Helm release name for dashboard, alert, and OTel assets |
| `REPLACE_WITH_PROMETHEUS_SERVICE_URL` | In-cluster Prometheus URL used by KEDA and platform components |
| `REPLACE_WITH_PROMETHEUS_URL` | External Prometheus API URL used for live proof |
| `REPLACE_WITH_OTEL_SERVICE_NAMESPACE` | OTel resource namespace for inference spans |
| `REPLACE_WITH_OTLP_ENDPOINT` | Trace backend OTLP endpoint |
| `REPLACE_WITH_OTEL_COLLECTOR_IMAGE_REPOSITORY` / `tag` | Pinned OTel collector image |
| alert thresholds and severities | TTFT, queue, KV pressure, and XID routing policy |

See `impl/config/README.md` for placeholder purpose, source, expected format, and examples.

## Preflight

```bash
cd impl
python3 ci/validate_values.py environments/<env>.local.yaml

export OBSERVABILITY_NAMESPACE=<observability-namespace>
export PROMETHEUS_STACK_RELEASE=<prometheus-stack-release>
export INFERENCE_OBSERVABILITY_RELEASE=<observability-release>
```

Confirm the metric producers are expected to exist after E1/E2/E3 deploys:

```bash
kubectl get servicemonitor,podmonitor -n <observability-namespace>
kubectl get pods -A -l app.kubernetes.io/name=dcgm-exporter
```

## Deploy

```bash
cd impl
make deploy-observability \
  PROM_STACK_VALUES=observability/values-kube-prometheus-stack.yaml \
  OBSERVABILITY_VALUES=charts/observability/values.yaml \
  OBSERVABILITY_EXTRA_VALUES=environments/<env>.observability.yaml
```

The first release installs kube-prometheus-stack. The second release installs the
inference dashboard ConfigMap, PrometheusRule objects, and OTel collector
Deployment/Service.

## Live Proof

```bash
kubectl rollout status deployment \
  -l app.kubernetes.io/instance=<observability-release> \
  -n <observability-namespace> \
  --timeout=300s

kubectl get prometheusrule,configmap,svc \
  -n <observability-namespace> \
  -l app.kubernetes.io/instance=<observability-release>

export PROMETHEUS_URL=https://<prometheus-url>
make -C playbook validate-promql
```

Expected evidence:

- `validate-promql` returns data for the dashboard panel queries
- Grafana lists the `LLM Inference Platform` dashboard from the sidecar ConfigMap
- Prometheus shows `InferenceTTFTP95High`, `InferenceQueueBound`, `InferenceKVPressure`, and `GPUXIDError` rules
- a sample request produces gateway to engine trace spans in the configured OTLP backend
- `gateway_requests_total{tenant,priority_class,outcome}` is present with bounded tenant labels

## E4 Done Definition

E4 is complete only when:

- observability Helm values contain no unresolved environment placeholders
- kube-prometheus-stack and `charts/observability` deploy to the observability namespace
- dashboard ConfigMap is loaded by Grafana
- alert rules are present in Prometheus with environment-owned thresholds and severities
- OTel collector is running and exporting traces to the configured backend
- `make -C playbook validate-promql` passes with `PROMETHEUS_URL`
- live proof links or screenshots are attached to the release evidence
