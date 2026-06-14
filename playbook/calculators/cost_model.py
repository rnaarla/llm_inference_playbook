#!/usr/bin/env python3
"""§6.7 cost model from benchmark report + fleet economics."""
import argparse
import yaml
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Compute $/1M tokens at SLO from bench report")
    p.add_argument("report", type=Path, help="benchmark report YAML")
    p.add_argument("--gpu-hourly", type=float, default=2.50, help="USD per GPU-hour")
    p.add_argument("--gpus-per-replica", type=int, default=2)
    p.add_argument("--platform-overhead-hourly", type=float, default=2.0)
    p.add_argument("--replicas", type=int, default=None)
    args = p.parse_args()

    data = yaml.safe_load(args.report.read_text())["benchmark_report"]
    knee = data["results"]["goodput_knee"]
    replicas = args.replicas or data["decisions"].get("replica_count") or 1
    out_tok_s = knee.get("output_tok_s") or 0
    in_tok_s = knee.get("input_tok_s") or 0
    total_tok_s = out_tok_s + in_tok_s

    hourly = replicas * args.gpus_per_replica * args.gpu_hourly + args.platform_overhead_hourly

    def per_million(rate_tok_s: float) -> float:
        if rate_tok_s <= 0:
            return float("inf")
        return 1e6 * hourly / (3600 * rate_tok_s)

    cost = {
        "hourly_platform_cost_usd": hourly,
        "replicas": replicas,
        "usd_per_1m_input_at_slo": per_million(in_tok_s),
        "usd_per_1m_output_at_slo": per_million(out_tok_s),
        "usd_per_1m_total_at_slo": per_million(total_tok_s),
    }
    print(yaml.dump({"cost_model": cost}, sort_keys=False))


if __name__ == "__main__":
    main()
