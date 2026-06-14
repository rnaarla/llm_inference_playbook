# Appendix D — Canonical Evidence Bundle & Machine-Validation Ledger

Status key: **PASS** = executed on target fleet; **IMPLEMENTED** = automation exists; **BLOCKING** = requires GPU/staging run.

## D.1 Executed evidence (CPU / unit)

| Artifact | Method | Status |
|---|---|---|
| gateway (`playbook/ci/gateway.py`) | pytest 5/5 | **PASS** (unit) |
| capacity helper | live HF fetch Phi-3-mini | **PASS** |
| helm manifests | YAML parse + lint-k8s | **IMPLEMENTED** |
| benchmark report schema | JSON Schema + dry-run report | **IMPLEMENTED** (`make -C playbook bench-local-dry`) |
| PromQL panels | offline syntax validation | **IMPLEMENTED** |

## D.2 Fleet validation matrix

| Evidence artifact | Make target(s) | Status |
|---|---|---|
| Filled `versions.lock` (`validated_on`) | `record-validation` after `gpu` | **BLOCKING** — pins set, date empty |
| Benchmark report (real TTFT/TPOT/goodput) | `bench-local` | **BLOCKING** — script ready |
| Manifest deploy on pinned stack | `deploy-kind`, `lint-k8s` | **IMPLEMENTED** — needs GPU cluster for rollout PASS |
| Live PromQL against scraping vLLM | `validate-promql` + `PROMETHEUS_URL` | **BLOCKING** |
| Gateway load + cancellation | `test-gateway`, `test-cancel-stream` | **IMPLEMENTED** — staging hooks |
| Game-day bundle | `game-day` | **IMPLEMENTED** — wire `*_HOOK` for PASS |
| Fabric baseline (NCCL) | `fabric` | **IMPLEMENTED** — `fabric-dry` for template |
| MoE fabric report | `docs/companions/moe-multi-node-topology.md` §8 | **BLOCKING** |
| Cost model from bench | `cost-model` | **IMPLEMENTED** |

**Evidence statement pattern:** *Validated on profile `<name>` via `<targets>` on `<date>` by `<operator>`; logs at `playbook/benchmarks/runs/<sha>/`.*

After a full fleet pass: run `make -C playbook record-validation` and commit `versions.lock`.
