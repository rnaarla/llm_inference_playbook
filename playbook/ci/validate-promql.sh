#!/usr/bin/env bash
# Validate PromQL panel files. Live query when PROMETHEUS_URL is set.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PANELS="${ROOT}/dashboards/panels"

echo "==> PromQL panel syntax (offline)"
python3 - <<'PY' "${PANELS}"
import sys, re
from pathlib import Path
panels = Path(sys.argv[1])
bad = []
for p in sorted(panels.glob("*.promql")):
    for i, line in enumerate(p.read_text().splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if re.search(r'[\t\r]', line):
            bad.append(f"{p.name}:{i} contains control chars")
        if s.count("(") != s.count(")"):
            bad.append(f"{p.name}:{i} unbalanced parens: {s[:60]}")
    print(f"  ok  {p.name}")
if bad:
    raise SystemExit("\n".join(bad))
PY

if [[ -n "${PROMETHEUS_URL:-}" ]]; then
  echo "==> Live query against ${PROMETHEUS_URL}"
  while IFS= read -r q; do
    [[ -z "$q" || "$q" =~ ^# ]] && continue
    enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$q")
    url="${PROMETHEUS_URL%/}/api/v1/query?query=${enc}"
    if ! curl -sf "$url" | python3 -c "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='success', r"; then
      echo "FAIL query: $q"
      exit 1
    fi
    echo "  ok  ${q:0:72}..."
  done < <(grep -vh '^#' "${PANELS}"/*.promql | sed '/^\s*$/d')
  echo "validate-promql: live checks passed"
else
  echo "validate-promql: offline checks passed (set PROMETHEUS_URL for live scrape validation)"
fi
