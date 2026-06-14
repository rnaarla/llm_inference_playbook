#!/usr/bin/env bash
# §2.5 — benchmark protocol wrapper; emits schema-valid report under benchmarks/runs/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${BENCH_PROFILE:-h100-vllm-kserve}"
BASE_URL="${VLLM_BASE_URL:-http://localhost:8000}"
MODEL="${BENCH_MODEL:-microsoft/Phi-3-mini-4k-instruct}"
RUN_ID="$(git -C "${ROOT}/.." rev-parse --short HEAD 2>/dev/null || date +%Y%m%d)"
OUT_DIR="${ROOT}/benchmarks/runs/${RUN_ID}"
OPERATOR="${BENCH_OPERATOR:-$(whoami)}"
WARMUP_MIN="${BENCH_WARMUP_MIN:-10}"
STEADY_MIN="${BENCH_STEADY_MIN:-30}"

mkdir -p "${OUT_DIR}"

if [[ "${BENCH_DRY_RUN:-0}" == "1" ]]; then
  cat > "${OUT_DIR}/report.yaml" <<EOF
benchmark_report:
  profile: ${PROFILE}
  model: "${MODEL} (dry-run)"
  hardware: "unset — run on GPU fleet"
  traffic:
    source: synthetic-dry-run
    prompt_tokens:  { p50: 512, p95: 1024, p99: 2048 }
    output_tokens:  { p50: 256, p95: 512, p99: 1024 }
    cache_hit_rate: 0.0
    structured_output_fraction: 0.0
  results:
    ttft_ms:  { p50: 0, p95: 0, p99: 0, hit_p95: 0, miss_p95: 0 }
    tpot_ms:  { p50: 0, p95: 0, p99: 0 }
    e2e_s:    { p50: 0, p95: 0, p99: 0 }
    goodput_knee: { concurrency: 0, output_tok_s: 0, input_tok_s: 0 }
    queue_wait_ms_p95: 0
    preemptions: 0
    kv_usage_peak: 0.0
    dram_active_mean: 0.0
  decisions:
    per_replica_concurrency_cap: 0
    replica_count: 0
    keda_queue_threshold: 0
    cost_per_1M: { input: 0.0, output: 0.0, total: 0.0 }
  run: { warmup_min: ${WARMUP_MIN}, steady_min: ${STEADY_MIN}, date: "$(date -Iseconds)", operator: "${OPERATOR}" }
EOF
  bash "${ROOT}/ci/validate-benchmark-report.sh" "${OUT_DIR}/report.yaml"
  echo "bench-local: dry-run report at ${OUT_DIR}/report.yaml"
  exit 0
fi

if ! curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "FAIL: no engine at ${BASE_URL}. Use BENCH_DRY_RUN=1 for schema-only, or start vllm."
  exit 1
fi

if ! command -v vllm >/dev/null 2>&1; then
  echo "FAIL: vllm CLI not found — required for bench serve"
  exit 1
fi

echo "==> warmup ${WARMUP_MIN}m (manual timer — reduce for dev with BENCH_WARMUP_MIN=1)"
vllm bench serve \
  --backend openai-chat \
  --base-url "${BASE_URL}" \
  --model "${MODEL}" \
  --num-prompts 100 \
  --request-rate 4 \
  --max-concurrency 16 \
  2>&1 | tee "${OUT_DIR}/bench_warmup.log"

echo "==> steady-state sweep — adjust --max-concurrency for knee search"
vllm bench serve \
  --backend openai-chat \
  --base-url "${BASE_URL}" \
  --model "${MODEL}" \
  --num-prompts 1000 \
  --request-rate 8 \
  --max-concurrency 64 \
  2>&1 | tee "${OUT_DIR}/bench_steady.log"

python3 - <<'PY' "${OUT_DIR}" "${PROFILE}" "${MODEL}" "${OPERATOR}" "${WARMUP_MIN}" "${STEADY_MIN}"
import sys, re, yaml
from pathlib import Path
from datetime import datetime, timezone
out, profile, model, op = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
warmup, steady = int(sys.argv[5]), int(sys.argv[6])
log = (out / "bench_steady.log").read_text(errors="replace")
# Best-effort parse vllm bench output — fill zeros if not found
def find_float(pattern, default=0.0):
    m = re.search(pattern, log, re.I)
    return float(m.group(1)) if m else default
report = {
  "benchmark_report": {
    "profile": profile,
    "model": model,
    "hardware": "fill from nvidia-smi / cluster metadata",
    "traffic": {
      "source": "synthetic-vllm-bench",
      "prompt_tokens": {"p50": 512, "p95": 1024, "p99": 2048},
      "output_tokens": {"p50": 256, "p95": 512, "p99": 1024},
      "cache_hit_rate": 0.0,
      "structured_output_fraction": 0.0,
    },
    "results": {
      "ttft_ms": {"p50": find_float(r"TTFT.*?p50[=:\s]+([\d.]+)"), "p95": find_float(r"p95[=:\s]+([\d.]+)"),
                  "p99": 0, "hit_p95": 0, "miss_p95": find_float(r"TTFT.*?p95[=:\s]+([\d.]+)")},
      "tpot_ms": {"p50": 0, "p95": 0, "p99": 0},
      "e2e_s": {"p50": 0, "p95": 0, "p99": 0},
      "goodput_knee": {"concurrency": 64, "output_tok_s": find_float(r"Output.*?([\d.]+)\s*tok/s"), "input_tok_s": 0},
      "queue_wait_ms_p95": 0,
      "preemptions": 0,
      "kv_usage_peak": 0.0,
      "dram_active_mean": 0.0,
    },
    "decisions": {
      "per_replica_concurrency_cap": 0,
      "replica_count": 0,
      "keda_queue_threshold": 0,
      "cost_per_1M": {"input": 0.0, "output": 0.0, "total": 0.0},
    },
    "run": {"warmup_min": warmup, "steady_min": steady,
            "date": datetime.now(timezone.utc).isoformat(), "operator": op},
  }
}
(out / "report.yaml").write_text(yaml.dump(report, sort_keys=False))
print(f"wrote {out / 'report.yaml'} — review and fill decisions from knee analysis")
PY

bash "${ROOT}/ci/validate-benchmark-report.sh" "${OUT_DIR}/report.yaml"
echo "bench-local: ${OUT_DIR}/report.yaml"
