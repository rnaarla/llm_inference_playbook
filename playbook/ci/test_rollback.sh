#!/usr/bin/env bash
# §6.10 — canary eval regression triggers rollback
set -euo pipefail
HOOK="${ROLLBACK_HOOK:-}"

if [[ -z "$HOOK" ]]; then
  echo "SKIP: set ROLLBACK_HOOK to CI canary pipeline step"
  exit 0
fi
bash -c "$HOOK"
echo "test-rollback: hook completed"
