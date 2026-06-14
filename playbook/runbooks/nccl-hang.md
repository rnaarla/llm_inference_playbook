# NCCL hang — TP/PP group failure

## Actions
1. Treat whole parallel group as failure domain — restart group together.
2. Check IB rail / `NCCL_DEBUG=INFO` for Socket vs GDRDMA path (§5.4).
3. Fail over to warm spare if available (§6.6).

## Validation target
`bash playbook/benchmarks/nccl/run_fabric_validation.sh`
