from pathlib import Path

import yaml
from jsonschema import validate

from impl.fabric.nccl.parse_nccl_baseline import max_busbw


def _load_json(path: str):
    import json

    return json.loads(Path(path).read_text())


def test_nccl_sample_matches_schema():
    validate(
        yaml.safe_load(Path("impl/fabric/nccl/samples/fabric_baseline.example.yaml").read_text()),
        _load_json("impl/fabric/nccl/fabric_baseline.schema.json"),
    )


def test_moe_sample_matches_schema():
    validate(
        yaml.safe_load(Path("impl/fabric/moe/samples/moe_validation.example.yaml").read_text()),
        _load_json("impl/fabric/moe/moe_validation.schema.json"),
    )


def test_nccl_parser_extracts_max_busbw():
    text = "  8  0  float  sum  -  -  123.4\n 16  0  float  sum  -  -  234.5\n"
    assert max_busbw(text) == 234.5
