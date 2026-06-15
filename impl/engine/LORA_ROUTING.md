# LoRA Adapter Routing

This scaffold enables multi-adapter serving on a shared base-model pool without
hard-coding environment values.

## Required Configuration

- `engine/values-lora-pool.yaml` enables vLLM LoRA flags for the pool.
- `lora-adapter-registry.example.yaml` defines adapter id, digest-pinned OCI
  artifact, tenant ownership, route aliases, rank, and promotion metadata.
- `lora.adapterRegistryConfigName` points to a ConfigMap containing the adapter
  registry for the gateway/EPP and engine pods.
- `lora.adapters` maps each adapter id to the signed, digest-pinned adapter
  artifact pulled by the init container.

## Routing Assumptions

- Admission resolves tenant and model alias before routing.
- Gateway/EPP chooses an adapter id from the adapter registry and stamps it on
  the request using the controller-specific metadata mechanism.
- Engine replicas advertise loaded adapter ids through
  `REPLACE_WITH_ADAPTER_LOCALITY_LABEL`.
- The router prefers replicas that already hold the requested adapter to avoid
  cold-load churn.
- Requests with the same adapter id may be batched together; requests with
  different adapter ids should not be coalesced unless the serving runtime
  explicitly supports mixed-adapter batches.
- Adapter rank must be standardized per pool and stay at or below
  `engine.args.maxLoraRank`.

## Promotion Rules

Adapters follow the same governance path as base models:

1. Push adapter artifact to the private OCI registry.
2. Sign and attest it with `impl/governance/registry/sign_and_attest.sh`.
3. Record promotion metadata with approved digest and rollback reference.
4. Update the environment overlay with the digest-pinned adapter reference.
5. Roll the LoRA pool so init containers pull the approved adapter set.
