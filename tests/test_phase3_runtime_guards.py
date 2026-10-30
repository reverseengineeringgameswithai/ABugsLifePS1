"""Unit coverage for Phase-3 live-evidence provenance and log-completeness guards."""

import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools.phase3_spin_functional as spin
import tools.phase3_thud_trace as thud
import tools.phase3_render_descriptors as render_descriptors
import tools.live_session_provenance as provenance
from tools.live_session_provenance import (inspect_state_before_load,
                                           retained_pristine_save_gaps,
                                           select_pristine_save_anchors,
                                           write_live_evidence)
from tools.provision_clean_checkout_inputs import digest, provision


class FakeRig:
    def __init__(self, media=None, pages=None):
        self.media = list(media or [])
        self.pages = list(pages or [])

    def call(self, method, params=None):
        if method == "debugger.status":
            return {"paused": True, "running": False}
        if method == "emulator.getMediaInfo":
            return self.media.pop(0)
        if method == "accessLog.get":
            return self.pages.pop(0)
        raise AssertionError(f"unexpected RPC {method} {params}")


def test_spin_media_guard_rejects_a_swap_during_hash(monkeypatch):
    before = {"has_media": True, "path": "/disc/a.cue", "game_serial": "SCUS-94288",
              "subimage_count": 1, "subimage_index": 0}
    after = dict(before, path="/disc/b.cue")
    rig = FakeRig(media=[before, after])
    monkeypatch.setattr(spin, "verify_pristine_media_path",
                        lambda path: {"pristine_verified": True, "mounted_path": path})
    with pytest.raises(SystemExit, match="media changed while hashing"):
        spin.verified_media_identity(
            rig, {"game_serial": "SCUS-94288", "game_title": "A Bug's Life"})


def test_thud_media_guard_rejects_a_swap_during_hash(monkeypatch):
    before = {"has_media": True, "path": "/disc/a.cue", "game_serial": "SCUS-94288",
              "subimage_count": 1, "subimage_index": 0}
    after = dict(before, subimage_index=1)
    rig = FakeRig(media=[before, after])
    monkeypatch.setattr(thud, "verify_pristine_media_path",
                        lambda path: {"pristine_verified": True, "mounted_path": path})
    with pytest.raises(SystemExit, match="media changed while hashing"):
        thud.verified_media_identity(
            rig, {"game_serial": "SCUS-94288", "game_title": "A Bug's Life"})


def test_spin_access_log_guard_rejects_total_drift():
    watch = {"watch_id": 7, "hit_count": 2, "max_events": 100}
    rig = FakeRig(pages=[
        {"total": 2, "events": [{"event_id": 1}], "truncated": False,
         "watches": [watch]},
        {"total": 3, "events": [{"event_id": 2}], "truncated": False,
         "watches": [watch]},
    ])
    accounting, events = spin.checked_access_log(rig, 7)
    assert len(events) == 2
    assert accounting["totals_stable"] is False
    assert accounting["complete"] is False


def test_spin_access_log_guard_rejects_watch_cap_saturation():
    watch = {"watch_id": 7, "hit_count": 100, "max_events": 100}
    rig = FakeRig(pages=[
        {"total": 1, "events": [{"event_id": 1}], "truncated": False,
         "watches": [watch]},
    ])
    accounting, _ = spin.checked_access_log(rig, 7)
    assert accounting["watch_cap_saturated"] is True
    assert accounting["complete"] is False


def test_thud_access_log_guard_rejects_server_truncation():
    watches = [
        {"watch_id": 4, "hit_count": 1, "max_events": 100},
        {"watch_id": 5, "hit_count": 1, "max_events": 100},
    ]
    rig = FakeRig(pages=[
        {"total": 2, "events": [{"event_id": 1}, {"event_id": 2}],
         "truncated": True, "watches": watches},
    ])
    accounting, _ = thud.checked_access_log(rig, {4, 5})
    assert accounting["truncated"] is True
    assert accounting["complete"] is False


def test_preload_state_inspection_rejects_foreign_media(tmp_path):
    class StateClient:
        def call(self, method, params):
            assert method == "emulator.getStateInfo"
            return {"exists": True, "valid": True, "serial": "SLUS-00001",
                    "path": params["path"], "version": 84}

    with pytest.raises(SystemExit, match="save-state/media mismatch"):
        inspect_state_before_load(
            StateClient(), tmp_path / "foreign.sav",
            {"game_serial": "SCUS-94288"})


def test_same_serial_non_pristine_save_is_rejected_before_load():
    class StateClient:
        def call(self, method, params):
            assert method == "emulator.getStateInfo"
            return {
                "exists": True, "valid": True, "serial": "SCUS-94288",
                "media_path": "/operator/build/ABL_ALLMODS.cue",
                "path": params["path"], "version": 84,
            }

    with pytest.raises(SystemExit, match="media_class='non_pristine'"):
        inspect_state_before_load(
            StateClient(), ROOT / "collecting_FLIK_LEVELTRAINING.movie.sav",
            {"game_serial": "SCUS-94288"})


def test_embedded_mod_media_is_rejected_even_for_a_pristine_declared_save(monkeypatch):
    class StateClient:
        def call(self, method, params):
            assert method == "emulator.getStateInfo"
            return {
                "exists": True, "valid": True, "serial": "SCUS-94288",
                "media_path": "/operator/build/ABL_ALLMODS.cue",
                "path": params["path"], "version": 84,
            }

    monkeypatch.setattr(
        provenance, "_verify_pristine_state_media",
        lambda path: {"pristine_verified": False, "mounted_path": path})
    with pytest.raises(SystemExit, match="embedded media is not pristine"):
        inspect_state_before_load(
            StateClient(), ROOT / "level01.sav",
            {"game_serial": "SCUS-94288", "game_path": "/mounted/pristine.cue"})


def test_anchor_selector_uses_the_replayed_pristine_training_replacement():
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    anchors, selection = select_pristine_save_anchors(baseline)
    assert len(anchors) == 42
    assert selection["anchors_requested"] == 42
    assert selection["anchors_accepted"] == 42
    assert selection["anchors_rejected"] == 0
    assert selection["rejected"] == []
    assert ("training", "phase3_pristine_training_gameplay_i5.sav") in anchors
    assert ("training_completion", "training_all_stuff_collected_ending.sav") in anchors


def test_retained_origin_guard_recomputes_and_rejects_non_pristine_pin():
    entries = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())["entries"]
    rel = "collecting_FLIK_LEVELTRAINING.movie.sav"
    doc = {
        "anchors_used": 1,
        "fixture_sha256": {rel: entries[rel]["sha256"]},
        "run_provenance": {"anchor": {
            "saves": [rel],
            "fixture_sha256": {rel: entries[rel]["sha256"]},
            "state_inspections": [{
                "path": str(ROOT / rel), "exists": True, "valid": True,
                "serial": "SCUS-94288",
                "media_path": "/operator/build/ABL_ALLMODS.cue",
            }],
        }},
    }
    gaps = retained_pristine_save_gaps(doc)
    assert any("media_class='non_pristine'" in gap for gap in gaps)
    assert any("embedded media path" in gap for gap in gaps)


def test_semantically_identical_live_replay_preserves_retained_bytes(tmp_path):
    path = tmp_path / "evidence.json"
    first = {
        "generated": "2026-07-13",
        "run_provenance": {
            "command": "tool --port 1", "generator_sha256": "abc",
            "recorded_utc": "old", "debugger": {
                "config_dir": "/tmp/a", "port": 1, "token_sha256": "one",
                "owned_pid": 10,
            },
            "anchor": {"state_inspections": [{
                "path": "/checkout/a/level01.sav", "exists": True,
                "valid": True, "serial": "SCUS-94288", "version": 84,
                "timestamp": 1_783_011_223,
            }]},
            "cleanup": {"owned_pid_stopped": True,
                        "launcher_output": "Stopped pid 10"},
        },
        "observation": {"value": 7},
    }
    assert write_live_evidence(path, first) is True
    retained = path.read_bytes()
    replay = {
        **first,
        "generated": "2026-07-14",
        "run_provenance": {
            **first["run_provenance"],
            "command": "tool --port 2", "recorded_utc": "new",
            "debugger": {
                "config_dir": "/tmp/b", "port": 2, "token_sha256": "two",
                "owned_pid": 11,
            },
            "anchor": {"state_inspections": [{
                "path": "/checkout/b/level01.sav", "exists": True,
                "valid": True, "serial": "SCUS-94288", "version": 84,
                "timestamp": 1_784_016_658,
            }]},
            "cleanup": {"owned_pid_stopped": True,
                        "launcher_output": "Stopped pid 11"},
        },
    }
    assert write_live_evidence(path, replay) is False
    assert path.read_bytes() == retained


def test_snapshot_replay_paths_and_manifest_digest_are_only_path_scoped_volatile(
        tmp_path):
    """A fresh immutable sibling/manifest must not rewrite equal observations.

    The snapshot manifest digest includes its creation time and random sibling
    name.  Runtime/support-tree digests remain semantic and must still rewrite.
    """
    path = tmp_path / "transition.json"
    first = {
        "run_provenance": {
            "duckstation": {
                "binary_path": "/duckstation/bin/duckstation-qt.phase3-verifier-one",
                "binary_sha256": "a" * 64,
            },
            "toolchain_snapshot": {
                "path": "/tmp/one/snapshot_manifest.json",
                "manifest_sha256": "b" * 64,
                "binary_sha256": "a" * 64,
                "runtime_tree": {"manifest_sha256": "c" * 64},
            },
            "cleanup": {
                "private_binary_path":
                    "/duckstation/bin/duckstation-qt.phase3-verifier-one",
                "private_binary_sha256": "a" * 64,
            },
        },
        "observation": {"stages": 16},
    }
    assert write_live_evidence(path, first) is True
    retained = path.read_bytes()
    replay = json.loads(json.dumps(first))
    replay["run_provenance"]["duckstation"]["binary_path"] = \
        "/duckstation/bin/duckstation-qt.phase3-verifier-two"
    replay["run_provenance"]["toolchain_snapshot"].update({
        "path": "/tmp/two/snapshot_manifest.json",
        "manifest_sha256": "d" * 64,
    })
    replay["run_provenance"]["cleanup"]["private_binary_path"] = \
        "/duckstation/bin/duckstation-qt.phase3-verifier-two"
    assert write_live_evidence(path, replay) is False
    assert path.read_bytes() == retained

    replay["run_provenance"]["toolchain_snapshot"]["runtime_tree"][
        "manifest_sha256"] = "e" * 64
    assert write_live_evidence(path, replay) is True


def test_render_descriptor_integer_keys_do_not_cause_a_false_rewrite(tmp_path):
    """The live replay and retained JSON must compare in the same key domain."""
    path = tmp_path / "phase3_render_descriptors.json"
    first = {
        "generated": "2026-07-13",
        "per_anchor": {
            "stage01": {
                "pointers": ["0x80081D98"],
                "descriptors": {0: "000102030405060708090a0b"},
            },
        },
    }
    assert render_descriptors.write_render_evidence(path, first) is True
    retained = path.read_bytes()
    assert "0" in json.loads(retained)["per_anchor"]["stage01"]["descriptors"]

    replay = {**first, "generated": "2026-07-14"}
    assert render_descriptors.write_render_evidence(path, replay) is False
    assert path.read_bytes() == retained


def test_clean_provision_mtime_does_not_change_semantic_live_evidence(tmp_path):
    operator_fixture = tmp_path / "operator/level01.sav"
    checkout_fixture = tmp_path / "checkout/level01.sav"
    operator_fixture.parent.mkdir()
    operator_fixture.write_bytes(b"hash-pinned save bytes")
    os.utime(operator_fixture, (1_700_000_000, 1_700_000_000))
    row = {
        "class": "pristine",
        "source": operator_fixture,
        "target": checkout_fixture,
        "algorithm": "sha256",
        "digest": digest(operator_fixture, "sha256"),
        "size": operator_fixture.stat().st_size,
    }
    assert provision(row, verify_only=False) == "copied"
    # copyfile preserves bytes but not the source mtime, matching a fresh
    # clean-checkout provision from the centrally pinned operator fixture set.
    source_timestamp = int(operator_fixture.stat().st_mtime)
    provisioned_timestamp = int(checkout_fixture.stat().st_mtime)
    assert provisioned_timestamp != source_timestamp

    evidence_path = tmp_path / "record_probe.json"
    common = {
        "run_provenance": {"anchor": {"state_inspections": [{
            "exists": True, "valid": True, "serial": "SCUS-94288",
            "version": 84, "file_size": row["size"],
            "fixture_declaration": {"sha256": row["digest"], "size": row["size"]},
        }]}},
        "observation": {"typed_bytes": 181, "record_bytes": 524},
    }
    retained = json.loads(json.dumps(common))
    retained["run_provenance"]["anchor"]["state_inspections"][0].update({
        "path": str(operator_fixture), "timestamp": source_timestamp,
    })
    replay = json.loads(json.dumps(common))
    replay["run_provenance"]["anchor"]["state_inspections"][0].update({
        "path": str(checkout_fixture), "timestamp": provisioned_timestamp,
    })
    assert write_live_evidence(evidence_path, retained) is True
    banked = evidence_path.read_bytes()
    assert write_live_evidence(evidence_path, replay) is False
    assert evidence_path.read_bytes() == banked


def test_live_replay_writes_when_semantic_observation_changes(tmp_path):
    path = tmp_path / "evidence.json"
    assert write_live_evidence(path, {"observation": 1}) is True
    assert write_live_evidence(path, {"observation": 2}) is True
    assert json.loads(path.read_text())["observation"] == 2


def test_every_phase3_save_state_loader_uses_preload_inspection():
    offenders = []
    for path in sorted((ROOT / "tools").glob("phase3_*.py")):
        text = path.read_text()
        if "emulator.loadState" in text and "inspect_state_before_load" not in text:
            offenders.append(path.name)
    assert offenders == []


def test_affected_phase1_phase2_loaders_use_preload_origin_inspection():
    for rel in (
        "tools/phase1_census.py", "tools/phase2_oracle.py",
        "tools/phase2_death_matrix.py", "tools/phase2_gate_residuals.py",
        "tools/phase2_presentation_oracle.py", "tools/phase2_pool_arc_oracle.py",
    ):
        text = (ROOT / rel).read_text()
        assert "collecting_FLIK_LEVELTRAINING.movie.sav" not in text, rel
        assert "phase3_pristine_training_gameplay_i5.sav" in text, rel
        assert "inspect_state_before_load" in text, rel


def test_phase2_movie_and_save_collectors_guard_repro_profile_and_movie_order():
    for rel in ("tools/phase2_gate_residuals.py",
                "tools/phase2_pool_arc_oracle.py"):
        text = (ROOT / rel).read_text()
        assert "validate_repro_config" in text, rel
        assert 'add_argument("--repro-config-dir", required=True' in text, rel
        first_movie = text.index('c.call("movie.load"')
        save_lane = min(pos for marker in ("# ---- audio baseline", "# ---- arc sentinel")
                        if (pos := text.find(marker)) >= 0)
        assert first_movie < save_lane, rel
        first_playback = text.index('c.call("movie.startPlayback"')
        first_pause = text.index('c.call("debugger.pause"', first_playback)
        first_advance = text.index('c.call("movie.advanceToFrame"', first_playback)
        assert first_playback < first_pause < first_advance, rel

    compare = (ROOT / "tools/phase2_compare.py").read_text()
    assert "inspect_state_before_load" in compare
    assert compare.index("# ---- movie lane") < compare.index("# ---- anchor lane")
    playback = compare.index('c.call("movie.startPlayback"')
    assert playback < compare.index('c.call("debugger.pause"', playback)
