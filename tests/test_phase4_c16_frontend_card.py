"""Falsification guards for the C16 title-restart/native-card boundary."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_c16_frontend_card as frontend  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_c16_frontend_card.json"
ARTIFACT_SHA256 = "07116d292129ea581a8a96ca3122b84ba600ca4444ce4fc336a680dc5b0eb7e6"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_frontend_card_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert frontend.evidence_gaps(doc) == []
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_c16_frontend_card.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


def test_static_join_recomputes_and_lives_remains_outside_card_block():
    retained = load_artifact()
    assert frontend.build_static_join() == retained["static_join"]
    join = retained["static_join"]
    assert join["card_serialization"]["source_start"] == "0x8009EC68"
    assert join["card_serialization"]["source_end_exclusive"] == "0x8009EDB8"
    assert join["lives"] == {
        "address": "0x800A65A0", "width": "u8",
        "inside_serialized_block": False}


def test_card_progress_and_title_restart_mutations_turn_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["live"]["card_diff"]["changed_bytes"] = 1
    assert "card diff" in " ".join(frontend.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["natural_title_restart"]["boundaries"][2] \
        ["progress_block"]["sha256"] = "00" * 32
    assert "progress-block" in " ".join(frontend.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["last_start_removed"]["boundaries"][1] \
        ["snapshot"]["typed"]["lives"] = 5
    assert "title-Start lives split" in " ".join(frontend.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["natural_title_restart"]["boundaries"][3] \
        ["frame_capture"]["pixel_sha256"] = "00" * 32
    assert "visual hash" in " ".join(frontend.evidence_gaps(mutated))


def test_machine_contract_supersedes_continue_menu_wording_without_closure():
    schema = yaml.safe_load((ROOT / "config/phase4_lives_gameover.yaml").read_text())
    assert schema["schema"] == "abl-phase4-lives-gameover/2"
    restart = schema["reproduced_controls"]["post_game_over_title_restart"]
    assert restart["natural"] == {
        "scene": 0, "lives": 5, "writer": 0x80055550}
    assert restart["start_removed"] == {
        "scene": 0, "lives": 0, "writer_0x80055550_executed": False}
    assert restart["isolated_card_changed_bytes"] == 0
    assert restart["progress_block"]["sha256"] == frontend.PROGRESS_SHA256
    assert schema["campaign_state"] == "active_partial"
    assert "not evidence of a Continue menu choice" in \
        schema["supersession"]["corrected_claim"]


def test_memory_card_seed_declares_the_new_generator_consumer():
    runtime = yaml.safe_load((ROOT / "config/phase3_runtime_fixtures.yaml").read_text())
    fixture = runtime["fixtures"]["go_to_end_repro_memory_card"]
    assert fixture["sha256"] == frontend.CARD_SHA256
    assert "tools/phase4_c16_frontend_card.py" in fixture["consumers"]
    fixture_source = yaml.safe_load(
        (ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    c16_rows = [row for row in fixture_source["external_operator_fixture_inputs"]
                if row["path"].startswith("movies/Phase4/C16_gameover_continue")]
    assert len(c16_rows) == 2
    assert all("tools/phase4_c16_frontend_card.py" in row["consumers"]
               for row in c16_rows)
