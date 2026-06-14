#!/usr/bin/env bash
# Validate benchmark report YAML against JSON Schema
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="${1:-}"
SCHEMA="${ROOT}/benchmarks/benchmark_report.schema.json"

if [[ -z "$REPORT" ]]; then
  echo "usage: $0 <benchmark_report.yaml>"
  exit 2
fi

python3 - <<'PY' "$REPORT" "$SCHEMA"
import sys, yaml, json
from jsonschema import validate
from pathlib import Path
report_path, schema_path = Path(sys.argv[1]), Path(sys.argv[2])
data = yaml.safe_load(report_path.read_text())
if "benchmark_report" in data:
    data = data["benchmark_report"]
schema = json.loads(schema_path.read_text())
validate(instance=data, schema=schema)
print(f"valid: {report_path}")
PY
