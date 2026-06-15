# Design Choices

This document records the implementation choices that turn the reference
playbook into a deployable platform under `impl/`. It is intentionally separate
from the implementation plan: the plan says **what to build**; this file says
**what we chose and why**.

## Decision Summary

| Area | Choice | Why | Alternatives / Notes |
|---|---|---|---|
| Implementation boundary | Keep `docs/` as reference, `playbook/` as validation harness, and add `impl/` for running services | Preserves the playbook as a stable contract while allowing implementation code to evolve independently | Could merge everything under `playbook/`, but that blurs reference vs runtime |
| Environment configuration | Keep invariant architecture in source; resolve environment-specific values through `impl/config/env.example.yaml`, Helm values, secrets, or runtime env vars | Keeps scaffold portable across dev/staging/prod/clouds and avoids committing infrastructure details | Concrete environment overlays should live outside this public scaffold |
| First target profile | `h100-vllm-kserve` dense 70B-class profile | Smallest credible production baseline before MoE/frontier work | `moe-multinode-interim` remains a frontier track |
| Runtime engine | vLLM OpenAI-compatible server | Broad model support, strong serving ecosystem, existing profile and benchmark scripts | SGLang for structured/agentic traffic; TensorRT-LLM for NVIDIA-locked peak throughput |
| Deployment unit | Helm charts under `impl/charts/` | Native to Kubernetes, compatible with existing `playbook/helm` templates and GitOps flows | Kustomize-only would be simpler but weaker for composition |
| Cluster prerequisites | Helm chart for KEDA, DCGM exporter, cert-manager; GPU Operator documented as external/platform baseline | Avoids nesting heavyweight operator lifecycle in the app chart | GPU Operator can be added as a dependency if the target platform wants app-owned infra |
| Model cache | Signed OCI model artifact pulled by init container into `emptyDir` cache | Removes public runtime downloads, supports signing/provenance, avoids assuming RWX PVC | HostPath prewarm or RWO PVC are valid cluster-specific alternatives |
| Gateway baseline | kgateway + Gateway API Inference Extension | Kubernetes-native routing, supports endpoint-picking concepts, integrates cleanly with NetworkPolicy and EPP | Envoy AI Gateway remains a compatible alternative |
| Admission control | Separate internal admission service | Keeps token budgets, tenant policy, priority class assignment, and 429 behavior explicit and testable | Could be Envoy WASM/ext_authz only; service is easier to evolve first |
| Scheduler implementation | Library primitives for WFQ, reserves, brownout, routing | Lets the scheduling policy be embedded later in gateway/EPP without committing too early to one runtime | Dedicated scheduler service may be needed at larger scale |
| Brownout model | Feature-flagged ladder keyed to `kv_cache_usage_perc` with hysteresis | Matches §6.5 and avoids overload flapping | More signals can be added: queue velocity, admission rejection rate, tenant debt |
| Observability stack | kube-prometheus-stack + DCGM + Grafana + OpenTelemetry collector | Standard Kubernetes observability stack; satisfies live PromQL and trace requirements | Managed Prometheus/Grafana can replace chart deployment |
| Governance | Private OCI + cosign signing + load-time verification | Makes model provenance enforceable before `vllm serve` starts | Full SLSA attestation pipeline is staged in E5 |
| Eval gate | Declarative promotion pipeline scaffold | Separates quality promotion policy from serving runtime | Actual eval runners remain environment-specific |
| Guardrails | Dedicated guardrail service called from gateway | Keeps safety policy on the serving path and makes fail-open/fail-closed route behavior testable | Inline gateway filters may be lower latency later |
| LoRA serving | Shared base-model pool with adapter locality and batch-by-adapter support | Avoids one deployment per tenant adapter; aligns with §6.3 | Dedicated tenant pools remain valid for isolation-critical adapters |
| XID handling | Tiered watcher: recoverable restart, fatal cordon+drain | Avoids over-cordoning on recoverable XIDs while still handling fatal faults | Needs platform RBAC and DCGM integration to become production-ready |
| Fabric validation | NCCL macro + micro payload jobs | Separates prefill/weight movement from decode micro-all-reduce behavior | RCCL equivalent required for AMD profiles |
| Frontier track | Separate MoE/multi-node overlays and companion document | Keeps dense 70B implementation honest without pretending it covers 405B+ MoE | Frontier PASS requires `moe-multinode-interim` validation |

## Repository Boundary

The implementation uses three layers:

```text
docs/       reference and decision model
playbook/   validation harness, schemas, profiles, runbooks
impl/       deployable platform scaffolding and runtime components
```

This choice avoids turning the reference playbook into an environment-specific
deployment repo while still giving the implementation a concrete home.

## Environment-Agnostic Configuration

The implementation keeps **architectural invariants** in source and pushes
deployment-specific values to configuration. This includes hostnames, registry
endpoints, cloud account IDs, namespaces, secret names, scaling values, GPU node
selectors, compliance settings, and integration endpoints.

Configuration entry points:

- `impl/config/env.example.yaml` — complete environment contract
- `impl/environments/values.example.yaml` — Helm values shape
- runtime environment variables for operational hooks and controllers
- Kubernetes Secret / ExternalSecret objects for sensitive material

Files containing real environment values should not be committed. Use private
GitOps overlays, parameter stores, or secret managers to materialize them at
deployment time.

## Profile and Runtime

The first implementation target is `h100-vllm-kserve` because it is the smallest
profile that can prove the production contracts:

- dense 70B-class serving
- 2x H100 tensor-parallel replica shape
- OpenAI-compatible request path
- GPU smoke, real benchmark report, live PromQL, and staging game-day hooks

The MoE/frontier profile is kept separate as `moe-multinode-interim`. That is a
deliberate boundary: dense-profile validation should not be blocked by
multi-node EP topology work, and MoE should not inherit dense assumptions.

## Kubernetes Deployment

Helm is the implementation mechanism for runtime deployment:

- `impl/charts/inference-engine/` parameterizes the previous static manifests.
- `impl/charts/gateway/` wires Gateway API resources and the admission service.
- `impl/charts/cluster-prereqs/` installs shared prerequisites that are safe to
  own at the app/platform layer.

The original `playbook/helm/` files remain as validated shapes and compatibility
fallbacks. `playbook/ci/deploy-kind.sh` prefers the implementation chart when it
exists.

## Model Artifact Strategy

The implementation chooses signed OCI artifacts over public runtime downloads or
shared RWX PVCs.

Rationale:

- runtime pods should not fetch from public model hubs
- signed tags and digests allow fail-closed provenance
- init-container pull keeps the engine image focused on serving
- `emptyDir` avoids assuming a cluster has RWX storage

Cluster-specific alternatives can still be used: hostPath prewarming, per-replica
RWO PVCs, or RWX storage where supported.

## Gateway and Admission

Gateway API is the baseline routing surface because this platform is
Kubernetes-native and needs endpoint-picking behavior. The admission service is
separate because token accounting, tenant budgets, and fleet-state rejection are
business logic that should be independently tested.

The selected production path is:

```text
Gateway API / kgateway
  -> admission policy hook
  -> EPP / routing decision
  -> vLLM engine service
```

The Python gateway in `playbook/ci/gateway.py` remains a learning artifact only.
It is not part of the production implementation.

## Scheduler Policy

The scheduler is implemented first as reusable library primitives:

- weighted fair queueing over token cost
- reserve accounting by priority class
- brownout ladder state machine
- heavy-context routing classifier

This keeps the core policy testable before choosing whether it lives inside an
admission service, EPP plugin, gateway extension, or a dedicated scheduler
service.

## Observability

The baseline observability stack is Prometheus/Grafana/DCGM with OpenTelemetry
for traces. This is the shortest path to the playbook's validation contract:

- live PromQL must return data
- per-tenant labels must be available at ingress
- traces must attribute gateway, queue, and engine time
- GPU XID and KV pressure alerts must link to runbooks

Managed observability services can replace the Helm chart as long as the same
queries and labels remain valid.

## Governance and Release

The implementation separates three concerns:

1. **Artifact provenance:** OCI, cosign signatures, SBOM/SLSA metadata.
2. **Load-time verification:** init container verifies signature/digest before
   serving.
3. **Promotion quality:** eval-gate pipeline plus staged canary rollback.

This makes model promotion auditable and prevents an unsigned or swapped model
from becoming a runtime surprise.

## Safety and Guardrails

Guardrails are modeled as a dedicated service called by the gateway. The API
shape is intentionally stable:

- input moderation before engine dispatch
- streaming output moderation during response
- per-route fail-open/fail-closed behavior
- audit on policy decisions

The service skeleton uses fixture behavior today; production requires a real
safety model and latency budget.

## Frontier / T2 Scope

The dense profile and the frontier MoE profile are intentionally decoupled.
Frontier validation requires:

- real NCCL/RCCL fabric baselines
- multi-node TP/PP orchestration
- EP policy and expert imbalance monitoring
- disaggregated prefill/decode validation with fallback route
- tiered XID handling on real GPU nodes

These live under `impl/fabric/` and must be proven against the MoE companion
before the repo can claim 405B+ frontier serving.

## Open Decisions

| Decision | Default for now | When to revisit |
|---|---|---|
| Gateway implementation | kgateway + Gateway API | If Envoy AI Gateway provides stronger token-aware admission or simpler ops |
| Scheduler placement | Library primitives embedded later | Once gateway/EPP extension capabilities are confirmed |
| Model cache storage | OCI pull to `emptyDir` | If cold-start time requires hostPath prewarm or node-local cache DaemonSet |
| Guardrail implementation | Dedicated service | If streaming latency requires inline gateway filter |
| Observability deployment | kube-prometheus-stack | If managed Prometheus/Grafana is mandated |
| GPU Operator ownership | Platform prerequisite | If this repo must provision full cluster lifecycle |
