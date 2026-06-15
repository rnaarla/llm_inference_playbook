# Tooling

## Required for Offline Checks

| Tool | Purpose |
|---|---|
| Python 3.11+ | scripts and unit checks |
| make | command entrypoint |

## Optional for Infra Work

| Tool | Purpose |
|---|---|
| Helm | render/deploy charts |
| kubectl | interact with Kubernetes clusters |
| kubeconform | Kubernetes schema validation |
| helmfile | multi-chart orchestration |
| ORAS | push/pull model OCI artifacts |
| cosign | sign and verify artifacts |
| gitleaks | secret scanning |
| yq | shell-based YAML workflows |

## Setup

```bash
python3 -m venv playbook/.venv
playbook/.venv/bin/pip install -r playbook/requirements-dev.txt
PATH="$PWD/playbook/.venv/bin:$PATH" make -C playbook offline
```
