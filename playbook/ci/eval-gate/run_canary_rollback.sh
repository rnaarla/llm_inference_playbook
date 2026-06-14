#!/usr/bin/env bash
# Template canary rollback test — replace with org CI integration
set -euo pipefail
if [[ "${EVAL_FORCE_REGRESSION:-0}" == "1" ]]; then
  echo "eval regression detected — rollback"
  exit 1
fi
echo "canary quality OK"
