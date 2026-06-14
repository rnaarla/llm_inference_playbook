# Profile: h100-vllm-kserve

Canonical dense-model serving profile (70B FP8 class on 2×H100).

## Pinned stack

See [`../../versions.lock`](../../versions.lock). After every validation run, update `validated_on` / `validated_by`.

## Engine flags

See [`engine.flags`](engine.flags) — pass to `vllm serve` or helm args.

## Metrics

See [`metrics.txt`](metrics.txt) — used by `validate-promql`.

## Evidence artifacts

| Target | Output |
|---|---|
| `smoke-vllm` | TTFT bound on warm engine |
| `bench-local` | `benchmarks/runs/<sha>/report.yaml` |
| `validate-promql` | live panel query log |

## Startup verification

On engine start, capture log lines for:
- Attention backend (FlashAttention / FlashInfer path)
- Quantization format
- CUDA graph capture mode

Store in `benchmarks/runs/<sha>/engine_startup.log`.
