# E5 — Governance, Safety, and LoRA

## Objective

Prove the governed release path and safety serving scaffold in staging:

- model and adapter artifacts are signed, attested, and promoted by digest
- engine pods verify signatures and approved digests before serving
- eval-gate promotion metadata feeds runtime values
- guardrail policy is route-specific and fail-closed by default
- LoRA adapter registry is config-driven and router assumptions are explicit

## Required Configuration

Populate environment-specific values from:

- `impl/config/env.example.yaml`
- `impl/environments/values.example.yaml`
- `impl/governance/registry/promotion.example.yaml`
- `impl/guardrails/policy.example.yaml`
- `impl/engine/lora-adapter-registry.example.yaml`

Minimum E5 values:

| Field / env var | Purpose |
|---|---|
| `MODEL_ARTIFACT` / `model.artifact` | Digest-pinned OCI model artifact |
| `REPLACE_WITH_APPROVED_MODEL_DIGEST` | Digest approved by eval/promotion |
| `REPLACE_WITH_COSIGN_PUBLIC_KEY_SECRET` | Public key Secret mounted into verify init |
| `COSIGN_KEY` / `REPLACE_WITH_COSIGN_KEY_URI` | Signing key for release CI |
| `REPLACE_WITH_DOMAIN_EVAL_DATASET_URI` | Domain eval gate dataset |
| `REPLACE_WITH_PRODUCTION_REPLAY_DATASET_URI` | Replay eval gate dataset |
| `REPLACE_WITH_GUARDRAIL_IMAGE_REPOSITORY` / `tag` | Guardrail service image |
| `REPLACE_WITH_GUARDRAIL_SERVICE_NAME` | Guardrail service for gateway policy |
| `REPLACE_WITH_GUARDRAIL_CONFIG_NAME` | Guardrail route policy ConfigMap |
| `REPLACE_WITH_LORA_ADAPTER_REGISTRY_CONFIG` | Adapter registry ConfigMap |
| `REPLACE_WITH_APPROVED_ADAPTER_DIGEST` | Approved LoRA adapter digest |
| `REPLACE_WITH_ADAPTER_LOCALITY_LABEL` | Router locality label for loaded adapters |

See `impl/config/README.md` for placeholder purpose, source, expected format,
and examples.

## Preflight

Render environment-specific metadata and values from private config:

```bash
cd impl
python3 ci/validate_values.py environments/<env>.local.yaml
```

Prepare registry release artifacts:

```bash
ARTIFACT=<registry-host>/models/<model>@sha256:<digest> \
COSIGN_KEY=<kms-or-key-path> \
SBOM=sbom.spdx.json \
PROVENANCE=provenance.intoto.jsonl \
MODEL_CARD=model_card.md \
PROMOTION_METADATA=promotion.yaml \
bash governance/registry/sign_and_attest.sh
```

Create or update the required ConfigMaps/Secrets from your private overlay:

```bash
kubectl apply -n <namespace> -f <cosign-public-key-secret>.yaml
kubectl apply -n <namespace> -f <guardrail-policy-configmap>.yaml
kubectl apply -n <namespace> -f <lora-adapter-registry-configmap>.yaml
```

## Deploy and Integrate

Deploy the engine with verification enabled and, when needed, the LoRA overlay:

```bash
export INFERENCE_NAMESPACE=<namespace>
export INFERENCE_ENGINE_RELEASE=<engine-release>
export INFERENCE_ENGINE_DEPLOYMENT=<deployment-name>

cd impl
make deploy-engine ENGINE_VALUES=engine/values-lora-pool.yaml
```

Integrate guardrails through the gateway controller's policy mechanism:

- call guardrails after auth/admission and before engine dispatch for inputs
- call guardrails on bounded streaming output chunks
- apply `fail_closed` for safety-required routes
- apply `fail_open` only for explicitly configured lower-risk routes
- emit audit records for `block`, `fail_closed`, and `fail_open`

Integrate LoRA routing through Gateway API Inference Extension or the chosen
EPP implementation:

- resolve adapter id from tenant/model policy
- prefer replicas advertising `REPLACE_WITH_ADAPTER_LOCALITY_LABEL`
- batch only compatible adapter ids
- reject adapters whose rank exceeds the pool rank

## Validate

E5 intentionally does not add new local test harnesses. Use the existing
playbook/staging hooks when the environment is available:

```bash
export UNSIGNED_CHECKPOINT_HOOK=<staging unsigned-artifact script>
export GUARDRAIL_DOWN_HOOK=<staging guardrail-outage script>
export ROLLBACK_HOOK=<staging rollback/eval-gate script>

make -C playbook test-unsigned-checkpoint
make -C playbook test-guardrail-down
make -C playbook test-rollback
```

Expected results:

- unsigned or mutable model refs fail before engine readiness
- approved digest mismatch fails closed
- guardrail-required routes fail closed during guardrail outage
- lower-risk routes fail open only when configured and audited
- eval regression blocks promotion and leaves rollback metadata intact
- LoRA requests route to replicas with the requested adapter loaded

## E5 Done Definition

E5 is complete only when:

- registry signing attaches signature, SBOM, provenance, model-card, and
  promotion predicates
- promoted model and adapter refs are digest-pinned in private overlays
- engine chart deploys with verification enabled and readiness stays false on
  bad signatures or digest mismatch
- gateway policy calls guardrails with the documented `/moderate` contract
- guardrail route policy is fail-closed by default
- LoRA adapter registry is mounted and EPP/gateway routing honors adapter
  locality and rank assumptions
- existing staging hooks pass with `STAGING_REQUIRE=1` where applicable
