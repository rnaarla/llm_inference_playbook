# 6. Platform Engineering

The engine will do what it is told. The platform's job is to stop it being told to do something stupid. Each subsection below is a mechanism with an owner, a failure mode, and a runbook hook — the **owner-primitive model**: *Gateway* owns auth/routing/quotas; *Scheduler* owns admission/fairness; *Runtime* owns batching/KV; *Platform* owns placement/autoscaling; *SRE* owns SLOs/runbooks; *Security* owns provenance/audit.

### 6.A Traffic & fairness

#### 6.1 Admission control & priority classes (owner: gateway + scheduler)

**Mechanism — pre-engine checks, in order:**
1. **Authn → tenant resolution → budget lookup** (tenant TPM/RPM, concurrent-request cap).
2. **Token budget check**: `count_tokens(input) + max_tokens ≤ tenant_request_budget` AND `≤ model context policy`. Reject oversize with 400 (policy) — never let the engine discover it.
3. **Priority class assignment**: map tenant/route → {Critical, Standard, Sheddable}; propagate to the EPP criticality field.
4. **Fleet-state gate**: if fleet is past its goodput knee (queue depth or KV pressure signal), **shed Sheddable with 429 + `Retry-After`**, queue Standard with a bounded deadline, always admit Critical until its reserved capacity is exhausted. **Retry discipline:** clients (and any retrying gateway tier) must honor `Retry-After` with **jittered exponential backoff** — synchronized retries at the Retry-After instant re-create the spike exactly as the brownout ladder steps down, turning one overload into an oscillation. Publish the backoff requirement in the API contract and reject pathological retry patterns at the rate limiter.
5. **Cancellation**: client disconnect propagates to engine abort — abandoned generations are pure waste.

**Worked queue interaction:** a 128K-context Sheddable request arriving at `kv_cache_usage_perc = 0.88` is the canonical preemption-storm trigger. Admission rejects it (predicted KV ≈ 40 GiB > remaining budget) before it evicts twenty 4K-context Standard requests. This single check eliminates the most common shared-platform incident class.

**Failure mode:** budget service down → fail-static to cached budgets with conservative defaults; never fail-open on Critical capacity.

#### 6.2 Tenant isolation & fairness (owner: scheduler + platform)

- **Isolation tiers**: dedicated replicas for Critical tenants (hard isolation) → shared pools with weighted fairness for Standard → best-effort for Sheddable.
- **Queue discipline, concretely**: shared pools run **weighted fair queueing over token-cost, not request count** — each tenant has a weight; the scheduler dequeues the tenant with the lowest `served_token_cost / weight`, where a request's cost = `input_tokens + E[output_tokens]` (estimate from tenant history, reconcile on completion). Request-count fairness is gameable by long-context tenants; token-cost fairness is not.

  *Worked example — two tenants, one bursty.* Tenant A (weight 2, chat: ~500 in / ~300 out) and Tenant B (weight 1, RAG: ~8,000 in / ~400 out). Estimated cost per request: A ≈ 800, B ≈ 8,400. Both start at debt 0. B bursts 10 requests; A sends 4.
  - Dequeue order is by `debt/weight`: B's first request runs (0/1 = 0, tie broken arbitrarily), B's debt → 8,400/1 = 8,400. Now every A request (0/2 = 0) runs before B's second — A's four requests complete (debt 3,200/2 = 1,600) before B runs again. Net effect: **one B request admitted per ~10.5 A-requests-worth of tokens**, exactly the 2:1 weight ratio over token cost — B's burst cannot starve A, and A's high request *count* cannot starve B either.
  - **Prediction error**: suppose B's request actually generates 4,000 output tokens, not 400 (agentic blow-up). At completion, reconciliation adds the 3,600-token delta to B's debt — B's *next* dequeue is pushed further out, so the error self-corrects within one request. The dangerous direction is *under*-estimation at **admission** (reserve accounting admitted a request 10× its predicted size): bound it with per-request `max_tokens` caps (§6.1) so the worst-case error is capped, and track `|actual − predicted| / predicted` per tenant — persistently high values mean that tenant needs a tighter cap or its own pool.
  - Debt decays (e.g., halved per minute of inactivity) so a tenant idle for an hour doesn't return with infinite priority.
- **Starvation bound (aging)**: no admitted request waits more than `max_queue_wait` (e.g., 2× its class's TTFT SLO) — a request exceeding it gets a priority boost regardless of tenant weight, or a 503 with `Retry-After` if the deadline is unmeetable. Bounded-deadline queues turn "stuck behind a heavy tenant" from an incident into a defined behavior.
- **Reserve partitioning, with numbers**: a shared pool is split as **Critical reserve ≥ 30%** of knee capacity (admission for Critical succeeds even at full Standard load), **Standard 50–60%**, **Sheddable ≤ 10–20%** (first shed, never reserved). Reserves are admission-time accounting against the goodput knee (§2.5), not GPU partitions — the engine still batches everything together.
- **Token-budget accounting under streaming cancellation**: charge tenants for tokens **generated**, not tokens delivered — a client that disconnects mid-stream still consumed decode capacity until cancellation propagated. Reconcile on engine-side completion records, not gateway-side delivery counts; the delta between the two is your cancellation-waste metric (high values mean slow cancellation propagation, §1.3).
- **Multi-turn accounting**: with prefix caching, turn N re-sends the conversation but pays prefill only for the uncached suffix. Bill cached input tokens at a discounted rate (they cost VRAM residency, not compute) and meter per-**session** token budgets alongside per-request ones — per-request budgets alone let a tenant accumulate unbounded session context.
- **Per-tenant KV reservation**: cap any tenant's share of `kv_cache_usage_perc` (engine-level where supported; otherwise enforced via per-tenant concurrency × max-context at admission).
- **Prefix-cache namespacing**: shared system prompts create both an isolation question (tenant A's hot prefix evicting tenant B's) and a **chargeback question**. Policy options: namespace caches per tenant (clean, less reuse) or share with metered attribution (cache-hit tokens billed at the discounted rate to the *consumer*, VRAM carry attributed pro-rata to hit counts).
- **Noisy-neighbor detection & routing**: classify requests by predicted cost (context length percentile); route heavy contexts (e.g., >32K) to a dedicated **heavy pool**. Signals: per-tenant preemption count, per-tenant TTFT-miss spike, fairness-debt (`served_token_cost/weight` divergence across tenants).

#### 6.4 Structured output & agentic serving (owner: runtime + gateway)

Grammar-constrained decoding (xGrammar, Outlines, llguidance; SGLang jump-forward) enforces JSON-schema/regex validity at the sampler. Platform implications: **schema compilation is CPU work** — cache compiled grammars keyed by schema hash, or high-QPS structured traffic shifts the bottleneck host-ward; jump-forward multi-token emission improves latency on deterministic spans; failure modes to test: truncation under `max_tokens` mid-object (invalid JSON — gateway must detect and surface, not silently pass), EOS-bias distortions on tail fields. Agentic loops multiply request count per task — admission budgets (§6.1) must count *tokens per task*, not per request, to stop runaway agents.

#### 6.12 Safety & guardrail serving path (owner: gateway + safety)

Mechanism: insert guardrails in the serving path, not just policy docs. Input moderation and prompt-injection screening run at the gateway **after** auth/admission (§6.1) and **before** engine dispatch, and output moderation runs on the generated stream per the lifecycle/contract in §1.1 and §1.3. Guardrail components can use dedicated safety models and frameworks (examples: Llama Guard, ShieldGemma, NeMo Guardrails) for input/output policy checks, including PII detection/redaction. §6.8 remains the logging/audit-policy layer, while this section is the online enforcement layer.

Failure mode: guardrails are an extra forward pass in the critical path, so they spend TTFT/E2E budget (§1.1, §2.5). Mitigate with a small shared guardrail pool, batching, or overlapping input screening with tokenization/queueing so part of the safety compute is hidden under work already on the critical path; however, engine dispatch remains blocked until input screening resolves, and late rejects must trigger immediate cancellation/cleanup. For streaming output moderation, inspect rolling token/chunk windows during generation (not only at full completion) so first token delivery is preserved; the trade-off is earlier delivery versus a late-stream violation that still requires termination.

Policy decision (per-route, explicit, and reviewed like §6.1 fail-static admission): safety-required routes fail-closed on guardrail timeout/outage (safe refusal). Lower-risk routes may fail-open with mandatory logging/escalation, and this asymmetry is explicit — when a safety-required route fails open, classify it as a safety incident, not only availability debt.

Streaming cutoff semantics: if output moderation flags mid-stream, gateway emits a terminal `policy_violation` refusal/error event with a consistent 4xx policy status mapping, stops downstream bytes, and triggers cancellation on the engine path (§1.3/§6.1 abort path) to avoid unnecessary decoding compute.

Validation target/runbook hook: dashboard per-route block rate, guardrail latency P95, and fail-open/fail-closed counters; add `test-guardrail-down` (§0.2) that hard-fails the guardrail dependency and asserts safety-required routes fail-closed while non-critical routes fail-open with audit logs, and eval-gate guardrail model updates alongside other model changes (§6.10).

### 6.B Resilience & DR

#### 6.5 Degradation modes & brownout ladder (owner: SRE + scheduler)

Define behavior *before* saturation. Ladder keyed to fleet KV pressure and goodput-knee proximity:

| Trigger | Action (cumulative) |
|---|---|
| `kv_cache_usage_perc > 0.85` sustained | Stop admitting Sheddable (429 + Retry-After); alert |
| `> 0.90` | Cap `max_tokens` on Standard (e.g., →512); disable speculative decoding (frees draft VRAM + verification compute) |
| `> 0.95` | Route Standard overflow to **fallback smaller model** (e.g., 70B→8B with response header noting degraded tier); Critical only on primary |
| `> 0.97` or preemption storm | Shed Standard; Critical-only mode; page |
| Recovery | Step down ladder with hysteresis (re-admit one tier per stable interval — no flapping) |

Every rung is a feature flag, exercised in game days — an untested brownout mode is a second incident.

#### 6.6 DR, multi-region, and capacity contingency (owner: platform)

- **Model artifact replication**: every served model + adapter mirrored to a per-region private OCI registry; cold-start path never crosses regions or touches public internet.
- **Warm-spare strategy**: per-region N+1 warm; cross-region failover pool with weights pre-pulled (warm = minutes; cold 70B pull = tens of minutes — your RTO is dominated by weight movement).
- **RTO/RPO**: inference is stateless (RPO ≈ 0 — conversation state lives upstream); RTO = failover detection + warm-pool admission. Set and test a number.
- **GPU-supply contingency**: correlated failures are real (driver regression across a node group, region capacity exhaustion, NCCL deadlock taking out a TP×PP group). Plan: alternate-SKU fallback configs (the same model pre-validated on A100/MI300X pools), smaller-model fallback (§6.5 ladder), and a documented request-shedding order.
- **Spot/on-demand mix**: spot for Sheddable/batch pools with graceful-drain handlers on interrupt; never for Critical decode pools. **Drain timers must fit the interruption notice**: cloud spot notices are short and hard (AWS ~120s) — the pod's `terminationGracePeriodSeconds`, preStop sleep, and longest permitted stream on a spot node must all sum inside that window (§5.2), which usually means spot pools enforce shorter `max_tokens`/stream-duration caps than on-demand pools.

#### 6.11 Incident response (owner: SRE)

Severity matrix (SEV1 = Critical-tenant SLO breach or fleet-wide goodput collapse; SEV2 = brownout rung ≥2 engaged; SEV3 = single-replica/degraded redundancy). Paging policy tied to the alert set (§2.4). Postmortem template links: triggering signal → runbook used → ladder rungs engaged → capacity model delta → action items with owners. The runbook table below is the entry point:

| Signal | Diagnosis | Action |
|---|---|---|
| TTFT ↑, TPOT stable | queue/capacity | admission first (shed Sheddable), then scale out |
| TPOT ↑ | decode pressure: long ctx, KV saturation, prefill interference | lower `max-num-batched-tokens`; FP8 KV; evaluate disaggregation |
| Preemptions / KV evictions / recompute events > 0 | KV exhaustion | brownout ladder §6.5; reduce `max-model-len`/`max-num-seqs`. (vLLM V1 note: `num_requests_swapped`/`cpu_cache_usage_perc` are legacy swap-era metrics — rely on preemption/recompute counters unless your pinned profile still exposes swap) |
| OOM on spike | over-committed budget | recompute §2.1 with headroom; lower `gpu-memory-utilization` |
| Throughput collapse post-deploy | quant/spec-decode regression | auto-rollback; check α and eval deltas |
| XID / ECC errors | GPU hardware fault | Evaluate XID Tier: Restart container (13, 31) OR Cordon + drain (79, 94); `dcgmi diag -r 2`; compare busbw to §5.4 baseline |
| NCCL hang in TP/PP group | fabric or peer failure | whole parallel group is the failure domain — restart group, fail over to spare; check rail health |

### 6.C Economics & capacity

#### 6.7 Capacity & cost engineering (owner: platform + finance)

**The model [Derived] — report three metrics, never one.** Prompt-heavy RAG and output-heavy chat have opposite economics; a single blended number hides which one you have:
```
$/1M INPUT  tokens at SLO  = 1e6 × hourly_platform_cost / (3600 × SLO_input_tok_s)
$/1M OUTPUT tokens at SLO  = 1e6 × hourly_platform_cost / (3600 × SLO_output_tok_s)
$/1M TOTAL  tokens at SLO  = 1e6 × hourly_platform_cost / (3600 × SLO_total_tok_s)

where total_hourly_platform_cost = Σ GPU_hourly × replicas
                                  + router/CPU + storage + egress + observability
and the goodput rates decompose by: prompt/output mix, prefix-cache hit rate,
speculative acceptance rate, admission rejection rate.
```
Allocation note: input tokens consume prefill compute; output tokens consume decode bandwidth; cached input tokens consume neither (VRAM residency only). A cost model that bills them identically will mis-price RAG by an order of magnitude.

**Worked example [Derived — illustrative prices, substitute yours; output-token framing]:**
- 4 replicas × 2×H100 @ $2.50/GPU-hr = $20/hr; +$2/hr platform overhead → **$22/hr**.
- Measured SLO goodput at the knee: 3,000 **output** tok/s fleet-wide (alongside, say, 12,000 input tok/s at a 4:1 prompt:output mix → also report $0.51/1M input, $0.41/1M total).
- → $22 / (3600 × 3000) × 10⁶ ≈ **$2.04 per 1M output tokens at SLO**.
- **FP8 + prefix caching scenario**: FP8 halves GPU count for the same goodput (2 replicas × 2 GPU = $12/hr) and a 40% prefix-hit rate lifts effective goodput ~1.5× → $12 / (3600×4500) ×10⁶ ≈ **$0.74/1M output** — a 2.8× reduction from two software changes. This is the shape of argument that defends a capacity plan to finance.
- **Utilization cliff**: running at 60% of knee for latency safety raises $/1M by 1.67×; pushing to 95% saves money until one burst triggers the brownout ladder. Price the headroom explicitly.

**The hidden-cost ledger (the line items that surprise finance later):**
- **Critical reserve idle cost**: the §6.2 reserve (≥30% of knee for Critical) is capacity you pay for whether or not Critical traffic arrives — it is an availability premium, priced as such, not "waste."
- **Disaggregation network cost — with magnitude, parameterized by KV dtype**: cross-zone KV transfer is metered egress in cloud, and the numbers are not small. `KV_transfer_GiB = context_tokens × KV_bytes_per_token(kv_dtype) / 2³⁰`. For Llama-3-70B at 10K context **[Derived, §2.1]**: BF16 KV (0.31 MiB/token) ≈ **3.0 GiB**; FP8 KV (0.155 MiB/token) ≈ **1.5 GiB** — at a typical ~$0.01/GB cross-AZ rate, ~$0.03 vs ~$0.015 of pure network tax per request, at scale often exceeding the marginal GPU cost of the prefill itself. (FP8 KV halves the egress line as well as the VRAM line — another reason it's the §4.4 default.) Keep prefill and decode pools **zone-local** (same-AZ transfer is typically free) and treat any cross-zone disaggregation design as having failed this line item until proven otherwise.
- **Regional duplication**: every active region multiplies (replicas × model variants × adapters); DR warm spares (§6.6) are additional.
- **Cache-hit drift**: the $0.74 figure above assumes a 40% hit rate *that decays* as tenant mix and prompt templates evolve — monitor hit rate as a cost SLI and re-forecast quarterly.
- **Tokenizer variance**: tokens-per-character differs by tokenizer and language; cross-model cost comparisons must normalize or they're comparing different units.
- **Failed canaries and rollbacks**: each blocked promotion (§6.10) consumed eval-suite GPU time and canary capacity — budget a release-engineering overhead line (~2–5% of fleet in active-development phases).
- Add: reserved-vs-on-demand blend (commit the base, burst on demand) and the break-even point at which a smaller fallback model serves Standard traffic cheaper than scaling the large one.

### 6.D Governance & release

#### 6.8 Audit, compliance, and prompt-data policy (owner: security)

Request/response **audit schema**: timestamp, `X-Request-ID`, tenant, model+revision, adapter, token counts, latency metrics, admission decision, criticality, completion status — *content logging is a separate, explicit policy decision* (PII redaction pipeline, retention clock, encryption at rest, access controls). Map controls to your regimes (SOC 2, HIPAA, EU AI Act transparency duties); keep the model inventory (§6.9) as the system-of-record auditors see first.

**Transport security / zero-trust**: gateway↔engine traffic is internal but not exempt — regulated environments require **mTLS** on it, typically via service mesh (Istio/Linkerd, sidecar or ambient) since inference engines don't terminate TLS well themselves. The §5.2 NetworkPolicy is the floor (who may connect); mesh mTLS adds identity and encryption (proof of who connected). Budget the mesh's latency overhead into the TTFT SLO — measure it, don't assume it's free.

#### 6.9 Model governance & provenance (owner: security + platform)

Pipeline: **private OCI registry** (ORAS/registry-native model artifacts) → **sign** (sigstore/cosign) → **scan** (pickle/code-exec scanning for non-safetensors; CVE scan on serving images) → **model card** with provenance, license, eval results stored alongside the artifact → **promotion pipeline** dev→staging→prod gated on §6.10 evals. Runtime pulls **only** signed tags from the internal registry; admission of an unsigned artifact is a build-time failure, not a runtime discovery.

Extend this to **load-time verification**: an init container/sidecar runs `cosign verify` and digest-pin checks before `vllm serve` starts, so a tampered/swapped local checkpoint is rejected at startup. Digest pinning here means comparing the pulled artifact's content digest (for example, SHA256) to the approved digest recorded in release metadata. Keep approved digests in a trusted control-plane source (for example, signed promotion metadata or a locked deployment config) that the init path can read but not mutate. If the digest source or verification path is unavailable, the pod fails readiness (fail closed) and does not serve unverified weights.

Generate and retain an SBOM for the serving image (and ideally the model artifact bundle) so CVE response can answer "which deployments contain component X" without a fleet scrape. Attach SLSA provenance attestations to model artifacts and verify those attestations in the §6.10 promotion gate so promoted artifacts are traceable to their build inputs.

Validation hook (§0.2 style): `test-unsigned-checkpoint` injects a bad/missing signature and asserts readiness stays false and no traffic is admitted.

#### 6.10 Eval gates & release engineering (owner: platform + quality)

CI artifact, not a one-liner: every model/quant/adapter/engine-version change runs the gate — lm-eval baseline (GSM8K, MMLU, IFEval) + long-context (RULER) + tool-calling (BFCL) + domain corpus + **sampled production-traffic replay** — and **blocks promotion** on regression beyond the per-metric error budget. Canary rollout 5%→50%→100% gated on **goodput and quality signals** (structured-output validity rate, tool-call success rate), with automated rollback. A quantized canary whose BFCL drops 5 points rolls back without a human in the loop.

### 6.E Workload extensions

#### 6.3 LoRA / multi-adapter serving (owner: platform)

Running a distinct 70B deployment per fine-tune is financially ruinous; multiplex adapters on shared base-model pools:
```bash
# vLLM multi-LoRA (flags version-sensitive)
vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --enable-lora \
  --max-loras 8 \
  --max-lora-rank 64 \
  --lora-modules tenant-a=/adapters/tenant-a tenant-b=/adapters/tenant-b
```
Design points: **[T2]** batch by LoRA ID to amortize adapter hot-swap PCIe cost ([Appendix G](appendices/G-scale-tier-requirements.md#t2-lora-batch-by-id)). Additionally: keep hot adapters resident, LRU-evict cold; manage **rank-mix fragmentation** (multiplexing rank-16 and rank-64 in one engine fragments the adapter VRAM pool and disrupts continuous-batching efficiency — standardize ranks per pool); enforce **adapter-aware routing** (Inference Extension LoRA locality: route tenant-A to replicas already holding the adapter); ensure per-tenant adapter isolation; and eval-gate adapters like models (§6.10).
