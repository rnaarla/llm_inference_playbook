# Guardrail Provider Interface

Guardrail providers implement the stable `/moderate` contract used by the
gateway policy layer.

## Request

```json
{
  "tenant": "example-tenant",
  "route": "safety_required",
  "phase": "input",
  "text": "user or model text",
  "request_id": "req-123"
}
```

## Response

```json
{
  "allowed": true,
  "action": "allow",
  "reason": null,
  "phase": "input",
  "route": "safety_required",
  "tenant": "example-tenant",
  "audit_required": true
}
```

Supported actions:

- `allow`
- `block`
- `fail_open`
- `fail_closed`

## Provider Adapter Requirements

- deterministic timeout behavior
- explicit fail-open/fail-closed mapping per route
- no prompt/response content in logs unless content logging policy allows it
- bounded request/response size
- stable reason codes for audit
