#!/usr/bin/env bash
# Check versions.lock validated_on vs latest benchmark run date
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="${ROOT}/versions.lock"
RUNS="${ROOT}/benchmarks/runs"
OFFLINE=0
[[ "${1:-}" == "--offline" ]] && OFFLINE=1

python3 - <<'PY' "$LOCK" "$RUNS" "$OFFLINE"
import sys, yaml
from pathlib import Path
lock = yaml.safe_load(Path(sys.argv[1]).read_text())
runs = Path(sys.argv[2])
offline = sys.argv[3] == "1"
errors = []
for p in lock.get("profiles", []):
    name = p.get("profile", "?")
    for k, v in p.items():
        if k in ("profile", "notes"):
            continue
        if v == "" or v is None:
            errors.append(f"profile {name}: empty field {k}")
latest = None
if runs.exists():
    dirs = sorted([d for d in runs.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)
    if dirs:
        rp = dirs[0] / "report.yaml"
        if rp.exists():
            latest = yaml.safe_load(rp.read_text()).get("benchmark_report", {}).get("run", {}).get("date")
for p in lock.get("profiles", []):
    if p.get("profile") == "h100-vllm-kserve" and p.get("validated_on") and latest:
        if p["validated_on"] < latest[:10]:
            errors.append(f"validated_on {p['validated_on']} older than latest bench {latest[:10]}")
if errors and not offline:
    raise SystemExit("profile drift:\n" + "\n".join(errors))
if errors:
    print("profile drift (offline mode — warn only):")
    print("\n".join(errors))
else:
    print("check-profile-drift: OK")
PY
