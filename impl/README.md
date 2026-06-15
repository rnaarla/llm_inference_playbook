# Implementation

This tree is the deployable implementation that satisfies the contracts defined by
`docs/` and validated by `playbook/`.

Filling configuration placeholders makes the scaffold deployable; it does not
prove that the platform works. See
[`DEPLOYMENT_AND_VALIDATION.md`](DEPLOYMENT_AND_VALIDATION.md) for the boundary
between config, live infrastructure integration, and fleet evidence.

## Profiles

The first supported profile is `h100-vllm-kserve`:

- Engine: vLLM OpenAI server
- GPU shape: 2x H100 80GB per replica
- Model cache: signed OCI artifact pulled by an init container
- Gateway: kgateway / Gateway API Inference Extension (implemented under `gateway/`)
- Observability: Prometheus, DCGM exporter, Grafana, OpenTelemetry

## Epic Runbooks

| Epic | Runbook |
|---|---|
| E1 — Cluster, engine, and deployable baseline | [`epics/e1-cluster-engine-baseline.md`](epics/e1-cluster-engine-baseline.md) |
| E2 — Production gateway and admission control | [`epics/e2-gateway-admission.md`](epics/e2-gateway-admission.md) |
| E3 — Scheduler: fairness, brownout, and isolation | [`epics/e3-scheduler-fairness-brownout.md`](epics/e3-scheduler-fairness-brownout.md) |
| E4 — Observability | [`epics/e4-observability.md`](epics/e4-observability.md) |
| E5 — Governance, safety, and LoRA | [`epics/e5-governance-safety-lora.md`](epics/e5-governance-safety-lora.md) |
| E6 — Frontier scale: fabric, MoE, disaggregation, XID | [`epics/e6-frontier-fabric.md`](epics/e6-frontier-fabric.md) |

## Bootstrap Order

0. Materialize environment values from your parameter store or private overlay:
   ```bash
   cp config/env.example.yaml config/<env>.local.yaml
   cp environments/values.example.yaml environments/<env>.local.yaml
   # Replace every REPLACE_WITH_* placeholder outside this public scaffold.
   ```
1. Export required runtime values:
   ```bash
   export INFERENCE_NAMESPACE=<namespace>
   export OBSERVABILITY_NAMESPACE=<monitoring-namespace>
   export INFERENCE_ENGINE_RELEASE=<engine-release>
   export INFERENCE_ENGINE_DEPLOYMENT=<engine-deployment-name>
   export INFERENCE_ENGINE_SERVICE=<engine-service-name>
   export INFERENCE_GATEWAY_RELEASE=<gateway-release>
   export CLUSTER_PREREQS_RELEASE=<prereqs-release>
   export PROMETHEUS_STACK_RELEASE=<prometheus-stack-release>
   export INFERENCE_OBSERVABILITY_RELEASE=<observability-release>
   export ADMISSION_DEPLOYMENT_NAME=<admission-deployment-name>
   export XID_WATCHER_DAEMONSET=<xid-watcher-daemonset-name>
   ```
2. Install cluster prerequisites:
   ```bash
   make prereqs
   ```
3. Push or mirror the model artifact:
   ```bash
   make model-cache MODEL_SOURCE=/models/llama-3.1-70b-fp8
   ```
4. Deploy the engine:
   ```bash
   make deploy-engine
   ```
5. Deploy gateway and observability assets:
   ```bash
   make deploy-gateway
   make deploy-observability OBSERVABILITY_EXTRA_VALUES=environments/<env>.observability.yaml
   ```
6. Run the playbook validation contract:
   ```bash
   make validate-engine
   ```

The targets render and apply Helm charts. They assume an existing Kubernetes
cluster with GPU nodes; cloud-specific cluster provisioning can be added under
`terraform/`.

All deployment-specific values must be provided by config, secret managers, or
runtime environment variables. See [`config/README.md`](config/README.md) for
the complete placeholder reference, expected value formats, configuration
sources, and sample dev/staging/prod configurations.
