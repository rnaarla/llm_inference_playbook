# TTFT ↑, TPOT stable — queue / capacity

**Severity:** SEV2 if Critical tenant affected; SEV1 if fleet-wide.

## Diagnosis
Queue wait dominates; decode healthy (`TPOT` stable, `DRAM_ACTIVE` normal).

## Actions (in order)
1. Shed **Sheddable** at gateway (§6.1) — 429 + `Retry-After`.
2. Confirm `waiting > 2× running` alert (§2.4).
3. Check goodput knee vs current load (§2.5 report).
4. Scale replicas only after admission — reactive scale will not save TTFT mid-spike (§5.3).
5. Post-incident: update `replica_count` and KEDA threshold from bench report.

## Validation target
`make -C playbook test-tenant-quota`
