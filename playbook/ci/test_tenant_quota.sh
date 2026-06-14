#!/usr/bin/env bash
# §6.1 — over-budget tenant rejected at gateway before engine
set -euo pipefail
URL="${STAGING_GATEWAY_URL:-}"
REQUIRE="${STAGING_REQUIRE:-0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -n "$URL" ]]; then
  python3 - <<'PY' "$URL"
import sys, httpx
url = sys.argv[1]
r = httpx.post(f"{url}/v1/chat/completions",
    json={"model": "phi3", "messages": [{"role":"user","content":"x"}], "max_tokens": 999999}, timeout=5)
if r.status_code not in (400, 429):
    raise SystemExit(f"FAIL: expected 400/429 got {r.status_code}")
print("test-tenant-quota: staging admission rejected over-budget request")
PY
  exit 0
fi

if [[ "$REQUIRE" == "1" ]]; then
  echo "FAIL: STAGING_GATEWAY_URL required when STAGING_REQUIRE=1"
  exit 1
fi

cd "${ROOT}/ci" && python3 -m pytest test_gateway.py::test_max_tokens_admission_400_before_any_network -q
echo "test-tenant-quota: unit-level admission check passed"
