"""Falsifiable guards for the Phase-4 plant and player-power offline batch."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_offline_plant_power_batch as batch  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_plant_power_batch.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_batch_is_the_top_five_row_coherent_cluster():
    document = load(SUMMARY)
    assert document["schema"] == "abl-phase4-offline-plant-power-batch/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["queue_counts"] == {
        "rows": 107, "complete": 16, "open": 91,
        "offline_ready": 17, "offline_partial": 16,
        "live_required": 6, "no_capsule": 68,
    }
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "A13_cycle_plant_output", "B06_invincibility", "B07_health_power",
        "B08_bubble_shield", "B09_super_jump",
    ]
    assert [row["queue_rank"] for row in document["selected_rows"]] == [1, 2, 3, 4, 5]
    assert all(row["classification"] == "offline_ready"
               for row in document["selected_rows"])
    assert document["offline_batch"]["capsule_count"] == 9
    assert document["offline_batch"]["reconstructed_records"] == 16785
    assert len(document["capsule_summaries"]) == 9
    assert sum(row["records"] for row in document["capsule_summaries"]) == 16785
    assert {row: len(queries) for row, queries in
            document["offline_batch"]["exact_queue_queries"].items()} == {
        "A13_cycle_plant_output": 40,
        "B06_invincibility": 16,
        "B07_health_power": 20,
        "B08_bubble_shield": 16,
        "B09_super_jump": 16,
    }


def test_batch_pins_reader_capsules_sources_and_external_index():
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
    for relative, expected in document["source_dependencies"].items():
        assert phase4_common.sha256(ROOT / relative) == expected
    external = document["external_index"]
    external_path = Path(external["absolute_path"])
    assert external == {
        "absolute_path": str(external_path),
        "bytes": 53952029,
        "media_class": "external game-derived evidence; never commit",
        "preservation_required": True,
        "schema": "abl-phase4-external-plant-power-index/1",
        "sha256": "daf10dac46dd88cdba54541855ab944d2583f0b5abae749840c1dcb4a6fc9d83",
    }
    assert external_path.stat().st_size == external["bytes"]
    assert phase4_common.sha256(external_path) == external["sha256"]


def test_a13_retains_all_typed_creations_cursor_joins_and_table_variants():
    finding = load(SUMMARY)["derived_findings"]["A13_cycle_plant_output"]
    assert finding["creation_count"] == 22
    assert finding["retirement_count"] == 20
    observed = {
        Path(row["movie"]).stem: (row["creation_frames"], row["creation_types"],
                                   row["retirement_frames"])
        for row in finding["movies"]
    }
    assert observed == {
        "blue_seed_levels.movie": (
            [120, 1030, 2074, 2950], [7, 7, 6, 7], [754, 1704, 2794, 3762]),
        "brown_seed_levels.movie": (
            [144, 718, 1470, 1982], [5, 3, 8, 2], [472, 1166, 1950]),
        "green_seed_levels.movie": (
            [199, 801, 1467, 2087], [4, 10, 9, 1], [551, 1187, 2015, 2645]),
        "purple_seed_levels.movie": (
            [133, 675, 1253, 1657, 1941], [6, 6, 6, 5, 6],
            [437, 989, 1635, 1879, 2243]),
        "yellow_seed_levels.movie": (
            [144, 1120, 1758, 2034, 2910], [14, 13, 11, 11, 1],
            [814, 1556, 1852, 2518]),
    }
    assert all(len(row["cursor_events"]) == len(row["creation_frames"])
               for row in finding["movies"])
    assert all(all(event["plant_type_changes"] == 1
                   and event["after"] == event["before"] + 1
                   for event in row["cursor_events"])
               for row in finding["movies"])

    variants = finding["selector_variants"]
    assert set(variants) == {
        "bea914390921740ed74819afc477c4c13da8c5463bd158b7fc6203dc73c20394",
        "e81cf16a93aab32481e09f1b559cdad89cb9d4a02cda77e71380a3de4c954b86",
    }
    brown = variants["bea914390921740ed74819afc477c4c13da8c5463bd158b7fc6203dc73c20394"]
    common = variants["e81cf16a93aab32481e09f1b559cdad89cb9d4a02cda77e71380a3de4c954b86"]
    assert brown["movies"] == ["movies/Phase4/A13/brown_seed_levels.movie.json"]
    assert len(common["movies"]) == 4
    assert brown["matrix"][11] == [9, 0] and common["matrix"][11] == [1, 0]
    assert brown["matrix"][16:] == [[6, 12288]] * 4
    assert common["matrix"][16:] == [[14, 0], [13, 0], [11, 0], [11, 0]]


def test_power_rows_retain_bounded_health_and_jump_correlations():
    findings = load(SUMMARY)["derived_findings"]
    b06 = findings["B06_invincibility"]
    assert (b06["health_initial"], b06["health_final"]) == (4, 4)
    assert b06["health_events"] == []
    assert b06["status_values_low_u16"] == [0, 2, 8]
    assert b06["power_aux_raw_s16_range"] == [-30, 0]

    b07 = findings["B07_health_power"]
    assert (b07["health_initial"], b07["health_final"]) == (3, 4)
    assert [event["movie_frame"] for event in b07["health_events"]] == [77]
    assert b07["health_events"][0]["fields"]["health"] == {"before": 3, "after": 4}
    assert b07["health_events"][0]["correlations"] == {
        "plant_cursor_changed": False, "plant_pool_changed": True,
        "player_block_changed": True, "power_status_range_changed": False,
        "selector_matrix_changed": False, "spu_ram_changed": True,
        "vram_changed": True,
    }

    b08 = findings["B08_bubble_shield"]
    assert (b08["health_initial"], b08["health_final"]) == (4, 2)
    assert [event["movie_frame"] for event in b08["health_events"]] == [277, 381]
    assert [event["fields"]["health"] for event in b08["health_events"]] == [
        {"before": 4, "after": 3}, {"before": 3, "after": 2}]
    assert all(event["correlations"]["power_status_range_changed"]
               for event in b08["health_events"])

    b09 = findings["B09_super_jump"]
    assert b09["status_values_low_u16"] == [0, 32]
    assert b09["power_aux_raw_s16_range"] == [0, 0]
    assert b09["jump_episodes"] == [
        {"airborne_records": 46, "apex_movie_frame": 22, "apex_y": -16927,
         "landing_movie_frame": 48, "takeoff_movie_frame": 2,
         "takeoff_status_low_u16": 0, "takeoff_velocity_y": -2816,
         "takeoff_y": -2847},
        {"airborne_records": 56, "apex_movie_frame": 122, "apex_y": -26013,
         "landing_movie_frame": 152, "takeoff_movie_frame": 96,
         "takeoff_status_low_u16": 32, "takeoff_velocity_y": -3520,
         "takeoff_y": -3549},
    ]
    joined = " ".join(load(SUMMARY)["bounded_conclusions"])
    assert "does not merge them into one semantic flags value" in joined
    assert "does not attribute an exact CPU writer" in joined
    assert load(SUMMARY)["live_escalation"] is None


def test_source_guard_rejects_rank_drift_and_missing_selected_evidence():
    queue = load(ROOT / "analysis/phase4_offline_opportunity_queue.json")
    capsules = load(CAPSULES)
    drifted = deepcopy(queue)
    row = next(row for row in drifted["rows"]
               if row["row_id"] == "A13_cycle_plant_output")
    row["classification"] = "offline_ready"
    row["prior_offline_analysis"] = []
    row["priority"]["rank"] = 99
    errors, _, _ = batch.source_errors(drifted, capsules)
    assert any("rank changed" in error for error in errors)

    missing = deepcopy(capsules)
    missing["capsules"] = [row for row in missing["capsules"]
                           if row["movie"] !=
                           "movies/Phase4/B09_super_jump_comparison.movie.json"]
    errors, selected, _ = batch.source_errors(queue, missing)
    assert errors
    assert selected == []
