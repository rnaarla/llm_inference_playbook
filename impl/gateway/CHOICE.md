# Gateway Choice

Canonical design choices now live in [`../../docs/design-choices.md`](../../docs/design-choices.md).
This file keeps the gateway-specific rationale close to the manifests.

## Selected baseline: kgateway + Gateway API Inference Extension

The implementation uses Gateway API as the durable integration surface because
the rest of the platform is Kubernetes-native and the playbook requires
endpoint-picking signals (queue depth, KV pressure, LoRA locality, and
criticality). Envoy AI Gateway remains a compatible alternative, but this
baseline standardizes on Gateway API resources so engine routing, admission, and
network policy can all be expressed as cluster state.

## Production contract

The gateway layer owns:

- model alias translation
- authn/authz and tenant resolution
- admission and quota checks before the engine
- 429 + `Retry-After` under overload
- stream cancellation propagation
- request audit keyed by `X-Request-ID`
- tenant and priority labels for metrics

Admission is implemented as an internal service under `gateway/admission/`.
Integrate it with the selected gateway through ext_authz, WASM, or an equivalent
policy hook in the deployed distribution.
