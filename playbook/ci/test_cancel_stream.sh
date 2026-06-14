#!/usr/bin/env bash
# §6.2 — client disconnect mid-stream; engine should abort (observed via metrics/logs)
set -euo pipefail
URL="${STAGING_GATEWAY_URL:-http://localhost:8080}"
REQUIRE="${STAGING_REQUIRE:-0}"

if [[ "$REQUIRE" != "1" ]] && ! curl -sf "${URL}/docs" >/dev/null 2>&1; then
  echo "SKIP: set STAGING_GATEWAY_URL + STAGING_REQUIRE=1"
  exit 0
fi

python3 - <<'PY' "$URL"
import sys, httpx
url = sys.argv[1]
try:
    with httpx.stream("POST", f"{url}/v1/chat/completions",
        json={"model": "phi3", "messages": [{"role":"user","content":"long"}], "max_tokens": 256, "stream": True},
        timeout=5.0) as r:
        next(r.iter_bytes())
except httpx.ReadError:
    pass
print("test-cancel-stream: disconnect sent — verify engine abort in metrics/logs")
PY
