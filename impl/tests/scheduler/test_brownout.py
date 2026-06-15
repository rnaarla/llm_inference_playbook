from impl.scheduler.brownout.controller import BrownoutConfig, BrownoutController


def test_brownout_escalates_cumulatively():
    c = BrownoutController()
    state = c.evaluate(0.96)
    assert state.rung == 3
    assert "shed_sheddable" in state.actions
    assert "route_standard_to_fallback_model" in state.actions


def test_brownout_recovers_with_hysteresis_intervals():
    c = BrownoutController(BrownoutConfig(stable_recovery_intervals=2))
    assert c.evaluate(0.91).rung == 2
    assert c.evaluate(0.80).rung == 2
    assert c.evaluate(0.80).rung == 1


def test_preemption_storm_goes_to_max_rung():
    state = BrownoutController().evaluate(0.10, preemption_storm=True)
    assert state.rung == 4
    assert "critical_only" in state.actions
