# Guardrail Serving Path

The guardrail service is a gateway-facing scaffold for input and streaming
output moderation. It defines the stable contract and route policy shape; the
model call can be replaced with Llama Guard, ShieldGemma, or a private safety
model without changing the gateway integration.

## API Contract

`POST /moderate`

```json
{
  "tenant": "REPLACE_WITH_STANDARD_TENANT_ID",
  "route": "safety_required",
  "phase": "input",
  "request_id": "REPLACE_WITH_REQUEST_ID",
  "text": "user or generated text chunk"
}
```

Response:

```json
{
  "allowed": true,
  "action": "allow",
  "reason": null,
  "phase": "input",
  "route": "safety_required",
  "tenant": "REPLACE_WITH_STANDARD_TENANT_ID",
  "audit_required": true
}
```

Gateway behavior should be driven by `action`:

- `allow`: forward the request or chunk.
- `block`: reject input or terminate output with the configured safe response.
- `fail_closed`: reject safety-required traffic and emit audit.
- `fail_open`: continue lower-risk traffic and emit audit.

## Configuration

Set `GUARDRAIL_CONFIG=/config/guardrails.yaml` and mount a policy derived from
`policy.example.yaml`. Route names should align with gateway policy routes.

The route policy is intentionally controller-neutral. In kgateway/Envoy
deployments, map the guardrail call after auth/admission and before engine
dispatch for input moderation. For streaming output, call `/moderate` on bounded
chunks and apply the route's fail-open/fail-closed policy.
