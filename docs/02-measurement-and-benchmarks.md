# 2. Measurement Before Tuning

## 2.1 Capacity-planning arithmetic (heuristic with stated error bars — not "exact")

These formulas are planning estimates. Real memory depends on architecture (GQA/MQA/MLA, sliding-window layers), paged block slack, CUDA-graph capture, allocator fragmentation, activation peaks, LoRA adapters, draft models, and runtime implementation. **Apply a headroom factor and validate on your stack.** Use GiB consistently (1 GiB = 2³⁰ bytes); marketing "GB" (10⁹) inflates capacity ~7%.

```
WEIGHTS:     params × bytes/param
             70B × 2 (BF16) ≈ 140 GB ≈ 130 GiB | × 1 (FP8) ≈ 70 GB | × ~0.56 (Q4_K_M ≈ 4.5 bpw) ≈ 39 GB
KV/token:    2 × n_layers × n_kv_heads × head_dim × bytes_per_elem
KV total:    Σ over running requests (seq_len_i × KV/token)   ← not a clean batch×len product in practice
BUDGET:      weights + KV + activations + headroom
HEADROOM:    15–25% of total (allocator, CUDA graphs, sampler buffers, fragmentation, spikes)
```

**Worked: Llama-3-70B** (80 layers, 8 KV heads GQA, head_dim 128, BF16) **[Derived]**:
KV/token = 2×80×8×128×2 = 327,680 B ≈ **0.31 MiB/token**. 8 concurrent requests × 4,096 ctx ≈ **10 GiB**. The same model with MHA (64 KV heads) would need ~80 GiB — the **8× GQA payoff** that makes dense-70B serving tractable. One 128K-context request alone ≈ 40 GiB KV.

**The 70B fit question, corrected:**
- BF16 weights ≈ 140 GB. An H200 (141 GB) technically *holds the weights* — and nothing else. No KV cache of useful size, no headroom, no CUDA graphs. **70B BF16 production serving requires ≥2×80 GB GPUs, or quantization.** Single-H200 BF16 is a constrained-experiment configuration, not a production pattern.
- 70B **FP8** (~70 GB) on one H100-80GB is *tight* (≤10 GB for KV + headroom → short contexts, low concurrency); one H200 leaves ~60 GB for KV and is a genuinely comfortable single-GPU production fit. **[Derived]**
- PagedAttention bounds *internal* fragmentation to roughly the last partially-filled block per sequence (low single-digit % **[Cited: vLLM/PagedAttention paper, SOSP '23]**), but block slack, padding, and dynamic batching still mean memory is never perfectly packed — hence the headroom factor.

**Capacity planning helper** — a *planning aid, not a source of truth*. Parameter count follows a source-of-truth ladder: (1) **safetensors index metadata** (actual checkpoint tensor sizes — correct for MoE, tied embeddings, gated MLPs, MLA, multimodal heads); (2) **hub model_info parameter count**; (3) architecture heuristic — *last resort only*, wrong for non-standard layouts. Production workflows inspect **local** artifacts (the checkpoint you'll actually serve, from your registry §6.9); the network fetch below is for exploration only — and fails with 401 on gated repos (most production models), which is itself the argument for the local path.

**Artifact:** [`playbook/calculators/capacity.py`](../playbook/calculators/capacity.py)

```bash
python playbook/calculators/capacity.py meta-llama/Llama-3.1-70B-Instruct \
  --dtype bf16 --kv-dtype fp8 --ctx 16384 --concurrency 32 --headroom 0.20
```

## 2.2 Roofline and bottleneck classification

**[Derived from public specs]** H100 SXM5: ~989 TFLOPS dense FP16 / 3.35 TB/s HBM3 → ridge ≈ **295 FLOPs/byte FP16** (~591 FP8 at 1,979 TFLOPS). Prefill ≈ 200–400 FLOPs/byte → compute-bound, 90–95% util. Decode at low batch ≈ 1–2 FLOPs/byte — two orders of magnitude below the ridge → memory-bound, 20–40% util. **Decode throughput is set by HBM bandwidth, not TFLOPS.** Attention is memory-bound even in prefill — the motivation for FlashAttention (§3.4).

## 2.3 Profiling toolchain

```bash
# Nsight Systems — system timeline (kernels, memcpy, NVTX, CPU)
nsys profile --trace=cuda,cudnn,cublas,osrt,nvtx \
  --pytorch=functions-trace --cudabacktrace=all --delay=60 -o llm_profile python infer.py
nsys stats llm_profile.nsys-rep
```

```bash
# Nsight Compute — per-kernel roofline & bound classification
# GPU Speed-Of-Light: high SM%+low DRAM% = compute-bound; inverse = memory-bound
ncu --set roofline --kernel-name regex:attn --launch-count 10 -o kern python infer.py
```

```python
# PyTorch Profiler
from torch.profiler import profile, ProfilerActivity
with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
             profile_memory=True, with_stack=True) as prof:
    model.generate(**inputs)
prof.export_chrome_trace("trace.json")   # Perfetto / chrome://tracing
```

```bash
# Live GPU telemetry
nvidia-smi dmon -s pucvmet -d 2
# DCGM profiling fields (verify IDs against your DCGM release):
# 1001 GR_ENGINE_ACTIVE | 1002 SM_ACTIVE | 1004 TENSOR_ACTIVE | 1005 DRAM_ACTIVE (mem BW util)
dcgmi dmon -e 1001,1002,1004,1005 -d 1000
```

**Bottleneck classifier:** DRAM_ACTIVE high + TENSOR low → memory-bound (decode) → §4 memory recipes. TENSOR/SM high → compute-bound (prefill) → compute recipes. Both low + queue growing → host/scheduler/network bound — fix CPU-side code before touching the GPU.

## 2.4 Observability stack

**Artifact:** [`playbook/dashboards/prometheus.yml`](../playbook/dashboards/prometheus.yml)

```bash
# DCGM exporter (verify chart URL against current NVIDIA docs)
helm repo add gpu-helm-charts https://nvidia.github.io/dcgm-exporter/helm-charts
helm install dcgm gpu-helm-charts/dcgm-exporter -n monitoring
```

**PromQL panels (names are profile-pinned; examples reflect current vLLM V1 docs — V1 renamed the per-token histogram to `inter_token_latency`):**
```promql
histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m]))
histogram_quantile(0.95, rate(vllm:inter_token_latency_seconds_bucket[5m]))
vllm:num_requests_running    vllm:num_requests_waiting    vllm:kv_cache_usage_perc
rate(vllm:prefix_cache_hits[5m]) / rate(vllm:prefix_cache_queries[5m])
DCGM_FI_PROF_DRAM_ACTIVE
```

**Per-tenant slices (requires gateway-stamped labels from §6.1):** add `tenant` (and optionally `priority_class`) on request metrics at ingress, then propagate through queue/shed/fairness paths; keep label cardinality bounded (cap tenant set for dashboards and bucket long-tail into `other`) to keep observability overhead manageable.
```promql
# Engine/gateway metric names here are profile-pinned examples; adapt to your deployed stack.
# Per-tenant TTFT P95 (requires tenant label stamped at the gateway, §6.1)
# Example engine metric name (`vllm:*`) shown with the required histogram **bucket** suffix (`*_bucket`); replace only the metric prefix/name for your engine.
histogram_quantile(0.95, sum by (tenant, le) (rate(vllm:time_to_first_token_seconds_bucket[5m])))
# Per-tenant queue pressure and shed rate (gateway metric names are examples; adapt to your deployed gateway)
sum by (tenant) (rate(gateway_requests_total{outcome="queued"}[5m]))
sum by (tenant) (rate(gateway_requests_total{outcome="shed_429"}[5m]))
# Fairness-debt divergence across tenants (ties to §6.2 weighted fair queueing)
max(tenant_fairness_debt) - min(tenant_fairness_debt)
```
Tie these panels to §6.2 fairness signals and §6.7 token-cost attribution so per-tenant latency and chargeback stop hiding in fleet averages; as above, metric names are profile-pinned and must be adapted to your pinned gateway/engine profile.

**Alert starter set:** TTFT P95 > SLO 5m; `waiting > 2×running` 5m (queue-bound); `kv_cache_usage_perc > 0.92` (preemption imminent — triggers brownout ladder §6.5); `DCGM_FI_DEV_XID_ERRORS > 0` (GPU fault — drain node, §5.2 probes). Add OpenTelemetry tracing gateway→engine to attribute latency between queue wait and prefill.

## 2.5 Benchmarking methodology (protocol, not vibes)

**Protocol — fixed acceptance criteria:**
1. **Capture your distribution**: prompt-length P50/P95/P99, output-length distribution, cache-hit potential, structured-output fraction, from production traces where they exist. Synthetic-vs-production mismatch is the #1 source of wrong capacity numbers.
2. **Warmup 10 min** (CUDA graph capture, torch.compile, prefix-cache population) — never measure cold.
3. **Steady state ≥30 min** per concurrency level.
4. **Sweep request rate** until SLO goodput peaks then declines — that knee is the per-replica capacity number feeding autoscaling (§5.3) and cost (§6.7).
5. **Report**: TTFT P50/P95/P99 (split cache-hit vs cache-miss), TPOT P50/P95/P99, E2E, queue wait, preemption count, KV usage, DRAM/TENSOR active, $/1M tokens at SLO.
6. **Re-run on every engine upgrade and quantization change**; gate promotion on no-regression (§6.10).

```bash
# vLLM built-in (verify subcommand exists in your pinned release)
vllm bench serve --backend openai-chat --base-url http://localhost:8000 \
  --model microsoft/Phi-3-mini-4k-instruct \
  --dataset-name sharegpt --dataset-path ShareGPT_V3_unfiltered.json \
  --num-prompts 1000 --request-rate 8 --max-concurrency 64

# genai-perf / AIPerf — goodput with SLO constraints
genai-perf profile -m phi3 --service-kind openai --endpoint-type chat \
  --synthetic-input-tokens-mean 512 --output-tokens-mean 256 \
  --concurrency 32 --goodput time_to_first_token:500 inter_token_latency:50
```

**Prefix caching ⇒ split SLOs.** A cache hit skips prefill (TTFT ≈ queue + first decode step); a miss pays full prefill. One blended TTFT SLO is unenforceable — define **TTFT-hit** and **TTFT-miss** SLOs and monitor the hit rate as a first-class signal (it is also a cost driver, §6.7).

**Canonical benchmark report schema** — every `bench-local` run emits this:

**Artifact:** [`playbook/benchmarks/benchmark_report.schema.yaml`](../playbook/benchmarks/benchmark_report.schema.yaml)

---

# 3. Engine Selection (core track)

## ## 3.5 Parallelism primitives — the communication table (corrected)

Megatron-style TP on a standard transformer block requires communication after **both** the attention output projection **and** the MLP down projection:

| Primitive | What is sharded | Communication per layer (forward) | Link sensitivity |
|---|---|---|---|
| **TP** (tensor) | QKV/MLP weight matrices (column→row pattern) | **2 × all-reduce** (after attn out-proj, after MLP down-proj) **[Cited: Megatron-LM, Shoeybi et al.]** | Extreme — every layer, every step. NVLink-class only |
| **TP + SP** (sequence parallel) | + activations along sequence in norm/dropout regions | all-reduce decomposed into **reduce-scatter + all-gather** (same volume, less activation memory) | Same as TP |
| **PP** (pipeline) | Layer ranges across stages | point-to-point activation transfer per microbatch; bubble ≈ (PP−1)/(microbatches+PP−1) **[Derived]** | Tolerant — works across nodes/Ethernet |
| **DP** (replicas) | Nothing (full copies) | none at inference | None — the default throughput scaler |
| **EP** (expert, MoE) | Experts across GPUs | **all-to-all** token dispatch + combine per MoE layer — the real MoE bottleneck | High — wants NVLink/IB; bandwidth × token imbalance |

**Interconnect reality [Derived from specs]:** H100 NVLink4 ≈ 900 GB/s/GPU bidirectional; PCIe Gen5 x16 ≈ 128 GB/s — a 7× gap. TP across PCIe-only GPUs usually loses to PP or a bigger single GPU. RCCL/xGMI on AMD has different topology constraints — validate per §5.4.

## 3.6 Engine selection matrix

| Engine | Core tech | Reach for it when |
|---|---|---|
| **vLLM** | PagedAttention, V1 scheduler | Default: broad models, OpenAI API, LoRA, quant formats |
| **SGLang** | RadixAttention, jump-forward, overlap sched | Agents, multi-turn, few-shot, structured output |
| **TensorRT-LLM** | AOT compiled engines, in-flight batching, FP8/FP4 | Peak NVIDIA throughput; you accept compile + lock-in |
| **llama.cpp / Ollama** | GGUF, CPU/GPU layer offload | Local, edge, air-gapped, consumer GPUs |
| **NVIDIA Dynamo** | Disaggregated P/D, KV-aware routing, multi-node | Cluster-scale over vLLM/SGLang/TRT-LLM backends |
| **LMDeploy / DeepSpeed-MII** | TurboMind; Mooncake PD integration | Alternative runtimes, specific fits |

**[T2]** At hundreds of in-flight requests, Python GIL in the scheduler loop caps QPS — prefer C++ core schedulers (vLLM V1, TensorRT-LLM) for high-throughput tiers ([Appendix G](appendices/G-scale-tier-requirements.md#t2-cpp-scheduler-backends)).
