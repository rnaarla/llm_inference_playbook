from pathlib import Path


def test_all_charts_have_chart_and_values():
    charts = list(Path("impl/charts").glob("*/Chart.yaml"))
    assert charts
    for chart in charts:
        assert (chart.parent / "values.yaml").exists()


def test_chart_values_are_placeholder_driven():
    text = Path("impl/charts/inference-engine/values.yaml").read_text()
    assert "REPLACE_WITH_" in text
