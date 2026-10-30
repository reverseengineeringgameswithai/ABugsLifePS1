"""Falsification and retained-evidence guards for Phase-4 A18."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_pause as pause  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_pause.json"
ARTIFACT_SHA256 = "913ea4b05d0384951c6588df3c909ebfb1cb4d1e1082c5a0a83ec96aee3ed1f0"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_static_pause_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = pause.build_static_census()
    assert recomputed == retained
    assert pause.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["gameplay_state_machine"]["sha256"] == (
        "83d8e37d6b8bf8cd13e65ec6be99837d6e2975e9c1926d6ce9a812133bedc1f0")
    assert recomputed["regions"]["gameplay_frame_render"]["sha256"] == (
        "c5b19582683528ba2505bbc3152069421a457c8a688fd340d59e372417ef92f7")


def test_pause_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = pause.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["menu"]["confirmation_default"] = "yes"
    assert "exit confirmation default is not bound" in \
        pause.static_census_gaps(mutated)
    executable = bytearray(pause.EXE_PATH.read_bytes())
    executable[pause._va_offset(0x8004F3AC)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        pause.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["breadth"]["summary"]["resume_count"] = 18
    assert "19-anchor pause breadth is incomplete" in pause.evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["ownership"]["execution_trace"]["hit_counts"][
        "player_update"] = 1
    assert "pause ownership or presentation evidence is incomplete" in \
        pause.evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["exit"]["summary"]["positive_transition"] = 0
    assert "pause exit lifecycle is incomplete" in pause.evidence_gaps(mutated)


def test_retained_pause_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert pause.evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_pause.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_pause_schema_and_scenario_bind_the_live_boundary():
    schema = yaml.safe_load((ROOT / "config/phase4_pause.yaml").read_text())
    scenario = yaml.safe_load((
        ROOT / "tools/scenarios/duckstation/pristine_pause_exit.yaml").read_text())
    assert schema["schema"] == "abl-phase4-pause/1"
    assert schema["input"]["start_mask"] == "0x0008"
    assert schema["menu"]["confirmation_default"] == "no"
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
    assert scenario["anchor"] == {
        "type": "save_state", "path": "level02.sav",
        "sha256": "9c4cd968151e8c2f630b89b58a9da90e9143de6bd5b14c859e2b783d12f7f152"}
    phases = {row["id"]: row for row in scenario["phases"]}
    assert set(phases) == {"pause_entry", "ordinary_resume", "confirmed_exit"}
    assert phases["confirmed_exit"]["trigger"]["value"] == 5


def test_completed_pause_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "pause_shell")
    finding = common.finding_index()["pause_shell_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_a18_baseline_is_solved_only_by_retained_pause_evidence():
    rows = common.baseline_rows()
    row = rows["A18_pause"]
    assert row["status"] == "solved"
    assert "analysis/phase4_pause.json" in row["fixture_have"]
    assert "small_pause_issue.sav" not in row["fixture_have"]
