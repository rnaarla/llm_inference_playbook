# OOM on traffic spike

## Actions
1. Recompute capacity with headroom (§2.1): `python playbook/calculators/capacity.py ...`
2. Lower `--gpu-memory-utilization`.
3. Verify admission rejected oversize requests before engine (§6.1).

## Validation target
`make -C playbook test-kv-pressure`
