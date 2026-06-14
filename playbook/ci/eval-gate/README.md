# Eval gate pipeline (§6.10)

Minimum promotion checks:

1. `lm_eval` baseline (GSM8K, MMLU, IFEval)
2. Long-context (RULER), tool-calling (BFCL)
3. Sampled production traffic replay
4. Canary 5% → 50% → 100% on goodput + quality signals

## Rollback hook

Wire your CI canary step:

```bash
export ROLLBACK_HOOK='bash playbook/ci/eval-gate/run_canary_rollback.sh'
make -C playbook test-rollback
```

## Files

- `run_canary_rollback.sh` — template that fails when `EVAL_FORCE_REGRESSION=1`
