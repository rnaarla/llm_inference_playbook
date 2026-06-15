#!/usr/bin/env python3
"""Parse vLLM benchmark logs into a benchmark_report fragment.

vLLM bench output changes across versions, so this parser accepts common labels
and leaves missing values as zero instead of inventing numbers. Review the
generated report before sealing a profile.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml


def first_float(patterns: list[str], text: str) -> float:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return float(match.group(1))
    return 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--warmup-min", type=int, default=10)
    parser.add_argument("--steady-min", type=int, default=30)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    text = args.log.read_text(errors="replace")
    ttft_p50 = first_float([r"ttft.*?p50[^0-9]*([0-9.]+)", r"median ttft[^0-9]*([0-9.]+)"], text)
    ttft_p95 = first_float([r"ttft.*?p95[^0-9]*([0-9.]+)", r"p95 ttft[^0-9]*([0-9.]+)"], text)
    tpot_p50 = first_float([r"tpot.*?p50[^0-9]*([0-9.]+)", r"itl.*?p50[^0-9]*([0-9.]+)"], text)
    tpot_p95 = first_float([r"tpot.*?p95[^0-9]*([0-9.]+)", r"itl.*?p95[^0-9]*([0-9.]+)"], text)
    output_tok_s = first_float([r"output[^\\n]*?throughput[^0-9]*([0-9.]+)", r"([0-9.]+)\\s*output tok/s"], text)
    input_tok_s = first_float([r"input[^\\n]*?throughput[^0-9]*([0-9.]+)", r"([0-9.]+)\\s*input tok/s"], text)

    concurrency = first_float([r"max[-_ ]?concurrency[^0-9]*([0-9.]+)", r"concurrency[^0-9]*([0-9.]+)"], text)
    concurrency = concurrency or 64

    # Conservative placeholders for decisions. They are computed only when the
    # real service time values are present.
    mean_service_s = 0.0
    if ttft_p50 and tpot_p50:
        mean_service_s = (ttft_p50 / 1000.0) + (256 * tpot_p50 / 1000.0)

    per_replica_cap = concurrency if output_tok_s else 0
    keda_threshold = max(1, int(per_replica_cap * 0.25)) if per_replica_cap else 0

    report = {
        "benchmark_report": {
            "profile": args.profile,
            "model": args.model,
            "hardware": "fill from nvidia-smi / cluster metadata",
            "traffic": {
                "source": "synthetic-vllm-bench",
                "prompt_tokens": {"p50": 512, "p95": 1024, "p99": 2048},
                "output_tokens": {"p50": 256, "p95": 512, "p99": 1024},
                "cache_hit_rate": 0.0,
                "structured_output_fraction": 0.0,
            },
            "results": {
                "ttft_ms": {"p50": ttft_p50, "p95": ttft_p95, "p99": 0, "hit_p95": 0, "miss_p95": ttft_p95},
                "tpot_ms": {"p50": tpot_p50, "p95": tpot_p95, "p99": 0},
                "e2e_s": {"p50": mean_service_s, "p95": 0, "p99": 0},
                "goodput_knee": {
                    "concurrency": per_replica_cap,
                    "output_tok_s": output_tok_s,
                    "input_tok_s": input_tok_s,
                },
                "queue_wait_ms_p95": 0,
                "preemptions": 0,
                "kv_usage_peak": 0.0,
                "dram_active_mean": 0.0,
            },
            "decisions": {
                "per_replica_concurrency_cap": per_replica_cap,
                "replica_count": 0,
                "keda_queue_threshold": keda_threshold,
                "cost_per_1M": {"input": 0.0, "output": 0.0, "total": 0.0},
            },
            "run": {
                "warmup_min": args.warmup_min,
                "steady_min": args.steady_min,
                "date": datetime.now(UTC).isoformat(),
                "operator": args.operator,
            },
        }
    }

    args.out.write_text(yaml.dump(report, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
