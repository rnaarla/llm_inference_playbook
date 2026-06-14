# 1. Mental Model, First Token, and the Gateway

## 1.0 Platform contract (overview)

The engine executes requests; the **platform** decides which requests reach it. Read this before §1.1 — full mechanics live in [05-platform-engineering.md](05-platform-engineering.md).

| Layer | Owner | Owns |
|---|---|---|
| **Gateway** | Platform / edge | Authn/z, alias translation, admission, rate limits, cancellation propagation, metering |
| **Scheduler** | Platform | Priority classes, weighted fair queueing, reserve accounting, brownout triggers |
| **Runtime** | Engine | Continuous batching, KV cache, preemption (last line of defense) |
| **Platform** | Infra | Placement, autoscaling, model cache, DR, cost model |
| **SRE** | Ops | SLOs, alerts, incident runbooks, game days |
| **Security** | Security | Provenance, audit, mTLS policy, guardrails policy |

**Priority classes** (propagate from gateway through EPP to scheduler):

| Class | Admission under load | Reserve |
|---|---|---|
| **Critical** | Admitted until Critical reserve exhausted | ≥30% of goodput knee |
| **Standard** | Queued with bounded deadline; shed only at higher rungs | 50–60% |
| **Sheddable** | First rejected (429 + `Retry-After`) when fleet past knee | ≤10–20%, never reserved |

**Brownout ladder** — named degradation stages keyed to `kv_cache_usage_perc`; detail in §6.5. Every rung is a feature flag exercised in game days.

**Gateway hub** — three roles, three sections:

| Role | Section | Artifact |
|---|---|---|
| Contract (what it must do) | §1.3 | [gateway.py](../playbook/ci/gateway.py) (learning artifact) |
| K8s integration (EPP, KServe) | §5.6 | [helm/](../playbook/helm/) |
| Admission & quotas | §6.1 | runbooks + `test-tenant-quota` |

## 1.1 The request-to-token lifecycle

```
HTTP ingress (gateway/LB) → authn/authz → ADMISSION CONTROL (token budget, priority) 
  → tokenization (text → token IDs)
  → scheduling/queueing (waiting queue, priority class)
  → PREFILL  (all prompt tokens, one parallel pass, builds KV cache)   ← compute-bound
  → DECODE   (1 token per forward pass, reads weights + full KV cache) ← memory-bandwidth-bound
  → detokenization → streaming (SSE/WS) or JSON response
```

Note admission control appears *before* the engine. A platform that lets requests queue inside the engine until KV exhaustion triggers preemption storms has already failed; the gateway must reject (429 + `Retry-After`) what the fleet cannot serve within SLO. This is the single most common production incident pattern on shared LLM platforms (§6.1).

| Metric | Definition | Driven by | Typical chat SLO |
|---|---|---|---|
| **TTFT** | arrival → first token | queue wait + prefill | P95 < 500 ms (set separately for cache hit/miss) |
| **TPOT / ITL** | time between output tokens | memory BW, decode batch | < 50 ms (≈20 tok/s perceived) |
| **E2E** | TTFT + (out_tokens−1)×TPOT | both | per use case |
| **Throughput** | tok/s, req/s | batch, saturation | — |
| **Goodput** | req/s meeting **all** SLOs | the production metric | capacity is sized from this |

## 1.2 First token in <15 minutes — three paths

```bash
# PATH A — vLLM (production-aligned, OpenAI-compatible). Pin the version.
pip install "vllm==${VLLM_VERSION}"
vllm serve microsoft/Phi-3-mini-4k-instruct \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --port 8000

curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "microsoft/Phi-3-mini-4k-instruct",
  "messages": [{"role":"user","content":"Explain KV cache in one sentence."}],
  "max_tokens": 64, "stream": true}'
```

```bash
# PATH B — Ollama / llama.cpp (GGUF, CPU+GPU offload)
curl -fsSL https://ollama.com/install.sh | sh && ollama run tinyllama
# llama.cpp directly; -ngl = number of layers offloaded to GPU
./llama-server -m tinyllama-1.1b-chat.Q4_K_M.gguf -ngl 99 --port 8080
```

```bash
# PATH C — SGLang (benchmark head-to-head later, §5)
pip install "sglang[all]==${SGLANG_VERSION}"
python -m sglang.launch_server --model-path microsoft/Phi-3-mini-4k-instruct --port 30000
```

(HF TGI is in maintenance mode per Hugging Face's documentation **[Cited: HF docs, verify announcement date before quoting]** — use vLLM or SGLang for new builds.)

**Smoke test** — [`playbook/benchmarks/smoke_test.sh`](../playbook/benchmarks/smoke_test.sh) (also `make -C playbook smoke-vllm`):
```bash
# Expect: HTTP 200, non-empty choices[0], TTFT < 5s on a warm engine
bash playbook/benchmarks/smoke_test.sh
```

## 1.3 The inference gateway

> **⚠️ LEARNING ARTIFACT — DO NOT DEPLOY.** See [`playbook/ci/gateway.py`](../playbook/ci/gateway.py) — teaches alias translation, admission caps, and streaming relay. Single-process only; no circuit breaking or cancellation propagation. For production use **Envoy AI Gateway**, **kgateway + Gateway API Inference Extension** (§5.6), or **LiteLLM Proxy**. Unit tests: `make -C playbook test-gateway-unit`.

**What a production gateway must own** (the platform contract — each item maps to §6):
authn/authz; model-alias translation; **admission control** (per-tenant token budgets, max input/output/context, priority classes); rate limiting with 429 + `Retry-After`; retries with budget + circuit breaking; streaming **cancellation propagation** (client disconnect must cancel the engine request, or you pay for abandoned generations); request size limits; usage metering per tenant; audit logging keyed by `X-Request-ID`; idempotency keys for retried non-streaming calls.

| Production gateway | Use when |
|---|---|
| **Envoy AI Gateway** | Token-based rate limiting, multi-tenant quotas, upstream auth |
| **kgateway / Gateway API Inference Extension** | K8s-native, KV-cache- and LoRA-aware endpoint picking (§5.6) |
| **LiteLLM Proxy** | Multi-provider routing, budgets, virtual keys |
| **NGINX / HAProxy** | Plain L7 when nothing model-aware is needed |

**Streaming decision:** SSE for chat (unidirectional, OpenAI standard, proxy-friendly); WebSockets only for duplex (voice, interruptible agents); non-streaming for batch/internal calls. Hardening: disable proxy buffering (`proxy_buffering off`), idle timeout > max generation time, propagate `X-Request-ID`, enforce response-size and stream-duration ceilings.
**TCP Half-Open Mitigation:** Client disconnects are often silent (e.g., a mobile client dropping off the network without sending a FIN/RST packet). If the gateway does not notice, the engine bleeds decode capacity generating tokens for a vanished client. **[T2]** Tune HTTP/2 PING frames and TCP keepalives at the Envoy layer to detect dead connections in <5s — see [Appendix G](appendices/G-scale-tier-requirements.md#t2-tcp-half-open-mitigation).
