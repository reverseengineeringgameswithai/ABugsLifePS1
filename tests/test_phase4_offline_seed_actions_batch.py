"""Falsifiable guards for the A10/A11 external offline batch."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_offline_seed_actions_batch as batch  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_seed_actions_batch.json"


def load() -> dict:
    return json.loads(SUMMARY.read_text())


def test_seed_actions_batch_is_current_complete_and_external():
    document = load()
    assert document["schema"] == "abl-phase4-offline-seed-actions-batch/1"
    assert document["valid"] is True and document["errors"] == []
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "A11_seed_as_weapon", "A10_handstand"]
    assert document["offline_batch"]["capsule_count"] == 2
    assert document["offline_batch"]["reconstructed_records"] == 1821
    assert document["offline_batch"]["domains"] == [
        "registers", "ram", "vram", "spu_ram", "block_flow"]
    external = document["external_index"]
    assert len(external["sha256"]) == 64 and external["bytes"] > 0
    assert external["media_class"].endswith("never commit")
    assert external["preservation_required"] is True
    assert all(row["control_match"] for row in document["capsule_summaries"])


def test_seed_actions_findings_are_exact_bounded_frame_facts():
    findings = load()["derived_findings"]
    a10 = findings["A10_handstand"]
    assert a10["longest_exact_frozen_zero_grounded_run"] == {
        "start_movie_frame": 1102, "end_movie_frame": 1215,
        "records": 114, "position": [-68257, 9593, -7324], "grounded": 0}
    assert a10["dismount_state_6_event"]["movie_frame"] == 1222
    assert a10["dismount_state_6_event"]["fields"]["state"] == {
        "before": 5, "after": 6}
    assert a10["seed_actor_slots_exactly_xz_attached_during_frozen_run"] == []
    assert a10["active_plant_types_during_frozen_run"] == []
    assert not a10["dismount_state_6_event"]["candidate_function_flow"][
        "gameplay_effect_spawner"]["candidate_instruction_block_start_covered"]

    a11 = findings["A11_seed_as_weapon"]
    assert a11["detachment"]["movie_frame"] == 329
    assert a11["hit"]["movie_frame"] == 349
    assert a11["hit"]["target_knockback"] == -20
    assert a11["live_table_removal"]["movie_frame"] == 389
    assert a11["knockback_decay"]["records"] == 40
    assert a11["knockback_decay"]["two_frame_hold_per_integer_step"] is True
    assert a11["hit_candidate_arm_block_discriminator"] == {
        "contact_vs_actor_handler": True, "proximity_updater": False}
    assert a11["seed_stays_within_64_units_after_hit"] is False


def test_seed_actions_generator_recomputes_identically_and_pins_sources():
    document = load()
    external_path = Path(document["external_index"]["absolute_path"])
    external, summary = batch.build(external_path)
    assert batch.render(external) == external_path.read_bytes()
    assert batch.render(summary) == SUMMARY.read_bytes()
    for relative, expected in document["source_dependencies"].items():
        assert phase4_common.sha256(ROOT / relative) == expected
    capsule = json.loads((ROOT / "analysis/phase4_trace_capsule_set.json").read_text())
    assert document["offline_batch"]["reader_sha256"] == \
        capsule["offline_reader_snapshot"]["sha256"]
    assert {len(row["offline_batch_queries"])
            for row in json.loads((ROOT / "analysis/phase4_offline_opportunity_queue.json").read_text())["rows"]
            if row["row_id"] in {"A10_handstand", "A11_seed_as_weapon"}} == {8, 9}
