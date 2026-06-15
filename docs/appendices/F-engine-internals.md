# Appendix F — Engine Internals (Deep Dive)

## 3.1 Minimal engine from scratch

```python
# The decode loop at the heart of every engine
out = model(input_ids, use_cache=True)                 # PREFILL: one parallel pass
past = out.past_key_values
tok_id = out.logits[:, -1, :].argmax(-1, keepdim=True)
for _ in range(max_new_tokens):                        # DECODE: one token per pass
    out = model(tok_id, past_key_values=past, use_cache=True)
    past = out.past_key_values                         # KV cache grows by 1 token
    tok_id = sample(out.logits[:, -1, :])              # greedy / top-p / temperature
    if tok_id.item() == eos: break
```

Two leaps to a real engine: **continuous batching** (re-evaluate the batch every iteration — admit/retire at token granularity) and **paged KV** (no contiguous max-length pre-allocation).

```python
# Iteration-level scheduler skeleton (the Orca/vLLM idea)
while True:
    finished = [s for s in running if s.done]; running -= set(finished)
    free_blocks += release(finished)
    # Admission inside the engine is the LAST line of defense; the gateway (§6.1)
    # should have already enforced budgets. Engine-side: admit only if KV fits.
    while waiting and fits(waiting[0], free_blocks):
        running.add(waiting.pop(0))
    step_batch = build_batch(running)        # mixed prefill+decode (chunked prefill)
    logits = model.forward(step_batch)       # ONE fused forward for everyone
    append_tokens(running, sample(logits))
    # Under KV pressure: preempt lowest-priority sequences (swap to CPU or recompute) —
    # preemption is the engine's overload behavior; visible as vllm:num_preemptions.
```
Build this against a 1B model and you understand 80% of vLLM's scheduler — including why preemption policy and admission order are *platform* decisions, not engine trivia.

## 3.2 vLLM internals
- **PagedAttention** **[Cited: Kwon et al., SOSP '23, arXiv:2309.06180]**: KV in fixed blocks (16 tokens default); per-sequence block tables map logical→physical (OS-paging analogy); copy-on-write prefix sharing; internal fragmentation bounded to the last partial block. Paper reports 2–4× throughput vs FasterTransformer/Orca at equal latency (paper config).
- **Continuous batching**: waiting/running/swapped queues; token-granular admission; preemption by recompute or swap when KV exhausts.
- **V1 engine** (default in 2025-era releases — verify your pin): zero-copy DMA, pinned host memory, restructured scheduler, independent prefill/decode handling.
- **Chunked prefill** (Sarathi lineage): long prefills split into `--max-num-batched-tokens` chunks, piggybacked with decodes → protects ITL from long-prompt interference.
- Prefix caching, piecewise CUDA graphs, torch.compile, FlashAttention/FlashInfer kernel stack. **[T2]** CUDA graph pools splinter under dynamic batching — bucketize graph capture and pad to power-of-2 lengths ([Appendix G](G-scale-tier-requirements.md#t2-cuda-graph-bucketization)).

## 3.3 SGLang internals
- **RadixAttention** **[Cited: SGLang paper/LMSYS report, Jan 2024]**: KV cache in a radix tree keyed by token sequence; matched prefixes cost zero prefill; **LRU eviction** over tree nodes under memory pressure — note that under severe pressure, eviction of hot shared prefixes converts cache-hit traffic to cache-miss TTFT, which is why hit-rate monitoring matters (§2.5). Up to 6.4× on prefix-heavy workloads vs then-current vLLM (paper config; vLLM has since added prefix caching — re-benchmark, **[Directional]**).
- **Jump-forward decoding** + xGrammar: constrained decoding via compressed FSM emits multi-token deterministic spans (~2× latency win on structured output, **[Vendor: SGLang materials — resolve per Appendix B]**). Note grammar compilation and FSM evaluation add **CPU-side cost** — structured output shifts bottlenecks host-ward at high QPS (§6.4).
- **Overlap scheduler**: CPU scheduling overlapped with GPU compute (vendor-reported utilization gains, **[Vendor]**).
- **sgl-router**: routes on radix-tree cache state fleet-wide.

## 3.4 FlashAttention — what it actually does
Never materializes the N×N attention matrix in HBM; tiles Q/K/V into SRAM, computes **online softmax** incrementally. FA2 = better warp-level parallelism. **FA3** (Hopper): producer/consumer **warp specialization** with TMA + FP8 — paper reports ~75% H100 FP16 utilization (~740 TFLOPS) and ~1.2 PFLOPS FP8, vs ~35% for FA2 **[Cited: Shah et al., arXiv:2407.08608 — benchmark-specific]**. **Kernel-path selection is version-sensitive**, the same way CRDs and flags are: which attention backend an engine picks depends on engine release, FlashAttention/FlashInfer build, GPU arch, head dim, dtype, and feature flags (e.g., FP8 KV or sliding window can route to a different kernel). Confirm the active backend per profile (vLLM logs the selected attention backend at startup) rather than assuming FA3.
