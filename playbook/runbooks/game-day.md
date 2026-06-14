# Game day — staging fleet validation bundle

Run quarterly on **staging** (never first touch in prod). Requires `STAGING_GATEWAY_URL`, `STAGING_ENGINE_URL`, and feature flags for brownout rungs.

## Checklist

| Step | Command | Pass criteria |
|---|---|---|
| 1 | `make -C playbook test-gateway-unit` | 5/5 unit tests |
| 2 | `make -C playbook test-gateway` | alias, 429 under load |
| 3 | `make -C playbook test-tenant-quota` | 400/429 before engine |
| 4 | `make -C playbook test-cancel-stream` | engine abort on disconnect |
| 5 | `make -C playbook test-kv-pressure` | Critical reserve holds |
| 6 | `make -C playbook test-brownout` | ladder rungs + hysteresis |
| 7 | `make -C playbook test-gpu-xid-sim` | tiered XID response |
| 8 | `make -C playbook test-rollback` | canary rollback on regression |
| 9 | `make -C playbook test-unsigned-checkpoint` | fail-closed readiness |
| 10 | `make -C playbook test-guardrail-down` | safety routes fail-closed |

## Record
Update `docs/appendices/D-evidence-ledger.md` with date, operator, and links under `playbook/benchmarks/runs/`.
