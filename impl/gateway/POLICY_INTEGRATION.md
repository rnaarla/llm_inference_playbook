# Gateway Policy Integration

The implementation chart emits `inference-gateway-policy` as a controller-neutral
policy description. Production clusters must translate that into the selected
Gateway API controller's policy resources.

## Required policy behavior

1. Call admission service before forwarding to the engine:
   - service: `REPLACE_WITH_ADMISSION_SERVICE_NAME`
   - path: `/admit`
   - tenant header: `X-Tenant-ID`
   - request id header: `X-Request-ID`
2. Rewrite request body model alias to `served_model` from the admission result
   when the controller supports body transforms. If body rewrite is not available,
   run a lightweight gateway adapter in front of the engine.
3. Add headers from the admission result:
   - `X-Priority-Class`
   - `X-Served-Model`
   - `X-Tenant-ID`
4. Propagate downstream disconnect upstream to vLLM.
5. Emit audit logs and `gateway_requests_total{tenant,priority_class,outcome}`.

## Controller mappings

| Controller | Policy mechanism |
|---|---|
| kgateway / Envoy | ext_authz, EnvoyFilter, WASM, or provider ExternalAuthPolicy |
| Envoy Gateway | SecurityPolicy / ExtensionServerPolicy depending on version |
| NGINX Gateway | auth_request + Lua/body transform adapter |

If the selected controller cannot rewrite OpenAI request bodies, deploy an
adapter service that performs alias translation and then forwards to the engine.
