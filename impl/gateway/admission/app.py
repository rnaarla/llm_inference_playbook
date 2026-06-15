"""Admission service for pre-engine inference checks.

This service is designed to sit behind a gateway policy hook. It validates
tenant and model policy before the engine sees a request, and returns the
translated served model name plus priority class.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

CONFIG_PATH = Path(os.environ.get("ADMISSION_CONFIG", "/config/tenants.yaml"))
FLEET_KV_PRESSURE = float(os.environ.get("FLEET_KV_PRESSURE", "0"))
DEFAULT_TENANT_ID = os.environ.get("DEFAULT_TENANT_ID", "REPLACE_WITH_DEFAULT_TENANT_ID")

app = FastAPI(title="inference-admission")

_request_counts: dict[tuple[str, int], int] = {}
_token_counts: dict[tuple[str, int], int] = {}
_outcome_counts: dict[tuple[str, str, str], int] = {}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return yaml.safe_load(Path(__file__).with_name("tenants.example.yaml").read_text())
    return yaml.safe_load(CONFIG_PATH.read_text())


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    # Conservative fallback: roughly 4 chars/token. Production should call the
    # tokenizer for the served model.
    chars = sum(len(str(m.get("content", ""))) for m in messages)
    return max(1, chars // 4)


def current_minute() -> int:
    return int(time.time() // 60)


def increment_and_check(tenant: str, input_tokens: int, max_tokens: int, policy: dict[str, Any]) -> None:
    bucket = current_minute()
    rpm_key = (tenant, bucket)
    tpm_key = (tenant, bucket)
    _request_counts[rpm_key] = _request_counts.get(rpm_key, 0) + 1
    _token_counts[tpm_key] = _token_counts.get(tpm_key, 0) + input_tokens + max_tokens
    if _request_counts[rpm_key] > int(policy["rpm"]):
        raise HTTPException(status_code=429, detail="tenant RPM exceeded", headers={"Retry-After": "30"})
    if _token_counts[tpm_key] > int(policy["tpm"]):
        raise HTTPException(status_code=429, detail="tenant TPM exceeded", headers={"Retry-After": "30"})


def record_outcome(tenant: str, priority: str, outcome: str) -> None:
    key = (tenant, priority, outcome)
    _outcome_counts[key] = _outcome_counts.get(key, 0) + 1


def audit_event(request_id: str, tenant: str, model_alias: str, priority: str, outcome: str, reason: str = "") -> None:
    # Keep stdout structured so a sidecar/log pipeline can collect this without
    # coupling admission logic to a specific audit sink.
    print(
        {
            "event": "admission_decision",
            "request_id": request_id,
            "tenant": tenant,
            "model_alias": model_alias,
            "priority_class": priority,
            "outcome": outcome,
            "reason": reason,
        },
        flush=True,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    lines = [
        "# HELP gateway_requests_total Admission decisions by tenant, priority, and outcome.",
        "# TYPE gateway_requests_total counter",
    ]
    for (tenant, priority, outcome), value in sorted(_outcome_counts.items()):
        lines.append(
            f'gateway_requests_total{{tenant="{tenant}",priority_class="{priority}",outcome="{outcome}"}} {value}'
        )
    return "\n".join(lines) + "\n"


@app.post("/admit")
async def admit(
    request: Request,
    x_tenant_id: str = Header(default=DEFAULT_TENANT_ID),
    x_request_id: str = Header(default="missing"),
) -> dict[str, Any]:
    cfg = load_config()
    body = await request.json()
    alias = body.get("model", "llama70b")
    priority = "Standard"
    model_cfg = cfg.get("models", {}).get(alias)
    if not model_cfg:
        record_outcome(x_tenant_id, priority, "rejected_404")
        audit_event(x_request_id, x_tenant_id, alias, priority, "rejected_404", "unknown_model_alias")
        raise HTTPException(status_code=404, detail=f"unknown model alias: {alias}")

    tenant_cfg = cfg.get("tenants", {}).get(x_tenant_id, {})
    defaults = cfg.get("defaults", {})
    policy = {**defaults, **tenant_cfg}

    max_tokens = int(body.get("max_tokens") or body.get("max_completion_tokens") or policy["max_output_tokens"])
    input_tokens = estimate_tokens(body.get("messages", []))
    total_context = input_tokens + max_tokens

    priority = policy.get("priority_class", "Standard")

    if input_tokens > int(policy["max_input_tokens"]):
        record_outcome(x_tenant_id, priority, "rejected_400")
        audit_event(x_request_id, x_tenant_id, alias, priority, "rejected_400", "input_tokens")
        raise HTTPException(status_code=400, detail="input tokens exceed tenant policy")
    if max_tokens > int(policy["max_output_tokens"]):
        record_outcome(x_tenant_id, priority, "rejected_400")
        audit_event(x_request_id, x_tenant_id, alias, priority, "rejected_400", "max_tokens")
        raise HTTPException(status_code=400, detail="max_tokens exceeds tenant policy")
    if total_context > int(model_cfg["max_context_tokens"]):
        record_outcome(x_tenant_id, priority, "rejected_400")
        audit_event(x_request_id, x_tenant_id, alias, priority, "rejected_400", "model_context")
        raise HTTPException(status_code=400, detail="request exceeds model context policy")

    try:
        increment_and_check(x_tenant_id, input_tokens, max_tokens, policy)
    except HTTPException as exc:
        record_outcome(x_tenant_id, priority, f"rejected_{exc.status_code}")
        audit_event(x_request_id, x_tenant_id, alias, priority, f"rejected_{exc.status_code}", str(exc.detail))
        raise

    if FLEET_KV_PRESSURE >= 0.85 and priority == "Sheddable":
        record_outcome(x_tenant_id, priority, "shed_429")
        audit_event(x_request_id, x_tenant_id, alias, priority, "shed_429", "fleet_saturated")
        raise HTTPException(status_code=429, detail="fleet saturated", headers={"Retry-After": "30"})

    record_outcome(x_tenant_id, priority, "admitted")
    audit_event(x_request_id, x_tenant_id, alias, priority, "admitted")
    return {
        "tenant": x_tenant_id,
        "request_id": x_request_id,
        "model_alias": alias,
        "served_model": model_cfg["served_name"],
        "priority_class": priority,
        "input_tokens_estimate": input_tokens,
        "max_tokens": max_tokens,
        "headers": {
            "X-Request-ID": x_request_id,
            "X-Tenant-ID": x_tenant_id,
            "X-Priority-Class": priority,
            "X-Served-Model": model_cfg["served_name"],
        },
    }
