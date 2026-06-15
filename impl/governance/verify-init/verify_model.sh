#!/usr/bin/env bash
set -euo pipefail

ARTIFACT="${MODEL_ARTIFACT:?MODEL_ARTIFACT required}"
PUBLIC_KEY="${COSIGN_PUBLIC_KEY:-/cosign/cosign.pub}"
APPROVED_DIGEST="${APPROVED_DIGEST:-}"
FAIL_CLOSED="${FAIL_CLOSED:-true}"
COSIGN_IDENTITY_REGEXP="${COSIGN_IDENTITY_REGEXP:-}"
COSIGN_ISSUER="${COSIGN_ISSUER:-}"

verify_args=(--key "$PUBLIC_KEY")
if [[ -n "$COSIGN_IDENTITY_REGEXP" ]]; then
  verify_args+=(--certificate-identity-regexp "$COSIGN_IDENTITY_REGEXP")
fi
if [[ -n "$COSIGN_ISSUER" ]]; then
  verify_args+=(--certificate-oidc-issuer "$COSIGN_ISSUER")
fi

if ! cosign verify "${verify_args[@]}" "$ARTIFACT"; then
  if [[ "$FAIL_CLOSED" == "true" ]]; then
    echo "model signature verification failed: ${ARTIFACT}"
    exit 1
  fi
  echo "WARN: model signature verification failed but FAIL_CLOSED=false"
fi

if [[ -n "$APPROVED_DIGEST" ]]; then
  if [[ "$ARTIFACT" != *"@${APPROVED_DIGEST}" && "$ARTIFACT" != *"@sha256:${APPROVED_DIGEST#sha256:}" ]]; then
    if command -v crane >/dev/null 2>&1; then
      RESOLVED="$(crane digest "$ARTIFACT")"
      if [[ "$RESOLVED" != "$APPROVED_DIGEST" && "$RESOLVED" != "sha256:${APPROVED_DIGEST#sha256:}" ]]; then
        echo "digest mismatch: expected ${APPROVED_DIGEST}, got ${RESOLVED}"
        exit 1
      fi
    else
      echo "approved digest configured but artifact is not digest-pinned and crane is unavailable"
      exit 1
    fi
  fi
fi

echo "model verification passed: ${ARTIFACT}"
