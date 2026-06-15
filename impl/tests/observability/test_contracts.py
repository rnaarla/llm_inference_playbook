import json
from pathlib import Path

import yaml


def test_dashboard_json_is_valid():
    for path in Path("impl/observability/dashboards").glob("*.json"):
        assert json.loads(path.read_text())["panels"]


def test_observability_chart_runbook_values_exist():
    values = yaml.safe_load(Path("impl/charts/observability/values.yaml").read_text())
    runbooks = values["alerts"]["runbooks"]
    assert set(runbooks) == {"ttft", "queue", "kv", "xid"}
    for runbook in runbooks.values():
        assert Path(runbook).exists()
