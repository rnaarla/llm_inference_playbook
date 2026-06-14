#!/usr/bin/env bash
# §6.2 — heavy context flood; Critical reserve / heavy pool (staging harness hook)
set -euo pipefail
HOOK="${KV_PRESSURE_HOOK:-}"

if [[ -z "$HOOK" ]]; then
  echo "SKIP: set KV_PRESSURE_HOOK to staging script that floods heavy contexts"
  exit 0
fi
bash -c "$HOOK"
echo "test-kv-pressure: hook completed"
