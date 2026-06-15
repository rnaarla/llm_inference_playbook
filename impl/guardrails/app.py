"""Guardrail service scaffold for gateway integration.

The API is intentionally stable: gateways call `/moderate` with tenant, route,
phase, and text, then apply the returned action. Route policy is loaded from
YAML so failure mode and enforcement can differ by route without code changes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

CONFIG_PATH = Path(os.environ.get("GUARDRAIL_CONFIG", "/config/guardrails.yaml"))

app = FastAPI(title="inference-guardrails")


class GuardrailRequest(BaseModel):
    tenant: str
    route: str
    text: str
    phase: Literal["input", "output"]
    request_id: str = "missing"


class GuardrailDecision(BaseModel):
    allowed: bool
    action: Literal["allow", "block", "fail_open", "fail_closed"]
    reason: str | None
    phase: Literal["input", "output"]
    route: str
    tenant: str
    audit_required: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text())
    return yaml.safe_load(Path(__file__).with_name("policy.example.yaml").read_text())


def route_policy(cfg: dict, route: str) -> dict:
    defaults = cfg.get("defaults", {})
    route_cfg = cfg.get("routes", {}).get(route, {})
    return {**defaults, **route_cfg}


@app.post("/moderate")
def moderate(req: GuardrailRequest) -> GuardrailDecision:
    # Replace with Llama Guard / ShieldGemma / policy model call. Keep the API
    # shape stable so gateway fail-open/fail-closed behavior can be wired once.
    cfg = load_config()
    policy = route_policy(cfg, req.route)
    phase_policy = policy.get(req.phase, {})

    if not phase_policy.get("enabled", True):
        return GuardrailDecision(
            allowed=True,
            action="allow",
            reason="phase_disabled",
            phase=req.phase,
            route=req.route,
            tenant=req.tenant,
            audit_required=bool(policy.get("audit_required", True)),
        )

    if "guardrail_backend_down_fixture" in req.text:
        mode = phase_policy.get("on_unavailable", policy.get("on_unavailable", "fail_closed"))
        allowed = mode == "fail_open"
        return GuardrailDecision(
            allowed=allowed,
            action="fail_open" if allowed else "fail_closed",
            reason="guardrail_backend_unavailable",
            phase=req.phase,
            route=req.route,
            tenant=req.tenant,
            audit_required=True,
        )

    blocked = False
    reason = None
    if "policy_violation_fixture" in req.text:
        blocked = True
        reason = "fixture_policy_violation"

    return GuardrailDecision(
        allowed=not blocked,
        action="block" if blocked else "allow",
        reason=reason,
        phase=req.phase,
        route=req.route,
        tenant=req.tenant,
        audit_required=bool(policy.get("audit_required", True)),
    )


@app.get("/routes")
def routes() -> dict:
    cfg = load_config()
    return {"defaults": cfg.get("defaults", {}), "routes": cfg.get("routes", {})}
