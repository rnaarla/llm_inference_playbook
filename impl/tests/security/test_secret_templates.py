from pathlib import Path

import yaml


def test_external_secret_template_has_no_real_values():
    docs = list(yaml.safe_load_all(Path("impl/secrets/external-secrets.example.yaml").read_text()))
    assert len(docs) == 3
    rendered = Path("impl/secrets/external-secrets.example.yaml").read_text()
    assert "REPLACE_WITH_" in rendered
    assert "registry.internal" not in rendered


def test_rbac_review_checklist_exists():
    text = Path("impl/security/rbac-review-checklist.md").read_text()
    assert "No wildcard" in text
    assert "XID Watcher" in text
