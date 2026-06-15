#!/usr/bin/env bash
# §5.2 — apply helm kustomization to cluster (kind/minikube/staging)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/.." && pwd)"
NS="${DEPLOY_NAMESPACE:-inference}"
RELEASE="${ENGINE_RELEASE:-inference-engine}"
ENGINE_CHART="${ENGINE_CHART:-${REPO_ROOT}/impl/charts/inference-engine}"
ENGINE_VALUES="${ENGINE_VALUES:-${REPO_ROOT}/impl/engine/values-h100-vllm-kserve.yaml}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "FAIL: kubectl required"
  exit 1
fi

if [[ "${DEPLOY_DRY_RUN:-0}" == "1" ]]; then
  if command -v helm >/dev/null 2>&1 && [[ -d "${ENGINE_CHART}" ]]; then
    helm template "${RELEASE}" "${ENGINE_CHART}" \
      --namespace "${NS}" \
      -f "${ENGINE_CHART}/values.yaml" \
      -f "${ENGINE_VALUES}" | head -80
  else
    kubectl kustomize "${ROOT}/helm" | head -40
  fi
  echo "deploy-kind: dry-run render OK"
  exit 0
fi

kubectl get ns "${NS}" >/dev/null 2>&1 || kubectl create ns "${NS}"
if command -v helm >/dev/null 2>&1 && [[ -d "${ENGINE_CHART}" ]]; then
  helm upgrade --install "${RELEASE}" "${ENGINE_CHART}" \
    --namespace "${NS}" \
    -f "${ENGINE_CHART}/values.yaml" \
    -f "${ENGINE_VALUES}"
else
  kubectl apply -k "${ROOT}/helm" -n "${NS}"
fi
kubectl rollout status deployment/vllm-llama70b -n "${NS}" --timeout=900s || {
  echo "WARN: rollout timeout — GPU nodes may be required"
  exit 1
}
echo "deploy-kind: applied to namespace ${NS}"
