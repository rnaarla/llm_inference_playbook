# Appendix D — Canonical Evidence Bundle & Machine-Validation Ledger

This document includes one canonical evidence bundle for the artifacts validatable in an authoring environment; the paired repository contains the complete rerunnable artifacts, logs, and GPU-dependent evidence. Each entry carries `profile / date / artifact-hash / operator`; entries marked **BLOCKING** are required-empty until a GPU profile run fills them, and they are the precise boundary between this reference and a production platform standard.

## D.1 Executed evidence (real runs, this bundle)

```yaml
evidence_bundle:
  bundle_date: "2026-06-10"
  operator: "authoring environment (CPU-only; no GPU profile available)"
  entries:
  - artifact: gateway (§1.3, playbook/ci/gateway.py)
    hash: d6fd4cd3fe5a
    method: pytest, FastAPI TestClient — 5/5 passed
    evidence: |
      test_unknown_alias_404                          PASSED
      test_max_tokens_admission_400_before_any_network PASSED
      test_route_round_robin_cycles_pool               PASSED
      test_alias_translation_table_maps_to_served_name PASSED
      test_route_raises_http_exception_not_crash       PASSED
    claim_validated: "admission rejects over-budget and unknown-model requests BEFORE any upstream call (§6.1 order of checks)"
  - artifact: capacity helper (playbook/calculators/capacity.py)
    hash: 64f95d554796
    method: live execution against microsoft/Phi-3-mini-4k-instruct
    evidence: |
      param source: safetensors-index
      checkpoint size: 7.1 GiB
      kv/token (fp8) = 0.19 MiB   KV@16x4096 = 12.0 GiB   TOTAL+headroom = 22.9 GiB
    claim_validated: "safetensors-index path resolves checkpoint bytes; KV/token matches hand arithmetic (2x32x32x96x1 B). Execution previously caught the bfloat16 alias defect — templates that haven't been executed contain bugs reading cannot find"
  - artifact: manifest set (§5.2) + all YAML blocks
    method: static parse — 6 blocks / 10 documents
    evidence: "all parse as valid YAML; calculator and gateway code compile"
    claim_validated: "structural validity only — NOT schema conformance against pinned K8s/KServe (see D.2)"
```

## D.2 BLOCKING — required-empty until a filled profile run

| Evidence artifact | Make target(s) | Status |
|---|---|---|
| Filled `versions.lock` profile (h100-vllm-kserve) | — | **BLOCKING — requires team validation run** |
| Benchmark report (§2.5 schema, real TTFT/TPOT/goodput) | `bench-local` | **BLOCKING — requires GPU** |
| Manifest schema conformance + render on pinned stack | `deploy-kind`, `lint-k8s` | **BLOCKING — requires pinned cluster** |
| Live PromQL returns against a scraping vLLM | `validate-promql` | **BLOCKING — requires live engine** |
| Gateway under concurrency + cancellation propagation | `test-gateway`, `test-cancel-stream` | **BLOCKING — unit-level passed (D.1); load-level open** |
| Game-day bundle: brownout, quota, XID, KV-pressure, rollback | `test-brownout` … `test-rollback` | **BLOCKING — requires staging fleet** |

**Evidence statements** (the per-section pattern, used once a profile fills the table): *"Validated on profile `<name>` via `<targets>` on `<date>` by `<operator>`; full logs at `/benchmarks/runs/<sha>`."* The bundle embeds proof of one canonical pass; the repo holds exhaustive outputs for re-validation, drift checks, and incident follow-up. Do not paste full logs or transcripts into this document — the repo proves, the playbook teaches.
