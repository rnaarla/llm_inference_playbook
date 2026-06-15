# Configuration Contract

The implementation scaffold is environment-agnostic. Values that differ across
development, staging, production, cloud accounts, regions, or compliance
boundaries must come from configuration rather than source code.

Use this document as the source of truth for every `REPLACE_WITH_*` placeholder,
runtime environment variable, Kubernetes Secret reference, and deployment values
file.

For the distinction between filling placeholders and proving a live fleet, see
[`../DEPLOYMENT_AND_VALIDATION.md`](../DEPLOYMENT_AND_VALIDATION.md).

## Files

| File | Purpose | Commit real values? |
|---|---|---|
| `env.example.yaml` | Complete environment contract in neutral YAML form | No |
| `../environments/values.example.yaml` | Helm values shape consumed by charts | No |
| `../environments/*.local.yaml` | Developer or environment-specific overlay | No, ignored |
| `../environments/*.secret.yaml` | Secret-backed overlay generated from secret manager | No, ignored |
| `../charts/*/values.yaml` | Chart defaults containing placeholders only | Yes, placeholders only |
| `../../examples/*.local.yaml` | Fake, safe sample environment values | Yes, examples only |

## Configuration Sources

Use one or more of:

| Source | Use for |
|---|---|
| Helm values generated from a parameter store | non-secret environment settings: namespaces, hostnames, replica counts |
| Kubernetes Secrets / External Secrets | HF tokens, cosign public keys, certificates, registry credentials |
| Cloud secret managers | source of truth for sensitive values |
| Runtime environment variables | Make targets, local validation, operational hooks |
| Private GitOps overlays | per-environment declarative deployment state |

Do **not** commit real infrastructure endpoints, hostnames, cloud account IDs,
registry hosts, database/storage connection details, secrets, keys,
certificates, regional policy, or compliance settings.

## Required Runtime Environment Variables

These are consumed by `impl/Makefile` and deployment/validation scripts.

| Variable | Purpose | Source | Expected value | Example |
|---|---|---|---|---|
| `INFERENCE_NAMESPACE` | Kubernetes namespace for gateway, admission, and engine | GitOps / deploy env | DNS-label namespace | `llm-inference-staging` |
| `OBSERVABILITY_NAMESPACE` | Namespace for Prometheus/Grafana/OTel | GitOps / deploy env | DNS-label namespace | `observability-staging` |
| `INFERENCE_ENGINE_RELEASE` | Helm release name for engine chart | GitOps / deploy env | Helm release name | `llm-engine-staging` |
| `INFERENCE_ENGINE_DEPLOYMENT` | Engine Deployment name for rollout checks | Helm values / deploy env | Kubernetes resource name | `vllm-llama70b-staging` |
| `INFERENCE_ENGINE_SERVICE` | Engine Service name for smoke validation | Helm values / deploy env | Kubernetes Service name | `vllm-llama70b-staging` |
| `INFERENCE_GATEWAY_RELEASE` | Helm release name for gateway chart | GitOps / deploy env | Helm release name | `llm-gateway-staging` |
| `CLUSTER_PREREQS_RELEASE` | Helm release name for prerequisite chart | GitOps / deploy env | Helm release name | `llm-prereqs-staging` |
| `PROMETHEUS_STACK_RELEASE` | Helm release name for kube-prometheus-stack | GitOps / deploy env | Helm release name | `llm-prometheus-staging` |
| `INFERENCE_OBSERVABILITY_RELEASE` | Helm release name for inference observability assets | GitOps / deploy env | Helm release name | `llm-observability-staging` |
| `ADMISSION_DEPLOYMENT_NAME` | Admission Deployment name for rollout checks | Helm values / deploy env | Kubernetes resource name | `inference-admission-staging` |
| `XID_WATCHER_DAEMONSET` | XID watcher DaemonSet name for rollout checks | Frontier fabric values / deploy env | Kubernetes resource name | `xid-watcher-staging` |
| `VLLM_BASE_URL` | Direct engine URL for smoke/bench | Runtime / service discovery | URL | `http://10.0.12.34:8000` |
| `PROMETHEUS_URL` | Prometheus API URL for live PromQL validation | Runtime / service discovery | URL ending at Prometheus root | `https://prometheus.staging.example.com` |
| `STAGING_GATEWAY_URL` | Gateway URL for staging game-day tests | Runtime / service discovery | HTTPS URL | `https://llm.staging.example.com` |
| `STAGING_REQUIRE` | Fail instead of skip when staging endpoint is absent | Runtime | `0` or `1` | `1` |

## Optional Runtime Hooks

These turn game-day placeholders into real staging validations.

| Variable | Purpose | Source | Expected value | Example |
|---|---|---|---|---|
| `BROWNOUT_HOOK` | Drives KV pressure through brownout rungs | Runbook / staging script | Shell command | `bash ops/game-day/brownout.sh` |
| `KV_PRESSURE_HOOK` | Floods heavy contexts and verifies reserve behavior | Runbook / staging script | Shell command | `bash ops/game-day/kv-pressure.sh` |
| `XID_SIM_HOOK` | Injects simulated XID and checks watcher action | Runbook / staging script | Shell command | `bash ops/game-day/xid-sim.sh 13` |
| `ROLLBACK_HOOK` | Runs canary rollback/eval regression test | CI pipeline | Shell command | `bash ci/eval/run_seeded_regression.sh` |
| `UNSIGNED_CHECKPOINT_HOOK` | Verifies bad model signature fails closed | CI / staging script | Shell command | `bash ops/security/unsigned-model.sh` |
| `GUARDRAIL_DOWN_HOOK` | Verifies guardrail outage policy | Runbook / staging script | Shell command | `bash ops/game-day/guardrail-down.sh` |
| `MODEL_SOURCE` | Local model directory to package as OCI artifact | Operator workstation / CI | filesystem path | `/mnt/models/llama-3.1-70b-fp8` |
| `MODEL_ARTIFACT` | Destination OCI artifact reference | Registry config | OCI reference | `oci://registry.example.com/models/llama-3.1-70b-fp8:2026-06-14` |
| `COSIGN_KEY` | Signing key path for model artifact push | Secret manager / CI secret | filesystem path or KMS URI | `awskms:///alias/model-signing` |

## Placeholder Reference

### Environment and Kubernetes

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_ENVIRONMENT_NAME` | Human-readable environment label | Parameter store / GitOps | `dev`, `staging`, `prod`, or org convention | `staging` |
| `REPLACE_WITH_REGION` | Deployment region | Cloud config | Region or datacenter code | `us-east-1` |
| `REPLACE_WITH_COMPLIANCE_PROFILE` | Compliance regime attached to deployment | Governance config | Profile identifier | `soc2-internal` |
| `REPLACE_WITH_INFERENCE_NAMESPACE` | Runtime namespace | GitOps | Kubernetes namespace | `llm-inference-staging` |
| `REPLACE_WITH_MONITORING_NAMESPACE` | Observability namespace | GitOps | Kubernetes namespace | `observability-staging` |
| `REPLACE_WITH_GATEWAY_CLASS` | Gateway API class | Cluster platform config | Installed GatewayClass name | `kgateway` |

### Networking

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_INFERENCE_HOSTNAME` | Public or internal gateway hostname | DNS / ingress config | FQDN | `llm.staging.example.com` |
| `REPLACE_WITH_GATEWAY_ROLE_LABEL` | Label used by NetworkPolicy to allow gateway → engine | Gateway chart values | Kubernetes label value | `inference-gateway` |

### Registry and Artifacts

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_REGISTRY_HOST` | Internal registry host | Artifact registry config | Registry DNS name | `registry.staging.example.com` |
| `REPLACE_WITH_MODEL` | Model artifact name/path | Model registry metadata | OCI repository segment | `llama-3.1-70b-fp8` |
| `REPLACE_WITH_TAG` | Generic artifact tag | Release metadata | immutable tag | `2026-06-14.1` |
| `REPLACE_WITH_SIGNED_TAG` | Signed model/adapter tag | Promotion metadata | immutable signed tag | `sha-abc1234` |
| `REPLACE_WITH_APPROVED_MODEL_DIGEST` | Approved model artifact digest | Promotion metadata | `sha256:<hex>` | `sha256:abc123...` |
| `REPLACE_WITH_APPROVED_ADAPTER_DIGEST` | Approved LoRA adapter digest | Adapter promotion metadata | `sha256:<hex>` | `sha256:def456...` |
| `REPLACE_WITH_COSIGN_PUBLIC_KEY_SECRET` | K8s Secret containing cosign public key | Secret manager / ExternalSecret | Secret name | `cosign-model-public-key` |
| `REPLACE_WITH_COSIGN_KEY_URI` | Signing key used by release CI | Secret manager / KMS | KMS URI or secret-mounted path | `awskms:///alias/model-signing` |

### Model and Engine

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_PROFILE_NAME` | Validation profile name | `playbook/versions.lock` | profile key | `h100-vllm-kserve` |
| `REPLACE_WITH_MODEL_ALIAS` | Client-facing model alias | Gateway/admission config | short model id | `llama70b` |
| `REPLACE_WITH_SERVED_MODEL_NAME` | Engine-served model name | Engine profile | exact served name expected by vLLM | `meta-llama/Llama-3.1-70B-Instruct` |
| `REPLACE_WITH_MAX_CONTEXT_TOKENS` | Admission context cap | Product/model policy | integer tokens | `16384` |
| `REPLACE_WITH_ENGINE_RELEASE` | Helm release for engine | Deployment env | Helm release name | `llm-engine-staging` |
| `REPLACE_WITH_ENGINE_DEPLOYMENT` | Engine Deployment name | Helm values | Kubernetes resource name | `vllm-llama70b-staging` |
| `REPLACE_WITH_VLLM_IMAGE_REPOSITORY` | Engine image repository | Image registry config | OCI image repository | `vllm/vllm-openai` or internal mirror |
| `REPLACE_WITH_VLLM_IMAGE_TAG` | Engine image tag | Release metadata | image tag pinned to profile | `v0.9.1` |
| `REPLACE_WITH_DTYPE` | Engine dtype | Profile config | vLLM dtype | `bfloat16` |
| `REPLACE_WITH_QUANTIZATION` | Weight quantization mode | Profile config | vLLM quantization flag | `fp8` |
| `REPLACE_WITH_KV_CACHE_DTYPE` | KV cache dtype | Profile config | vLLM KV dtype | `fp8` |
| `REPLACE_WITH_GPU_MEMORY_UTILIZATION` | vLLM GPU memory utilization cap | Profile config | string/float in `[0,1]` | `0.90` |
| `REPLACE_WITH_HF_TOKEN_SECRET` | Optional HF token Secret | Secret manager / ExternalSecret | Secret name | `hf-token-staging` |

### Resources and Scaling

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_GPU_COUNT` | GPUs per engine pod | Capacity plan | integer | `2` |
| `REPLACE_WITH_GPU_NODE_SELECTOR_KEY` | GPU node label key | Cluster config | label key | `nvidia.com/gpu.product` |
| `REPLACE_WITH_GPU_NODE_SELECTOR_VALUE` | GPU node label value | Cluster config | label value | `NVIDIA-H100-80GB-HBM3` |
| `REPLACE_WITH_ENGINE_REPLICA_COUNT` | Initial replicas | Benchmark/capacity plan | integer | `2` |
| `REPLACE_WITH_MIN_REPLICAS` | KEDA minimum replicas | Capacity plan | integer | `2` |
| `REPLACE_WITH_MAX_REPLICAS` | KEDA maximum replicas | Budget/capacity plan | integer | `12` |
| `REPLACE_WITH_QUEUE_THRESHOLD` | Per-replica queue threshold | Benchmark report §5.3 | integer string | `6` |

### Gateway and Admission

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_GATEWAY_NAME` | Gateway resource name | Helm values | Kubernetes resource name | `llm-gateway-staging` |
| `REPLACE_WITH_ENGINE_SERVICE_NAME` | Backend engine Service | Helm values | Kubernetes Service name | `vllm-llama70b-staging` |
| `REPLACE_WITH_ADMISSION_IMAGE_REPOSITORY` | Admission service image repo | Image registry config | OCI image repository | `registry.staging.example.com/inference-admission` |
| `REPLACE_WITH_ADMISSION_IMAGE_TAG` | Admission service image tag | Release metadata | image tag | `2026-06-14.1` |
| `REPLACE_WITH_ADMISSION_REPLICAS` | Admission service replica count | Capacity/SLO plan | integer | `2` |
| `REPLACE_WITH_ADMISSION_CONFIG_NAME` | Admission tenant policy ConfigMap | Helm values | ConfigMap name | `inference-admission-tenants-staging` |
| `REPLACE_WITH_ADMISSION_SERVICE_NAME` | Admission Service name | Helm values | Kubernetes Service name | `inference-admission-staging` |
| `REPLACE_WITH_DEFAULT_TENANT_ID` | Fallback tenant when header is absent | Admission policy | tenant id or disabled sentinel | `standard-prod` |
| `REPLACE_WITH_CRITICAL_TENANT_ID` | Critical tenant key in policy | Tenant registry | tenant id | `payments-prod` |
| `REPLACE_WITH_STANDARD_TENANT_ID` | Standard tenant key in policy | Tenant registry | tenant id | `search-prod` |
| `REPLACE_WITH_SHEDDABLE_TENANT_ID` | Best-effort tenant key in policy | Tenant registry | tenant id | `experiments` |

### Scheduler, Reserves, and Brownout

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_GOODPUT_KNEE_CONCURRENCY` | Concurrency at the validated goodput knee | E1 benchmark report / capacity plan | positive integer | `48` |
| `REPLACE_WITH_DEFAULT_TENANT_KV_TOKENS` | Default per-tenant KV token reservation cap | Capacity plan | positive integer tokens | `1000000` |
| `REPLACE_WITH_CRITICAL_TENANT_KV_TOKENS` | Critical tenant KV reservation cap | Tenant SLO config | positive integer tokens | `2000000` |
| `REPLACE_WITH_STANDARD_TENANT_KV_TOKENS` | Standard tenant KV reservation cap | Tenant SLO config | positive integer tokens | `1000000` |
| `REPLACE_WITH_SHEDDABLE_TENANT_KV_TOKENS` | Sheddable tenant KV reservation cap | Tenant SLO config | positive integer tokens | `500000` |
| `REPLACE_WITH_BROWNOUT_STANDARD_MAX_TOKENS` | Standard max-token cap applied at brownout rung 2 | Product policy | positive integer tokens | `1024` |
| `REPLACE_WITH_BROWNOUT_FALLBACK_MODEL_ALIAS` | Lower-cost model alias for brownout rung 3 | Model routing policy | configured model alias | `llama8b` |
| `REPLACE_WITH_HEAVY_CONTEXT_THRESHOLD_TOKENS` | Routing threshold for heavy-pool isolation | Product/model policy | positive integer tokens | `32000` |
| `REPLACE_WITH_CRITICAL_POOL_NAME` | Pool/service key for Critical traffic | Gateway/EPP policy | route or service id | `critical` |
| `REPLACE_WITH_STANDARD_POOL_NAME` | Pool/service key for normal traffic | Gateway/EPP policy | route or service id | `standard` |
| `REPLACE_WITH_HEAVY_POOL_NAME` | Pool/service key for heavy contexts | Gateway/EPP policy | route or service id | `heavy-context` |

E3 assumes the gateway or EPP integration consumes the scheduler policy and
exports queue debt, reserve rejection, brownout rung, and route decision metrics.
This scaffold does not install a scheduler service by itself.

### Observability

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_PROMETHEUS_URL` | External Prometheus API URL for validation | Observability platform | URL | `https://prometheus.staging.example.com` |
| `REPLACE_WITH_PROMETHEUS_SERVICE_URL` | In-cluster Prometheus URL for KEDA | Service discovery | URL | `http://prometheus-operated.observability.svc:9090` |
| `REPLACE_WITH_PROMETHEUS_STACK_RELEASE` | Helm release for kube-prometheus-stack | GitOps / deploy env | Helm release name | `llm-prometheus-staging` |
| `REPLACE_WITH_OBSERVABILITY_RELEASE` | Helm release for inference dashboard, alert, and OTel assets | GitOps / deploy env | Helm release name | `llm-observability-staging` |
| `REPLACE_WITH_OTEL_SERVICE_NAMESPACE` | OTel service namespace attribute | Observability config | string | `llm-inference-staging` |
| `REPLACE_WITH_OTLP_ENDPOINT` | OTLP exporter endpoint | Observability config | host:port | `tempo.observability.svc:4317` |
| `REPLACE_WITH_OTEL_COLLECTOR_IMAGE_REPOSITORY` | OTel collector image repository | Image registry config | OCI image repository | `otel/opentelemetry-collector-contrib` |
| `REPLACE_WITH_OTEL_COLLECTOR_IMAGE_TAG` | OTel collector image tag | Release metadata | pinned image tag | `0.104.0` |
| `REPLACE_WITH_OTEL_MEMORY_LIMIT_MIB` | OTel collector memory limiter value | Capacity plan | integer MiB | `384` |
| `REPLACE_WITH_TTFT_P95_SLO_SECONDS` | TTFT P95 alert threshold | SLO config | seconds as float | `0.5` |
| `REPLACE_WITH_WAITING_TO_RUNNING_ALERT_RATIO` | Queue-bound alert ratio | SLO config | numeric ratio | `2` |
| `REPLACE_WITH_KV_CACHE_ALERT_THRESHOLD` | KV pressure alert threshold | Capacity/SLO config | ratio in `[0,1]` | `0.92` |
| `REPLACE_WITH_XID_ALERT_LOOKBACK` | XID alert lookback window | Observability config | Prometheus duration | `5m` |
| `REPLACE_WITH_TTFT_ALERT_SEVERITY` | TTFT alert route severity | Incident response policy | severity label | `sev2` |
| `REPLACE_WITH_QUEUE_ALERT_SEVERITY` | queue-bound alert route severity | Incident response policy | severity label | `sev2` |
| `REPLACE_WITH_KV_ALERT_SEVERITY` | KV pressure alert route severity | Incident response policy | severity label | `sev2` |
| `REPLACE_WITH_XID_ALERT_SEVERITY` | GPU XID alert route severity | Incident response policy | severity label | `sev2` |

### Security and Compliance

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_TRUE_OR_FALSE` | Boolean security setting | Compliance profile | `true` or `false` | `true` |
| `REPLACE_WITH_AUDIT_SINK` | Audit log destination | Security platform | sink id / URL / topic | `kafka://audit.llm-requests` |
| `REPLACE_WITH_CERTIFICATE_ISSUER` | Certificate issuer for gateway/mTLS | cert-manager / PKI | issuer name | `platform-ca-issuer` |

### Governance and Guardrails

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_PROMOTION_TIMESTAMP` | Time a digest was promoted | Release CI | RFC3339 timestamp | `2026-06-14T22:00:00Z` |
| `REPLACE_WITH_PROMOTION_ACTOR` | Human or service account approving promotion | Release system | user/service id | `ml-release-bot` |
| `REPLACE_WITH_CHANGE_REQUEST_ID` | Change-management reference | Release system | ticket/change id | `CHG-12345` |
| `REPLACE_WITH_PREVIOUS_APPROVED_DIGEST` | Rollback digest for the prior approved artifact | Promotion metadata | `sha256:<hex>` | `sha256:987...` |
| `REPLACE_WITH_MODEL_SOURCE_URI` | Source model checkpoint or upstream artifact | Model registry | URI | `s3://model-source/llama70b` |
| `REPLACE_WITH_MODEL_LICENSE` | Model license identifier | Model card / legal review | SPDX or policy id | `llama3.1-community` |
| `REPLACE_WITH_MODEL_OWNER` | Owning team for release and incidents | Ownership registry | team slug | `ml-platform` |
| `REPLACE_WITH_BUILD_COMMIT` | Commit that produced the artifact | CI | git SHA | `abc1234` |
| `REPLACE_WITH_BUILD_WORKFLOW_URI` | Build workflow run URI | CI | URL | `https://github.com/org/repo/actions/runs/1` |
| `REPLACE_WITH_SBOM_ATTESTATION_URI` | SBOM attestation pointer | Registry / transparency log | URI | `oci://registry/attestations/sbom` |
| `REPLACE_WITH_SLSA_ATTESTATION_URI` | SLSA provenance pointer | Registry / transparency log | URI | `oci://registry/attestations/slsa` |
| `REPLACE_WITH_MODEL_CARD_URI` | Stored model card pointer | Registry / docs store | URI | `s3://model-cards/llama70b.md` |
| `REPLACE_WITH_EVAL_PIPELINE_RUN_URI` | Eval-gate run that approved promotion | CI / eval system | URL or run id | `https://ci.example/runs/42` |
| `REPLACE_WITH_PROMOTION_METADATA_URI` | Promotion metadata storage pointer | Release system | URI | `s3://promotions/llama70b/prod.yaml` |
| `REPLACE_WITH_ADAPTER_PROMOTION_METADATA_URI` | Adapter promotion metadata pointer | Release system | URI | `s3://promotions/adapters/a.yaml` |
| `REPLACE_WITH_GUARDRAIL_IMAGE_REPOSITORY` | Guardrail service image repository | Image registry config | OCI image repository | `registry.example.com/inference-guardrails` |
| `REPLACE_WITH_GUARDRAIL_IMAGE_TAG` | Guardrail service image tag | Release metadata | image tag | `2026-06-14.1` |
| `REPLACE_WITH_GUARDRAIL_REPLICAS` | Guardrail service replica count | Safety/SLO capacity plan | integer | `2` |
| `REPLACE_WITH_GUARDRAIL_SERVICE_NAME` | Guardrail service called by gateway policy | Helm values | Kubernetes Service name | `inference-guardrails` |
| `REPLACE_WITH_GUARDRAIL_CONFIG_NAME` | Guardrail route policy ConfigMap | GitOps / Helm values | Kubernetes ConfigMap name | `guardrail-policy-staging` |
| `REPLACE_WITH_REQUEST_ID` | Request id propagated to guardrail audit | Gateway | UUID/string | `req-123` |


### Gateway Policy Examples

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_GATEWAY_AUTH_POLICY_NAME` | kgateway external auth policy name | Gateway overlay | Kubernetes resource name | `llm-auth-policy-staging` |
| `REPLACE_WITH_GATEWAY_SECURITY_POLICY_NAME` | Envoy Gateway security policy name | Gateway overlay | Kubernetes resource name | `llm-security-policy-staging` |
| `REPLACE_WITH_HTTPROUTE_NAME` | HTTPRoute bound to admission policy | Gateway chart output | Kubernetes resource name | `llm-gateway-openai` |
| `REPLACE_WITH_GUARDRAIL_PROVIDER_NAME` | Guardrail backend provider name | Safety platform | provider id | `llama-guard` |
| `REPLACE_WITH_PROVIDER_TYPE` | Guardrail provider type | Safety platform | enum/string | `http` |
| `REPLACE_WITH_GUARDRAIL_PROVIDER_ENDPOINT` | Guardrail provider endpoint | Secret/config store | URL | `https://guardrails.staging.example.com` |
| `REPLACE_WITH_GUARDRAIL_PROVIDER_TIMEOUT_MS` | Guardrail provider timeout | Route policy | integer ms | `250` |
| `REPLACE_WITH_GUARDRAIL_PROVIDER_AUTH_SECRET` | Secret for guardrail provider auth | Secret manager | Kubernetes Secret name | `guardrail-provider-auth` |

### LoRA, Eval, and Frontier

| Placeholder | Purpose | Config source | Expected value | Sample |
|---|---|---|---|---|
| `REPLACE_WITH_ADAPTER_ID` | Adapter id in values map | Adapter registry | tenant/model adapter id | `tenant-a-support` |
| `REPLACE_WITH_ADAPTER` | Adapter artifact name | Adapter registry | OCI repository segment | `tenant-a-support-r64` |
| `REPLACE_WITH_LORA_ADAPTER_REGISTRY_CONFIG` | ConfigMap containing adapter registry metadata | GitOps / Helm values | Kubernetes ConfigMap name | `lora-adapter-registry` |
| `REPLACE_WITH_ADAPTER_LOCALITY_LABEL` | Label used for adapter-aware routing | Gateway/EPP config | Kubernetes label key | `inference.platform/loaded-adapter` |
| `REPLACE_WITH_DOMAIN_EVAL_DATASET_URI` | Domain eval dataset | Evaluation data catalog | URI | `s3://ml-evals-staging/domain/v1.jsonl` |
| `REPLACE_WITH_PRODUCTION_REPLAY_DATASET_URI` | Sampled production replay dataset | Evaluation data catalog | URI | `s3://ml-evals-staging/replay/2026-06-14.jsonl` |
| `REPLACE_WITH_MULTINODE_ENGINE_DEPLOYMENT` | Multi-node engine Deployment name | Helm values | Kubernetes resource name | `vllm-405b-staging` |
| `REPLACE_WITH_MULTINODE_ENGINE_REPLICA_COUNT` | Multi-node deployment replica count | Capacity plan | integer | `1` |
| `REPLACE_WITH_FRONTIER_PROFILE_NAME` | Frontier validation profile key | `versions.lock` / release metadata | profile key | `moe-multinode-interim` |
| `REPLACE_WITH_FRONTIER_MODEL_ALIAS` | Client-facing frontier model alias | Gateway/model registry | model alias | `llama405b` |
| `REPLACE_WITH_FRONTIER_SERVED_MODEL_NAME` | Engine-served frontier model name | Model registry | exact served model name | `meta-llama/Llama-3.1-405B-Instruct` |
| `REPLACE_WITH_FRONTIER_MODEL` | Frontier model artifact repository segment | Model registry | OCI path segment | `llama-3.1-405b-fp8` |
| `REPLACE_WITH_FRONTIER_MAX_MODEL_LEN` | Frontier max model length | Capacity plan | integer tokens | `8192` |
| `REPLACE_WITH_TENSOR_PARALLEL_SIZE` | Tensor parallel width | Topology plan | integer | `8` |
| `REPLACE_WITH_PIPELINE_PARALLEL_SIZE` | Pipeline parallel width | Topology plan | integer | `2` |
| `REPLACE_WITH_PROCESS_GROUP_FAILURE_DOMAIN` | Failure-domain label for TP/PP group | Platform policy | label/string | `tp-pp-group` |
| `REPLACE_WITH_FABRIC_TOPOLOGY_CLASS` | Fabric class used for evidence grouping | Cluster platform | topology identifier | `h100-ib-rail-aligned` |
| `REPLACE_WITH_NCCL_IB_HCA` | HCA allowlist for NCCL rail pinning | Cluster platform | comma-separated HCA list | `mlx5_0,mlx5_1` |
| `REPLACE_WITH_NCCL_JOB_NAME` | NCCL baseline Job name | GitOps / operator | Kubernetes resource name | `nccl-fabric-baseline` |
| `REPLACE_WITH_NCCL_TESTS_IMAGE` | Prebuilt NCCL tests image | Image registry | OCI image reference | `registry.example.com/platform/nccl-tests:2026-06-14` |
| `REPLACE_WITH_NCCL_TESTS_PATH` | Directory containing `all_reduce_perf` | NCCL tests image contract | absolute path | `/opt/nccl-tests/build` |
| `REPLACE_WITH_NCCL_MACRO_MIN_BYTES` | Macro all-reduce lower bound | Fabric runbook | nccl-tests byte value | `1G` |
| `REPLACE_WITH_NCCL_MACRO_MAX_BYTES` | Macro all-reduce upper bound | Fabric runbook | nccl-tests byte value | `8G` |
| `REPLACE_WITH_NCCL_MICRO_MIN_BYTES` | Micro all-reduce lower bound | Fabric runbook | nccl-tests byte value | `8` |
| `REPLACE_WITH_NCCL_MICRO_MAX_BYTES` | Micro all-reduce upper bound | Fabric runbook | nccl-tests byte value | `2M` |
| `REPLACE_WITH_NCCL_MICRO_ALGO` | Decode-sensitive NCCL algorithm | Fabric tuning | NCCL algorithm | `Tree` |
| `REPLACE_WITH_NCCL_MICRO_PROTO` | Decode-sensitive NCCL protocol | Fabric tuning | NCCL protocol | `Simple` |
| `REPLACE_WITH_EXPERT_PARALLEL_SIZE` | Expert parallel width | MoE topology plan | integer | `8` |
| `REPLACE_WITH_MAX_EXPERT_IMBALANCE_RATIO` | Alert/gate for hot expert skew | SLO policy | decimal string | `1.25` |
| `REPLACE_WITH_FABRIC_BUSBW_MIN_FRACTION` | Minimum bus bandwidth fraction | Fabric SLO policy | decimal string | `0.80` |
| `REPLACE_WITH_HOT_EXPERT_POLICY` | Hot expert mitigation policy | Routing/platform policy | policy key | `route-to-hot-expert-pool` |
| `REPLACE_WITH_MOE_FALLBACK_POOL` | MoE fallback engine pool | Routing config | service/pool name | `frontier-monolithic-pool` |
| `REPLACE_WITH_DISAGG_PROFILE_NAME` | Disaggregated serving profile key | Release metadata | profile key | `h100-vllm-kserve` |
| `REPLACE_WITH_PREFILL_POOL_DEPLOYMENT` | Prefill pool Deployment name | Helm values | Kubernetes resource name | `vllm-prefill-pool` |
| `REPLACE_WITH_DECODE_POOL_DEPLOYMENT` | Decode pool Deployment name | Helm values | Kubernetes resource name | `vllm-decode-pool` |
| `REPLACE_WITH_PREFILL_POOL_SERVICE` | Prefill pool Service name | Helm values | Kubernetes Service name | `vllm-prefill-pool` |
| `REPLACE_WITH_DECODE_POOL_SERVICE` | Decode pool Service name | Helm values | Kubernetes Service name | `vllm-decode-pool` |
| `REPLACE_WITH_KV_TRANSFER_CONNECTOR` | KV transfer connector | Engine/disagg support matrix | connector name | `NixlConnector` |
| `REPLACE_WITH_PREFILL_KV_ENDPOINT` | Prefill KV transfer endpoint | Service discovery | URL or host:port | `vllm-prefill-kv.llm.svc:5555` |
| `REPLACE_WITH_DECODE_KV_ENDPOINT` | Decode KV transfer endpoint | Service discovery | URL or host:port | `vllm-decode-kv.llm.svc:5555` |
| `REPLACE_WITH_KV_TRANSFER_TIMEOUT_MS` | KV transfer timeout budget | SLO/capacity plan | integer milliseconds | `250` |
| `REPLACE_WITH_MONOLITHIC_FALLBACK_POOL` | P/D fallback pool | Routing config | service/pool name | `vllm-monolithic-pool` |
| `REPLACE_WITH_XID_WATCHER_IMAGE` | XID watcher image | Image registry | OCI image reference | `registry.example.com/platform/xid-watcher:2026-06-14` |
| `REPLACE_WITH_XID_WATCHER_SERVICE_ACCOUNT` | XID watcher ServiceAccount | GitOps | Kubernetes resource name | `xid-watcher` |
| `REPLACE_WITH_XID_WATCHER_CLUSTER_ROLE` | XID watcher ClusterRole | GitOps | Kubernetes resource name | `xid-watcher` |
| `REPLACE_WITH_XID_WATCHER_CLUSTER_ROLE_BINDING` | XID watcher ClusterRoleBinding | GitOps | Kubernetes resource name | `xid-watcher` |
| `REPLACE_WITH_XID_WATCHER_CONFIG_NAME` | XID watcher ConfigMap | GitOps | Kubernetes resource name | `xid-watcher-config` |
| `REPLACE_WITH_XID_WATCHER_DAEMONSET` | XID watcher DaemonSet | GitOps | Kubernetes resource name | `xid-watcher` |
| `REPLACE_WITH_XID_TARGET_POD_SELECTOR` | Engine pods eligible for tier-1 restart | Platform policy | Kubernetes label selector | `app.kubernetes.io/component=engine` |
| `REPLACE_WITH_XID_DRAIN_TIMEOUT` | Fatal drain timeout | Platform policy | duration string | `10m` |

## Sample Environment Configurations

These samples are illustrative only. Store real versions in a private GitOps
repo, parameter store, or secret manager.

Complete fake examples are available in:

- `examples/dev.local.yaml`
- `examples/staging.local.yaml`
- `examples/production.local.yaml`

### Development

```yaml
environment:
  name: dev
  region: local
  compliance_profile: none
kubernetes:
  namespace: llm-dev
  monitoring_namespace: observability-dev
  gateway_class_name: kgateway-dev
network:
  public_hostname: llm.dev.example.test
registry:
  model_artifact: oci://registry.dev.example.test/models/llama-3.1-8b@sha256:devdigest
model:
  alias: llama8b
  served_name: meta-llama/Llama-3.1-8B-Instruct
  max_context_tokens: 4096
resources:
  gpu_count: 1
  gpu_node_selector_key: nvidia.com/gpu.product
  gpu_node_selector_value: NVIDIA-L40S
scaling:
  replicas: 1
  min_replicas: 1
  max_replicas: 2
  keda_queue_threshold: \"2\"
observability:
  prometheus_stack_release: llm-prometheus-dev
  release_name: llm-observability-dev
  otel_collector_image: otel/opentelemetry-collector-contrib
  otel_collector_tag: 0.104.0
  otel_memory_limit_mib: 256
  alerts:
    ttft_p95_slo_seconds: 1.0
    waiting_to_running_ratio: 3
    kv_cache_threshold: 0.90
    xid_lookback: 5m
scheduler:
  reserves:
    knee_concurrency: 8
    default_tenant_kv_tokens: 250000
  routing:
    heavy_threshold_tokens: 8192
```

### Staging

```yaml
environment:
  name: staging
  region: us-east-1
  compliance_profile: internal
kubernetes:
  namespace: llm-inference-staging
  monitoring_namespace: observability-staging
  gateway_class_name: kgateway
network:
  public_hostname: llm.staging.example.com
registry:
  model_artifact: oci://registry.staging.example.com/models/llama-3.1-70b-fp8@sha256:stagingdigest
  admission_image: registry.staging.example.com/inference-admission
  admission_tag: \"2026-06-14.1\"
model:
  alias: llama70b
  served_name: meta-llama/Llama-3.1-70B-Instruct
  max_context_tokens: 16384
resources:
  gpu_count: 2
  gpu_node_selector_key: nvidia.com/gpu.product
  gpu_node_selector_value: NVIDIA-H100-80GB-HBM3
scaling:
  replicas: 2
  min_replicas: 2
  max_replicas: 6
  keda_queue_threshold: \"6\"
observability:
  prometheus_url: https://prometheus.staging.example.com
  prometheus_service_url: http://prometheus-operated.observability-staging.svc:9090
  prometheus_stack_release: llm-prometheus-staging
  release_name: llm-observability-staging
  otel_collector_image: otel/opentelemetry-collector-contrib
  otel_collector_tag: 0.104.0
  otel_memory_limit_mib: 384
  alerts:
    ttft_p95_slo_seconds: 0.5
    waiting_to_running_ratio: 2
    kv_cache_threshold: 0.92
    xid_lookback: 5m
scheduler:
  reserves:
    knee_concurrency: 48
    default_tenant_kv_tokens: 1000000
  brownout:
    fallback_model_alias: llama8b
  routing:
    heavy_threshold_tokens: 32000
```

### Production

```yaml
environment:
  name: prod
  region: us-east-1
  compliance_profile: soc2
kubernetes:
  namespace: llm-inference-prod
  monitoring_namespace: observability-prod
  gateway_class_name: kgateway
network:
  public_hostname: llm.example.com
registry:
  model_artifact: oci://registry.example.com/models/llama-3.1-70b-fp8@sha256:proddigest
model:
  alias: llama70b
  served_name: meta-llama/Llama-3.1-70B-Instruct
  max_context_tokens: 16384
resources:
  gpu_count: 2
  gpu_node_selector_key: nvidia.com/gpu.product
  gpu_node_selector_value: NVIDIA-H100-80GB-HBM3
scaling:
  replicas: 4
  min_replicas: 4
  max_replicas: 12
  keda_queue_threshold: \"6\"
security:
  service_mesh_mtls_required: true
  audit_sink: kafka://audit-prod/llm-requests
  certificate_issuer: prod-platform-ca
observability:
  prometheus_stack_release: llm-prometheus-prod
  release_name: llm-observability-prod
  otel_collector_image: registry.example.com/observability/otel-collector
  otel_collector_tag: sha-release
  otel_memory_limit_mib: 512
  alerts:
    ttft_p95_slo_seconds: 0.5
    waiting_to_running_ratio: 2
    kv_cache_threshold: 0.92
    xid_lookback: 5m
scheduler:
  reserves:
    knee_concurrency: 96
    default_tenant_kv_tokens: 1500000
  brownout:
    fallback_model_alias: llama8b
  routing:
    heavy_threshold_tokens: 32000
```

## Sample Kubernetes Secret Manifests

Use External Secrets or your platform secret manager in production. These are
shape examples only.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: hf-token-staging
  namespace: llm-inference-staging
type: Opaque
stringData:
  token: REPLACE_WITH_HF_TOKEN
---
apiVersion: v1
kind: Secret
metadata:
  name: cosign-model-public-key
  namespace: llm-inference-staging
type: Opaque
stringData:
  cosign.pub: |
    -----BEGIN PUBLIC KEY-----
    REPLACE_WITH_PUBLIC_KEY
    -----END PUBLIC KEY-----
```

## Sample Deployment Flow

```bash
export INFERENCE_NAMESPACE=llm-inference-staging
export OBSERVABILITY_NAMESPACE=observability-staging
export INFERENCE_ENGINE_RELEASE=llm-engine-staging
export INFERENCE_ENGINE_DEPLOYMENT=vllm-llama70b-staging
export INFERENCE_ENGINE_SERVICE=vllm-llama70b-staging
export INFERENCE_GATEWAY_RELEASE=llm-gateway-staging
export CLUSTER_PREREQS_RELEASE=llm-prereqs-staging
export PROMETHEUS_STACK_RELEASE=llm-prometheus-staging
export INFERENCE_OBSERVABILITY_RELEASE=llm-observability-staging
export ADMISSION_DEPLOYMENT_NAME=inference-admission-staging
export XID_WATCHER_DAEMONSET=xid-watcher-staging

helm template llm-engine-staging ../charts/inference-engine \\
  -f ../charts/inference-engine/values.yaml \\
  -f ../environments/staging.local.yaml
```
