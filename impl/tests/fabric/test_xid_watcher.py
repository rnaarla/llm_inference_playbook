import importlib.util
from pathlib import Path

module_path = Path("impl/fabric/xid-watcher/watcher.py")
spec = importlib.util.spec_from_file_location("xid_watcher", module_path)
watcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watcher)


def test_parse_xids_from_env(monkeypatch):
    monkeypatch.setenv("XID_RECOVERABLE", "1, 2")
    assert watcher.parse_xids("XID_RECOVERABLE", "") == {1, 2}


def test_run_renders_template(monkeypatch):
    calls = []
    monkeypatch.setattr(watcher, "NODE_NAME", "node-a")
    monkeypatch.setattr(watcher.subprocess, "run", lambda cmd, shell, check: calls.append(cmd))
    watcher.run("echo ${NODE_NAME} ${XID}", 79)
    assert calls == ["echo node-a 79"]
