# Runbooks — §6.11 incident entry points

| Signal | Runbook |
|---|---|
| TTFT ↑, TPOT stable | [ttft-queue-capacity.md](ttft-queue-capacity.md) |
| TPOT ↑ | [tpot-decode-pressure.md](tpot-decode-pressure.md) |
| Preemptions / KV evictions | [kv-exhaustion.md](kv-exhaustion.md) |
| OOM on spike | [oom-spike.md](oom-spike.md) |
| Throughput collapse post-deploy | [post-deploy-throughput.md](post-deploy-throughput.md) |
| XID / ECC errors | [xid-ecc.md](xid-ecc.md) |
| NCCL hang in TP/PP group | [nccl-hang.md](nccl-hang.md) |
| Full game-day bundle | [game-day.md](game-day.md) |

Execute against staging: `make -C playbook game-day`
