#!/usr/bin/env bash
# Smoke test — run after every deployment; gate readiness on it (§1.2).
# Expect: HTTP 200, non-empty choices[0], TTFT < 5s on a warm engine.
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8000}"
MODEL="${MODEL:-microsoft/Phi-3-mini-4k-instruct}"

time curl -sf "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":4}" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); assert r['choices'][0]['message']['content']; print('OK')"
