from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import ps1_scenario as ps


def minimal_scenario() -> dict:
    return {
        "schema_version": 1,
        "id": "unit_slice",
        "target": {"disc": "build/test.cue", "expected_serial": "SCUS-94288"},
        "playback": {"movie": "fixture.movie.json"},
        "phases": [{
            "id": "check",
            "trigger": {"type": "movie_frame", "target": 10},
            "assertions": [{"id": "value", "type": "memory", "address": 0x80010000,
                            "width": "u16", "op": "eq", "expected": 7}],
        }],
    }


def test_schema_parses_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "scenario.yaml"
    path.write_text(yaml.safe_dump(minimal_scenario()))
    assert ps.load_scenario(path)["id"] == "unit_slice"


def test_schema_accepts_interpreter_realtime_movie_trigger() -> None:
    doc = minimal_scenario()
    doc["launch"] = {"profile": "repro", "execution_mode": "Interpreter"}
    doc["phases"][0]["trigger"]["type"] = "movie_frame_realtime"
    ps.validate_scenario(doc)


def test_schema_rejects_duplicate_assertion_ids() -> None:
    doc = minimal_scenario()
    doc["phases"][0]["assertions"] *= 2
    with pytest.raises(ps.ScenarioError, match="duplicate assertion"):
        ps.validate_scenario(doc)


class MemoryClient:
    def call(self, method, params=None, timeout=None):
        assert method == "debugger.readMemory"
        return {"hex": "0700"}


def test_memory_assertion_reports_actual_and_divergence(tmp_path: Path) -> None:
    doc = minimal_scenario()
    runner = ps.ScenarioRunner(tmp_path / "s.yaml", doc)
    assertion = doc["phases"][0]["assertions"][0]
    passed = runner._assertion(MemoryClient(), assertion)
    assert passed["passed"] is True
    assert passed["actual"] == 7
    failed = runner._assertion(MemoryClient(), {**assertion, "expected": 8})
    assert failed["passed"] is False
    assert failed["address"] == "0x80010000"
    assert failed["expected"] == 8 and failed["actual"] == 7


class ScreenshotClient:
    def call(self, method, params=None, timeout=None):
        if method == "emulator.captureFrame":
            path = Path(params["path"])
            path.write_bytes(b"captured-frame")
            return {"captured": True, "path": str(path), "frame": 123}
        assert method == "emulator.advanceFrames"
        return {"execution": {"completed": True, "advanced_frames": 1}}


def test_screenshot_capture_can_persist_outside_disposable_config(tmp_path: Path) -> None:
    doc = minimal_scenario()
    evidence_dir = tmp_path / "report" / "evidence"
    evidence_dir.mkdir(parents=True)
    runner = ps.ScenarioRunner(tmp_path / "s.yaml", doc, evidence_dir=evidence_dir)
    runner.evidence_dir = runner.requested_evidence_dir
    capture = runner._capture(
        ScreenshotClient(), {"id": "visual_check", "type": "screenshot"})
    expected_path = evidence_dir / "visual_check.png"
    assert capture["result"]["path"] == str(expected_path)
    assert capture["result"]["sha256"] == ps.sha256(expected_path)
    assert expected_path.read_bytes() == b"captured-frame"


class FakeClient:
    def __init__(self, host, port, transport):
        self.authenticated = None
        self.calls = []

    def authenticate(self, token):
        self.authenticated = token

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, params or {}))
        return {}


def test_isolated_lifecycle_uses_unique_values_and_owned_cleanup(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "unique-config"
    commands = []

    def fake_run(command, **kwargs):
        commands.append([str(c) for c in command])
        if "stop" in command:
            (cfg / "instance.pid").unlink(missing_ok=True)
            return SimpleNamespace(returncode=0, stdout="Stopped isolated instance.", stderr="")
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "instance.pid").write_text("4242")
        token = command[command.index("--token") + 1]
        return SimpleNamespace(returncode=0, stdout=f"READY token={token}", stderr="")

    monkeypatch.setattr(ps.tempfile, "mkdtemp", lambda **kwargs: str(cfg))
    monkeypatch.setattr(ps, "_free_port", lambda: 34567)
    monkeypatch.setattr(ps.secrets, "token_urlsafe", lambda n: "unit-secret-token")
    monkeypatch.setattr(ps.subprocess, "run", fake_run)
    monkeypatch.setattr(ps, "DebuggerClient", FakeClient)
    disc = tmp_path / "disc.cue"
    disc.write_text('FILE "disc.bin" BINARY\n')
    report = {}
    lifecycle = ps.IsolatedLifecycle(disc, "repro", report, execution_mode="Interpreter")
    client = lifecycle.start()
    assert client.authenticated == "abl_unit-secret-token"
    assert report["lifecycle"]["config_dir"] == str(cfg.resolve())
    assert report["lifecycle"]["port"] == 34567
    assert report["lifecycle"]["execution_mode"] == "Interpreter"
    assert "unit-secret-token" not in report["lifecycle"]["launch_stdout"]
    start_token = commands[0][commands[0].index("--token") + 1]
    assert start_token == "abl_unit-secret-token"
    assert not start_token.startswith("-")
    start = commands[0]
    assert start[start.index("--execution-mode") + 1] == "Interpreter"
    lifecycle.cleanup()
    assert report["lifecycle"]["cleanup"]["success"] is True
    stop = commands[-1]
    assert stop[1] == "stop"
    assert stop[stop.index("--config-dir") + 1] == str(cfg.resolve())


def test_cleanup_without_started_instance_never_calls_stop(tmp_path: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(ps.subprocess, "run", lambda *a, **k: calls.append(a))
    report = {"lifecycle": {"cleanup": {"attempted": False, "success": False}}}
    lifecycle = ps.IsolatedLifecycle(tmp_path / "disc.cue", "repro", report)
    lifecycle.cleanup()
    assert calls == []
