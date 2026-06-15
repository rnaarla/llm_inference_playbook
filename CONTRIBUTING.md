# Contributing

Thanks for contributing. This repository is a reference playbook plus
environment-agnostic implementation scaffold. It is not a hosted service and
does not contain real environment values.

## Repository Layout

| Path | Purpose |
|---|---|
| `docs/` | Reference playbook, design decisions, implementation plans |
| `playbook/` | Validation harness, schemas, runbooks, profile contracts |
| `impl/` | Deployable scaffolds and implementation modules |
| `examples/` | Fake, safe configuration examples |

## Local Setup

```bash
python3 -m venv playbook/.venv
playbook/.venv/bin/pip install -r playbook/requirements-dev.txt
PATH="$PWD/playbook/.venv/bin:$PATH" make -C playbook offline
```

## Before Opening a PR

Run:

```bash
PATH="$PWD/playbook/.venv/bin:$PATH" make -C playbook offline
python3 impl/ci/validate_values.py impl/environments/values.example.yaml --allow-placeholders
python3 -m compileall -q impl
git diff --check
```

## Adding Profiles

1. Add a profile to `playbook/versions.lock`.
2. Add profile docs under `playbook/profiles/<profile>/`.
3. Add implementation values under `impl/engine/values-<profile>.yaml`.
4. Document every new placeholder in `impl/config/README.md`.
5. Do not set `validated_on` until live validation has passed.

## Placeholder and Secret Policy

Do not commit:

- real hostnames or account IDs
- real registry endpoints
- kubeconfigs
- private keys or certificates
- tokens or credentials
- `.local.yaml` or `.secret.yaml` overlays

Use `REPLACE_WITH_*` placeholders in public scaffolds and document them in
`impl/config/README.md`.

## Style

- Keep docs concise and link to detailed runbooks.
- Keep deployment-specific values out of source.
- Prefer small, typed Python modules for reusable implementation logic.
- For YAML, prefer explicit placeholder values over hidden defaults.

## PR Checklist

- [ ] Offline checks pass
- [ ] Docs updated
- [ ] New placeholders documented
- [ ] No secrets or environment-specific values committed
- [ ] Status docs reflect scaffold vs live proof honestly
