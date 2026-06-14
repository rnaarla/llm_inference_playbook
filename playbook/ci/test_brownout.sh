#!/usr/bin/env bash
# §6.5 — brownout ladder rungs (staging feature flags)
set -euo pipefail
HOOK="${BROWNOUT_HOOK:-}"

if [[ -z "$HOOK" ]]; then
  echo "SKIP: set BROWNOUT_HOOK to script that drives kv_cache_usage_perc through ladder"
  exit 0
fi
bash -c "$HOOK"
echo "test-brownout: hook completed"
