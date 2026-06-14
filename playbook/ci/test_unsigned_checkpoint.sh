#!/usr/bin/env bash
# §6.9 — unsigned checkpoint → readiness false
set -euo pipefail
HOOK="${UNSIGNED_CHECKPOINT_HOOK:-}"

if [[ -z "$HOOK" ]]; then
  echo "SKIP: set UNSIGNED_CHECKPOINT_HOOK to init-container cosign verify test"
  exit 0
fi
bash -c "$HOOK"
echo "test-unsigned-checkpoint: hook completed"
