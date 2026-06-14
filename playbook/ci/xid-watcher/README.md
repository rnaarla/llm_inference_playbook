# XID watcher — platform component (§5.2)

Tiered GPU fault handling:

| Tier | XID examples | Action |
|---|---|---|
| Recoverable | 13, 31 | Restart engine container |
| Fatal | 79, 94 | Cordon node, drain |

## Deploy

Apply `xid-watcher-daemonset.yaml` to GPU nodes (requires DCGM + node cordon permissions).

## Test hook

Set `XID_SIM_HOOK` to a script that injects a simulated XID and asserts watcher behavior:

```bash
export XID_SIM_HOOK='kubectl exec -n inference deploy/xid-watcher -- /scripts/simulate_xid.sh 13'
make -C playbook test-gpu-xid-sim
```

## Files

- `xid-watcher-daemonset.yaml` — placeholder DaemonSet spec (customize for your DCGM exporter version)
