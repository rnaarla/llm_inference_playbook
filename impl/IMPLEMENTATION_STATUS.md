# Implementation Status

This repo contains deployable/configurable implementation scaffolding for each
major platform area. Fleet validation still requires a real GPU cluster, gateway
controller, registry, and Prometheus stack.

## Epic status

| Epic | Status | Implemented paths | Remaining live work |
|---|---|---|---|
| E1 — Cluster + engine baseline | Ready to prove | `charts/cluster-prereqs`, `charts/inference-engine`, `engine/model-cache`, `engine/bench`, `epics/e1-cluster-engine-baseline.md` | Install on GPU cluster, push signed model artifact, run real bench |
| E2 — Gateway + admission | Ready to prove | `gateway/CHOICE.md`, `gateway/POLICY_INTEGRATION.md`, `gateway/admission`, `charts/gateway`, `epics/e2-gateway-admission.md` | Build/push admission image, install Gateway API controller, map policy config to controller-specific ext_authz |
| E3 — Scheduler | Ready to prove | `scheduler/config.py`, `scheduler/wfq`, `scheduler/reserves`, `scheduler/brownout`, `scheduler/routing`, `epics/e3-scheduler-fairness-brownout.md` | Embed primitives in gateway/EPP path, map policy actions to controller-specific config, export scheduler metrics |
| E4 — Observability | Ready to prove | `charts/observability`, `observability/values-kube-prometheus-stack.yaml`, dashboards, OTel collector, `epics/e4-observability.md` | Deploy stack, connect trace backend, and validate live PromQL |
| E5 — Governance / safety / LoRA | Ready to prove | `governance/registry`, `governance/verify-init`, `governance/eval-gate`, `guardrails`, `engine/values-lora-pool.yaml`, `engine/lora-adapter-registry.example.yaml`, `engine/LORA_ROUTING.md`, `epics/e5-governance-safety-lora.md` | Build/push guardrail service image, map gateway guardrail hook to controller policy, run promotion pipeline against real registry and eval infrastructure |
| E6 — Frontier fabric | Deployable scaffolds | `fabric/xid-watcher`, `fabric/nccl`, `fabric/multinode`, `fabric/moe`, `fabric/disagg`, `epics/e6-frontier-fabric.md` | Build/push XID watcher image, review RBAC, run on multi-node GPU fabric, and fill MoE evidence |

## Local validation

CPU-safe checks:

```bash
cd playbook
PATH="$(pwd)/.venv/bin:$PATH" make offline
```

Cluster checks:

```bash
cd impl
make up
make validate-engine
```

The cluster checks are expected to fail until a GPU cluster, signed model
artifact, and gateway controller are available.
