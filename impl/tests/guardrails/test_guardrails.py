from pathlib import Path

from fastapi.testclient import TestClient

import impl.guardrails.app as guardrail_app

client = TestClient(guardrail_app.app)
guardrail_app.CONFIG_PATH = Path("impl/guardrails/policy.example.yaml")


def test_policy_violation_blocks():
    r = client.post("/moderate", json={"tenant": "t", "route": "safety_required", "text": "policy_violation_fixture", "phase": "input"})
    assert r.status_code == 200
    assert not r.json()["allowed"]
    assert r.json()["action"] == "block"


def test_backend_down_uses_failure_mode():
    r = client.post("/moderate", json={"tenant": "t", "route": "safety_required", "text": "guardrail_backend_down_fixture", "phase": "input"})
    assert r.status_code == 200
    assert r.json()["action"] in {"fail_open", "fail_closed"}
