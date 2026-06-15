# E1 — Cluster, Engine, and Deployable Baseline

## Objective

Prove the dense serving baseline on a real GPU cluster:

- GPU node pool and prerequisites are present
- vLLM engine chart renders and deploys
- signed OCI model artifact is pulled by init container
- smoke test passes against a warm engine
- benchmark report contains real non-zero TTFT/TPOT/goodput values
- `versions.lock` is stamped after validation

## Required configuration

Populate an environment-specific values file from:

- `impl/config/env.example.yaml`
- `impl/environments/values.example.yaml`

The E1 values must resolve at least:

| Field | Purpose |
|---|---|
| `INFERENCE_NAMESPACE` | Namespace where engine runs |
| `INFERENCE_ENGINE_RELEASE` | Helm release name |
| `INFERENCE_ENGINE_DEPLOYMENT` | Deployment name for rollout checks |
| `INFERENCE_ENGINE_SERVICE` | Service name for smoke validation |
| `MODEL_ARTIFACT` / `model.artifact` | Signed OCI model artifact |
| `REPLACE_WITH_VLLM_IMAGE_REPOSITORY` / `tag` | Pinned vLLM image |
| GPU node selector | Schedules engine on correct GPU nodes |
| KEDA values | min/max replicas and queue threshold from capacity plan |
| `PROMETHEUS_URL` | Required for live PromQL validation |

See `impl/config/README.md` for placeholder purpose, source, expected value,
and examples.

## Preflight

```bash
cd impl
python3 ci/validate_values.py environments/<env>.local.yaml

export INFERENCE_NAMESPACE=<namespace>
export INFERENCE_ENGINE_RELEASE=<engine-release>
export INFERENCE_ENGINE_DEPLOYMENT=<deployment-name>
export INFERENCE_ENGINE_SERVICE=<service-name>
```

## Deploy

```bash
cd impl
make prereqs
make deploy-engine ENGINE_VALUES=environments/<env>.local.yaml
```

## Validate

```bash
export VLLM_BASE_URL=http://<engine-service>:8000
export SMOKE_REQUIRE_SERVER=1
export PROMETHEUS_URL=https://<prometheus-url>

make -C playbook gpu
```

Expected artifacts:

```text
playbook/benchmarks/runs/<sha>/report.yaml
playbook/benchmarks/runs/<sha>/bench_steady.log
playbook/benchmarks/runs/<sha>/engine_startup.log
```

## Seal

After `make -C playbook gpu` passes with real non-zero metrics:

```bash
make -C playbook record-validation
git add playbook/versions.lock docs/appendices/D-evidence-ledger.md
```

Update `docs/appendices/D-evidence-ledger.md` with the run path and operator.

## E1 Done Definition

E1 is complete only when:

- `impl` config validates with no unresolved placeholders
- engine Helm chart deploys to the GPU cluster
- `smoke-vllm` passes with `SMOKE_REQUIRE_SERVER=1`
- `bench-local` writes a non-dry-run report with non-zero values
- `validate-promql` passes with `PROMETHEUS_URL`
- `versions.lock` has `validated_on` and `validated_by`
