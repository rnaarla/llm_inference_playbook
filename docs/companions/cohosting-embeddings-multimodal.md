# Embeddings, Rerankers, and Multimodal Co-Hosting Companion

Extends [Appendix C](../appendices/C-cohosting-boundary.md) to actionable design.

---

## 1. When to read

Co-hosting non-chat workloads on the LLM inference cluster, or when RAG pipeline latency budgets require dedicated encoder/reranker pools.

---

## 2. Embeddings and rerankers

| Property | Implication |
|---|---|
| No decode phase | Size on QPS + batch latency, not TTFT/TPOT knee |
| No KV cache | Do not co-locate on LLM **decode** GPUs |
| Upstream of chat | P99 adds directly to user TTFT budget |

**Design:**

- Dedicated pools on L4/MIG/fractional GPU slices  
- Gateway: request-rate quotas > token budgets  
- Same admission layer (§6.1) with per-route class **Sheddable** default  

---

## 3. Multimodal (vision-language, audio)

| Break | Fix |
|---|---|
| Encoder cost ∝ media size | Admission counts media units + projected image tokens |
| KV math uses text tokens only | Capacity script must use post-projection token count |
| Large payloads | Gateway body limits; audit policy for media retention (§6.8) |

**Eval gate:** multimodal eval suite pinned per profile — higher version volatility than text-only.

---

## 4. Capacity isolation

Never share brownout ladder between LLM decode fleet and embedding burst pools — separate `kv_cache_usage_perc` signals or independent clusters.

---

## Evidence

Separate benchmark reports per workload class under `playbook/benchmarks/runs/`.
