# Post-deploy throughput collapse

## Actions
1. Trigger automated rollback (§6.10).
2. Compare eval deltas: BFCL, structured-output validity, spec-decode α.
3. Hold promotion until bench-local knee matches pre-canary report.

## Validation target
`make -C playbook test-rollback`
