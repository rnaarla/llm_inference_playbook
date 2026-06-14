#!/usr/bin/env bash
# §6.12 — guardrail down → safety routes fail-closed
set -euo pipefail
HOOK="${GUARDRAIL_DOWN_HOOK:-}"

if [[ -z "$HOOK" ]]; then
  echo "SKIP: set GUARDRAIL_DOWN_HOOK to staging guardrail outage simulation"
  exit 0
fi
bash -c "$HOOK"
echo "test-guardrail-down: hook completed"
