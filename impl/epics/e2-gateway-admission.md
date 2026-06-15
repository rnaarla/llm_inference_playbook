# E2 — Production Gateway and Admission Control

## Objective

Prove the production gateway path in staging:

- Gateway API controller routes OpenAI-compatible traffic to the engine
- admission service rejects invalid/over-budget requests before engine dispatch
- model aliases are translated to served model names
- tenant and priority metadata is propagated
- streaming disconnects cancel upstream engine work
- audit and request metrics are emitted

## Required configuration

Populate the gateway section in an environment values file from:

- `impl/config/env.example.yaml`
- `impl/environments/values.example.yaml`
- `impl/charts/gateway/values.yaml`

Minimum E2 values:

| Field / env var | Purpose |
|---|---|
| `REPLACE_WITH_GATEWAY_NAME` | Gateway resource name |
| `REPLACE_WITH_GATEWAY_CLASS` | Installed GatewayClass |
| `REPLACE_WITH_INFERENCE_HOSTNAME` | HTTPRoute hostname |
| `REPLACE_WITH_ENGINE_SERVICE_NAME` | backend engine Service |
| `REPLACE_WITH_ADMISSION_IMAGE_REPOSITORY` | admission service image repository |
| `REPLACE_WITH_ADMISSION_IMAGE_TAG` | admission service image tag |
| `REPLACE_WITH_ADMISSION_SERVICE_NAME` | admission Service name |
| `REPLACE_WITH_ADMISSION_CONFIG_NAME` | admission ConfigMap name |
| `REPLACE_WITH_DEFAULT_TENANT_ID` | fallback tenant when `X-Tenant-ID` absent |
| `REPLACE_WITH_MODEL_ALIAS` | client-facing alias |
| `REPLACE_WITH_SERVED_MODEL_NAME` | vLLM served model name |
| `STAGING_GATEWAY_URL` | URL used by playbook validation tests |
| `STAGING_REQUIRE=1` | fail closed when staging gateway is unavailable |

See `impl/config/README.md` for purpose, source, expected format, and examples.

## Preflight

```bash
cd impl
python3 ci/validate_values.py environments/<env>.local.yaml

cd gateway/admission
python3 -m pytest test_app.py -q
```

Build and push the admission image using your environment-specific registry:

```bash
docker build -t <registry-host>/inference-admission:<tag> impl/gateway/admission
docker push <registry-host>/inference-admission:<tag>
```

## Deploy

```bash
export INFERENCE_NAMESPACE=<namespace>
export INFERENCE_GATEWAY_RELEASE=<gateway-release>
export ADMISSION_DEPLOYMENT_NAME=<admission-deployment-name>

cd impl
make deploy-gateway
```

The chart emits a controller-neutral `*-policy` ConfigMap. Map it to your
Gateway controller's policy mechanism as documented in:

- `impl/gateway/POLICY_INTEGRATION.md`

## Validate

```bash
export STAGING_GATEWAY_URL=https://<gateway-hostname>
export STAGING_REQUIRE=1

make -C playbook test-gateway
make -C playbook test-tenant-quota
make -C playbook test-cancel-stream
```

Expected results:

- valid requests return 200 from the engine path
- over-budget requests return 400 or 429 before engine dispatch
- load test returns 200/429, not 5xx
- disconnect test shows engine-side abort in logs/metrics
- admission `/metrics` exposes `gateway_requests_total{tenant,priority_class,outcome}`

## E2 Done Definition

E2 is complete only when:

- gateway chart deploys to staging
- admission image is built and running
- controller-specific policy hook calls `/admit`
- alias translation reaches the engine using `served_model`
- `test-gateway`, `test-tenant-quota`, and `test-cancel-stream` pass with `STAGING_REQUIRE=1`
- audit logs and `gateway_requests_total` are visible in observability
