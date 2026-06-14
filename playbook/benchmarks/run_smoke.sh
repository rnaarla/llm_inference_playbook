#!/usr/bin/env bash
# §1.2 — smoke test against a running vLLM OpenAI endpoint
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${VLLM_BASE_URL:-http://localhost:8000}"
MODEL="${SMOKE_MODEL:-microsoft/Phi-3-mini-4k-instruct}"
MAX_TTFT_SEC="${SMOKE_MAX_TTFT_SEC:-5}"

if ! curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
  if [[ "${SMOKE_REQUIRE_SERVER:-0}" == "1" ]]; then
    echo "FAIL: no server at ${BASE_URL} (set VLLM_BASE_URL or start vllm serve)"
    exit 1
  fi
  echo "SKIP: no server at ${BASE_URL} — set SMOKE_REQUIRE_SERVER=1 to fail closed"
  exit 0
fi

START=$(python3 -c "import time; print(time.perf_counter())")
bash "${ROOT}/benchmarks/smoke_test.sh"
END=$(python3 -c "import time; print(time.perf_counter())")
ELAPSED=$(python3 -c "print(${END} - ${START})")
python3 -c "import sys; sys.exit(0 if float('${ELAPSED}') < float('${MAX_TTFT_SEC}') else 1)" || {
  echo "FAIL: TTFT/wall ${ELAPSED}s exceeds ${MAX_TTFT_SEC}s"
  exit 1
}
echo "smoke-vllm: OK (${ELAPSED}s)"
