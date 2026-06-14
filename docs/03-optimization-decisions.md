# 4. Optimization (Decision Contracts, Not Tips)

Every optimization below carries a **decision contract**: precondition (measured), expected metric movement, cost/failure mode, rollback. Apply nothing without its precondition.

## 4.0 The decision framework

| Measured bottleneck | Symptoms | Apply (in order) |
|---|---|---|
| **Memory-bound** (decode) | DRAM_ACTIVE high, TENSOR low | FP8 KV cache → weight quant (FP8 → AWQ/GPTQ INT4) → larger batch → prefix caching → KV offload |
| **Compute-bound** (prefill) | TENSOR/SM high | Chunked-prefill tuning → FP8 compute → CUDA graphs/torch.compile → disaggregation |
| **Latency-bound** (low batch) | SLO miss at low QPS | Speculative decoding (verify α) → higher-bandwidth GPU → smaller/quantized model |
| **Queue-bound** | waiting ≫ running, TPOT stable | Admission control first (§6.1), then replicas + autoscaling (§5.3) |

## 4.1 Production vLLM config template

**[T1]** Lock application clocks (`nvidia-smi -lgc <target_freq>`) on TP groups to prevent thermal throttling from destabilizing TPOT. **[T2]** fleet-wide clock policy — [Appendix G](appendices/G-scale-tier-requirements.md#t2-gpu-clock-lock).

```bash
# Comments above flags — backslash must be the last character on a continued line.
# TP across an NVLink pair:
#   --tensor-parallel-size 2
# FP8 KV cache: ~2x KV capacity → larger feasible batch (precondition: Hopper/Ada+, eval-gated)
#   --kv-cache-dtype fp8
# Cap context to the product's real need — the single biggest KV lever:
#   --max-model-len 16384
# Chunked-prefill token budget: raise = throughput, lower = better ITL:
#   --max-num-batched-tokens 8192
# [T2] NUMA pinning — bind to CPU socket matching GPU PCIe switch and NIC (see Appendix G)
# numactl --cpunodebind=0 --membind=0
numactl --cpunodebind=0 --membind=0 vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --quantization fp8 \
  --kv-cache-dtype fp8 \
  --max-model-len 16384 \
  --max-num-seqs 256 \
  --max-num-batched-tokens 8192 \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --gpu-memory-utilization 0.90 \
  --port 8000
```

## 4.2 Quantization — kernel coverage, pipeline, and eval gates

**FP8 capability is not one thing [corrected]:**

| Arch | SM | FP8 status |
|---|---|---|
| Ada (L40S, RTX 4090) | 8.9 | FP8 instructions present; **kernel coverage in vLLM/TRT-LLM is narrower than Hopper** — validate your exact model/kernel path |
| Hopper (H100/H200) | 9.0 | Full FP8 inference path; the recommended starting point |
| Blackwell (B200/GB200) | 10.0 | FP8 + FP4 (NVFP4); mixed precision (FP4 weights, FP8/BF16 attention) is the production pattern **[Vendor]** |

Checkpoint format is a second compatibility axis (compressed-tensors vs fbgemm-fp8 vs TRT-LLM engines) — match format to engine.

```python
# FP8 W8A8 with llm-compressor (vLLM-native)
from llmcompressor.transformers import oneshot
from llmcompressor.modifiers.quantization import QuantizationModifier
oneshot(model="meta-llama/Llama-3.1-70B-Instruct",
        recipe=QuantizationModifier(targets="Linear", scheme="FP8_DYNAMIC",
                                    ignore=["lm_head"]),
        output_dir="Llama-3.1-70B-FP8")
# then: vllm serve ./Llama-3.1-70B-FP8
```

| Method | Scheme | Use when | Watch for |
|---|---|---|---|
| **FP8 dynamic** | W8A8 float | Hopper/Blackwell default; usually safe | format/engine match |
| **SmoothQuant** | W8A8 INT | Broad HW throughput | activation outliers |
| **AWQ / GPTQ** | W4A16 | VRAM-constrained decode | **needs domain eval** — benchmark-invisible regressions are common |
| **NVFP4** | 4-bit float | Blackwell | mixed precision pattern; **[Vendor]** accuracy claims |
| **GGUF Q4_K_M** | ~4.5 bpw | llama.cpp local | quality cliff is Q3→Q4 |

**Eval gate with teeth (a benchmark-clean quant can still crater tool-calling):**
```bash
# Necessary baseline:
lm_eval --model vllm --model_args pretrained=./Llama-3.1-70B-FP8 \
  --tasks gsm8k,mmlu,ifeval --batch_size auto
# Sufficient gate adds: long-context (RULER), tool/function-calling (BFCL),
# your domain corpus, and PRODUCTION TRAFFIC REPLAY (sampled, anonymized).
# Promotion rule: block if any tracked metric regresses beyond the error budget (§6.10).
```

## 4.3 Speculative decoding — decision contract

**Precondition:** latency-bound at low/medium batch; measured acceptance rate **α ≥ ~0.6** on *your* traffic. **Failure mode:** at α < 0.5 or at high batch, verification overhead reduces throughput — and production batch sizes fluctuate, so a config that wins at 3 a.m. can lose at peak. **Mitigation:** isolate speculative decoding to dedicated low-latency pools, or toggle on load signals, rather than enabling fleet-wide. **Rollback:** remove the flag; no state.

```bash
# EAGLE-3 in vLLM (schema is version-sensitive — verify against your pin)
vllm serve meta-llama/Llama-3.1-70B-Instruct --tensor-parallel-size 2 \
  --speculative-config '{"method":"eagle3","model":"yuhuili/EAGLE3-LLaMA3.1-Instruct-70B","num_speculative_tokens":4}'

# n-gram / prompt-lookup: zero extra model — strong for RAG/summarization where output echoes input
vllm serve MODEL \
  --speculative-config '{"method":"ngram","num_speculative_tokens":4,"prompt_lookup_max":4}'
```
EAGLE-3 paper reports ~3–6.5× over autoregressive at low batch **[Cited: Li et al., EAGLE-3 — paper config; production gains are typically lower and workload-dependent [Directional]]**.

## 4.4 KV-cache management ladder
1. `--max-model-len` capped to real product need (cheapest win)
2. `--kv-cache-dtype fp8` (eval-gated)
3. Prefix caching (vLLM) / RadixAttention (SGLang default) — then **split TTFT SLOs** (§2.5) and decide the multi-tenant cache policy (§6.2: shared prefixes are a chargeback and isolation question, not just a perf feature)
4. CPU/NVMe offload + cross-instance reuse: **LMCache** (connector names/roles are version-sensitive). **[T2]** Mandate GPU-Direct Storage (GDS / `libcufile`) for NVMe KV offload — [Appendix G](appendices/G-scale-tier-requirements.md#t2-gds-kv-offload).
5. Cluster KV pooling: **Mooncake** / **NIXL** (§5.7). For cross-node or SSD offload, you must use heavily pipelined, asynchronous CUDA streams (e.g. overlapping `cudaMemcpyAsync` with the next prefill chunk) so transfer times do not block the active generation stream.

## 4.5 Hardware decision table (inputs first, labels removed)

Choosing hardware requires: model + dtype, context P95/P99, output length, TTFT/TPOT SLO, QPS, batchability, cache-reuse rate, interconnect available, region, and price. The table gives physical envelopes — **[Derived from public specs]** — not verdicts:

| GPU | Mem / BW | Physical envelope |
|---|---|---|
| RTX 4090 / 5090 | 24–32 GB / ~1 TB/s | dev, ≤13B, local INT4; FP8 on Ada = limited kernels |
| L40S | 48 GB / 0.86 TB/s | ≤34B INT4/FP8, cost-efficient inference |
| A100 80GB | 80 GB / 2 TB/s | mature fleets; 70B BF16 = 2× |
| H100 80GB | 80 GB / 3.35 TB/s | 70B FP8 single-GPU is *tight* (short ctx, low concurrency); 70B BF16 = 2× |
| H200 | 141 GB / 4.8 TB/s | 70B FP8 single-GPU comfortable; 70B BF16 single-GPU = weights-only, **not** production; highest Hopper decode bandwidth |
| B200 | 192 GB / ~8 TB/s | Blackwell FP4/FP8; verify per-SKU capacity |
| GB200 NVL72 | rack-scale, NVLink5 | frontier MoE; aggregate figures are **[Vendor]** |
| MI300X | 192 GB / 5.3 TB/s | largest single-GPU HBM class; software maturity gap is real but moving fast — **re-benchmark on current ROCm/vLLM before deciding [Directional]** |
| MI325X | 256 GB / 6.0 TB/s | same caveat; split from MI300X deliberately |

**Buying rule:** memory-bound serving buys **bandwidth + capacity**; prefill-heavy buys FP8/FP4 compute. Fit check via the §2.1 calculator with headroom. TP only within an NVLink/xGMI domain.
