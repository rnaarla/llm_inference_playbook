# XID Watcher

Node-local watcher for tiered GPU XID remediation.

## Deployment Contract

The watcher intentionally has no workload-specific deployment names. Each
environment supplies:

| Placeholder / env var | Purpose |
|---|---|
| `REPLACE_WITH_XID_WATCHER_IMAGE` | Image containing `watcher.py`, `kubectl`, Python 3, and node-local GPU telemetry access |
| `REPLACE_WITH_XID_TARGET_POD_SELECTOR` | Label selector for engine pods that may be restarted for recoverable XIDs |
| `REPLACE_WITH_XID_DRAIN_TIMEOUT` | Timeout passed to the fatal drain command |
| `XID_RECOVERABLE` | Comma-separated recoverable XID tier, default `13,31` |
| `XID_FATAL` | Comma-separated fatal XID tier, default `79,94` |
| `XID_RECOVERABLE_CMD` | Command template for tier-1 remediation |
| `XID_FATAL_CORDON_CMD` | Command template for node cordon |
| `XID_FATAL_DRAIN_CMD` | Command template for node drain |

Command templates are expanded by the watcher before execution. Available
template variables include all container environment variables plus `NODE_NAME`
and `XID`.

## RBAC Assumptions

`kubernetes.yaml` grants the minimum scaffold permissions needed for the default
commands:

- read and patch nodes for cordon
- list and delete pods for tier-1 restart by selector
- create pod evictions for drain

Production clusters should bind this only to GPU node pools and restrict the
target pod selector to inference workloads managed by the platform.

## Operational Notes

- The container must be able to read node-local XID telemetry, either through
  `nvidia-smi` or a production image/runtime integration with DCGM.
- Do not request `nvidia.com/gpu` for the watcher DaemonSet; it should observe
  GPU nodes without reserving serving capacity.
- If your platform already has a remediation controller, set the command
  templates to call that controller instead of invoking `kubectl` directly.
- Fatal XIDs should page the fabric/on-call owner and block rescheduling until
  the node is inspected.
