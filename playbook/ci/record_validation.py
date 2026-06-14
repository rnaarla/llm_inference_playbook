#!/usr/bin/env python3
"""Set validated_on / validated_by on h100-vllm-kserve after fleet pass."""
import yaml
from datetime import date
from pathlib import Path

lock_path = Path(__file__).resolve().parent.parent / "versions.lock"
lock = yaml.safe_load(lock_path.read_text())
for p in lock["profiles"]:
    if p["profile"] == "h100-vllm-kserve":
        p["validated_on"] = str(date.today())
        p["validated_by"] = "make record-validation"
lock_path.write_text(yaml.dump(lock, sort_keys=False, default_flow_style=False))
print("updated h100-vllm-kserve validated_on — commit versions.lock after full gpu+staging pass")
