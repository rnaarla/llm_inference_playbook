# XID / ECC GPU fault

## Tiered handling ([T2] detail: docs/appendices/G-scale-tier-requirements.md)

| Tier | Examples | Action |
|---|---|---|
| Recoverable | XID 13, 31 | Restart engine container |
| Fatal | XID 79, 94 | Cordon node, drain, `dcgmi diag -r 2` |

Compare NCCL busbw to fabric baseline: `playbook/benchmarks/fabric_baseline.yaml`

## Validation target
`make -C playbook test-gpu-xid-sim`
