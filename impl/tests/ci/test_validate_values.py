from pathlib import Path

from impl.ci.validate_values import walk


def test_detects_unresolved_placeholder():
    errors = walk({"x": "REPLACE_WITH_VALUE"})
    assert any("unresolved placeholder" in e for e in errors)


def test_detects_required_zero_values():
    errors = walk({"replicaCount": 0})
    assert errors == ["$.replicaCount: must be non-zero/non-empty"]


def test_safe_examples_do_not_contain_placeholders():
    for path in Path("examples").glob("*.local.yaml"):
        assert not [e for e in walk(__import__("yaml").safe_load(path.read_text())) if "unresolved placeholder" in e]
