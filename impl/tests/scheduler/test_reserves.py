from impl.scheduler.reserves.reserves import ReserveConfig, ReserveLedger


def test_reserve_ledger_admit_and_release_once():
    ledger = ReserveLedger(ReserveConfig(knee_concurrency=10, tenant_kv_tokens={"t": 100}))
    decision = ledger.admit("r1", "t", "Critical", 50)
    assert decision.admitted
    assert not ledger.admit("r1", "t", "Critical", 10).admitted
    assert ledger.release("r1")
    assert not ledger.release("r1")


def test_tenant_kv_cap_blocks_large_request():
    ledger = ReserveLedger(ReserveConfig(knee_concurrency=10, tenant_kv_tokens={"t": 100}))
    decision = ledger.admit("r1", "t", "Standard", 101)
    assert not decision.admitted
    assert decision.reason == "tenant_kv_cap_exceeded"


def test_reserve_config_rejects_invalid_fraction_sum():
    try:
        ReserveConfig(knee_concurrency=1, critical_fraction=0.5, standard_fraction=0.5, sheddable_fraction=0.5)
    except ValueError as exc:
        assert "sum" in str(exc)
    else:
        raise AssertionError("expected ValueError")
