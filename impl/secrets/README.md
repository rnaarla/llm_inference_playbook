# Secret Delivery Templates

These templates define the expected shape for secret delivery. They are not
cluster-specific; bind them to your External Secrets operator, cloud secret
manager, or private GitOps overlay.

Required secret categories:

| Secret | Purpose |
|---|---|
| HF/model source token | Optional model-source authentication |
| registry pull credentials | Pull engine/admission/guardrail images and model artifacts |
| cosign public key | Verify signed model artifacts at load time |
| gateway TLS/mTLS certs | Terminate or originate secure gateway traffic |
