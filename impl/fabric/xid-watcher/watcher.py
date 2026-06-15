"""Tiered XID watcher.

The watcher runs node-local and classifies XID codes into recoverable and fatal
tiers. Actions are injected as shell command templates so deployments can choose
their own remediation controller, namespace, pod selector, and drain policy
without hardcoded workload names in the watcher process.
"""

from __future__ import annotations

import os
import subprocess
import time
from string import Template


def parse_xids(name: str, default: str) -> set[int]:
    values: set[int] = set()
    for token in os.environ.get(name, default).split(","):
        token = token.strip()
        if token:
            values.add(int(token))
    return values


RECOVERABLE = parse_xids("XID_RECOVERABLE", "13,31")
FATAL = parse_xids("XID_FATAL", "79,94")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", os.environ.get("POLL_INTERVAL", "10")))
NODE_NAME = os.environ.get("NODE_NAME", "")
RESTART_CMD = os.environ.get("XID_RECOVERABLE_CMD") or os.environ.get("RESTART_CMD")
CORDON_CMD = os.environ.get("XID_FATAL_CORDON_CMD") or os.environ.get("CORDON_CMD")
DRAIN_CMD = os.environ.get("XID_FATAL_DRAIN_CMD") or os.environ.get("DRAIN_CMD")


def xid_events() -> list[int]:
    # In production, prefer DCGM field watches or exporter events. This fallback
    # reads nvidia-smi query output for simple node-local deployment.
    try:
        out = subprocess.check_output(["nvidia-smi", "-q", "-d", "ERROR"], text=True)
    except Exception:
        return []
    events: list[int] = []
    for line in out.splitlines():
        if "Xid" in line:
            for token in line.replace(":", " ").split():
                if token.isdigit():
                    events.append(int(token))
    return events


def run(cmd: str, xid: int) -> None:
    if not cmd:
        raise RuntimeError("XID watcher command is not configured")
    values = dict(os.environ)
    values.update({"NODE_NAME": NODE_NAME, "XID": str(xid)})
    rendered = Template(cmd).safe_substitute(values)
    subprocess.run(rendered, shell=True, check=False)


def handle(xid: int) -> None:
    if xid in RECOVERABLE:
        run(RESTART_CMD, xid)
    elif xid in FATAL:
        run(CORDON_CMD, xid)
        run(DRAIN_CMD, xid)


def main() -> None:
    seen: set[int] = set()
    while True:
        for xid in xid_events():
            if xid not in seen:
                handle(xid)
                seen.add(xid)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
