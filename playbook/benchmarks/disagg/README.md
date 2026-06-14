# Disaggregated prefill/decode validation (§5.7)

## Prerequisites
- NIXL connector wired per pinned vLLM profile
- Prefill and decode pools with monolithic fallback route

## Measure
1. Per-token KV transfer latency over fabric (budget into TTFT SLO)
2. Fallback: KV fabric partition → decode pool monolithic prefill

## Run
```bash
export DISAGG_PREFILL_URL=http://prefill-pool:8000
export DISAGG_DECODE_URL=http://decode-pool:8000
# org-specific load generator comparing TTFT/TPOT vs monolithic
```

Record results in `benchmarks/runs/<sha>/disagg_report.yaml`.
