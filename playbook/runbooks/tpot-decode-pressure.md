# TPOT ↑ — decode pressure

## Diagnosis
Memory-bound decode: high `DRAM_ACTIVE`, long contexts, KV saturation, or prefill interference.

## Actions
1. Lower `--max-num-batched-tokens` (chunked prefill budget).
2. Enable or verify FP8 KV (eval-gated, §4.2).
3. Route heavy contexts to heavy pool (§6.2).
4. If prefill interference persists: evaluate disaggregation (§5.7).

## Validation target
`make -C playbook bench-local` after each change.
