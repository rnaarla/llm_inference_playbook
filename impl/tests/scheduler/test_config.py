from impl.scheduler.config import SchedulerConfig


def test_scheduler_config_loads_combined_shape():
    cfg = SchedulerConfig.from_dict(
        {
            "scheduler": {
                "wfq": {"tenants": {"a": {"weight": 2}}},
                "reserves": {"kneeConcurrency": 10},
                "brownout": {"enabled": True},
                "routing": {"heavyThresholdTokens": 100},
            }
        }
    )
    assert cfg.wfq.weights()["a"] == 2
    assert cfg.reserves.knee_concurrency == 10
    assert cfg.routing.heavy_threshold_tokens == 100
