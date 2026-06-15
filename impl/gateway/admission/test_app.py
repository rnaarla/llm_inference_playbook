from fastapi.testclient import TestClient
from pathlib import Path

import app as admission_app
from app import _outcome_counts, _request_counts, _token_counts, app


client = TestClient(app)
admission_app.CONFIG_PATH = Path(__file__).with_name("testdata") / "tenants.test.yaml"


def setup_function():
    _request_counts.clear()
    _token_counts.clear()
    _outcome_counts.clear()


def test_admits_and_translates_model_alias():
    r = client.post(
        "/admit",
        headers={"X-Tenant-ID": "standard-prod", "X-Request-ID": "req-1"},
        json={"model": "llama70b", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 8},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["served_model"] == "test-served-model"
    assert body["headers"]["X-Priority-Class"] == "Standard"


def test_rejects_unknown_model():
    r = client.post(
        "/admit",
        headers={"X-Tenant-ID": "standard-prod"},
        json={"model": "missing", "messages": [], "max_tokens": 1},
    )
    assert r.status_code == 404


def test_rejects_oversized_output_before_engine():
    r = client.post(
        "/admit",
        headers={"X-Tenant-ID": "standard-prod"},
        json={"model": "llama70b", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 999999},
    )
    assert r.status_code == 400
    assert "max_tokens" in r.text


def test_rpm_limit_returns_429_with_retry_after():
    for _ in range(120):
        assert client.post(
            "/admit",
            headers={"X-Tenant-ID": "standard-prod"},
            json={"model": "llama70b", "messages": [], "max_tokens": 1},
        ).status_code == 200
    r = client.post(
        "/admit",
        headers={"X-Tenant-ID": "standard-prod"},
        json={"model": "llama70b", "messages": [], "max_tokens": 1},
    )
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "30"


def test_metrics_expose_admission_outcomes():
    client.post(
        "/admit",
        headers={"X-Tenant-ID": "standard-prod"},
        json={"model": "llama70b", "messages": [], "max_tokens": 1},
    )
    metrics = client.get("/metrics").text
    assert 'gateway_requests_total{tenant="standard-prod",priority_class="Standard",outcome="admitted"} 1' in metrics
