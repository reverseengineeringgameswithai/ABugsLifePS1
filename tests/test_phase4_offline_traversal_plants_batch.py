"""Falsifiable guards for the Phase-4 traversal-plant offline batch."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_offline_traversal_plants_batch as batch  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_traversal_plants_batch.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
QUEUE = ROOT / "analysis/phase4_offline_opportunity_queue.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def findings() -> dict:
    return load(SUMMARY)["derived_findings"]


def test_batch_is_the_six_highest_ranked_coherent_open_rows():
    document = load(SUMMARY)
    assert document["schema"] == "abl-phase4-offline-traversal-plants-batch/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["queue_counts"] == {
        "rows": 107, "complete": 16, "open": 91,
        "offline_ready": 6, "offline_partial": 27,
        "live_required": 6, "no_capsule": 68,
    }
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "B01_mushroom_trampoline", "B02_propeller_plant",
        "B03_dandelion_glide", "B04_cannon_plant",
        "B05_green_leaf_platforms", "B10_purple_berry_plants"]
    assert [row["queue_rank"] for row in document["selected_rows"]] == list(range(1, 7))
    assert all(row["classification"] == "offline_ready"
               for row in document["selected_rows"])
    assert document["offline_batch"]["capsule_count"] == 6
    assert document["offline_batch"]["reconstructed_records"] == 8572
    assert sum(row["records"] for row in document["capsule_summaries"]) == 8572
    assert {row_id: len(queries) for row_id, queries in
            document["offline_batch"]["exact_queue_queries"].items()} == {
        "B01_mushroom_trampoline": 7,
        "B02_propeller_plant": 7,
        "B03_dandelion_glide": 7,
        "B04_cannon_plant": 7,
        "B05_green_leaf_platforms": 7,
        "B10_purple_berry_plants": 8,
    }


def test_batch_pins_reader_capsules_movies_sources_and_external_index():
    document = load(SUMMARY)
    capsule_index = load(CAPSULES)
    reader = capsule_index["offline_reader_snapshot"]
    assert document["offline_batch"]["reader_path"] == reader["absolute_path"]
    assert document["offline_batch"]["reader_sha256"] == reader["sha256"]
    assert phase4_common.sha256(Path(reader["absolute_path"])) == reader["sha256"]
    current = {row["movie"]: row for row in capsule_index["capsules"]}
    for summary in document["capsule_summaries"]:
        capsule = current[summary["movie"]]
        assert summary["movie_sha256"] == capsule["movie_sha256"]
        assert summary["start_state"] == capsule["start_state"]
        assert summary["capsule_manifest_sha256"] == capsule["capsule_manifest_sha256"]
        assert summary["capsule_tree_sha256"] == capsule["capsule_tree_sha256"]
        movie = batch.movie_file(summary["movie"])
        assert movie.stat().st_size == summary["movie_bytes"]
        assert phase4_common.sha256(movie) == summary["movie_sha256"]
        assert summary["control_match"] is True
    for relative, expected in document["source_dependencies"].items():
        assert phase4_common.sha256(ROOT / relative) == expected
    external = document["external_index"]
    external_path = Path(external["absolute_path"])
    assert external == {
        "absolute_path": str(external_path),
        "bytes": 58047074,
        "media_class": "external game-derived evidence; never commit",
        "preservation_required": True,
        "schema": "abl-phase4-external-traversal-plants-index/1",
        "sha256": "96884a7373430b3b1431bd3b52eb004531c8e894d2adc89d19b3afb36868e99d",
    }
    assert external_path.stat().st_size == external["bytes"]
    assert phase4_common.sha256(external_path) == external["sha256"]


def test_mushrooms_retain_four_distinct_bounce_boundaries():
    finding = findings()["B01_mushroom_trampoline"]
    assert finding["bounce_velocity_y"] == -3328
    assert [row["movie_frame"] for row in finding["bounce_events"]] == [207, 335, 385, 435]
    assert finding["distinct_nearest_plant_slots"] == [2, 4, 5, 6]
    assert [row["nearest_type_5_plant"]["state"]
            for row in finding["bounce_events"]] == [2, 2, 2, 2]
    assert [row["mushroom_handler_block_count"]
            for row in finding["bounce_events"]] == [5, 5, 5, 5]
    assert "does not prove a combo law" in finding["bounded_observation"]


def test_propeller_retains_two_lift_ramps_and_bounded_seed_sequence():
    finding = findings()["B02_propeller_plant"]
    runs = finding["player_lift_runs"]
    assert [(row["start_movie_frame"], row["end_movie_frame"])
            for row in runs] == [(61, 82), (525, 546)]
    assert [row["minimum_velocity_y"] for row in runs] == [-3072, -3072]
    assert [[step["velocity_y"] for step in row["velocity_steps"]] for row in runs] == [
        [-2048, -2304, -2560, -2816, -3072],
        [-2048, -2304, -2560, -2816, -3072],
    ]
    seed = finding["nearby_seed_vertical_motion"]
    assert seed["slot"] == 26
    assert seed["address"] == "0x800a0ae8"
    assert seed["exact_player_attachment_interval"] == {
        "start_movie_frame": 441, "end_movie_frame": 476}
    assert seed["attachment_end_to_second_lift_start_frames"] == 49
    assert seed["minimum_velocity_y"] == -3584
    assert seed["minimum_y"] == -149214
    assert "does not prove propeller-to-seed causality" in finding["bounded_observation"]


def test_dandelion_and_cannon_findings_preserve_negative_boundaries():
    dandelion = findings()["B03_dandelion_glide"]
    assert [(row["movie_frame"], row["before_velocity_y"], row["after_velocity_y"])
            for row in dandelion["dandelion_velocity_transitions"]] == [
        (180, 1856, -4096)]
    assert dandelion["propeller_dandelion_handler_overlap"] == {
        "first_grounded_zero_velocity_frame": 974,
        "first_movie_frame": 914,
        "last_movie_frame": 996,
        "retained_frames": 42,
    }
    cannon = findings()["B04_cannon_plant"]
    assert cannon["seated_constant_interval"]["start_movie_frame"] == 121
    assert cannon["seated_constant_interval"]["end_movie_frame"] == 152
    assert cannon["launch"] == {
        "cannon_handler_block_count": 1,
        "dandelion_handler_block_count": 1,
        "movie_frame": 153,
        "velocity_y": -7936,
    }
    assert cannon["later_discrete_dandelion_impulse_frames"] == []
    assert "movie name is not proof" in cannon["bounded_observation"]


def test_green_fixture_retains_four_distinct_complete_lifecycles():
    finding = findings()["B05_green_leaf_platforms"]
    cycles = finding["green_plant_cycles"]
    assert [(row["plant_type"], row["slot"], row["creation_movie_frame"],
             row["retirement_movie_frame"], row["retained_lifetime_frames"])
            for row in cycles] == [
        (4, 3, 199, 551, 352),
        (10, 4, 801, 1187, 386),
        (9, 5, 1467, 2015, 548),
        (1, 6, 2087, 2645, 558),
    ]
    assert [[row["after"] for row in cycle["phase_transitions"]]
            for cycle in cycles] == [[5, 7, 69, 5]] * 4
    assert finding["green_collision_tail_block_count"] == 27140
    assert "do not bind a specific leaf plane" in finding["bounded_observation"]


def test_purple_fixture_retains_four_lifecycles_and_equip_order():
    finding = findings()["B10_purple_berry_plants"]
    assert finding["observed_equip_sequence"] == [0, 1, 2, 4, 3]
    events = finding["equipped_berry_transitions"]
    assert [row["movie_frame"] for row in events] == [253, 777, 1343, 2061]
    assert [row["grant_handler_movie_frame"] for row in events] == [253, 777, 1343, 2061]
    assert [row["creation_to_equip_frames"] for row in events] == [120, 102, 90, 120]
    assert all(row["range_changed"] is True for row in events)
    assert [(row["creation_movie_frame"], row["retirement_movie_frame"])
            for row in finding["purple_plant_cycles"]] == [
        (133, 437), (675, 989), (1253, 1635), (1941, 2243)]
    assert load(SUMMARY)["live_escalation"] is None


def test_source_guard_rejects_rank_drift_missing_capsule_and_wrong_row_count():
    queue = load(QUEUE)
    capsules = load(CAPSULES)
    drifted = deepcopy(queue)
    row = next(row for row in drifted["rows"]
               if row["row_id"] == "B01_mushroom_trampoline")
    row["classification"] = "offline_ready"
    row["prior_offline_analysis"] = []
    row["priority"]["rank"] = 99
    errors, _, _ = batch.source_errors(drifted, capsules)
    assert any("rank changed" in error for error in errors)

    missing = deepcopy(capsules)
    missing["capsules"] = [row for row in missing["capsules"]
                           if row["movie"] !=
                           "movies/Phase4/B04_cannon_dandelion_combo.movie.json"]
    errors, selected, _ = batch.source_errors(queue, missing)
    assert any("selected capsule absent" in error for error in errors)
    assert len(selected) == 5

    short = deepcopy(queue)
    short["rows"].pop()
    errors, _, _ = batch.source_errors(short, capsules)
    assert any("exactly 107 rows" in error for error in errors)
