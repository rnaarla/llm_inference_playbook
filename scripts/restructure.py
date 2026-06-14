#!/usr/bin/env python3
"""Split monolith playbook into docs/ and apply organization transforms."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "llm-inference-platform-playbook.md"

SECTION_1_0 = '''## 1.0 Platform contract (overview)

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

'''

SCALE_TIER_LEGEND = '''
## 0.3a Scale tier legend

Requirements are tagged by fleet scale. Hyperscale detail lives in [appendices/G-scale-tier-requirements.md](appendices/G-scale-tier-requirements.md).

| Tag | Fleet scale | Examples |
|---|---|---|
| **[T0]** | Any production | Smoke tests, admission control, eval gates |
| **[T1]** | Multi-tenant shared platform (~100+ GPU) | Per-tenant fairness, brownout ladder, prefix-cache policy |
| **[T2]** | Hyperscale / strict tail-SLO (~1000+ GPU) | DHT KV routing, GDS offload, tiered XID handling, NUMA pinning |

'''

COMPANION_REGISTRY = '''
## 0.5 Companion document registry

Out-of-scope topics with explicit decision thresholds. Do not infer topology/engineering detail from this playbook when a companion is required.

| Companion | Read when | Inputs from core playbook | Interim guidance |
|---|---|---|---|
| **MoE / multi-node topology** (405B–671B) | EP needed (§5.1), fabric validated (§5.4), decision needs NVLink-domain planning or wide-EP routing | §3.5 parallelism table, §5.1 tree, §5.4 gates | §5.4–5.5 |
| **Embeddings / rerankers / multimodal** | Co-hosting non-chat workloads on the inference cluster | [Appendix C](appendices/C-cohosting-boundary.md) boundary | Appendix C |

If your decision requires deferred companion material, this playbook is **insufficient** for that decision alone.

'''

MAKEFILE_MAP = '''
### Makefile target → section map

| Make target | Primary sections | Owner |
|---|---|---|
| `smoke-vllm` | §1.2 | Platform |
| `bench-local` | §2.5, §5.3, §6.7 | Platform + Finance |
| `validate-promql` | §2.4 | SRE |
| `lint-k8s`, `deploy-kind` | §5.2 | Platform |
| `test-gateway`, `test-gateway-unit` | §1.3, §5.6, §6.1 | Platform |
| `test-cancel-stream` | §1.3, §6.2 | Platform |
| `test-tenant-quota` | §6.1 | Platform |
| `test-brownout` | §6.5 | SRE |
| `test-kv-pressure` | §6.2 | Platform |
| `test-gpu-xid-sim` | §5.2 | SRE |
| `test-rollback` | §6.10 | Platform + Quality |

'''

MAANG_REPLACEMENTS = [
    (
        r"At MAANG scale, \*\*strict HTTP/2 PING frames and TCP keepalives\*\* must be tuned at the Envoy layer to detect dead connections in < 5 seconds and forcibly sever upstream streams.",
        "**[T2]** Tune HTTP/2 PING frames and TCP keepalives at the Envoy layer to detect dead connections in <5s — see [Appendix G](appendices/G-scale-tier-requirements.md#t2-tcp-half-open-mitigation).",
    ),
    (
        r"\*\*MAANG-scale CUDA Graph Warning:\*\* Dynamic batching and sequence length variations cause CUDA graph memory pools to splinter\. To prevent VRAM OOMs and avoid catastrophic host-device sync overhead, you must mandate custom graph management \(e\.g\., heavily bucketized graph capturing and padding to power-of-2 sequence lengths\)\.",
        "**[T2]** CUDA graph pools splinter under dynamic batching — bucketize graph capture and pad to power-of-2 lengths ([Appendix G](appendices/G-scale-tier-requirements.md#t2-cuda-graph-bucketization)).",
    ),
    (
        r"\*\*MAANG Requirement — Phase Out the Python GIL:\*\* At heavy concurrency \(hundreds of in-flight requests\), Python's Global Interpreter Lock \(GIL\) within the scheduling/engine loop becomes the ceiling on QPS, severely thrashing `TPOT`\. MAANG-scale platforms mandate pure C\+\+ execution backends for their high-throughput standard tiers\. You must migrate completely to engines with C\+\+ core schedulers \(e\.g\., vLLM's newer V1 C\+\+ architecture, TensorRT-LLM\) explicitly avoiding Python-bound control loops on the critical path\.",
        "**[T2]** At hundreds of in-flight requests, Python GIL in the scheduler loop caps QPS — prefer C++ core schedulers (vLLM V1, TensorRT-LLM) for high-throughput tiers ([Appendix G](appendices/G-scale-tier-requirements.md#t2-cpp-scheduler-backends)).",
    ),
    (
        r"\*\*Node-Level Hardware Determinism:\*\* Before launching the engine, you must guarantee deterministic hardware availability\. An 8-GPU Tensor Parallel group is only as fast as its hottest, most restricted chip\. At MAANG scale, \*\*lock application clocks\*\* \(`nvidia-smi -lgc <target_freq>`\) to prevent dynamic thermal throttling from destabilizing `TPOT` across the fleet\.",
        "**[T1]** Lock application clocks (`nvidia-smi -lgc <target_freq>`) on TP groups to prevent thermal throttling from destabilizing TPOT. **[T2]** fleet-wide clock policy — [Appendix G](appendices/G-scale-tier-requirements.md#t2-gpu-clock-lock).",
    ),
    (
        r"# MAANG-scale NUMA Pinning: Launching kernels from the wrong CPU socket across the UPI/QPI link ruins tail latency\.\n# MUST bind the engine to the CPU socket matching the GPU's PCIe switch and NIC via numactl\.",
        "# [T2] NUMA pinning — bind to CPU socket matching GPU PCIe switch and NIC (see Appendix G)\n# numactl --cpunodebind=0 --membind=0",
    ),
    (
        r"\*\*MAANG-scale GDS Rule:\*\* Bouncing weights or disaggregated KV cache through the CPU is unacceptable at scale\. You must mandate \*\*GPU-Direct Storage \(GDS / `libcufile`\)\*\* to enable direct PCIe-to-GPU pathways for NVMe KV-cache swapping\.",
        "**[T2]** Mandate GPU-Direct Storage (GDS / `libcufile`) for NVMe KV offload — [Appendix G](appendices/G-scale-tier-requirements.md#t2-gds-kv-offload).",
    ),
    (
        r"At MAANG scale, cordoning nodes on \*any\* XID error is too blunt\. You must split XID watcher logic into tiers:",
        "**[T2]** Tier XID handling instead of cordoning on every error ([Appendix G](appendices/G-scale-tier-requirements.md#t2-tiered-xid-handling)):",
    ),
    (
        r"# MAANG-scale Micro-payload test \(Decode\): TP all-reduce payloads for single tokens are tiny\. Wait times here destroy TPOT\.",
        "# [T2] Micro-payload all-reduce test (decode TPOT) — see Appendix G",
    ),
    (
        r"#    MAANG-scale requirement: Mandate InfiniBand Adaptive Routing \(AR\) and SHARP in the fabric to prevent single-link drops \(Go-Back-N retransmits\) from stalling the pipeline \(straggler detection\)\.",
        "# [T2] Mandate IB Adaptive Routing (AR) and SHARP — see Appendix G",
    ),
    (
        r"\*\*MAANG-scale KV Routing:\*\* Polling an EPP via Gateway API is too slow for dynamic prefix states at scale\. Use an \*\*inverted index \(DHT like Redis\)\*\* populated directly by the engine's block manager\. The gateway must map request prompt sequences to physical node/GPU block addresses in real-time, achieving 90%\+ prefix hit rates\.",
        "**[T2]** For dynamic prefix routing at scale, use a DHT/inverted index fed by the engine block manager — [Appendix G](appendices/G-scale-tier-requirements.md#t2-dht-prefix-routing).",
    ),
    (
        r"Design points: \*\*MAANG-scale Adapter-Aware Batching\*\*: adapter \*\*hot-swap cost\*\* \(host→device copy on activation\) incurs immense PCIe bandwidth penalties\. Continuously paging 1GB LoRA weights in and out from host memory to GPU VRAM for interleaved requests tanks goodput\. You must mandate \*\*batching by LoRA ID\*\* \(automatically stalling a tenant's request for a few milliseconds to accrue a batch for that specific adapter\) to amortize the PCIe transfer cost\. Additionally:",
        "Design points: **[T2]** batch by LoRA ID to amortize adapter hot-swap PCIe cost ([Appendix G](appendices/G-scale-tier-requirements.md#t2-lora-batch-by-id)). Additionally:",
    ),
]

ARTIFACT_REPLACEMENTS = [
    (
        r"```yaml\n# versions\.lock — one entry per validated profile\.[\s\S]*?```",
        "**Artifact:** [`playbook/versions.lock`](../playbook/versions.lock) — fill every field before adoption; empty = build failure.",
    ),
    (
        r"```python\n# gateway\.py — LEARNING ARTIFACT\.[\s\S]*?```",
        "> **⚠️ LEARNING ARTIFACT — DO NOT DEPLOY.** See [`playbook/ci/gateway.py`](../playbook/ci/gateway.py). Unit tests: `make -C playbook test-gateway-unit`.",
    ),
    (
        r"```python\n# capacity\.py — PLANNING HELPER\.[\s\S]*?```",
        "**Artifact:** [`playbook/calculators/capacity.py`](../playbook/calculators/capacity.py)\n\n```bash\npython playbook/calculators/capacity.py meta-llama/Llama-3.1-70B-Instruct \\\n  --dtype bf16 --kv-dtype fp8 --ctx 16384 --concurrency 32 --headroom 0.20\n```",
    ),
    (
        r"```yaml\n# prometheus\.yml[\s\S]*?```",
        "**Artifact:** [`playbook/dashboards/prometheus.yml`](../playbook/dashboards/prometheus.yml)",
    ),
    (
        r"\*\*Canonical benchmark report schema\*\* — every `bench-local` run emits this;[\s\S]*?```yaml\nbenchmark_report:[\s\S]*?```",
        "**Canonical benchmark report schema** — every `bench-local` run emits this:\n\n**Artifact:** [`playbook/benchmarks/benchmark_report.schema.yaml`](../playbook/benchmarks/benchmark_report.schema.yaml)",
    ),
    (
        r"```yaml\n# --- deployment\.yaml ---[\s\S]*?ports: \[\{ port: 8000 \}\]\n```",
        "**Artifact:** [`playbook/helm/`](../playbook/helm/) — `deployment.yaml`, `service.yaml`, `pvc.yaml`, `pdb.yaml`, `networkpolicy.yaml`, `keda-scaledobject.yaml`",
    ),
    (
        r"```yaml\napiVersion: keda\.sh/v1alpha1[\s\S]*?threshold: \"6\"\n```",
        "KEDA ScaledObject: [`playbook/helm/keda-scaledobject.yaml`](../playbook/helm/keda-scaledobject.yaml)",
    ),
]

STAGE6_SUBPARTS = {
    "## 6.1 ": "### 6.A Traffic & fairness\n\n#### 6.1 ",
    "## 6.2 ": "#### 6.2 ",
    "## 6.4 ": "#### 6.4 ",
    "## 6.12 ": "#### 6.12 ",
    "## 6.5 ": "### 6.B Resilience & DR\n\n#### 6.5 ",
    "## 6.6 ": "#### 6.6 ",
    "## 6.11 ": "#### 6.11 ",
    "## 6.7 ": "### 6.C Economics & capacity\n\n#### 6.7 ",
    "## 6.3 ": "### 6.E Workload extensions\n\n#### 6.3 ",
    "## 6.8 ": "### 6.D Governance & release\n\n#### 6.8 ",
    "## 6.9 ": "#### 6.9 ",
    "## 6.10 ": "#### 6.10 ",
}


def extract_between(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    if end is None:
        return text[i:]
    j = text.index(end, i + len(start))
    return text[i:j]


def transform(body: str) -> str:
    for pat, repl in MAANG_REPLACEMENTS:
        body = re.sub(pat, repl, body)
    for pat, repl in ARTIFACT_REPLACEMENTS:
        body = re.sub(pat, repl, body, count=1)
    return body


def main() -> None:
    raw = SRC.read_text()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "appendices").mkdir(exist_ok=True)

    # --- README hub (§0 + navigation) ---
    sec0 = extract_between(raw, "# 0. HOW TO READ", "---\n\n# STAGE 1")
    sec0 = sec0.replace("## 0.3 Claim-confidence legend", SCALE_TIER_LEGEND + "## 0.3 Claim-confidence legend")
    sec0 = sec0.replace(
        "## 0.4 Scope and assumptions",
        "## 0.4 Scope and assumptions",
    )
    # Trim MoE deferral from 0.4 — moved to companion registry
    sec0 = re.sub(
        r"- \*\*The MoE / extreme multi-node boundary, stated precisely\.\*\*[^\n]+\n",
        "",
        sec0,
    )
    sec0 = sec0.rstrip() + COMPANION_REGISTRY + MAKEFILE_MAP

    readme = f"""# The LLM Inference Platform Engineering Playbook — v5

*Document teaches; [`playbook/`](../playbook/) proves. Every artifact must pass the profile contract (§0.1) against a filled [`versions.lock`](../playbook/versions.lock) before use.*

## Start here — persona paths

| Persona | Path |
|---|---|
| **Day 1 — first token** | §0 → [01-first-token](docs/01-first-token-and-gateway.md) §1.2 → `make -C playbook smoke-vllm` |
| **Capacity planning** | §0.4 traffic model → [02-measurement](docs/02-measurement-and-benchmarks.md) §2.1, §2.5 → [04-scale](docs/04-scale-and-kubernetes.md) §5.3 → [05-platform](docs/05-platform-engineering.md) §6.7 |
| **Production hardening** | [01](docs/01-first-token-and-gateway.md) §1.0, §1.3 → [04](docs/04-scale-and-kubernetes.md) §5.2 → [05](docs/05-platform-engineering.md) §6.A–6.B |
| **Performance tuning** | [02](docs/02-measurement-and-benchmarks.md) §2.2–2.3 → [03](docs/03-optimization-decisions.md) → re-bench §2.5 |
| **Release / upgrade** | §0.1 profile → [05](docs/05-platform-engineering.md) §6.10 → [Appendix D](docs/appendices/D-evidence-ledger.md) |

## Decision index

| Decision | Section | Artifact | Make target |
|---|---|---|---|
| Engine selection | [§3.6](docs/02-measurement-and-benchmarks.md#36-engine-selection-matrix) | — | `bench-local` |
| TP vs PP vs DP | [§5.1](docs/04-scale-and-kubernetes.md#51-parallelism-decision-tree) | [capacity.py](../playbook/calculators/capacity.py) | — |
| Quantization promotion | [§4.2](docs/03-optimization-decisions.md#42-quantization--kernel-coverage-pipeline-and-eval-gates) | — | `test-rollback` |
| Speculative decoding | [§4.3](docs/03-optimization-decisions.md#43-speculative-decoding--decision-contract) | — | `bench-local` |
| Disaggregation | [§5.7](docs/04-scale-and-kubernetes.md#57-disaggregated-prefilldecode--with-blast-radius) | helm | `bench-local` |
| Admission / shedding | [§6.1](docs/05-platform-engineering.md#61-admission-control--priority-classes-owner-gateway--scheduler) | [gateway.py](../playbook/ci/gateway.py) | `test-tenant-quota` |
| Brownout response | [§6.5](docs/05-platform-engineering.md#65-degradation-modes--brownout-ladder-owner-sre--scheduler) | runbooks | `test-brownout` |
| Fabric validation | [§5.4](docs/04-scale-and-kubernetes.md#54-fabric--topology-validation-gate-dont-hope) | nccl-tests | — |
| Model promotion | [§6.10](docs/05-platform-engineering.md#610-eval-gates--release-engineering-owner-platform--quality) | ci/ | `test-rollback` |

## Table of contents

| Doc | Contents |
|---|---|
| [01-first-token-and-gateway.md](docs/01-first-token-and-gateway.md) | §1.0 platform contract, lifecycle, first token, gateway |
| [02-measurement-and-benchmarks.md](docs/02-measurement-and-benchmarks.md) | §2 measurement, §3.5–3.6 engine selection |
| [03-optimization-decisions.md](docs/03-optimization-decisions.md) | §4 optimization decision contracts |
| [04-scale-and-kubernetes.md](docs/04-scale-and-kubernetes.md) | §5 K8s, fabric, disaggregation |
| [05-platform-engineering.md](docs/05-platform-engineering.md) | §6 platform (6.A–6.E) |
| [F-engine-internals.md](docs/appendices/F-engine-internals.md) | §3.1–3.4 deep dive |
| [G-scale-tier-requirements.md](docs/appendices/G-scale-tier-requirements.md) | [T2] hyperscale requirements |
| [B-claims-register.md](docs/appendices/B-claims-register.md) | Claims worklist |
| [C-cohosting-boundary.md](docs/appendices/C-cohosting-boundary.md) | Embeddings / multimodal boundary |
| [D-evidence-ledger.md](docs/appendices/D-evidence-ledger.md) | Validation ledger |
| [E-caveats.md](docs/appendices/E-caveats.md) | Caveats |

---

{sec0}
"""
    (ROOT / "README.md").write_text(readme)

    # --- Doc 01: Stage 1 + §1.0 ---
    s1 = extract_between(raw, "# STAGE 1", "---\n\n# STAGE 2")
    s1 = s1.replace("# STAGE 1 — Mental Model, First Token, and the Gateway\n\n", "# 1. Mental Model, First Token, and the Gateway\n\n")
    s1 = s1.replace("## 1.1 The request-to-token lifecycle", SECTION_1_0 + "## 1.1 The request-to-token lifecycle")
    s1 = transform(s1)
    (docs / "01-first-token-and-gateway.md").write_text(s1.strip() + "\n")

    # --- Doc 02: Stage 2 + 3.5, 3.6 ---
    s2 = extract_between(raw, "# STAGE 2", "---\n\n# STAGE 3")
    s3part = extract_between(raw, "## 3.5 Parallelism", "---\n\n# STAGE 4")
    s2 = s2.replace("# STAGE 2 — Measurement Before Tuning: Capacity Arithmetic, Profiling, Benchmarking\n\n", "# 2. Measurement Before Tuning\n\n")
    s2 = transform(s2)
    s2 = s2.rstrip() + "\n\n---\n\n# 3. Engine Selection (core track)\n\n" + transform("## " + s3part)
    (docs / "02-measurement-and-benchmarks.md").write_text(s2.strip() + "\n")

    # --- Doc 03: Stage 4 ---
    s4 = extract_between(raw, "# STAGE 4", "---\n\n# STAGE 5")
    s4 = s4.replace("# STAGE 4 — Optimization (Decision Contracts, Not Tips)\n\n", "# 4. Optimization (Decision Contracts, Not Tips)\n\n")
    s4 = transform(s4)
    (docs / "03-optimization-decisions.md").write_text(s4.strip() + "\n")

    # --- Doc 05: Stage 5 ---
    s5 = extract_between(raw, "# STAGE 5", "---\n\n# STAGE 6")
    s5 = s5.replace("# STAGE 5 — Scale: Kubernetes, Sizing Math, Fabric, Disaggregation\n\n", "# 5. Scale: Kubernetes, Sizing Math, Fabric, Disaggregation\n\n")
    s5 = transform(s5)
    (docs / "04-scale-and-kubernetes.md").write_text(s5.strip() + "\n")

    # --- Doc 06: Stage 6 with sub-parts ---
    s6 = extract_between(raw, "# STAGE 6", "---\n\n# APPENDIX A")
    s6 = s6.replace("# STAGE 6 — PLATFORM ENGINEERING (the layer the engine cannot give you)\n\n", "# 6. Platform Engineering\n\n")
    for old, new in STAGE6_SUBPARTS.items():
        s6 = s6.replace(old, new)
    s6 = transform(s6)
    (docs / "05-platform-engineering.md").write_text(s6.strip() + "\n")

    # --- Appendix F: Stage 3 deep dive ---
    s3deep = extract_between(raw, "# STAGE 3 — Engine Internals (and Building One)", "## 3.5 Parallelism")
    s3deep = s3deep.replace("# STAGE 3 — Engine Internals (and Building One)\n\n", "# Appendix F — Engine Internals (Deep Dive)\n\n")
    s3deep = transform(s3deep)
    (docs / "appendices" / "F-engine-internals.md").write_text(s3deep.strip() + "\n")

    # --- Appendix G: extracted MAANG/T2 content ---
    appendix_g = """# Appendix G — Scale Tier [T2] Requirements

Hyperscale requirements extracted from the core playbook. Adopt when tagged **[T2]** in the body.

## T2: TCP half-open mitigation

Client disconnects are often silent (mobile clients dropping without FIN/RST). If the gateway does not notice, the engine bleeds decode capacity. Tune **HTTP/2 PING frames and TCP keepalives** at the Envoy layer to detect dead connections in <5s and forcibly sever upstream streams.

## T2: CUDA graph bucketization

Dynamic batching and sequence-length variation cause CUDA graph memory pools to splinter. Mandate custom graph management: heavily bucketized graph capturing and padding to power-of-2 sequence lengths to prevent VRAM OOMs and host-device sync overhead.

## T2: C++ scheduler backends

At hundreds of in-flight requests, Python GIL in the scheduling loop caps QPS and thrashes TPOT. Mandate C++ core schedulers (vLLM V1, TensorRT-LLM); avoid Python-bound control loops on the critical path.

## T2: GPU clock lock

An 8-GPU TP group is only as fast as its hottest chip. Lock application clocks (`nvidia-smi -lgc <target_freq>`) fleet-wide to prevent thermal throttling from destabilizing TPOT.

## T2: NUMA pinning

Launching kernels from the wrong CPU socket across UPI/QPI ruins tail latency. Bind the engine to the CPU socket matching the GPU PCIe switch and NIC:

```bash
numactl --cpunodebind=0 --membind=0 vllm serve ...
```

## T2: GDS KV offload

Bouncing disaggregated KV cache through the CPU is unacceptable at scale. Mandate **GPU-Direct Storage (GDS / libcufile)** for direct PCIe-to-GPU NVMe KV-cache swapping.

## T2: Tiered XID handling

Cordoning nodes on any XID error is too blunt:

1. **Recoverable** (XID 13, 31): restart engine container.
2. **Fatal** (XID 79, 94): cordon, taint, drain.

## T2: Fabric micro-payload and IB AR/SHARP

- Run NCCL all-reduce with `-b 8 -e 2M` for decode-sized TP payloads; enforce `NCCL_ALGO=Tree`, `NCCL_PROTO=Simple`.
- Mandate InfiniBand Adaptive Routing (AR) and SHARP to prevent single-link drops from stalling PP/EP pipelines.

## T2: DHT prefix routing

Polling EPP via Gateway API is too slow for dynamic prefix states. Use an **inverted index (DHT like Redis)** populated by the engine block manager so the gateway maps prompt sequences to node/GPU block addresses in real time (target 90%+ prefix hit rates).

## T2: LoRA batch-by-ID

Adapter hot-swap (host→device copy) incurs PCIe penalties. Mandate **batching by LoRA ID** — stall requests briefly to accrue a batch for the same adapter before activation.
"""
    (docs / "appendices" / "G-scale-tier-requirements.md").write_text(appendix_g)

    # --- Appendices B, C, D, E (from monolith) ---
    for letter, title in [
        ("B", "Claims Register"),
        ("C", "Co-Hosting Boundary"),
        ("D", "Evidence Ledger"),
        ("E", "Caveats"),
    ]:
        if letter == "B":
            start = "# APPENDIX B — Claims Register"
            end = "# APPENDIX C —"
        elif letter == "C":
            start = "# APPENDIX C — Co-Hosting Boundary"
            end = "# APPENDIX D —"
        elif letter == "D":
            start = "# APPENDIX D — Canonical Evidence Bundle"
            end = "# APPENDIX E —"
        else:
            start = "# APPENDIX E — Caveats"
            end = None
        content = extract_between(raw, start, end)
        content = content.replace(f"# APPENDIX {letter} —", f"# Appendix {letter} —")
        content = transform(content)
        # Update artifact paths in D
        content = content.replace("gateway (§1.3, extracted verbatim)", "gateway (§1.3, playbook/ci/gateway.py)")
        content = content.replace("capacity helper (§2.1)", "capacity helper (playbook/calculators/capacity.py)")
        (docs / "appendices" / f"{letter}-{'claims-register' if letter=='B' else 'cohosting-boundary' if letter=='C' else 'evidence-ledger' if letter=='D' else 'caveats'}.md").write_text(content.strip() + "\n")

    # --- Redirect monolith ---
    redirect = """# Moved — LLM Inference Platform Playbook v5

This playbook has been reorganized. **Start at [README.md](README.md).**

- Prose and decisions: [`docs/`](docs/)
- Executable artifacts: [`playbook/`](playbook/)
"""
    SRC.write_text(redirect)
    print("Restructure complete.")


if __name__ == "__main__":
    main()
