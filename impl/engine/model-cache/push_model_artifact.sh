#!/usr/bin/env bash
set -euo pipefail

MODEL_SOURCE="${MODEL_SOURCE:-}"
MODEL_ARTIFACT="${MODEL_ARTIFACT:-}"
COSIGN_KEY="${COSIGN_KEY:-}"

if [[ -z "$MODEL_SOURCE" || -z "$MODEL_ARTIFACT" ]]; then
  echo "MODEL_SOURCE and MODEL_ARTIFACT are required"
  exit 2
fi

if ! command -v oras >/dev/null 2>&1; then
  echo "oras is required"
  exit 2
fi

echo "Pushing ${MODEL_SOURCE} to ${MODEL_ARTIFACT}"
oras push "${MODEL_ARTIFACT}" "${MODEL_SOURCE}:application/vnd.llm.model.layer.v1+tar"

if [[ -n "$COSIGN_KEY" ]]; then
  if ! command -v cosign >/dev/null 2>&1; then
    echo "cosign is required when COSIGN_KEY is set"
    exit 2
  fi
  cosign sign --key "${COSIGN_KEY}" "${MODEL_ARTIFACT}"
else
  echo "WARN: COSIGN_KEY unset; pushed artifact is not signed by this script"
fi
