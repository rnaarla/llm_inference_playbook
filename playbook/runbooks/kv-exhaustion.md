# KV exhaustion — preemptions / evictions

## Diagnosis
`kv_cache_usage_perc > 0.92` or preemption counters increasing.

## Actions
1. Engage brownout ladder (§6.5) — rungs are feature-flagged.
2. Reduce `--max-model-len`, `--max-num-seqs`.
3. Stop admitting Sheddable; cap Standard `max_tokens`.
4. Page if rung ≥3.

## Validation target
`make -C playbook test-brownout`
