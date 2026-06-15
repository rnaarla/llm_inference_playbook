# E6 — Frontier Scale: Fabric, MoE, Disaggregation, XID

## Objective

Prove the frontier serving track on a real multi-node GPU fabric:

- XID watcher performs tiered recovery without hardcoded workload names
- NCCL fabric baseline records macro and micro all-reduce behavior for the target topology
- 405B-class multi-node serving uses TP within node and PP across nodes
- MoE expert parallelism has placement policy, imbalance monitoring, and hot-expert response
- disaggregated prefill/decode pools have monolithic fallback and transfer budgets

## Required configuration

Populate the E6 values from:

- `impl/config/env.example.yaml`
- `impl/environments/values.example.yaml`
- `impl/fabric/xid-watcher/kubernetes.yaml`
- `impl/fabric/nccl/nccl-tests-job.yaml`
- `impl/fabric/multinode/values-405b-tp8-pp2.yaml`
- `impl/fabric/moe/ep-policy.yaml`
- `impl/fabric/disagg/values-prefill-pool.yaml`
- `impl/fabric/disagg/values-decode-pool.yaml`

Minimum E6 values:

| Field / env var | Purpose |
|---|---|
| `REPLACE_WITH_XID_WATCHER_IMAGE` | Image containing watcher, `kubectl`, Python, and GPU telemetry access |
| `REPLACE_WITH_XID_TARGET_POD_SELECTOR` | Engine pod selector eligible for recoverable XID restart |
| `REPLACE_WITH_XID_DRAIN_TIMEOUT` | Fatal drain timeout |
| `REPLACE_WITH_NCCL_TESTS_IMAGE` | Prebuilt NCCL tests image, mirrored into the environment registry |
| `REPLACE_WITH_NCCL_IB_HCA` | Allowed HCA list for aligned rail topology |
| `REPLACE_WITH_FRONTIER_PROFILE_NAME` | Frontier profile key, such as `moe-multinode-interim` |
| `REPLACE_WITH_FRONTIER_SERVED_MODEL_NAME` | Exact model name served by the engine |
| `REPLACE_WITH_TENSOR_PARALLEL_SIZE` | TP width, normally contained within a single NVLink domain |
| `REPLACE_WITH_PIPELINE_PARALLEL_SIZE` | PP width across nodes after in-node TP is exhausted |
| `REPLACE_WITH_EXPERT_PARALLEL_SIZE` | EP width for MoE expert placement |
| `REPLACE_WITH_KV_TRANSFER_CONNECTOR` | P/D connector implementation, for example NIXL in supported environments |
| `REPLACE_WITH_MONOLITHIC_FALLBACK_POOL` | Fallback route when P/D transfer is degraded |

See `impl/config/README.md` for placeholder purpose, source, expected format,
and examples.

## Integration Steps

1. Build and publish the XID watcher image with `watcher.py`, `kubectl`, and
   the runtime integration used to read XID telemetry.
2. Render `impl/fabric/xid-watcher/kubernetes.yaml` through your GitOps or
   parameter-store templating path and deploy it only to GPU node pools.
3. Mirror a prebuilt NCCL tests image into the environment registry and render
   `impl/fabric/nccl/nccl-tests-job.yaml` with the topology-specific HCA and
   payload settings.
4. Render the multi-node engine values and confirm TP, PP, GPU count, node
   selector, and process-group failure domain match the target topology.
5. Apply `impl/fabric/moe/ep-policy.yaml` to the gateway/EPP or platform policy
   mechanism that owns MoE placement and hot-expert routing.
6. Deploy prefill and decode pool overlays only after the monolithic fallback
   pool is healthy and routable.

## Live Proof Requirements

Record the following evidence from staging or production-like hardware:

- XID watcher logs showing recoverable XIDs restart selected engine pods and
  fatal XIDs cordon and drain the affected node.
- NCCL macro and micro all-reduce output for the topology class, with busbw
  compared against the profile threshold from `ep-policy.yaml`.
- Multi-node engine rollout history for the staged sequence: one node, rack, fleet.
- MoE per-expert token rate, dispatch latency, combine latency, and imbalance
  panels populated from live traffic or production-shaped replay.
- Prefill/decode transfer latency, fallback activation path, and monolithic pool
  health during a fabric-partition game day.

## Checklist

- [ ] XID watcher image is built from a private, pinned base image.
- [ ] XID RBAC is reviewed by the cluster platform owner.
- [ ] XID target pod selector matches only inference engine pods.
- [ ] NCCL tests image contains `all_reduce_perf`; no cluster-time source clone.
- [ ] `NCCL_IB_HCA` matches aligned rails on every frontier node.
- [ ] TP groups stay inside NVLink domains unless explicitly waived.
- [ ] PP spans nodes only after in-node TP is exhausted.
- [ ] MoE hot-expert policy and fallback pool are configured.
- [ ] P/D pools have explicit connector, endpoint, timeout, and fallback values.
- [ ] Evidence links are added to the MoE companion and Appendix D when validated.

## E6 Done Definition

E6 is complete only when:

- all E6 manifests and overlays render with no unresolved placeholders
- XID watcher is deployed on GPU nodes with reviewed RBAC
- frontier NCCL baseline is captured for the target topology
- multi-node serving is rolled out through the staged sequence
- MoE imbalance and dispatch/combine metrics are live
- disaggregated prefill/decode serves with monolithic fallback configured
- `moe-multinode-interim` or the environment-specific frontier profile is stamped
  with `validated_on` only after live proof is attached
