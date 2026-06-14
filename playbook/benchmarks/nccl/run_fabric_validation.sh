#!/usr/bin/env bash
# §5.4 — NCCL fabric validation (macro + micro payloads)
set -euo pipefail
OUT="${FABRIC_BASELINE_OUT:-$(cd "$(dirname "$0")/../.." && pwd)/benchmarks/fabric_baseline.yaml}"
GPUS="${FABRIC_GPUS:-8}"

if ! command -v nvcc >/dev/null 2>&1 && [[ ! -d build ]]; then
  if [[ "${FABRIC_DRY_RUN:-0}" == "1" ]]; then
    cat > "$OUT" <<EOF
# fabric baseline — dry-run template (fill on GPU cluster)
topology: HGX-H100-NVSwitch
date: "$(date -Iseconds)"
macro_1g_8g_busbw_gbs: 0
micro_8_2m_busbw_gbs: 0
nccl_algo: Tree
nccl_proto: Simple
notes: "Run nccl-tests all_reduce_perf on TP group; gate >= 80% theoretical"
EOF
    echo "fabric validation: dry-run template → $OUT"
    exit 0
  fi
  echo "SKIP: nccl-tests not built — clone NVIDIA/nccl-tests && make, or FABRIC_DRY_RUN=1"
  exit 0
fi

MACRO=$(./build/all_reduce_perf -b 1G -e 8G -f 2 -g "$GPUS" 2>&1 | tee /dev/stderr | tail -5)
MICRO=$(NCCL_ALGO=Tree NCCL_PROTO=Simple ./build/all_reduce_perf -b 8 -e 2M -f 2 -g "$GPUS" 2>&1 | tee /dev/stderr | tail -5)

python3 - <<'PY' "$OUT" "$MACRO" "$MICRO"
import sys, yaml
from datetime import datetime, timezone
out = sys.argv[1]
doc = {
  "topology": "fill-from-nvidia-smi-topo-m",
  "date": datetime.now(timezone.utc).isoformat(),
  "macro_log_tail": sys.argv[2][-500:],
  "micro_log_tail": sys.argv[3][-500:],
  "nccl_algo": "Tree",
  "nccl_proto": "Simple",
  "gate": "busbw >= 80% theoretical for TP group",
}
open(out, "w").write(yaml.dump(doc, sort_keys=False))
print(f"wrote {out}")
PY
