"""Fail-closed guards for the 107-row Phase-4 offline scheduler."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_inventory  # noqa: E402
import phase4_priority  # noqa: E402
import phase4_offline_queue  # noqa: E402
import phase4_live_escalations  # noqa: E402
import phase4_duckstation_late_batch  # noqa: E402


QUEUE = ROOT / "analysis/phase4_offline_opportunity_queue.json"
MOVIES = ROOT / "analysis/phase4_movie_inventory.json"
ESCALATIONS = ROOT / "analysis/phase4_live_escalations.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_default_movie_root_is_the_provisioned_tested_checkout():
    assert "OPERATOR_ROOT" not in phase4_offline_queue.__dict__
    assert phase4_offline_queue.common.ROOT == ROOT


def test_movie_inventory_is_recursive_pinned_and_consumes_no_backups():
    document = load(MOVIES)
    assert document["schema"] == "abl-phase4-movie-inventory/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["movie_root"] == "movies"
    assert document["counts"]["all_files"] == 135
    assert document["counts"]["all_movies"] == 78
    assert document["counts"]["phase4_files"] == 100
    assert document["counts"]["phase4_movies"] == 50
    assert document["counts"]["phase4_start_states"] == 50
    assert document["counts"]["all_backups"] == 0
    assert document["counts"]["phase4_backups"] == 0
    assert document["counts"]["consumed_files"] == 110
    assert document["counts"]["undeclared_files"] == 0
    assert not any("relative_path" in row for row in document["files"])
    consumed = [row for row in document["files"] if row["consumed_by_capsule_set"]]
    assert all(row["centrally_declared"] for row in consumed)
    assert all(row["declared_hash_matches"] and row["declared_size_matches"] for row in consumed)
    assert all(row["declared_media_class"] in {"pristine", "pristine_serial"} for row in consumed)
    assert not any(row["kind"] == "backup" for row in consumed)
    central = load(ROOT / "analysis/phase0_2_external_fixture_set.json")
    preservation_indexes = {
        "analysis/phase4_movie_inventory.json",
        "analysis/phase4_offline_opportunity_queue.json",
        "analysis/phase4_offline_contact_batch.json",
        "analysis/phase4_offline_collectibles_batch.json",
        "analysis/phase4_offline_plant_power_batch.json",
        "analysis/phase4_offline_plant_weapon_batch.json",
        "analysis/phase4_offline_seed_lifecycle_batch.json",
        "analysis/phase4_offline_traversal_plants_batch.json",
        "analysis/phase4_offline_seed_actions_batch.json",
        "analysis/phase4_offline_bonus_objectives_batch.json",
        "analysis/phase4_offline_e08_batch.json",
        "analysis/phase4_offline_fmv_batch.json",
    }
    assert not any(
        preservation_indexes.intersection(row.get("consumers") or [])
        for row in (central.get("entries") or {}).values()
    )


def test_queue_has_exact_current_107_rows_and_one_derived_classification():
    document = load(QUEUE)
    mechanics = set(phase4_common.baseline_rows())
    rows = document["rows"]
    assert document["schema"] == "abl-phase4-offline-opportunity-queue/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["classification_values"] == list(phase4_offline_queue.CLASSIFICATIONS)
    assert len(rows) == len({row["row_id"] for row in rows}) == len(mechanics) == 107
    assert {row["row_id"] for row in rows} == mechanics
    assert document["counts"]["open"] == 91
    assert document["counts"] == {
        "rows": 107, "complete": 16, "open": 91,
        "offline_ready": 0, "offline_partial": 42,
        "live_required": 0, "no_capsule": 65,
    }
    assert sum(document["counts"][name] for name in phase4_offline_queue.CLASSIFICATIONS) == 107
    assert all(row["classification"] in phase4_offline_queue.CLASSIFICATIONS for row in rows)
    assert not any(any(key in row for key in phase4_common.SELF_CERTIFYING_KEYS) for row in rows)


def test_queue_pins_current_sources_reader_movies_and_capsules():
    document = load(QUEUE)
    movies = load(MOVIES)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    inputs = document["inputs"]
    assert inputs["mechanics_registry_sha256"] == phase4_common.sha256(phase4_common.BASELINE_PATH)
    assert inputs["campaign_registry_sha256"] == phase4_common.sha256(phase4_common.REGISTRY_PATH)
    assert inputs["coverage_matrix_sha256"] == phase4_common.sha256(phase4_offline_queue.COVERAGE_PATH)
    assert inputs["fixture_audit_sha256"] == phase4_common.sha256(phase4_offline_queue.FIXTURE_AUDIT_PATH)
    assert inputs["capsule_index_sha256"] == phase4_common.sha256(phase4_offline_queue.CAPSULE_PATH)
    assert inputs["movie_inventory_sha256"] == phase4_offline_queue.bytes_sha256(
        phase4_offline_queue.json_bytes(movies))
    assert inputs["movie_tree_sha256"] == movies["tree_sha256"]
    assert inputs["offline_analysis_artifact_sha256"] == {
        "analysis/phase4_offline_contact_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_contact_batch.json"),
        "analysis/phase4_offline_collectibles_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_collectibles_batch.json"),
        "analysis/phase4_offline_plant_power_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_plant_power_batch.json"),
        "analysis/phase4_offline_plant_weapon_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_plant_weapon_batch.json"),
        "analysis/phase4_offline_seed_lifecycle_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_seed_lifecycle_batch.json"),
        "analysis/phase4_offline_traversal_plants_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_traversal_plants_batch.json"),
        "analysis/phase4_offline_seed_actions_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_seed_actions_batch.json"),
        "analysis/phase4_offline_bonus_objectives_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_bonus_objectives_batch.json"),
        "analysis/phase4_offline_e08_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_e08_batch.json"),
        "analysis/phase4_offline_fmv_batch.json": phase4_common.sha256(
            ROOT / "analysis/phase4_offline_fmv_batch.json"),
    }
    reader = Path(capsules["offline_reader_snapshot"]["absolute_path"])
    assert inputs["offline_reader_sha256"] == phase4_common.sha256(reader)
    current_capsules = {row["movie"]: row for row in capsules["capsules"]}
    for row in document["rows"]:
        for capsule in row["relevant_capsules"]:
            current = current_capsules[capsule["movie"]]
            assert capsule["movie_sha256"] == current["movie_sha256"]
            assert capsule["capsule_manifest_sha256"] == current["capsule_manifest_sha256"]
            assert capsule["capsule_tree_sha256"] == current["capsule_tree_sha256"]


def test_queue_completion_fixture_and_priority_inputs_are_low_level_rederived():
    registry = phase4_common.load_yaml(phase4_common.REGISTRY_PATH)
    mechanics = phase4_common.load_yaml(phase4_common.BASELINE_PATH)
    retained_coverage = load(ROOT / "analysis/phase4_coverage_matrix.json")
    retained_fixture = load(ROOT / "analysis/phase4_fixture_audit.json")
    retained_priority = load(ROOT / "analysis/phase4_priority.json")
    assert phase4_common.semantic_without_generated(retained_coverage) == \
        phase4_common.semantic_without_generated(
            phase4_coverage.build(registry, mechanics))
    assert phase4_common.semantic_without_generated(retained_fixture) == \
        phase4_common.semantic_without_generated(
            phase4_inventory.build_fixture_audit(mechanics, registry))
    assert phase4_common.semantic_without_generated(retained_priority) == \
        phase4_common.semantic_without_generated(
            phase4_priority.build(registry, mechanics))


def test_queue_retains_every_completed_offline_batch_and_has_no_ready_rows_left():
    document = load(QUEUE)
    rows = {row["row_id"]: row for row in document["rows"]}
    ranked = sorted(document["rows"], key=lambda row: row["priority"]["rank"])
    assert [row["row_id"] for row in ranked[:5]] == [
        "C16_lives_gameover", "C15_checkpoints", "E08_props_movers_gates",
        "E10_hazards", "E15_fmv",
    ]
    assert all(row["classification"] == "offline_partial" for row in ranked[:5])
    assert not any(row["classification"] == "offline_ready" for row in ranked)
    assert len(rows["E10_hazards"]["relevant_capsules"]) == 8
    assert len(rows["D11_mites_grubs"]["relevant_capsules"]) == 2
    for row_id, selection_rank in (
        ("E10_hazards", 1), ("D11_mites_grubs", 2), ("D08_flies", 3),
        ("D09_cockroaches", 4), ("D15_daddy_long_legs", 5),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_contact_batch.json",
            "schema": "abl-phase4-offline-contact-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_contact_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_contact_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("C01_grain_pickup", 1), ("C02_fifty_grain_reward", 2),
        ("C13_grain_harvester", 3), ("C14_telescope", 4),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_collectibles_batch.json",
            "schema": "abl-phase4-offline-collectibles-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_collectibles_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_collectibles_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("A13_cycle_plant_output", 1), ("B06_invincibility", 2),
        ("B07_health_power", 3), ("B08_bubble_shield", 4),
        ("B09_super_jump", 5),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_plant_power_batch.json",
            "schema": "abl-phase4-offline-plant-power-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_plant_power_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_plant_power_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("B11_blue_berry_shooter", 1), ("B12_homing_shooter", 2),
        ("B13_mine_plant", 3),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_plant_weapon_batch.json",
            "schema": "abl-phase4-offline-plant-weapon-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_plant_weapon_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_plant_weapon_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("A09_seed_pickup_drop", 1), ("A14_plant_seed", 2),
        ("A15_uproot_plant", 3),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_seed_lifecycle_batch.json",
            "schema": "abl-phase4-offline-seed-lifecycle-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_seed_lifecycle_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_seed_lifecycle_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("B01_mushroom_trampoline", 1), ("B02_propeller_plant", 2),
        ("B03_dandelion_glide", 3), ("B04_cannon_plant", 4),
        ("B05_green_leaf_platforms", 5), ("B10_purple_berry_plants", 6),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_traversal_plants_batch.json",
            "schema": "abl-phase4-offline-traversal-plants-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_traversal_plants_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_traversal_plants_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("A11_seed_as_weapon", 1), ("A10_handstand", 2),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_seed_actions_batch.json",
            "schema": "abl-phase4-offline-seed-actions-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_seed_actions_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_seed_actions_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    for row_id, selection_rank in (
        ("C18_bonus_entry", 1), ("F16_bonus1_spiders", 2),
        ("F17_bonus2_mushrooms", 3), ("F18_bonus3_grasshoppers", 4),
    ):
        assert rows[row_id]["classification"] == "offline_partial"
        assert rows[row_id]["prior_offline_analysis"] == [{
            "artifact": "analysis/phase4_offline_bonus_objectives_batch.json",
            "schema": "abl-phase4-offline-bonus-objectives-batch/1",
            "external_index_sha256": load(
                ROOT / "analysis/phase4_offline_bonus_objectives_batch.json"
            )["external_index"]["sha256"],
            "reader_sha256": load(
                ROOT / "analysis/phase4_offline_bonus_objectives_batch.json"
            )["offline_batch"]["reader_sha256"],
            "selection_queue_rank": selection_rank,
        }]
    assert rows["E08_props_movers_gates"]["prior_offline_analysis"] == [{
        "artifact": "analysis/phase4_offline_e08_batch.json",
        "schema": "abl-phase4-offline-e08-batch/1",
        "external_index_sha256": load(
            ROOT / "analysis/phase4_offline_e08_batch.json"
        )["external_index"]["sha256"],
        "reader_sha256": load(
            ROOT / "analysis/phase4_offline_e08_batch.json"
        )["offline_batch"]["reader_sha256"],
        "selection_queue_rank": 3,
    }]
    assert rows["E15_fmv"]["prior_offline_analysis"] == [{
        "artifact": "analysis/phase4_offline_fmv_batch.json",
        "schema": "abl-phase4-offline-fmv-batch/1",
        "external_index_sha256": load(
            ROOT / "analysis/phase4_offline_fmv_batch.json"
        )["external_index"]["sha256"],
        "reader_sha256": load(
            ROOT / "analysis/phase4_offline_fmv_batch.json"
        )["offline_batch"]["reader_sha256"],
        "selection_queue_rank": 5,
    }]
    assert all(rows[row_id]["classification"] == "offline_partial"
               for row_id in ("C15_checkpoints", "C16_lives_gameover", "E08_props_movers_gates", "E15_fmv"))
    for row in ranked[:5]:
        assert row["offline_batch_queries"]
        assert row["offline_answerable_questions"]
        assert row["offline_derivable_assertions"]
        assert row["named_unknowns"]
        assert row["available_domains"] == [
            "block_flow", "ram", "registers", "run_local_full_state_checkpoints", "spu_ram", "vram"]


def test_queue_guard_rejects_omission_duplicate_stale_hash_and_manual_pass():
    document = load(QUEUE)
    expected = set(phase4_common.baseline_rows())
    omitted = deepcopy(document)
    omitted["rows"].pop()
    assert any("row count" in error for error in phase4_offline_queue.structural_errors(omitted, expected))
    duplicated = deepcopy(document)
    duplicated["rows"][-1] = deepcopy(duplicated["rows"][0])
    assert any("duplicate" in error for error in phase4_offline_queue.structural_errors(duplicated, expected))
    stale = deepcopy(document)
    stale["inputs"]["capsule_index_sha256"] = "0" * 64
    assert any("source hashes" in error for error in phase4_offline_queue.structural_errors(
        stale, expected, document["inputs"]))
    authored = deepcopy(document)
    authored["rows"][0]["passes"] = True
    assert any("self-certifying" in error for error in phase4_offline_queue.structural_errors(authored, expected))


def test_live_ledger_retires_both_dma_windows_and_banks_late_passive():
    document = load(ESCALATIONS)
    assert document["schema"] == "abl-phase4-live-escalations/1"
    assert document["valid"] is True
    assert document["errors"] == []
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    assert {entry["id"] for entry in document["entries"]} == {
        entry["id"] for entry in source["entries"]
    }
    assert {entry["target_row"] for entry in document["entries"]} == {
        "A10_handstand", "A11_seed_as_weapon",
        "C18_bonus_entry", "F16_bonus1_spiders",
        "F17_bonus2_mushrooms", "F18_bonus3_grasshoppers",
        "E15_fmv",
    }
    executed = [entry for entry in document["entries"] if entry["state"] == "executed"]
    planned = [entry for entry in document["entries"] if entry["state"] == "planned"]
    assert len(executed) == 30
    assert planned == []
    two_pc_first_hit = next(
        entry for entry in executed
        if entry["id"] == "P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT"
    )
    assert two_pc_first_hit["id"] == \
        "P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT"
    assert two_pc_first_hit["missing_fact_id"] == \
        "E15/completed-level-b-natural-scene-setup-first-hit"
    passive_first_hit, precise_first_hit = two_pc_first_hit[
        "receipt_plan"]["receipts"]
    assert passive_first_hit["observer_method"] == "debugger.getRegisters"
    assert passive_first_hit["capture_window"] == {
        "clock": "emulator_frame", "start": 15776, "stop": 15872,
        "stop_inclusive": False,
    }
    assert precise_first_hit["observer_method"] == "debugger.addBreakpoint"
    assert precise_first_hit["capture_window"] == {
        "clock": "emulator_frame", "start": 15792, "stop": 15856,
        "stop_inclusive": False,
    }
    assert precise_first_hit["prelude_receipt_id"] == \
        passive_first_hit["id"]
    assert passive_first_hit["capture_window"]["start"] < \
        precise_first_hit["capture_window"]["start"]
    assert passive_first_hit["capture_window"]["stop"] > \
        precise_first_hit["capture_window"]["stop"]
    assert "Only a later iteration whose immutable" in \
        two_pc_first_hit["live_experiment"]
    anchor_query = two_pc_first_hit["offline_queries"][0]
    assert anchor_query["command"].startswith(
        "python3 tools/phase4_atomic_anchor_projection.py --input ")
    assert "aedb9bb4905be6750f4fbde8c60bf5c0a5833e686411038bde7fde5ea4f4faa7" \
        in anchor_query["answer"]
    assert two_pc_first_hit["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    first_hit_result = two_pc_first_hit["execution_result"]
    assert first_hit_result["control_outcome"] == "falsified"
    assert first_hit_result["record_counts"][
        "investigator_live_receipts"] == 2
    assert first_hit_result["record_counts"]["candidate_pc_hits"] == 0
    assert first_hit_result["record_counts"][
        "owned_breakpoints_removed"] == 2
    assert first_hit_result["banked_analysis"] == {
        "path": "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
        "sha256":
            "74b0c00b6ad4b3728d0c909aaa4ef1c4314a6cdf45b4f8452680e76ed777a350",
    }
    assert "failure frame 15857 without either hit" in \
        first_hit_result["observed_answers"]
    exact_pc = next(
        entry for entry in executed
        if entry["id"]
        == "P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE"
    )
    assert exact_pc["id"] == \
        "P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE"
    assert exact_pc["missing_fact_id"] == \
        "E15/completed-level-b-region-b-exact-pc-dma-provenance"
    passive_exact, native_exact, repeat_exact = exact_pc[
        "receipt_plan"]["receipts"]
    assert passive_exact["capture_window"] == {
        "clock": "emulator_frame", "start": 15800, "stop": 15896,
        "stop_inclusive": False,
    }
    assert passive_exact["observer_method"] == "debugger.getRegisters"
    for precise in (native_exact, repeat_exact):
        assert precise["capture_window"] == {
            "clock": "emulator_frame", "start": 15816, "stop": 15880,
            "stop_inclusive": False,
        }
        assert precise["observer_method"] == "transferLog.start"
        assert precise["atomic_method"] == "scenario.runBatch"
        assert precise["prelude_receipt_id"] == passive_exact["id"]
    assert passive_exact["capture_window"]["start"] < \
        native_exact["capture_window"]["start"]
    assert passive_exact["capture_window"]["stop"] > \
        native_exact["capture_window"]["stop"]
    assert exact_pc["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    assert "Do not execute until the direct-command receipt emitter" in \
        exact_pc["live_experiment"]
    assert "No retained low-level artifact identifies the native transfer" in \
        exact_pc["missing_information"]
    exact_result = exact_pc["execution_result"]
    assert exact_result["control_outcome"] == "falsified_repeated"
    assert exact_result["record_counts"]["investigator_live_receipts"] == 3
    assert exact_result["record_counts"]["precise_live_receipts"] == 2
    assert exact_result["record_counts"][
        "promotion_admissible_live_receipts"
    ] == 0
    assert exact_result["banked_analysis"] == {
            "path": "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json",
            "sha256": (
                "a59f8fa90e235ed733c50cfc7552c22e81f45446c7c11073649307e6c3eb6b55"
            ),
        }
    assert "escaped the finite frame-15880 bound" in \
        exact_result["observed_answers"]
    late_arm = next(
        entry for entry in executed
        if entry["id"]
        == "P4-R6-ITER3-E15-LEVELB-REGIONB-LATE-DMA-PROVENANCE"
    )
    assert late_arm["id"] == \
        "P4-R6-ITER3-E15-LEVELB-REGIONB-LATE-DMA-PROVENANCE"
    assert late_arm["missing_fact_id"] == \
        "E15/completed-level-b-region-b-first-late-dma-write"
    [passive_late] = late_arm["receipt_plan"]["receipts"]
    assert passive_late["capture_window"] == {
        "clock": "emulator_frame", "start": 15720, "stop": 16120,
        "stop_inclusive": False,
    }
    assert "tools/phase4_duckstation_late_batch.py" in \
        late_arm["live_experiment"]
    late_result = late_arm["execution_result"]
    assert late_result["control_outcome"] == "not_evaluated"
    assert late_result["record_counts"]["observer_frames"] == 800
    assert late_result["record_counts"]["precise_live_receipts"] == 0
    assert late_result["record_counts"]["promoted_dimensions"] == 0
    assert late_result["banked_analysis"] == {
        "path": "analysis/phase4_fmv_levelb_region_b_dma_late_result.json",
        "sha256": (
            "b0ec7e9fa015d94180fc26f74c376d7e343e53ee72a13d29ec5a00ef901d6433"
        ),
    }
    assert "transfer pagination was" in late_result["observed_answers"]
    assert "static subwindow decomposition" in \
        late_result["observed_answers"]
    function_plan = next(
        entry for entry in executed
        if entry["id"]
        == "P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY"
    )
    assert function_plan["id"] == \
        "P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY"
    assert function_plan["missing_fact_id"] == \
        "E15/present-rect-height-function-cardinality"
    passive_function, precise_function = function_plan[
        "receipt_plan"]["receipts"]
    assert passive_function["capture_window"] == {
        "clock": "movie_frame", "start": 150, "stop": 270,
        "stop_inclusive": False,
    }
    assert passive_function["observer_method"] == "debugger.getRegisters"
    assert passive_function["prelude_receipt_id"] is None
    assert precise_function["capture_window"] == {
        "clock": "movie_frame", "start": 160, "stop": 260,
        "stop_inclusive": False,
    }
    assert precise_function["observer_method"] == "functionTrace.start"
    assert precise_function["prelude_receipt_id"] == passive_function["id"]
    dma_plan = next(
        entry for entry in executed
        if entry["id"]
        == "P4-R6-ITER2-E15-LEVELB-REGIONB-DMA-PROVENANCE"
    )
    assert dma_plan["missing_fact_id"] == \
        "E15/completed-level-b-region-b-first-dma-write"
    [passive_dma] = dma_plan["receipt_plan"]["receipts"]
    assert passive_dma["capture_window"] == {
        "clock": "emulator_frame", "start": 0, "stop": 16120,
        "stop_inclusive": False,
    }
    assert passive_dma["observer_method"] == "debugger.getRegisters"
    assert passive_dma["prelude_receipt_id"] is None
    dma_result = dma_plan["execution_result"]
    assert dma_result["control_outcome"] == "not_evaluated"
    assert dma_result["record_counts"]["investigator_live_receipts"] == 1
    assert dma_result["record_counts"]["precise_live_receipts"] == 0
    assert dma_result["record_counts"][
        "promotion_admissible_live_receipts"] == 0
    assert dma_result["banked_analysis"] == {
        "path": "analysis/phase4_fmv_levelb_region_b_dma_attempt.json",
        "sha256": (
            "a69ad6ad0681317384141c4d66f4ab69997ca038887009b585fb8ff6bb1fe15d"
        ),
    }
    assert "produced no closed receipt" in dma_result["observed_answers"]
    assert "supplies no DMA event" in dma_result["observed_answers"]
    assert function_plan["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    assert "exactly three times" in function_plan["hypothesis"]
    assert "changes no guest state or input" in function_plan["native_control"]
    assert function_plan["execution_result"]["control_outcome"] == "falsified"
    assert function_plan["execution_result"]["record_counts"][
        "function_events"] == 44
    assert function_plan["execution_result"]["record_counts"][
        "observed_calls"] == 22
    assert function_plan["execution_result"]["record_counts"][
        "promotion_admissible_live_receipts"] == 0
    assert function_plan["execution_result"]["banked_analysis"] == {
        "path": (
            "analysis/"
            "phase4_fmv_present_rect_height_function_trace_result.json"
        ),
        "sha256": (
            "6064fe8a9720854cfb9b2ab14876a0c50c976e04c361f089897beec2c235604d"
        ),
    }
    assert "eleven entry/exit pairs" in function_plan[
        "execution_result"]["observed_answers"]
    assert "0x800B6C34" in function_plan[
        "execution_result"]["observed_answers"]
    writer_plan = next(
        entry for entry in executed
        if entry["id"] == "P4-ITER110-E15-PRESENT-RECT-HEIGHT-WRITER"
    )
    assert writer_plan["missing_fact_id"] == \
        "E15/present-rect-height-runtime-writer"
    passive_writer, precise_writer = writer_plan["receipt_plan"]["receipts"]
    assert passive_writer["capture_window"] == {
        "clock": "movie_frame", "start": 150, "stop": 270,
        "stop_inclusive": False,
    }
    assert passive_writer["observer_method"] == "debugger.getRegisters"
    assert passive_writer["prelude_receipt_id"] is None
    assert precise_writer["capture_window"] == {
        "clock": "movie_frame", "start": 160, "stop": 260,
        "stop_inclusive": False,
    }
    assert precise_writer["observer_method"] == "accessLog.addWatch"
    assert precise_writer["prelude_receipt_id"] == passive_writer["id"]
    assert writer_plan["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    assert "Zero CPU writes" in writer_plan["hypothesis"]
    assert "no P4-ITER109 branch write" in writer_plan["native_control"]
    assert writer_plan["execution_result"]["control_outcome"] == "falsified"
    assert writer_plan["execution_result"]["record_counts"][
        "access_events"] == 64
    assert writer_plan["execution_result"]["record_counts"][
        "promotion_admissible_live_receipts"] == 0
    assert writer_plan["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_present_rect_height_writer_result.json",
        "sha256":
            "59fb66dcf293d9549e52715ffafc0f77615e213d06c48b281ecdbe10aebe7aa1",
    }
    failure_plan = next(
        entry for entry in executed
        if entry["id"] == "P4-ITER109-E15-FILE-OPEN-FAILURE-ROUTING")
    assert failure_plan["missing_fact_id"] == \
        "E15/file-open-failure-routing-outcome"
    passive, precise = failure_plan["receipt_plan"]["receipts"]
    assert passive["capture_window"] == {
        "clock": "movie_frame", "start": 160, "stop": 260,
        "stop_inclusive": False,
    }
    assert passive["precise"] is False
    assert passive["prelude_receipt_id"] is None
    assert precise["capture_window"] == {
        "clock": "movie_frame", "start": 170, "stop": 240,
        "stop_inclusive": False,
    }
    assert precise["observer_method"] == "functionTrace.start"
    assert precise["prelude_receipt_id"] == passive["id"]
    assert failure_plan["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    assert failure_plan["execution_result"]["control_outcome"] == "falsified"
    assert failure_plan["execution_result"]["record_counts"][
        "diagnostic_sequences"] == 0
    assert failure_plan["execution_result"]["record_counts"][
        "shared_initialization_sequences"] == 2
    assert failure_plan["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_file_open_failure_result.json",
        "sha256":
            "b5e35e73a2cb1e40d3924addd2bded150ada44b2bd2e2d9ec14ac6af775cafe0",
    }
    cd_event = next(
        entry for entry in executed
        if entry["id"] == "P4-ITER107-E15-CD-EVENT-EXIT-CONTROL")
    assert cd_event["missing_fact_id"] == "E15/cd-event-exit-interface"
    passive, precise = cd_event["receipt_plan"]["receipts"]
    assert passive["capture_window"] == {
        "clock": "movie_frame", "start": 249, "stop": 340,
        "stop_inclusive": False,
    }
    assert precise["capture_window"] == {
        "clock": "movie_frame", "start": 250, "stop": 330,
        "stop_inclusive": False,
    }
    assert precise["observer_method"] == "functionTrace.start"
    assert precise["prelude_receipt_id"] == passive["id"]
    assert cd_event["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    assert cd_event["execution_result"]["control_outcome"] == "survived"
    assert cd_event["execution_result"]["record_counts"][
        "positive_target_exit_events"] == 6
    assert cd_event["execution_result"]["record_counts"][
        "negative_target_exit_events"] == 0
    assert cd_event["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_cd_event_exit_result.json",
        "sha256":
            "751adb79de41f84fd1f517e0ccb65a98c445b4a6b989474f47e28a90e28e28ef",
    }
    decoded_record = next(
        entry for entry in executed
        if entry["id"] ==
        "P4-ITER102-E15-DECODED-RECORD-ABSENCE-CONTROL")
    assert decoded_record["missing_fact_id"] == \
        "E15/decoded-record-absence-lifecycle"
    assert decoded_record["derived_pre_run_audit"][
        "target_classification"] == "offline_partial"
    assert decoded_record["derived_pre_run_audit"][
        "higher_priority_offline_ready_rows"] == []
    passive, precise = decoded_record["receipt_plan"]["receipts"]
    assert passive["observer_method"] == "debugger.getRegisters"
    assert precise["observer_method"] == "accessLog.addWatch"
    assert passive["capture_window"] == {
        "clock": "movie_frame", "start": 649, "stop": 900,
        "stop_inclusive": False,
    }
    assert precise["capture_window"] == {
        "clock": "movie_frame", "start": 650, "stop": 850,
        "stop_inclusive": False,
    }
    assert precise["prelude_receipt_id"] == passive["id"]
    assert decoded_record["execution_result"]["control_outcome"] == \
        "falsified"
    assert decoded_record["execution_result"]["record_counts"] == {
        "emulator_launches": 2,
        "completed_atomic_jobs": 4,
        "replay_frames": 3500,
        "observer_frames": 902,
        "exact_after_load_writes": 1,
        "owned_pids_stopped": 2,
        "positive_latch_writes": 1,
        "negative_latch_writes": 0,
        "negative_retained_function_events": 64,
        "negative_discarded_function_events": 26,
        "promotion_admissible_live_receipts": 0,
    }
    assert decoded_record["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_decoded_record_control_result.json",
        "sha256":
            "508a374a772199cc6f640ac2f0e17d84fc36c93293861a438b63b1442f20253e",
    }
    retention = next(
        entry for entry in executed
        if entry["id"] ==
        "P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL")
    assert retention["missing_fact_id"] == \
        "E15/decoded-record-retention-lifecycle"
    passive, precise = retention["receipt_plan"]["receipts"]
    assert passive["capture_window"] == {
        "clock": "movie_frame", "start": 649, "stop": 900,
        "stop_inclusive": False,
    }
    assert precise["capture_window"] == {
        "clock": "movie_frame", "start": 650, "stop": 850,
        "stop_inclusive": False,
    }
    assert precise["prelude_receipt_id"] == passive["id"]
    assert retention["execution_result"]["control_outcome"] == "survived"
    assert retention["execution_result"]["record_counts"][
        "native_retained_function_events"] == 90
    assert retention["execution_result"]["record_counts"][
        "native_discarded_function_events"] == 0
    assert retention["execution_result"]["record_counts"][
        "promotion_admissible_live_receipts"] == 0
    assert retention["execution_result"]["banked_analysis"] == {
        "path":
            "analysis/phase4_fmv_decoded_record_retention_result.json",
        "sha256":
            "d8d2e85a60eb8705c1e5b60885d133d8ae33a1081681689185e07ea572d1ec9a",
    }
    phase_neutral_menu = next(
        entry for entry in executed
        if entry["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")
    assert phase_neutral_menu["missing_fact_id"] == \
        "E15/menu-phase-neutral-owner-coverage"
    assert [row["observer_method"] for row in
            phase_neutral_menu["receipt_plan"]["receipts"]] == [
        "debugger.getRegisters", "movie.traceToFrame",
        "debugger.getRegisters", "movie.traceToFrame",
    ]
    menu_v2_runs = [
        entry for entry in executed
        if entry["execution_result"].get("execution_kind") ==
        "v2_receipt_set"
        and entry["id"] in {
            "P4-ITER92-E15-MENU-NONBOOT-OWNER-COVERAGE",
            "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE",
        }]
    assert [entry["id"] for entry in menu_v2_runs] == [
        "P4-ITER92-E15-MENU-NONBOOT-OWNER-COVERAGE",
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE",
    ]
    assert menu_v2_runs[0]["missing_fact_id"] == \
        "E15/menu-nonboot-owner-coverage"
    assert menu_v2_runs[1]["missing_fact_id"] == \
        "E15/menu-phase-neutral-owner-coverage"
    capsule_runs = [
        entry for entry in executed
        if entry["execution_result"].get(
            "execution_kind", "trace_capsule_collection") ==
        "trace_capsule_collection"]
    atomic_runs = [
        entry for entry in executed
        if entry["execution_result"].get("execution_kind") ==
        "atomic_batch_control"]
    phase_neutral_runs = [
        entry for entry in executed
        if entry["execution_result"].get("execution_kind") ==
        "phase_neutral_movie_control"]
    assert len(capsule_runs) == 6
    assert [entry["id"] for entry in atomic_runs] == [
        "P4-ITER79-E15-CALLBACK-TEARDOWN-CONTROL",
        "P4-ITER81-E15-NATURAL-LEVELA-COMPLETION-CONTROL",
        "P4-ITER82-E15-NATURAL-EXIT-CAUSE-CONTROL",
        "P4-ITER83-E15-LOSE-GAMEOVER-LIFECYCLE-CONTROL",
        "P4-ITER86-E15-LEVELB-LIFECYCLE-CONTROL",
        "P4-ITER87-E15-LEVELB-SAVE-ANCHOR-CONTROL",
    ]
    assert [entry["id"] for entry in phase_neutral_runs] == [
        "P4-ITER88-E15-LEVELB-PHASE-NEUTRAL-REVALIDATION",
        "P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE",
        "P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE",
        "P4-ITER91-E15-FINALE-ENDPOINT-CORRECTION",
    ]
    assert {
        entry["target_row"]: len(entry["relevant_capsules"])
        for entry in document["entries"]
    } == {
        "A10_handstand": 1, "A11_seed_as_weapon": 1,
        "C18_bonus_entry": 3, "F16_bonus1_spiders": 1,
        "F17_bonus2_mushrooms": 1, "F18_bonus3_grasshoppers": 1,
        "E15_fmv": 2,
    }
    assert all(entry["derived_pre_run_audit"]["target_classification"] == "live_required"
               for entry in capsule_runs)
    assert all(entry["derived_pre_run_audit"]["target_classification"] ==
               "offline_partial" for entry in atomic_runs)
    assert all(entry["derived_pre_run_audit"]["target_classification"] ==
               "offline_partial" for entry in phase_neutral_runs)
    assert all(entry["derived_pre_run_audit"]["target_classification"] ==
               "offline_partial" for entry in menu_v2_runs)
    assert all(entry["derived_pre_run_audit"]["higher_priority_offline_ready_rows"] == []
               for entry in document["entries"])
    assert all(entry["derived_post_run_audit"]["target_classification"] == "offline_partial"
               for entry in executed)
    assert all(entry["execution_result"]["frame_chunks_byte_identical"] is True
               for entry in capsule_runs)
    assert atomic_runs[0]["execution_result"]["record_counts"] == {
        "atomic_batches": 3, "jobs": 6, "function_events": 16}
    assert atomic_runs[1]["execution_result"]["record_counts"] == {
        "atomic_batches": 1, "jobs": 2, "function_events": 12}
    assert atomic_runs[2]["execution_result"]["record_counts"] == {
        "atomic_batches": 1, "jobs": 2, "function_events": 12,
        "access_events": 33, "resident_causal_access_events": 7}
    assert atomic_runs[3]["execution_result"]["record_counts"] == {
        "atomic_batches": 1, "jobs": 2,
        "failed_positive_function_events": 0,
        "cached_control_pairs": 1, "staged_exact_stops": 8,
        "staged_access_events": 3}
    level_b_counts = {
        "atomic_batches": 1, "atomic_jobs": 2,
        "atomic_caller_hits": 0,
        "atomic_typed_selected_limit_events": 7,
        "save_recipe_branches": 2, "save_recipe_caller_hits": 0,
        "save_recipe_function_events": 0,
        "phase_neutral_branches": 2,
        "phase_neutral_coverage_ranges": 12,
        "phase_neutral_completed_level_b_positive": 1,
        "phase_neutral_completed_level_b_neutral": 0,
    }
    assert atomic_runs[4]["execution_result"]["record_counts"] == level_b_counts
    assert atomic_runs[5]["execution_result"]["record_counts"] == level_b_counts
    assert phase_neutral_runs[0]["execution_result"]["record_counts"] == \
        level_b_counts
    assert phase_neutral_runs[1]["execution_result"]["record_counts"] == {
        "localization_queries": 12,
        "localization_coverage_ranges": 12,
        "positive_function_events": 8,
        "positive_execution_events": 1,
        "positive_access_events": 228,
        "neutral_function_events": 14,
        "neutral_execution_events": 0,
        "neutral_access_events": 231,
        "debugger_cleanup_actions": 30,
    }
    assert phase_neutral_runs[2]["execution_result"]["record_counts"] == {
        "cycle_neutral_queries": 4,
        "coverage_ranges": 4,
        "bare_pc_alias_hits": 326,
        "resident_finale_route_hits": 0,
        "debugger_cleanup_actions": 10,
    }
    assert phase_neutral_runs[2]["execution_result"]["superseded_by"] == \
        "P4-ITER91-E15-FINALE-ENDPOINT-CORRECTION"
    assert phase_neutral_runs[3]["execution_result"]["record_counts"] == {
        "cycle_neutral_queries": 4,
        "coverage_ranges": 4,
        "complete_consumption_queries": 2,
        "bare_pc_alias_hits": 326,
        "resident_finale_route_hits": 0,
        "debugger_cleanup_actions": 10,
    }
    assert menu_v2_runs[0]["execution_result"]["record_counts"] == {
        "closed_v2_receipts": 4,
        "atomic_jobs": 8,
        "replay_frames": 60620,
        "execution_events": 6,
        "endpoint_control_failures": 3,
        "owned_pids_stopped": 4,
    }
    assert menu_v2_runs[0]["execution_result"]["control_outcome"] == "falsified"
    assert menu_v2_runs[1]["execution_result"]["record_counts"] == {
        "closed_v2_receipts": 4,
        "atomic_jobs": 8,
        "atomic_replay_frames": 60620,
        "native_observer_replay_frames": 15155,
        "native_coverage_hits": 3266,
        "native_control_failures": 2,
        "owned_pids_stopped": 4,
    }
    assert menu_v2_runs[1]["execution_result"]["control_outcome"] == "falsified"
    selector_control = next(
        entry for entry in executed
        if entry["id"] ==
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL")
    assert selector_control["state"] == "executed"
    assert selector_control["missing_fact_id"] == \
        "E15/c16-selector40-lifecycle"
    assert len(selector_control["receipt_plan"]["receipts"]) == 2
    assert selector_control["execution_result"]["execution_kind"] == \
        "v2_receipt_set"
    assert selector_control["execution_result"]["control_outcome"] == \
        "falsified"
    assert selector_control["execution_result"]["record_counts"] == {
        "emulator_launches": 2,
        "completed_atomic_jobs": 4,
        "exact_after_load_writes": 1,
        "lifecycle_observer_events": 0,
        "owned_pids_stopped": 2,
        "admissible_live_receipts": 0,
    }
    assert selector_control["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_c16_selector_control_result.json",
        "sha256":
            "831389a00758bf3fa75dfd6fdd46e2115b72cb5c04a517b716c1750c330bdcaf",
    }
    staged_control = next(
        entry for entry in executed
        if entry["id"] ==
        "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL")
    assert staged_control["missing_fact_id"] == \
        "E15/c16-staged-selector40-lifecycle"
    assert staged_control["execution_result"]["control_outcome"] == "survived"
    assert staged_control["execution_result"]["record_counts"] == {
        "emulator_launches": 2,
        "completed_atomic_jobs": 4,
        "replay_frames": 16024,
        "observer_frames": 14826,
        "exact_after_load_writes": 1,
        "owned_pids_stopped": 2,
        "intrinsically_valid_live_receipts": 2,
        "method_trial_admissible_live_receipts": 0,
    }
    assert staged_control["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_c16_selector_control_result.json",
        "sha256":
            "831389a00758bf3fa75dfd6fdd46e2115b72cb5c04a517b716c1750c330bdcaf",
    }
    assert document["counts"] == {"entries": 30, "executed": 30, "planned": 0}
    assert phase4_live_escalations.build() == document


def test_live_ledger_rejects_planned_entry_without_missing_fact_id():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    mutated = deepcopy(source)
    entry = next(
        row for row in mutated["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")
    del entry["missing_fact_id"]
    document = phase4_live_escalations.build(mutated, queue, capsules)
    assert any("typed entry lacks missing_fact_id" in error
               for error in document["errors"])


def test_live_ledger_rejects_planned_entry_without_receipt_plan():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    mutated = deepcopy(source)
    entry = next(
        row for row in mutated["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")
    del entry["receipt_plan"]
    document = phase4_live_escalations.build(mutated, queue, capsules)
    assert any("planned entry lacks receipt_plan" in error
               for error in document["errors"])


def test_live_ledger_requires_precise_observers_to_pin_wider_passive_preludes():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")

    wrong_precision = deepcopy(source)
    plan = next(
        row for row in wrong_precision["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")["receipt_plan"]
    plan["receipts"][1]["precise"] = False
    document = phase4_live_escalations.build(
        wrong_precision, queue, capsules)
    assert any("precise flag disagrees with its observer" in error
               for error in document["errors"])

    missing_prelude = deepcopy(source)
    plan = next(
        row for row in missing_prelude["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")["receipt_plan"]
    plan["receipts"] = [
        row for row in plan["receipts"]
        if row["id"] != "menu-v1-phase-neutral-passive-prelude"
    ]
    document = phase4_live_escalations.build(
        missing_prelude, queue, capsules)
    assert any("prelude is absent or not passive" in error
               for error in document["errors"])

    equal_window = deepcopy(source)
    plan = next(
        row for row in equal_window["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")["receipt_plan"]
    plan["receipts"][0]["capture_window"]["stop"] = \
        plan["receipts"][1]["capture_window"]["stop"]
    document = phase4_live_escalations.build(
        equal_window, queue, capsules)
    assert any("lacks a strictly wider passive prelude" in error
               for error in document["errors"])


def test_live_ledger_classifies_managed_breakpoints_as_precise_observers():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    mutated = deepcopy(source)
    plan = next(
        row for row in mutated["entries"]
        if row["id"] ==
        "P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT")["receipt_plan"]
    plan["receipts"][1]["precise"] = False
    document = phase4_live_escalations.build(mutated, queue, capsules)
    assert any("precise flag disagrees with its observer" in error
               for error in document["errors"])


def test_two_pc_first_hit_passive_plan_uses_the_validated_cold_boot_adapter():
    plan = phase4_common.load_yaml(
        ROOT
        / "config/phase4_fmv_levelb_two_pc_first_hit_passive_batch.yaml")
    assert phase4_duckstation_late_batch.validate_plan(
        plan, allow_executed=True) == []
    assert {
        job["staged_prelude"]["target_frame"]
        for job in plan["jobs"]
    } == {15776}
    assert {
        job["run"]["frames"]
        for job in plan["jobs"]
    } == {96}

    unstaged = deepcopy(plan)
    unstaged["jobs"][0].pop("staged_prelude")
    errors = phase4_duckstation_late_batch.validate_plan(
        unstaged, allow_executed=True)
    assert any("nonzero cold-boot capture requires" in error
               for error in errors)


def test_live_ledger_receipt_plan_requires_central_pristine_movie_pin():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    mutated = deepcopy(source)
    plan = next(
        row for row in mutated["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")["receipt_plan"]
    plan["receipts"][0]["movie_sha256"] = "0" * 64
    document = phase4_live_escalations.build(mutated, queue, capsules)
    assert any("movie is not centrally pinned pristine evidence" in error
               for error in document["errors"])


def test_live_ledger_rejects_atomic_counts_that_disagree_with_banked_analysis():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    mutated = deepcopy(source)
    entry = next(row for row in mutated["entries"]
                 if row["id"] ==
                 "P4-ITER81-E15-NATURAL-LEVELA-COMPLETION-CONTROL")
    entry["execution_result"]["record_counts"]["jobs"] = 3
    document = phase4_live_escalations.build(mutated, queue, capsules)
    assert any("controlled execution record counts drifted" in error
               for error in document["errors"])


def test_live_ledger_rejects_v2_receipt_and_control_result_drift():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")

    bad_counts = deepcopy(source)
    entry = next(
        row for row in bad_counts["entries"]
        if row["id"] ==
        "P4-ITER92-E15-MENU-NONBOOT-OWNER-COVERAGE")
    entry["execution_result"]["record_counts"]["atomic_jobs"] = 7
    document = phase4_live_escalations.build(
        bad_counts, queue, capsules)
    assert any("v2 execution record counts drifted" in error
               for error in document["errors"])

    bad_receipt = deepcopy(source)
    entry = next(
        row for row in bad_receipt["entries"]
        if row["id"] ==
        "P4-ITER92-E15-MENU-NONBOOT-OWNER-COVERAGE")
    entry["execution_result"]["external_receipts"][0]["sha256"] = "0" * 64
    document = phase4_live_escalations.build(
        bad_receipt, queue, capsules)
    assert any("v2 external receipt drifted" in error
               for error in document["errors"])


def test_live_ledger_retains_exact_historical_runtime_without_relabeling_current():
    document = load(ESCALATIONS)
    historical = next(
        row for row in document["entries"]
        if row["id"] ==
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE")
    identity = historical["derived_runtime_identity"]
    assert identity == {
        "executed_sha256":
            "91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6",
        "current_manifest_sha256":
            "d68b2c6d25f6795a921f5d1fa64ae33c66af3e3d47a786ee45853170766588cd",
        "current_manifest_match": False,
        "retained_receipt_and_batch_match": True,
        "classification": "historical_exact_not_current",
    }


def test_live_ledger_rejects_invalid_supersession_links_and_reasons():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")

    missing = deepcopy(source)
    historical = next(
        row for row in missing["entries"]
        if row["id"] == "P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE")
    historical["execution_result"]["superseded_by"] = "P4-NOT-PRESENT"
    document = phase4_live_escalations.build(missing, queue, capsules)
    assert any("superseding escalation P4-NOT-PRESENT is absent" in error
               for error in document["errors"])

    self_link = deepcopy(source)
    historical = next(
        row for row in self_link["entries"]
        if row["id"] == "P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE")
    historical["execution_result"]["superseded_by"] = historical["id"]
    document = phase4_live_escalations.build(self_link, queue, capsules)
    assert any("cannot supersede itself" in error for error in document["errors"])

    unbounded = deepcopy(source)
    historical = next(
        row for row in unbounded["entries"]
        if row["id"] == "P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE")
    historical["execution_result"]["supersession_reason"] = "off by one"
    document = phase4_live_escalations.build(unbounded, queue, capsules)
    assert any("lacks a bounded reason" in error for error in document["errors"])


def test_live_ledger_preserves_historical_atomic_capsules_but_exhausts_plans():
    source = phase4_common.load_yaml(
        ROOT / "config/phase4_live_escalations.yaml")
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    historical = next(
        row for row in source["entries"]
        if row["id"] == "P4-ITER82-E15-NATURAL-EXIT-CAUSE-CONTROL")
    assert historical["pre_run_audit"]["relevant_capsule_count"] == \
        len(historical["relevant_capsules"]) == 1
    assert not any(
        historical["id"] in error
        for error in phase4_live_escalations.build(
            source, queue, capsules)["errors"])

    stale_history = deepcopy(source)
    stale_entry = next(
        row for row in stale_history["entries"]
        if row["id"] == historical["id"])
    stale_entry["pre_run_audit"]["relevant_capsule_count"] = 2
    document = phase4_live_escalations.build(
        stale_history, queue, capsules)
    assert any(
        "historical atomic capsule set does not match" in error
        for error in document["errors"])

    incomplete_plan = deepcopy(source)
    planned = next(
        row for row in incomplete_plan["entries"]
        if row["id"] ==
        "P4-ITER83-E15-LOSE-GAMEOVER-LIFECYCLE-CONTROL")
    planned["state"] = "planned"
    planned["relevant_capsules"] = planned["relevant_capsules"][1:]
    document = phase4_live_escalations.build(
        incomplete_plan, queue, capsules)
    assert any(
        "relevant capsules do not exhaust" in error
        for error in document["errors"])


def test_live_ledger_rejects_generic_causality_control_justification():
    queue = load(QUEUE)
    capsules = load(ROOT / "analysis/phase4_trace_capsule_set.json")
    target = next(row for row in queue["rows"] if row["row_id"] == "E10_hazards")
    relevant = [{
        key: capsule[key]
        for key in ("movie", "movie_sha256", "capsule_manifest_sha256",
                    "capsule_tree_sha256")
    } for capsule in target["relevant_capsules"]]
    source = {
        "schema": "abl-phase4-live-escalation-source/1",
        "entries": [{
            "id": "generic-rejected",
            "target_row": "E10_hazards",
            "hypothesis": "A named hazard lead changes health through an unknown owner.",
            "relevant_capsules": relevant,
            "offline_queries": [{
                "command": target["offline_batch_queries"][0]["command"],
                "window": "all retained frame boundaries",
                "domains": ["ram", "block_flow"],
                "answer": "The retained frame window and health change were reconstructed.",
            }],
            "answers_obtained": "The frame-boundary outcome and hotspot window are known.",
            "missing_information": "Needs exact causality/control and no more specific missing domain.",
            "live_experiment": "Run a hypothetical exact instruction trace over the named window.",
            "native_control": "Replay an unedited same-state branch through the same endpoint.",
            "expected_evidence": "An exact writer event and matched endpoint would be retained.",
            "priority_justification": {
                "reason": "The target is already the highest-ranked offline-ready row.",
                "higher_priority_offline_ready": "none",
                "load_bearing_evidence": "queue rank 1",
            },
        }],
    }
    document = phase4_live_escalations.build(source, queue, capsules)
    assert any("forbidden generic causality wording" in error
               for error in document["errors"])
