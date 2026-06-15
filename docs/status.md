# Project Status

Status terms:

- **Reference complete** — documented design exists.
- **Scaffolded** — implementation shape exists but needs environment integration.
- **Ready to prove** — configuration and live proof steps are documented.
- **Proven** — live validation has passed and evidence is recorded.

| Area | Status | Notes |
|---|---|---|
| Reference playbook | Reference complete | `docs/01`–`05`, appendices, companions |
| Offline checks | Implemented | `make -C playbook offline` plus config/example validation |
| Engine chart | Ready to prove | requires GPU cluster and signed model artifact |
| Gateway/admission | Ready to prove | local admission tests and coverage are implemented; live controller policy mapping remains |
| Scheduler | Ready to prove | library primitives; requires gateway/EPP integration |
| Observability | Ready to prove | requires live Prometheus/Grafana/OTel |
| Governance/guardrails/LoRA | Ready to prove | requires registry, keys, eval infra, guardrail model |
| Frontier fabric | Ready to prove | NCCL/MoE schemas, parser, samples, XID scaffold; requires multi-node GPU fabric for proof |
| Test coverage | Implemented baseline | `impl/` logic coverage gate starts at 60%; current local run is ~77% |
| CI/CD hardening | Implemented baseline | SHA-pinned actions, split CI jobs, chart render/lint, ruff, coverage, link check, secret scan |
| Non-infra production scaffolds | Implemented | gateway policies, secret templates, threat/security docs, eval workflow examples, NCCL/MoE schemas |
| Fleet validation | Not proven | user-provided environment required |

## Current Proof Boundary

The repository can prove offline usability without GPUs. It cannot prove
production behavior until deployed to a real environment and validated through
the `playbook/` targets.

See:

- `impl/DEPLOYMENT_AND_VALIDATION.md`
- `docs/appendices/D-evidence-ledger.md`
- `impl/IMPLEMENTATION_STATUS.md`
