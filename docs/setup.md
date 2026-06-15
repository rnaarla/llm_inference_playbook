# Setup

This setup path verifies the repository without GPUs, clusters, secrets, or real
infrastructure.

## Requirements

Required for offline checks:

- Python 3.11+
- `make`

Optional for deeper infra checks:

- Helm
- kubectl
- kubeconform
- helmfile
- ORAS
- cosign
- gitleaks
- yq

## Offline Quickstart

```bash
git clone <repo-url>
cd llm_inference_playbook

python3 -m venv playbook/.venv
playbook/.venv/bin/pip install -r playbook/requirements-dev.txt
PATH="$PWD/playbook/.venv/bin:$PATH" make -C playbook offline
```

Expected result:

- PromQL files parse offline
- Kubernetes YAML parses
- gateway unit tests pass
- dry-run benchmark report validates against schema
- profile drift warnings appear because live validation has not been run

## Implementation Config Check

```bash
python3 impl/ci/validate_values.py impl/environments/values.example.yaml --allow-placeholders
```

For a real environment overlay:

```bash
python3 impl/ci/validate_values.py impl/environments/staging.local.yaml
```

## Live Validation

Live validation requires user-provided infrastructure. See
`impl/DEPLOYMENT_AND_VALIDATION.md`.
