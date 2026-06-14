# 5. Scale: Kubernetes, Sizing Math, Fabric, Disaggregation

## 5.1 Parallelism decision tree

```
Does the model (quantized) fit on ONE GPU with KV + headroom (§2.1 calculator)?
 ├─ YES → DP replicas. Scale out. Stop adding parallelism.
 └─ NO → Does it fit in ONE NODE (NVLink/xGMI domain)?
     ├─ YES → TP = smallest power of 2 that fits. + DP for throughput.
     └─ NO → TP within node × PP across nodes.
              MoE? → TP/DP for dense layers + EP for experts;
                     your bottleneck is now all-to-all bandwidth, not FLOPS.
Disaggregate prefill/decode only on measured interference or SKU economics (§5.7).
```

**Workload × interconnect → topology matrix** (compact form of the tree, indexed by the two inputs that actually decide it):

| Prompt-length profile | NVSwitch/NVLink node | PCIe-only node | Multi-node IB/RoCE | Multi-node Ethernet |
|---|---|---|---|---|
| **Short prompts, chatty** (P95 < 2K) | DP replicas; TP only if model doesn't fit | DP replicas of quantized single-GPU fits — avoid TP | DP across nodes | DP across nodes |
| **Mixed** (P95 2K–16K) | TP-to-fit + DP; chunked prefill on | smallest quantization that fits one GPU, else PP | TP in-node × DP across | same; never TP across the wire |
| **Long-context heavy** (P95 > 32K) | TP + heavy-pool isolation (§6.2); disaggregation candidate | wrong hardware class — re-plan | TP in-node × PP across; disaggregated P/D pools | PP only; expect TTFT pain, set SLOs accordingly |
| **MoE** | TP dense + EP experts in NVLink domain | not viable at scale | EP across nodes — all-to-all is the budget | not viable at scale |

## 5.2 Production vLLM on Kubernetes (completed manifest set)

**Artifact:** [`playbook/helm/`](../playbook/helm/) — `deployment.yaml`, `service.yaml`, `pvc.yaml`, `pdb.yaml`, `networkpolicy.yaml`, `keda-scaledobject.yaml`

**Granular GPU-Fault Detection (XID Handling) is a platform component, not a probe.** The wedged-CUDA-context problem (HTTP 200 while the GPU is dead) is solved by a **DCGM/XID watcher**. **[T2]** Tier XID handling instead of cordoning on every error ([Appendix G](appendices/G-scale-tier-requirements.md#t2-tiered-xid-handling)):
1. **Recoverable Faults (e.g., XID 13, 31 - memory page fault / user-space crash):** Unmap the process and restart the engine container (avoids a full node cordon and a 15-minute K8s rescheduling cycle).
2. **Fatal Faults (e.g., XID 79, 94 - fallen off bus, uncontained ECC):** Cordon the node, taint, and drain `DCGM_FI_DEV_XID_ERRORS`.
The startup probe proves the context once; the watcher catches it dying later — without generating synthetic load every minute on every pod.

**Model-cache strategy — RWX is one option, not the default.** RWX PVCs require a compatible storage class (NFS/CephFS/Filestore) many GPU clusters lack. Alternatives, in rough order of preference: **(a)** bake/pull model as an **OCI artifact** (KServe model-cache, ORAS) — immutable, signed (§6.9), CDN-able; **(b)** per-node **hostPath cache pre-warmed by a DaemonSet** — fastest cold start, node-local; **(c)** RWO PVC per replica — simple, duplicates storage; **(d)** RWX shared cache — convenient where the storage class exists. Choose per cluster; the manifest's PVC is a placeholder for that decision.

**Zero-trust note:** the manifest serves bare HTTP on 8000. Regulated environments require **mTLS between gateway and engine** — typically via a service mesh (Istio/Linkerd sidecars or ambient) rather than engine-level TLS. Treat the NetworkPolicy above as the floor and mesh mTLS as the regulated-environment standard (§6.8).

## 5.3 Autoscaling — sizing math first, KEDA second

**Derive the threshold; don't guess it.** Little's Law: `L = λ × W` (in-system requests = arrival rate × time-in-system).

```
From the §2.5 benchmark at the goodput knee:
  W            = E[TTFT] + E[output_tokens] × E[TPOT]          (mean service time at knee)
  C_replica    = concurrency at knee (bounded by KV budget: KV_total / E[KV per request])
  replicas     = ceil( λ_P99 × W / (C_replica × safety) ),  safety ≈ 0.7–0.8
  KEDA queue threshold ≈ C_replica × (1 − safety)            (queue forming past headroom)
```

**Worked [Derived]:** knee at C_replica = 24, W = 12 s, expected peak λ = 6 req/s → in-flight = 72 → replicas = ceil(72 / (24×0.75)) = **4**, queue threshold ≈ 24×0.25 = **6** per replica.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: { name: vllm-scaler }
spec:
  scaleTargetRef: { name: vllm-llama70b }
  minReplicaCount: 2
  maxReplicaCount: 12          # from sizing math + budget, not vibes
  cooldownPeriod: 600          # GPU pods churn slowly; flapping is expensive
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      query: sum(vllm:num_requests_waiting{app="vllm-llama70b"}) / count(vllm:num_requests_waiting{app="vllm-llama70b"})
      threshold: "6"           # derived above — per-replica queue headroom
```

**Reactive autoscaling cannot save TTFT during a spike.** Scrape interval + KEDA loop + pod schedule + multi-minute weight load = the SLO is blown long before the new replica serves. Production pattern:
1. **Admission control absorbs the spike** (§6.1): shed Sheddable-class traffic with 429 + `Retry-After` the moment the fleet passes its goodput knee — protect Critical-class SLOs.
2. **Warm headroom**: run N+1 with pre-pulled weights (PVC/OCI cache makes "warm" minutes→seconds); for bursty products keep a scaled-to-zero-but-image-warm pool.
3. **Predictive scaling** where traffic has diurnal shape (scale on schedule or token-velocity trend, not just instantaneous queue).
Autoscaling reclaims cost at the timescale of tens of minutes; it is not a latency-protection mechanism.

## 5.4 Fabric & topology validation (gate, don't hope)

TP=8 over a non-NVSwitch topology silently halves throughput; a mis-mapped IB rail does the same across nodes. **Validate before first serve, and after any driver/firmware change:**

```bash
# 1. Topology audit — expect NV# (NVLink) between TP peers, not PHB/PIX (PCIe)
nvidia-smi topo -m

# 2. NCCL all-reduce busbw across the intended TP/PP group
git clone https://github.com/NVIDIA/nccl-tests && cd nccl-tests && make
# Macro-payload test (Prefill/Weights):
./build/all_reduce_perf -b 1G -e 8G -f 2 -g 8
# [T2] Micro-payload all-reduce test (decode TPOT) — see Appendix G
./build/all_reduce_perf -b 8 -e 2M -f 2 -g 8
# ENFORCE fast decode protocols in your engine environment: NCCL_ALGO=Tree and NCCL_PROTO=Simple (or LL128)
# GATE: busbw ≥ ~80% of the topology's theoretical (e.g., NVSwitch HGX H100 ≈ 450+ GB/s
# busbw expected). If you're at 50%, STOP and debug topology before benchmarking the engine.

# 3. Multi-node: verify rail alignment and RDMA
#    NCCL_IB_HCA pinned to the correct HCAs; GPUDirect RDMA active (no host bounce)
# [T2] Mandate IB Adaptive Routing (AR) and SHARP — see Appendix G
NCCL_DEBUG=INFO NCCL_IB_HCA=mlx5_0,mlx5_1 ./build/all_reduce_perf -b 1G -e 8G -g 16
# Inspect NCCL_DEBUG output: "via NET/IB/GDRDMA" good; "via NET/Socket" = silent death.

# 4. AMD: rccl-tests with xGMI topology; different constraints — validate separately.
```
Record passing busbw numbers per topology class in the runbook; future incident triage compares against them.

## 5.5 Multi-node 405B-class serving

```bash
# vLLM multi-node: TP within node (NVLink), PP across nodes (verify script path in your pin)
# Node 0:
bash examples/online_serving/run_cluster.sh vllm/vllm-openai HEAD_IP --head
# Node 1..N: same with --worker; then on head:
vllm serve meta-llama/Llama-3.1-405B-Instruct \
  --tensor-parallel-size 8 \
  --pipeline-parallel-size 2 \
  --quantization fp8 \
  --kv-cache-dtype fp8 \
  --max-model-len 8192
```
Pipeline bubble ≈ (PP−1)/(microbatches+PP−1) **[Derived]** — keep PP small and microbatches high. MoE (DeepSeek-class): EP for experts; the all-to-all dispatch is the bottleneck — size IB/NVLink for it and monitor token imbalance across experts.

## 5.6 K8s control plane: KServe, Inference Extension, Ray Serve

```yaml
# KServe LLMInferenceService — CRD shape is version-sensitive; validate against your pin
apiVersion: serving.kserve.io/v1alpha1
kind: LLMInferenceService
metadata: { name: llama70b }
spec:
  model: { uri: "oci://registry.internal/models/llama-3.1-70b-fp8:SIGNED_TAG", name: llama-70b }
  replicas: 2
  router: { route: {}, gateway: {}, scheduler: {} }
```
Note the model URI: **private OCI registry with a signed tag** (§6.9) — not a runtime pull from the public internet.

**Gateway API Inference Extension / Endpoint Picker (EPP):** routes on a scoring function over live signals — KV-cache utilization, queue depth, LoRA-adapter locality, prefix-cache affinity — plus request **criticality** (Critical vs Sheddable; sheddable dropped under saturation). This is the production replacement for the round-robin logic in §1.3, and the enforcement point for §6.1 priorities. Behavior depends on the gateway/EPP implementation — verify against your pinned release. **[T2]** For dynamic prefix routing at scale, use a DHT/inverted index fed by the engine block manager — [Appendix G](appendices/G-scale-tier-requirements.md#t2-dht-prefix-routing).

**Ray Serve** (API evolves — verify): choose it for many-model fleets, fractional/heterogeneous GPU packing, and Python-level composition; choose KServe/llm-d for K8s-native CRDs + gateway integration; KubeRay gives both.

```python
from ray import serve
from ray.serve.llm import LLMConfig, build_openai_app
config = LLMConfig(
    model_loading_config={"model_id": "llama-70b",
                          "model_source": "meta-llama/Llama-3.1-70B-Instruct"},
    deployment_config={"autoscaling_config": {"min_replicas": 1, "max_replicas": 4,
                       "target_ongoing_requests": 32}},
    engine_kwargs={"tensor_parallel_size": 2, "kv_cache_dtype": "fp8",
                   "enable_prefix_caching": True},
)
app = build_openai_app({"llm_configs": [config]})
```

## 5.7 Disaggregated prefill/decode — with blast radius

**Adopt when (measured):** (a) TPOT SLO violations trace to prefill interference (long-prompt bursts spiking ITL despite chunked prefill), or (b) phase economics favor different SKUs (compute-dense prefill pool, bandwidth-dense decode pool).

```bash
# vLLM + NIXL KV transfer. NOTE: kv_role semantics are version-sensitive — in current
# releases the upper-level router (Dynamo/llm-d proxy) determines actual P/D roles;
# treat these flags as connector wiring, not role enforcement. Verify against your pin.
# Prefill pool:
vllm serve MODEL --kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_producer"}'
# Decode pool:
vllm serve MODEL --kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_consumer"}'
```

**Blast radius and fallback (design these before enabling):**
- **KV-transfer fabric partition** (NIXL/RDMA path down): router must fall back to **monolithic serving** on the decode pool (it has full weights — it can prefill, at degraded TTFT) rather than failing requests. Keep a monolithic fallback route configured and tested.
- **Prefill-pool loss**: same fallback; decode pool absorbs at reduced goodput → brownout ladder (§6.5) sheds load.
- **Decode-pool loss**: no fallback — this is your real availability domain; size N+1 there first.
- **Transfer latency** adds to TTFT: budget it (measure per-token KV transfer time over your fabric) and re-check the TTFT SLO before declaring victory.

Orchestrate with **NVIDIA Dynamo** or **llm-d**; prefix-cache-aware routing alone has produced multi-fold throughput and TTFT improvements in published case studies — figures are config-specific, so locate and verify the primary source before quoting any number (Appendix B worklist). **Mooncake** supplies cluster-wide KV pooling across DRAM/SSD/RDMA **[Cited: FAST '25]**.
