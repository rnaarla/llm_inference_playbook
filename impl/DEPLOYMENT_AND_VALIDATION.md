# Deployment and Validation Boundary

This implementation scaffold is environment-agnostic. Filling placeholders is
required, but it is only the first step. A profile becomes **proven** only after
the configured platform is deployed to real infrastructure and the validation
targets pass against live services.

## What placeholders solve

Configuration answers: **what should this deploy connect to?**

Examples:

| Area | Populated by config |
|---|---|
| Kubernetes | namespaces, release names, deployment/service names |
| Gateway | GatewayClass, hostnames, policy attachment names |
| Registry | image repositories, model artifact URIs, adapter artifact URIs |
| Secrets | HF token Secret name, cosign public key Secret, registry auth Secret |
| Observability | Prometheus URL, OTLP endpoint, dashboard namespace |
| Capacity | replica counts, GPU count, KEDA queue threshold |
| Tenancy | tenant IDs, priority class policy, admission caps |
| Security | mTLS requirement, audit sink, certificate issuer |

Use:

- `impl/config/env.example.yaml`
- `impl/environments/values.example.yaml`
- Kubernetes Secrets / ExternalSecrets
- cloud secret managers
- private GitOps overlays
- runtime environment variables

## What placeholders do not solve

Configuration does **not** create or prove the external systems.

| Gap | Requires real integration |
|---|---|
| GPU/staging deployment | GPU nodes, NVIDIA driver/operator, scheduling labels, engine image pull, model artifact access |
| Controller-specific policy mapping | Actual Gateway API controller CRDs/filters for ext_authz, body rewrite/adapter, cancellation |
| Registry/secrets | OCI registry, signed artifacts, cosign keys, registry credentials, secret sync |
| Prometheus/OTel endpoints | Deployed Prometheus/Grafana/OTel/Tempo or managed equivalents, scrape discovery, network access |
| Fleet validation | Live `make` targets against GPU/staging services and captured evidence |

## End-to-end flow

### 1. Materialize config

```bash
cp impl/environments/values.example.yaml impl/environments/staging.local.yaml
# Replace every REPLACE_WITH_* via private GitOps, parameter store, or secret manager.
```

Validate the shape:

```bash
make -C impl validate-config ENV_VALUES=impl/environments/staging.local.yaml
```

### 2. Ensure external prerequisites exist

Before deployment, the environment must provide:

| Prerequisite | How to verify |
|---|---|
| GPU nodes | `kubectl get nodes -l <gpu-node-selector-key>=<gpu-node-selector-value>` |
| GPU runtime | run a debug pod and execute `nvidia-smi` |
| Gateway controller | `kubectl get gatewayclass` includes configured class |
| Registry access | pod can pull engine/admission images and model artifact |
| Secrets | `kubectl get secret <hf-token>`, `kubectl get secret <cosign-public-key>` |
| Prometheus | `curl "$PROMETHEUS_URL/api/v1/query?query=up"` |
| OTLP backend | collector can connect to configured `OTLP_ENDPOINT` |

### 3. Deploy

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

make -C impl up ENGINE_VALUES=environments/staging.local.yaml
```

### 4. Map gateway policy

The gateway chart emits a controller-neutral policy config. You must translate it
to the selected controller's policy resources.

Required behavior:

1. Call admission service before engine dispatch.
2. Pass `X-Tenant-ID` and `X-Request-ID`.
3. Rewrite or adapt model alias to the admitted `served_model`.
4. Add priority and tenant metadata headers.
5. Propagate downstream disconnect upstream.
6. Emit gateway/admission metrics and audit events.

See `impl/gateway/POLICY_INTEGRATION.md`.

### 5. Prove the live fleet

Dense baseline:

```bash
export VLLM_BASE_URL=http://<engine-service>:8000
export PROMETHEUS_URL=https://<prometheus-url>
export SMOKE_REQUIRE_SERVER=1

make -C playbook gpu
```

Staging behavior:

```bash
export STAGING_GATEWAY_URL=https://<gateway-hostname>
export STAGING_REQUIRE=1

make -C playbook test-gateway
make -C playbook test-tenant-quota
make -C playbook test-cancel-stream
```

Game-day hooks remain environment-owned and should be wired only when the
corresponding live systems exist:

```bash
export BROWNOUT_HOOK='bash <private-runbook>/brownout.sh'
export KV_PRESSURE_HOOK='bash <private-runbook>/kv-pressure.sh'
export XID_SIM_HOOK='bash <private-runbook>/xid-sim.sh'
export ROLLBACK_HOOK='bash <private-ci>/seeded-regression.sh'
export UNSIGNED_CHECKPOINT_HOOK='bash <private-security>/unsigned-model.sh'
export GUARDRAIL_DOWN_HOOK='bash <private-runbook>/guardrail-down.sh'

make -C playbook game-day
```

### 6. Seal evidence

After live checks pass:

```bash
make -C playbook record-validation
```

Then update:

- `playbook/versions.lock`
- `docs/appendices/D-evidence-ledger.md`
- `playbook/benchmarks/runs/<sha>/`

## Completion levels

| Level | Meaning |
|---|---|
| Scaffolded | Code/config/docs exist, may still contain placeholders |
| Ready to prove | Config contract and live proof steps documented |
| Deployed | Resources are installed in a target environment |
| Proven | Live `make` targets passed and evidence is recorded |

## Current status

The implementation is **ready to prove** at the scaffold level. It is not
fleet-proven until the configured GPU/staging environment exists and the live
validation commands above pass.
