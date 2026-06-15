from impl.scheduler.routing.cost_classifier import CostClassifier, RoutingConfig


def test_critical_requests_route_to_critical_pool():
    decision = CostClassifier().target_pool("Critical", 100_000, 1)
    assert decision.pool == "critical"
    assert decision.reason == "critical_priority"


def test_heavy_context_routes_to_heavy_pool():
    decision = CostClassifier(RoutingConfig(heavy_threshold_tokens=100)).target_pool("Standard", 90, 10)
    assert decision.pool == "heavy"


def test_negative_tokens_rejected():
    try:
        CostClassifier().classify_context(-1, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
