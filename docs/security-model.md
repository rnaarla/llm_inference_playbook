# Security Model

## Trust Boundaries

| Boundary | Assets | Primary controls |
|---|---|---|
| Client -> Gateway | request content, tenant identity | TLS/mTLS, authn/z, rate limits, audit IDs |
| Gateway -> Admission | tenant policy, token budget | internal service identity, ext_authz policy, bounded labels |
| Admission -> Engine | model alias, priority class | model rewrite contract, NetworkPolicy, request headers |
| Registry -> Init Container | model artifacts, adapters | OCI registry auth, cosign signature, digest pinning |
| Engine -> Observability | metrics/traces/logs | label cardinality limits, PII logging policy |
| CI -> Release | images, charts, docs | SHA-pinned actions, secret scanning, SBOM, provenance |

## Sensitive Data

Never commit real tenant data, prompts, model credentials, cloud account IDs,
private registry hosts, kubeconfigs, certificates, private keys, or environment
overlays.

## Required Production Controls

- Gateway authentication and authorization before admission.
- Admission fail-closed for missing tenant policy on safety-required routes.
- Signed model artifacts and load-time verification.
- Registry credentials delivered through secret manager or External Secrets.
- NetworkPolicy restricting engine ingress to gateway and monitoring.
- mTLS/service mesh for regulated environments.
- Audit logs keyed by `X-Request-ID` with content logging as an explicit policy.

## Residual Risks

- Controller-specific gateway policy mappings are environment-owned.
- Guardrail backend is a scaffold until a real policy model is deployed.
- Live fabric and GPU failure behavior must be proven in staging.
