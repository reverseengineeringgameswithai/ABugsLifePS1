"""Falsifiable guards for the Phase-4 seed lifecycle offline batch."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_offline_seed_lifecycle_batch as batch  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_seed_lifecycle_batch.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
QUEUE = ROOT / "analysis/phase4_offline_opportunity_queue.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_batch_is_the_three_highest_ranked_coherent_open_rows():
    document = load(SUMMARY)
    assert document["schema"] == "abl-phase4-offline-seed-lifecycle-batch/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["queue_counts"] == {
        "rows": 107, "complete": 16, "open": 91,
        "offline_ready": 9, "offline_partial": 24,
        "live_required": 6, "no_capsule": 68,
    }
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "A09_seed_pickup_drop", "A14_plant_seed", "A15_uproot_plant"]
    assert [row["queue_rank"] for row in document["selected_rows"]] == [1, 2, 3]
    assert all(row["classification"] == "offline_ready"
               for row in document["selected_rows"])
    assert document["offline_batch"]["capsule_count"] == 3
    assert document["offline_batch"]["reconstructed_records"] == 6025
    assert len(document["capsule_summaries"]) == 3
    assert sum(row["records"] for row in document["capsule_summaries"]) == 6025
    assert {row_id: len(queries) for row_id, queries in
            document["offline_batch"]["exact_queue_queries"].items()} == {
        "A09_seed_pickup_drop": 18,
        "A14_plant_seed": 9,
        "A15_uproot_plant": 9,
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
        "bytes": 25730624,
        "media_class": "external game-derived evidence; never commit",
        "preservation_required": True,
        "schema": "abl-phase4-external-seed-lifecycle-index/1",
        "sha256": "64edaa57ce386f2065fc26eae6ef5d7ed66a13cdf7077f281232f56ab50310c5",
    }
    assert external_path.stat().st_size == external["bytes"]
    assert phase4_common.sha256(external_path) == external["sha256"]


def test_a09_retains_three_exact_attachment_release_and_reversal_episodes():
    finding = load(SUMMARY)["derived_findings"]["A09_seed_pickup_drop"]
    assert finding["mobile_seed_slot"] == 20
    assert finding["mobile_seed_address"] == "0x800a07d0"
    runs = finding["carry_runs"]
    assert [(row["start_movie_frame"], row["end_movie_frame"])
            for row in runs] == [(146, 173), (280, 557), (680, 697)]
    assert [row["pickup_press_frame"] for row in runs] == [111, 245, 644]
    assert [row["pickup_to_attachment_frames"] for row in runs] == [35, 35, 36]
    assert [row["drop_press_frame"] for row in runs] == [171, 556, 696]
    assert [row["detachment_movie_frame"] for row in runs] == [174, 558, 698]
    assert [row["drop_to_detachment_frames"] for row in runs] == [3, 2, 2]
    assert [(row["first_horizontal_velocity_reversal"]["movie_frame"],
             row["first_horizontal_velocity_reversal"]["component"],
             row["first_horizontal_velocity_reversal"]["initial_value"],
             row["first_horizontal_velocity_reversal"]["reversed_value"])
            for row in runs] == [
        (192, "velocity_x", -71, 668),
        (562, "velocity_z", -1022, 1168),
        (720, "velocity_x", -18, 700),
    ]
    assert [row["first_stable_position"]["movie_frame"] for row in runs] == [206, 606, 746]
    assert all("collision primitive or geometry" in finding["bounded_observation"]
               for _ in [0])


def test_a14_retains_four_cursor_advancing_seed_raise_creations():
    finding = load(SUMMARY)["derived_findings"]["A14_plant_seed"]
    assert finding["mobile_seed_slot"] == 1
    assert finding["mobile_seed_address"] == "0x8009fe04"
    creations = finding["creations"]
    assert [row["movie_frame"] for row in creations] == [120, 1030, 2074, 2950]
    assert [row["after_type"] for row in creations] == [7, 7, 6, 7]
    assert [(row["cursor_before"], row["cursor_after"]) for row in creations] == [
        (0, 1), (1, 2), (2, 3), (3, 4)]
    assert [row["nearest_prior_cross_press"] for row in creations] == [70, 967, 2032, 2898]
    assert [row["cross_to_creation_frames"] for row in creations] == [50, 63, 42, 52]
    assert [row["seed_raise_episode"]["start_movie_frame"] for row in creations] == [
        102, 1012, 2056, 2932]
    assert all(row["seed_raise_episode"]["end_movie_frame"] == row["movie_frame"]
               for row in creations)
    assert all(row["seed_raise_episode"]["net_y"] == 20480 for row in creations)


def test_a15_retains_four_descents_retirements_and_nonuniversal_phase_byte():
    finding = load(SUMMARY)["derived_findings"]["A15_uproot_plant"]
    retirements = finding["retirements"]
    assert [row["movie_frame"] for row in retirements] == [754, 1704, 2794, 3762]
    assert [row["before_type"] for row in retirements] == [7, 7, 6, 7]
    assert finding["retirement_phase_raw_values"] == [5, 5, 13, 5]
    assert [row["nearest_prior_square_press"] for row in retirements] == [
        657, 1595, 2684, 3653]
    assert [row["square_to_descent_frames"] for row in retirements] == [45, 53, 52, 53]
    assert [row["seed_descent_episode"]["start_movie_frame"] for row in retirements] == [
        702, 1648, 2736, 3706]
    assert [row["seed_descent_episode"]["end_movie_frame"] for row in retirements] == [
        728, 1674, 2762, 3732]
    assert [row["retirement_after_descent_frames"] for row in retirements] == [26, 30, 32, 30]
    assert "not a universal player-uproot signature" in finding["bounded_observation"]
    conclusions = " ".join(load(SUMMARY)["bounded_conclusions"])
    assert "actor pool base is 0x8009FD80" in conclusions
    assert "does not attribute an exact CPU writer" in conclusions
    assert load(SUMMARY)["live_escalation"] is None


def test_source_guard_rejects_rank_drift_missing_capsule_and_wrong_row_count():
    queue = load(QUEUE)
    capsules = load(CAPSULES)
    drifted = deepcopy(queue)
    row = next(row for row in drifted["rows"]
               if row["row_id"] == "A09_seed_pickup_drop")
    row["classification"] = "offline_ready"
    row["prior_offline_analysis"] = []
    row["priority"]["rank"] = 99
    errors, _, _ = batch.source_errors(drifted, capsules)
    assert any("rank changed" in error for error in errors)

    missing = deepcopy(capsules)
    missing["capsules"] = [row for row in missing["capsules"]
                           if row["movie"] !=
                           "movies/Phase4/A13/blue_seed_levels.movie.json"]
    errors, selected, _ = batch.source_errors(queue, missing)
    assert any("selected capsule absent" in error for error in errors)
    assert len(selected) == 2

    short = deepcopy(queue)
    short["rows"].pop()
    errors, _, _ = batch.source_errors(short, capsules)
    assert any("exactly 107 rows" in error for error in errors)
