#!/usr/bin/env python3
"""Validate that an environment values file has no unresolved placeholders.

This is intentionally generic: it checks YAML/JSON/text recursively for
`REPLACE_WITH_*`, empty strings, and zero values in fields that must be set
before deployment. It does not validate secrets themselves; it validates that
the environment overlay is wired.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PLACEHOLDER_RE = re.compile(r"REPLACE_WITH_[A-Z0-9_]+")

REQUIRED_NON_ZERO_KEYS = {
    "replicaCount",
    "gpu_count",
    "replicas",
    "min_replicas",
    "max_replicas",
    "max_context_tokens",
}


def walk(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in REQUIRED_NON_ZERO_KEYS and child in (0, "0", None, ""):
                errors.append(f"{child_path}: must be non-zero/non-empty")
            errors.extend(walk(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            errors.extend(walk(child, f"{path}[{idx}]"))
    elif isinstance(value, str):
        if PLACEHOLDER_RE.search(value):
            errors.append(f"{path}: unresolved placeholder {value!r}")
        if value.strip() == "":
            errors.append(f"{path}: empty string")
    elif value is None:
        errors.append(f"{path}: null value")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values_file", type=Path)
    parser.add_argument("--allow-placeholders", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(args.values_file.read_text())
    errors = walk(data)
    if args.allow_placeholders:
        errors = [e for e in errors if "unresolved placeholder" not in e]
    if errors:
        print("configuration validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"configuration validation passed: {args.values_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
