#!/usr/bin/env python3
"""Check relative markdown links to repository files."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")
errors: list[str] = []

for md in ROOT.rglob("*.md"):
    if ".git" in md.parts or "playbook/.venv" in str(md):
        continue
    text = md.read_text(encoding="utf-8")
    for match in LINK_RE.finditer(text):
        target = match.group(1).split("#", 1)[0]
        if not target or target.startswith(SKIP_PREFIXES):
            continue
        if target.startswith("./"):
            target = target[2:]
        path = (md.parent / target).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            continue
        if not path.exists():
            errors.append(f"{md.relative_to(ROOT)}: missing link target {match.group(1)}")

if errors:
    print("internal link check failed:")
    for error in errors:
        print(f"  - {error}")
    raise SystemExit(1)
print("internal link check passed")
