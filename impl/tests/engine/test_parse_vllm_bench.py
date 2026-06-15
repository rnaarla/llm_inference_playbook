
import yaml

from impl.engine.bench.parse_vllm_bench import first_float, main


def test_first_float_uses_first_matching_pattern():
    assert first_float([r"missing ([0-9.]+)", r"value ([0-9.]+)"], "value 12.5") == 12.5


def test_parser_writes_schema_shape(tmp_path, monkeypatch):
    log = tmp_path / "bench.log"
    out = tmp_path / "report.yaml"
    log.write_text("TTFT p50 100\nTTFT p95 200\nTPOT p50 10\nTPOT p95 20\nOutput throughput 300\nInput throughput 900\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "parse_vllm_bench.py",
            "--log",
            str(log),
            "--profile",
            "p",
            "--model",
            "m",
            "--operator",
            "op",
            "--out",
            str(out),
        ],
    )
    assert main() == 0
    report = yaml.safe_load(out.read_text())["benchmark_report"]
    assert report["results"]["ttft_ms"]["p50"] == 100
    assert report["results"]["goodput_knee"]["output_tok_s"] == 300
