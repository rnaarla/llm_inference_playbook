from hypothesis import given
from hypothesis import strategies as st

from impl.scheduler.wfq.scheduler import Request, WeightedFairQueue, WFQConfig


def test_weighted_queue_uses_fifo_tie_break_then_debt_ratio():
    q = WeightedFairQueue({"a": 2.0, "b": 1.0}, clock=lambda: 0.0)
    q.enqueue(Request("b1", "b", "Standard", 100, 0))
    q.enqueue(Request("a1", "a", "Standard", 100, 0))
    q.enqueue(Request("b2", "b", "Standard", 100, 0))

    assert q.dequeue().tenant == "b"  # equal score tie breaks by enqueue order
    assert q.dequeue().tenant == "a"  # b now has higher debt/weight


def test_reconcile_adds_actual_delta_to_debt():
    q = WeightedFairQueue({"a": 1.0}, clock=lambda: 0.0)
    q.enqueue(Request("a1", "a", "Standard", 10, 10))
    req = q.dequeue()
    q.reconcile(req.tenant, req.estimated_cost, 10, 40)
    assert q.snapshot().debt_by_tenant["a"] == 50


@given(weight=st.floats(min_value=0.1, max_value=10), cost=st.integers(min_value=1, max_value=10000))
def test_debt_ratio_scales_by_weight(weight, cost):
    q = WeightedFairQueue({"tenant": weight}, clock=lambda: 0.0)
    q.enqueue(Request("r", "tenant", "Standard", cost, 0))
    q.dequeue()
    assert q.debt_ratio()["tenant"] == cost / weight


def test_wfq_config_rejects_empty_tenants():
    try:
        WFQConfig.from_dict({"tenants": {}})
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:
        raise AssertionError("expected ValueError")
