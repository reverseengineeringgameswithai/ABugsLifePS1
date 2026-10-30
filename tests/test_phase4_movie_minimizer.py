"""Contract and mutation tests for hierarchical movie/scenario minimization."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_movie_minimizer as minimizer  # noqa: E402


def hex64(label: bytes) -> str:
    return hashlib.sha256(label).hexdigest()


def valid_receipt(movie_hash: str, scenario_hash: str | None = None,
                  assertions: list[str] | None = None) -> dict:
    return {
        "schema": minimizer.RECEIPT_SCHEMA,
        "movie_sha256": movie_hash,
        "scenario_sha256": scenario_hash,
        "assertion_ids": assertions or [],
        "runtime": {
            "emulator": "DuckStation",
            "execution_mode": "Interpreter",
            "movie_execution_mode": "Interpreter",
            "config_dir": "/tmp/duckstation-minimizer-test",
            "isolated": True,
            "config_recreated": True,
            "normal_profile_used": False,
            "loopback_host": "127.0.0.1",
            "port": 42123,
            "token_sha256": hex64(b"token"),
            "media_sha256": hex64(b"media"),
            "binary_sha256": hex64(b"binary"),
            "config_identity_sha256": hex64(b"config"),
            "launcher_sha256": hex64(b"launcher"),
            "media_verified": True,
            "media_serial": "SCUS-94288",
            "movie_reproducible": True,
            "source_revision": "test-revision-dirty-recorded",
            "settings": {"verified": True, "cpu_execution_mode": "Interpreter"},
            "pid_owned_by_config": True,
            "cleanup_complete": True,
        },
        "anchor": {"source_class": "cold_boot", "candidate_class": "cold_boot",
                   "identity_verified": True, "identity_sha256": hex64(b"anchor")},
        "instrumentation_rearmed_after_load": True,
        "replays": [
            {"role": "assertion", "run_id": "assertion-1", "passed": True,
             "errors": [], "truncated": False, "movie_sha256": movie_hash},
            {"role": "control", "run_id": "control-1", "passed": True,
             "errors": [], "truncated": False, "movie_sha256": movie_hash},
        ],
    }


def test_synthetic_pilot_is_reproducible_and_non_runtime():
    report = minimizer.build_pilot()
    assert report["schema"] == minimizer.PILOT_SCHEMA
    assert report["runtime_evidence"] is False
    assert report["summary"]["frames_before"] == 12
    assert report["summary"]["frames_after"] == 2
    assert report["summary"]["active_frames_after"] == 2
    assert report["production_contract"]["execution_mode"] == "Interpreter"
    assert (ROOT / "analysis/phase4_movie_minimizer_pilot.json").read_bytes() == \
        minimizer.canonical_json(report)


def test_receipt_accepts_only_full_interpreter_assertion_and_control_contract():
    movie_hash = hex64(b"movie")
    receipt = valid_receipt(movie_hash, assertions=["assertion-a"])
    minimizer.validate_replay_receipt(
        receipt, movie_sha256=movie_hash, scenario_sha256=None,
        anchor="cold_boot", expected_assertions=["assertion-a"],
        expected_media_serial="SCUS-94288")
    mutations = [
        ("schema", lambda row: row.update(schema="wrong/1")),
        ("emulator", lambda row: row["runtime"].update(emulator="OtherEmulator")),
        ("cached execution", lambda row: row["runtime"].update(execution_mode="CachedInterpreter")),
        ("cached movie", lambda row: row["runtime"].update(movie_execution_mode="CachedInterpreter")),
        ("relative config", lambda row: row["runtime"].update(config_dir="relative/config")),
        ("shared config", lambda row: row["runtime"].update(isolated=False)),
        ("stale config", lambda row: row["runtime"].update(config_recreated=False)),
        ("normal profile", lambda row: row["runtime"].update(normal_profile_used=True)),
        ("remote host", lambda row: row["runtime"].update(loopback_host="192.0.2.1")),
        ("bad port", lambda row: row["runtime"].update(port=0)),
        ("boolean port", lambda row: row["runtime"].update(port=True)),
        ("token hash", lambda row: row["runtime"].update(token_sha256="bad")),
        ("media hash", lambda row: row["runtime"].update(media_sha256="bad")),
        ("binary hash", lambda row: row["runtime"].update(binary_sha256="bad")),
        ("config hash", lambda row: row["runtime"].update(config_identity_sha256="bad")),
        ("launcher hash", lambda row: row["runtime"].update(launcher_sha256="bad")),
        ("unverified media", lambda row: row["runtime"].update(media_verified=False)),
        ("media serial", lambda row: row["runtime"].update(media_serial="WRONG")),
        ("nonreproducible movie", lambda row: row["runtime"].update(movie_reproducible=False)),
        ("unverified settings", lambda row: row["runtime"]["settings"].update(verified=False)),
        ("cached setting", lambda row: row["runtime"]["settings"].update(
            cpu_execution_mode="CachedInterpreter")),
        ("source revision", lambda row: row["runtime"].update(source_revision="")),
        ("unowned pid", lambda row: row["runtime"].update(pid_owned_by_config=False)),
        ("cleanup incomplete", lambda row: row["runtime"].update(cleanup_complete=False)),
        ("movie binding", lambda row: row.update(movie_sha256=hex64(b"other-movie"))),
        ("scenario binding", lambda row: row.update(scenario_sha256=hex64(b"scenario"))),
        ("anchor source", lambda row: row["anchor"].update(source_class="save_state")),
        ("anchor candidate", lambda row: row["anchor"].update(candidate_class="save_state")),
        ("anchor identity", lambda row: row["anchor"].update(identity_verified=False)),
        ("anchor hash", lambda row: row["anchor"].update(identity_sha256="bad")),
        ("assertion universe", lambda row: row.update(assertion_ids=["different"])),
        ("duplicate assertions", lambda row: row.update(
            assertion_ids=["assertion-a", "assertion-a"])),
        ("non-string assertion", lambda row: row.update(assertion_ids=[1])),
        ("missing replay", lambda row: row["replays"].pop()),
        ("duplicate role", lambda row: row["replays"][1].update(role="assertion")),
        ("control failed", lambda row: row["replays"][1].update(passed=False)),
        ("control errors", lambda row: row["replays"][1].update(errors=["failure"])),
        ("control truncated", lambda row: row["replays"][1].update(truncated=True)),
        ("replay binding", lambda row: row["replays"][0].update(
            movie_sha256=hex64(b"other-movie"))),
        ("same run", lambda row: row["replays"][1].update(run_id="assertion-1")),
        ("empty run", lambda row: row["replays"][0].update(run_id="")),
        ("not rearmed", lambda row: row.update(instrumentation_rearmed_after_load=False)),
        ("raw secret", lambda row: row["runtime"].update(token="do-not-retain")),
        ("nested password", lambda row: row["runtime"].update(
            nested={"password": "do-not-retain"})),
    ]
    for label, mutate in mutations:
        changed = copy.deepcopy(receipt)
        mutate(changed)
        with pytest.raises(minimizer.MinimizerError, match="."):
            minimizer.validate_replay_receipt(
                changed, movie_sha256=movie_hash, scenario_sha256=None,
                anchor="cold_boot", expected_assertions=["assertion-a"],
                expected_media_serial="SCUS-94288")


def test_movie_validation_and_anchor_class_are_fail_closed():
    policy = minimizer.load_policy()
    movie = minimizer.synthetic_movie()
    assert minimizer.anchor_class(movie, None) == "cold_boot"
    state_movie = copy.deepcopy(movie)
    state_movie["start_state"] = {"path": "/external/pinned.sav", "from_boot": False}
    assert minimizer.anchor_class(state_movie, None) == "save_state"
    broken = copy.deepcopy(movie)
    broken["frames"][2]["frame"] = 10
    with pytest.raises(minimizer.MinimizerError, match="contiguous"):
        minimizer.validate_movie(broken, policy)
    broken = copy.deepcopy(movie)
    broken["frames"][0]["ports"]["0"]["lx"] = 300
    with pytest.raises(minimizer.MinimizerError, match="outside"):
        minimizer.validate_movie(broken, policy)
    broken = copy.deepcopy(movie)
    broken["version"] = 4
    with pytest.raises(minimizer.MinimizerError, match="version"):
        minimizer.validate_movie(broken, policy)
    broken = copy.deepcopy(movie)
    broken["frames"][0]["ports"]["0"]["turbo"] = True
    with pytest.raises(minimizer.MinimizerError, match="unknown"):
        minimizer.validate_movie(broken, policy)


def test_minimizer_never_accepts_without_evaluator_and_preserves_source(tmp_path):
    policy = minimizer.load_policy()
    movie = minimizer.validate_movie(minimizer.synthetic_movie(), policy)
    calls = []

    def evaluator(candidate, _scenario):
        states = [frame["ports"]["0"] for frame in candidate["frames"]]
        accepted = any(row["cross"] for row in states) and any(row["square"] for row in states)
        calls.append(accepted)
        return minimizer.Evaluation(accepted)

    result = minimizer.Minimizer(movie, None, policy, evaluator, 256).run()
    assert result["summary"]["frames_after"] == 2
    assert len(calls) == result["summary"]["evaluations"]
    source = tmp_path / "source.movie.json"
    source.write_bytes(minimizer.canonical_json(movie))
    external = tmp_path.parent / (tmp_path.name + "-external")
    before = source.read_bytes()
    paths = minimizer.write_external_result(result, external, source)
    assert source.read_bytes() == before
    assert all(path.is_file() for path in paths if path)
    with pytest.raises(minimizer.MinimizerError, match="overwrite existing"):
        minimizer.write_external_result(result, external, source)
    with pytest.raises(minimizer.MinimizerError, match="outside"):
        minimizer.write_external_result(result, ROOT / "analysis/minimized", source)


def test_dangling_output_symlink_cannot_redirect_into_repository(tmp_path, monkeypatch):
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    monkeypatch.setattr(minimizer, "ROOT", fake_root)
    policy = minimizer.load_policy()
    movie = minimizer.validate_movie(minimizer.synthetic_movie(), policy)
    result = {"movie": movie, "scenario": None,
              "summary": {"frames_before": 12, "frames_after": 12}, "history": []}
    source = tmp_path / "source.movie.json"
    source.write_bytes(minimizer.canonical_json(movie))
    output = tmp_path / "external"
    output.mkdir()
    target = fake_root / "analysis/redirected.movie.json"
    target.parent.mkdir()
    link = output / f"{source.stem}.minimized.json"
    link.symlink_to(target)

    with pytest.raises(minimizer.MinimizerError, match="overwrite existing"):
        minimizer.write_external_result(result, output, source)
    assert link.is_symlink()
    assert not target.exists()
    assert not (output / f"{source.stem}.minimization-report.json").exists()


def test_scenario_assertion_universe_is_immutable():
    scenario = {"playback": {"movie": "x.movie.json", "start_frame": 0},
                "phases": [{"id": "p", "trigger": {"type": "movie_frame", "target": 9},
                            "assertions": [{"id": "a"}, {"id": "b"}]}]}
    assert minimizer.assertion_ids(scenario) == ["a", "b"]
    scenario["phases"][0]["assertions"][1]["id"] = "a"
    with pytest.raises(minimizer.MinimizerError, match="duplicate"):
        minimizer.assertion_ids(scenario)


def test_frame_deletion_shifts_only_movie_frame_anchors():
    scenario = {
        "playback": {"movie": "x", "start_frame": 8},
        "phases": [
            {"trigger": {"type": "movie_frame", "target": 10}},
            {"trigger": {"type": "emulator_frame", "target": 100}},
        ],
    }
    shifted = minimizer.shift_scenario_after_delete(scenario, 2, 6)
    assert shifted["playback"]["start_frame"] == 4
    assert shifted["phases"][0]["trigger"]["target"] == 6
    assert shifted["phases"][1]["trigger"]["target"] == 100
    inside = minimizer.shift_scenario_after_delete(scenario, 7, 11)
    assert inside["playback"]["start_frame"] == 7
    assert inside["phases"][0]["trigger"]["target"] == 7
