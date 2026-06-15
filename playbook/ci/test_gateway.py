"""Unit tests for playbook/ci/gateway.py (§1.3 learning artifact)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gateway import app

client = TestClient(app)


def test_unknown_alias_404():
    r = client.post("/v1/chat/completions", json={"model": "nope", "messages": [], "max_tokens": 1})
    assert r.status_code == 404


def test_max_tokens_admission_400_before_any_network():
    r = client.post(
        "/v1/chat/completions",
        json={"model": "phi3", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 99999},
    )
    assert r.status_code == 400


def test_route_round_robin_cycles_pool():
    from gateway import MODELS, _rr
    _rr["phi3"] = 0
    n = len(MODELS["phi3"]["upstreams"])
    seen = set()
    for _ in range(n * 2):
        from gateway import route
        upstream, _ = route("phi3")
        seen.add(upstream)
    assert len(seen) == n


def test_alias_translation_table_maps_to_served_name():
    from gateway import MODELS
    assert MODELS["phi3"]["served_name"] == "microsoft/Phi-3-mini-4k-instruct"


def test_route_raises_http_exception_not_crash():
    from fastapi import HTTPException
    from gateway import route
    with pytest.raises(HTTPException):
        route("missing")
