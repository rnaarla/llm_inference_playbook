# MoE / Multi-Node Topology Companion (405B–671B)

**Status:** companion to core playbook v5  
**Read when:** §5.1 decision tree selects EP; §5.4 fabric gates pass macro but multi-node MoE deployment is planned  
**Inputs from core:** §3.5 parallelism table, §5.1 tree, §5.4 validation, interim §5.5

---

## 1. Decision threshold

Adopt this companion when **all** apply:

1. Model is MoE and does not fit single-node NVLink domain with KV + headroom  
2. Expert parallelism (EP) is required — all-to-all is the bottleneck, not FLOPS  
3. Core playbook §5.4 busbw gates pass on **both** macro (1G–8G) and micro (8B–2M) payloads  

If any fail, do not proceed to wide-EP production — fix topology first.

---

## 2. NVLink domain planning

| Layer | Rule |
|---|---|
| Dense layers | TP within NVLink domain; smallest power-of-2 that fits weights+KV |
| Experts | EP within domain first; cross-node EP only with IB/RoCE budget for all-to-all |
| Decode | Prefer DP replicas of TP groups; avoid TP across PCIe |
| PP | Across nodes only when in-node TP exhausted; keep PP stages small (bubble cost) |

**Gate:** `nvidia-smi topo -m` shows NV# between all TP peers in a group.

---

## 3. Rail-optimized InfiniBand

Multi-node EP requires **aligned rails** — each GPU's HCA maps to the same rail index across nodes.

Checklist:

- [ ] `NCCL_IB_HCA` pinned to intended HCAs per node  
- [ ] `NCCL_DEBUG=INFO` shows `via NET/IB/GDRDMA` (not `NET/Socket`)  
- [ ] Adaptive Routing (AR) enabled on fabric ([T2] — see Appendix G)  
- [ ] SHARP enabled where available for all-reduce heavy phases  

Record generated baselines at `playbook/benchmarks/fabric_baseline.yaml` or an
environment-specific path via `FABRIC_BASELINE_OUT`. Do not commit live fabric
outputs.

---

## 4. NCCL / RCCL tuning matrix (starting points)

Verify every value on **your** profile — these are hypotheses, not defaults.

| Workload phase | NCCL_ALGO | NCCL_PROTO | Notes |
|---|---|---|---|
| Prefill / large AR | Ring or Tree | Simple | macro payload test |
| Decode TP micro-AR | Tree | Simple or LL128 | micro payload test — TPOT sensitive |
| EP all-to-all | — | — | dominated by dispatch/combine libs; profile separately |

**Micro-payload gate:** decode TP all-reduce at 8B–2M must meet ≥80% theoretical busbw or TPOT will collapse.

---

## 5. Wide-EP and expert placement

MoE serving bottlenecks:

1. **Token imbalance** — hot experts saturate NICs while others idle  
2. **All-to-all latency** — every MoE layer pays dispatch + combine  
3. **Expert memory** — expert shards must fit per GPU with headroom  

Mitigations:

- Load-balancing loss at training time helps; at inference monitor per-expert token rates  
- Consider redundant expert replicas for hot experts (engine-specific)  
- Size IB fabric for **all-to-all bytes × layers × decode steps**, not just weight shard size  

---

## 6. Validation protocol

1. Run `playbook/benchmarks/nccl/run_fabric_validation.sh` on TP and EP process groups  
2. Single-node engine smoke with target model quant + EP width  
3. Multi-node PP+TP+EP staged rollout: 1 node → rack → fleet  
4. Bench with **production token-length distribution** (§2.5) — MoE all-to-all cost scales with batch × experts activated  

Profile: `moe-multinode-interim` in `versions.lock`.

---

## 7. Failure domains

| Event | Blast radius | Action |
|---|---|---|
| Single GPU XID | TP/EP group | Tiered XID handling (runbook `xid-ecc.md`) |
| NCCL hang | Whole parallel group | Restart group; check rails (`nccl-hang.md`) |
| Expert imbalance | Tail TPOT | Rebalance routing; dedicated hot-expert pools |

---

## 8. Relationship to disaggregation

MoE decode pools may still disaggregate prefill (§5.7) when prefill interference measured — budget KV transfer separately; EP all-to-all and KV transfer compete for NIC bandwidth on same nodes.

---

## Evidence

Fill `benchmarks/runs/<sha>/moe_fabric_report.yaml` after validation. Link from Appendix D when `validated_on` set on `moe-multinode-interim` profile.
