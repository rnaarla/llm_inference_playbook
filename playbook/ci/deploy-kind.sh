#!/usr/bin/env bash
# §5.2 — apply helm kustomization to cluster (kind/minikube/staging)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS="${DEPLOY_NAMESPACE:-inference}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "FAIL: kubectl required"
  exit 1
fi

if [[ "${DEPLOY_DRY_RUN:-0}" == "1" ]]; then
  kubectl kustomize "${ROOT}/helm" | head -40
  echo "deploy-kind: dry-run render OK"
  exit 0
fi

kubectl get ns "${NS}" >/dev/null 2>&1 || kubectl create ns "${NS}"
kubectl apply -k "${ROOT}/helm" -n "${NS}"
kubectl rollout status deployment/vllm-llama70b -n "${NS}" --timeout=900s || {
  echo "WARN: rollout timeout — GPU nodes may be required"
  exit 1
}
echo "deploy-kind: applied to namespace ${NS}"
