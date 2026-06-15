import re
from pathlib import Path

import yaml


def _metrics_from_panels() -> set[str]:
    metrics: set[str] = set()
    for path in Path("playbook/dashboards/panels").glob("*.promql"):
        for token in path.read_text().replace("(", " ").replace(")", " ").replace(",", " ").split():
            if token.startswith(("vllm:", "gateway_", "tenant_", "DCGM_")):
                token = token.split("{", 1)[0].strip()
                token = re.sub(r"\[[^\]]+\]$", "", token)
                metrics.add(token)
    return metrics


def test_panel_metrics_are_declared_in_contract():
    contract = yaml.safe_load(Path("impl/observability/metric_contract.yaml").read_text())
    declared = set(contract["engine_metrics"] + contract["gateway_metrics"] + contract["gpu_metrics"])
    assert _metrics_from_panels() <= declared


def test_slo_config_has_positive_values():
    slos = yaml.safe_load(Path("impl/slo/slo.example.yaml").read_text())["slos"]
    assert all(value > 0 for value in slos.values())
