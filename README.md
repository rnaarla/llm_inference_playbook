# The LLM Inference Platform Engineering Playbook — v5

*Document teaches; [`playbook/`](playbook/) proves. Every artifact must pass the profile contract (§0.1) against a filled [`versions.lock`](playbook/versions.lock) before use.*

This repository is a **reference playbook plus environment-agnostic implementation scaffold** for production-oriented LLM inference platform engineering. It is **not a turnkey deployment**: bring your own GPU cluster, Gateway API controller, OCI registry, secrets, model artifacts, and observability stack.

The implementation scaffold keeps all environment-specific values as placeholders or runtime configuration. See [`impl/config/README.md`](impl/config/README.md) and [`impl/DEPLOYMENT_AND_VALIDATION.md`](impl/DEPLOYMENT_AND_VALIDATION.md).

License: Apache-2.0. See [`LICENSE`](LICENSE).

## Quality Gates

The public scaffold is designed to pass offline without GPUs:

```bash
python3 -m venv /tmp/llm_inference_playbook_venv
/tmp/llm_inference_playbook_venv/bin/pip install -r playbook/requirements-dev.txt
PATH="/tmp/llm_inference_playbook_venv/bin:$PATH" make -C playbook offline
PATH="/tmp/llm_inference_playbook_venv/bin:$PATH" python -m pytest impl/tests impl/gateway/admission/test_app.py -q --cov=impl --cov-fail-under=60
```

Live GPU/staging proof remains environment-owned; see [`impl/DEPLOYMENT_AND_VALIDATION.md`](impl/DEPLOYMENT_AND_VALIDATION.md).

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
| TP vs PP vs DP | [§5.1](docs/04-scale-and-kubernetes.md#51-parallelism-decision-tree) | [capacity.py](playbook/calculators/capacity.py) | — |
| Quantization promotion | [§4.2](docs/03-optimization-decisions.md#42-quantization--kernel-coverage-pipeline-and-eval-gates) | — | `test-rollback` |
| Speculative decoding | [§4.3](docs/03-optimization-decisions.md#43-speculative-decoding--decision-contract) | — | `bench-local` |
| Disaggregation | [§5.7](docs/04-scale-and-kubernetes.md#57-disaggregated-prefilldecode--with-blast-radius) | helm | `bench-local` |
| Admission / shedding | [§6.1](docs/05-platform-engineering.md#61-admission-control--priority-classes-owner-gateway--scheduler) | [gateway.py](playbook/ci/gateway.py) | `test-tenant-quota` |
| Brownout response | [§6.5](docs/05-platform-engineering.md#65-degradation-modes--brownout-ladder-owner-sre--scheduler) | runbooks | `test-brownout` |
| Fabric validation | [§5.4](docs/04-scale-and-kubernetes.md#54-fabric--topology-validation-gate-dont-hope) | nccl-tests | — |
| Model promotion | [§6.10](docs/05-platform-engineering.md#610-eval-gates--release-engineering-owner-platform--quality) | ci/ | `test-rollback` |
| Implementation architecture | [Design choices](docs/design-choices.md) | `impl/` | `make -C playbook offline` |

## Table of contents

| Doc | Contents |
|---|---|
| [01-first-token-and-gateway.md](docs/01-first-token-and-gateway.md) | §1.0 platform contract, lifecycle, first token, gateway |
| [02-measurement-and-benchmarks.md](docs/02-measurement-and-benchmarks.md) | §2 measurement, §3.5–3.6 engine selection |
| [03-optimization-decisions.md](docs/03-optimization-decisions.md) | §4 optimization decision contracts |
| [04-scale-and-kubernetes.md](docs/04-scale-and-kubernetes.md) | §5 K8s, fabric, disaggregation |
| [05-platform-engineering.md](docs/05-platform-engineering.md) | §6 platform (6.A–6.E) |
| [design-choices.md](docs/design-choices.md) | Implementation design choice register |
| [setup.md](docs/setup.md) | Offline setup and quickstart |
| [architecture.md](docs/architecture.md) | Repository and platform architecture overview |
| [status.md](docs/status.md) | Scaffold/proof maturity matrix |
| [tooling.md](docs/tooling.md) | Required and optional tooling |
| [compatibility.md](docs/compatibility.md) | Target pins vs validated evidence |
| [impl/config/README.md](impl/config/README.md) | Environment placeholder and configuration reference |
| [impl/DEPLOYMENT_AND_VALIDATION.md](impl/DEPLOYMENT_AND_VALIDATION.md) | What config solves vs what requires live infrastructure proof |
| [F-engine-internals.md](docs/appendices/F-engine-internals.md) | §3.1–3.4 deep dive |
| [G-scale-tier-requirements.md](docs/appendices/G-scale-tier-requirements.md) | [T2] hyperscale requirements |
| [B-claims-register.md](docs/appendices/B-claims-register.md) | Claims worklist |
| [C-cohosting-boundary.md](docs/appendices/C-cohosting-boundary.md) | Embeddings / multimodal boundary |
| [D-evidence-ledger.md](docs/appendices/D-evidence-ledger.md) | Validation ledger |
| [E-caveats.md](docs/appendices/E-caveats.md) | Caveats |
| [moe-multi-node-topology.md](docs/companions/moe-multi-node-topology.md) | MoE / 405B+ companion |
| [cohosting-embeddings-multimodal.md](docs/companions/cohosting-embeddings-multimodal.md) | Embeddings / multimodal companion |

---

# 0. HOW TO READ THIS PLAYBOOK

## 0.1 Version lock — tested profiles (fill before adoption)

A bare version list warns about drift but gives no adoptable baseline. The unit of pinning is a **profile**: a named, dated, validated combination. Maintain at least one; every artifact in this playbook is re-validated against a profile, and the profile name appears in deployment annotations so incidents can be traced to a stack.

**Artifact:** [`playbook/versions.lock`](playbook/versions.lock) — one entry per validated profile. NO artifact ships against an unfilled profile.

**Rule:** no artifact enters a design doc or cluster without re-validation against its profile. Empty fields are a build-time failure, not a footnote.

## 0.2 Repo contract — what makes the templates executable

This document pairs with the [`playbook/`](playbook/) directory; the document teaches, the repo proves:

```text
playbook/
  helm/            # §5.2 manifest set (deployment, service, pdb, networkpolicy, keda)
  benchmarks/      # §2.5 smoke test + benchmark report schema
  dashboards/      # §2.4 prometheus.yml + Grafana JSON (add panels as adopted)
  runbooks/        # §6.11 paged-on documents (add per incident class)
  calculators/     # §2.1 capacity.py + §6.7 cost notebook (add as adopted)
  ci/              # §1.3 gateway learning artifact + §6.10 eval-gate pipeline
  versions.lock
  Makefile
```

Minimum Makefile contract — see [`playbook/Makefile`](playbook/Makefile). Targets passing **is** the definition of "validated" in §0.1. Full target → section map is below.


## 0.3a Scale tier legend

Requirements are tagged by fleet scale. Hyperscale detail lives in [docs/appendices/G-scale-tier-requirements.md](docs/appendices/G-scale-tier-requirements.md).

| Tag | Fleet scale | Examples |
|---|---|---|
| **[T0]** | Any production | Smoke tests, admission control, eval gates |
| **[T1]** | Multi-tenant shared platform (~100+ GPU) | Per-tenant fairness, brownout ladder, prefix-cache policy |
| **[T2]** | Hyperscale / strict tail-SLO (~1000+ GPU) | DHT KV routing, GDS offload, tiered XID handling, NUMA pinning |

## 0.3 Claim-confidence legend

Every quantitative claim in this document carries one of four tags:
- **[Derived]** — follows from arithmetic stated inline; check the inputs.
- **[Cited]** — from a primary paper/spec; footnoted with source, date, config.
- **[Vendor]** — vendor-reported, vendor-optimal config; treat as ceiling, not expectation.
- **[Directional]** — workload-dependent; validate on your own traffic before relying on it.

**Publication rule:** [Vendor] and [Directional] claims are acceptable in an internal working document; before *external* publication every such claim is **resolved** (primary source + config located, tag upgraded) **or removed**. The claims register (Appendix B) is the worklist.

## 0.4 Scope and assumptions

- **Workloads covered:** chat, RAG, agentic/tool-calling, structured output, batch inference. Embeddings/rerankers and multimodal are noted where they change the design.
- **Traffic model:** you must know your prompt-length P50/P95/P99, output-length distribution, cache-hit potential (shared system prompts? multi-turn?), and request criticality mix. Every capacity and cost number downstream is a function of this distribution.
- **SLO model:** TTFT, TPOT/ITL, E2E latency, availability, and $/1M tokens at SLO. Define cache-hit and cache-miss TTFT SLOs separately (§2.5) — prefix caching makes a single TTFT SLO unenforceable.
## 0.5 Companion document registry

Out-of-scope topics with explicit decision thresholds. Do not infer topology/engineering detail from this playbook when a companion is required.

| Companion | Read when | Inputs from core playbook | Interim guidance |
|---|---|---|---|
| **MoE / multi-node topology** (405B–671B) | EP needed (§5.1), fabric validated (§5.4), decision needs NVLink-domain planning or wide-EP routing | §3.5 parallelism table, §5.1 tree, §5.4 gates | [companions/moe-multi-node-topology.md](docs/companions/moe-multi-node-topology.md) |
| **Embeddings / rerankers / multimodal** | Co-hosting non-chat workloads on the inference cluster | [Appendix C](docs/appendices/C-cohosting-boundary.md) boundary | [companions/cohosting-embeddings-multimodal.md](docs/companions/cohosting-embeddings-multimodal.md) |

If your decision requires deferred companion material, this playbook is **insufficient** for that decision alone.


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

## Validation status

| Layer | Status | Command |
|---|---|---|
| Offline CI (lint, unit, schemas) | **IMPLEMENTED** | `make -C playbook offline` |
| Pinned stack (`versions.lock`) | **PINNED** — `validated_on` empty until fleet run | fill via `make -C playbook record-validation` after GPU pass |
| GPU smoke + bench | **SCRIPTS READY** | `make -C playbook gpu` (requires live vLLM) |
| Staging game-day | **HOOKS READY** | `make -C playbook game-day` + set `*_HOOK` env vars |
| MoE / multimodal companions | **DRAFT COMPLETE** | `docs/companions/` |
| Appendix D.2 fleet evidence | **BLOCKING until fleet run** | see [D-evidence-ledger](docs/appendices/D-evidence-ledger.md) |

