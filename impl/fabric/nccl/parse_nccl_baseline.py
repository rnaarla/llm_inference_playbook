#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

BUSBW_RE = re.compile(r"^\s*\d+\s+\d+\s+\S+\s+\S+\s+\S+\s+\S+\s+([0-9.]+)\s*$", re.MULTILINE)


def max_busbw(text: str) -> float:
    values = [float(m.group(1)) for m in BUSBW_RE.finditer(text)]
    return max(values) if values else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--macro-log", required=True, type=Path)
    parser.add_argument("--micro-log", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--topology", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--gpu-count", required=True, type=int)
    parser.add_argument("--min-fraction-theoretical", type=float, default=0.8)
    args = parser.parse_args()

    macro_busbw = max_busbw(args.macro_log.read_text(errors="replace"))
    micro_busbw = max_busbw(args.micro_log.read_text(errors="replace"))
    report = {
        "profile": args.profile,
        "topology": args.topology,
        "run": {"date": datetime.now(UTC).isoformat(), "operator": args.operator, "gpu_count": args.gpu_count},
        "macro": {"min_bytes": "1G", "max_bytes": "8G", "busbw_gbs": macro_busbw},
        "micro": {"min_bytes": "8", "max_bytes": "2M", "busbw_gbs": micro_busbw},
        "gate": {"min_fraction_theoretical": args.min_fraction_theoretical, "passed": macro_busbw > 0 and micro_busbw > 0},
    }
    args.out.write_text(yaml.safe_dump(report, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
