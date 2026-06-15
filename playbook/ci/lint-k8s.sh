#!/usr/bin/env bash
# Lint Kubernetes manifests under playbook/helm/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HELM="${ROOT}/helm"
FAILED=0

echo "==> YAML parse: ${HELM}/*.yaml"
python3 - <<'PY' "${HELM}"
import sys, yaml
from pathlib import Path
helm = Path(sys.argv[1])
for p in sorted(helm.glob("*.yaml")):
    with open(p) as f:
        docs = list(yaml.safe_load_all(f))
    if not docs or all(d is None for d in docs):
        raise SystemExit(f"empty or invalid: {p}")
    print(f"  ok  {p.name} ({len([d for d in docs if d])} doc(s))")
PY

if command -v kubeconform >/dev/null 2>&1; then
  echo "==> kubeconform"
  kubeconform -summary -ignore-missing-schemas "${HELM}"/*.yaml
else
  if [[ "${LINT_REQUIRE_KUBECONFORM:-0}" == "1" ]]; then
    echo "FAIL: kubeconform required when LINT_REQUIRE_KUBECONFORM=1"
    exit 1
  fi
  echo "==> kubeconform not installed — skipping schema conformance (install for full lint-k8s)"
fi

for f in "${HELM}"/*.yaml; do
  if grep -q 'vX\.Y\.Z' "$f" 2>/dev/null; then
    echo "WARN: unreplaced image tag in $f — set VLLM_IMAGE via kustomization"
  fi
done

echo "lint-k8s: structural checks passed"
