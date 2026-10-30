"""Falsifiable guards for the Phase-4 yellow-plant weapon offline batch."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_offline_plant_weapon_batch as batch  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_plant_weapon_batch.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
QUEUE = ROOT / "analysis/phase4_offline_opportunity_queue.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_batch_is_the_three_highest_ranked_coherent_open_rows():
    document = load(SUMMARY)
    assert document["schema"] == "abl-phase4-offline-plant-weapon-batch/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["queue_counts"] == {
        "rows": 107, "complete": 16, "open": 91,
        "offline_ready": 12, "offline_partial": 21,
        "live_required": 6, "no_capsule": 68,
    }
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "B11_blue_berry_shooter", "B12_homing_shooter", "B13_mine_plant"]
    assert [row["queue_rank"] for row in document["selected_rows"]] == [1, 2, 3]
    assert all(row["classification"] == "offline_ready"
               for row in document["selected_rows"])
    assert document["offline_batch"]["capsule_count"] == 4
    assert document["offline_batch"]["reconstructed_records"] == 5830
    assert len(document["capsule_summaries"]) == 4
    assert sum(row["records"] for row in document["capsule_summaries"]) == 5830
    assert {row_id: len(queries) for row_id, queries in
            document["offline_batch"]["exact_queue_queries"].items()} == {
        "B11_blue_berry_shooter": 16,
        "B12_homing_shooter": 16,
        "B13_mine_plant": 16,
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
        "bytes": 102510132,
        "media_class": "external game-derived evidence; never commit",
        "preservation_required": True,
        "schema": "abl-phase4-external-plant-weapon-index/1",
        "sha256": "15912c032fe7c648f10d6da4498a7d2d2233b71f74546316e7b0534831e77631",
    }
    assert external_path.stat().st_size == external["bytes"]
    assert phase4_common.sha256(external_path) == external["sha256"]


def test_b11_retains_type14_raw110_actor_boundary_and_constant_quota():
    finding = load(SUMMARY)["derived_findings"]["B11_blue_berry_shooter"]
    assert finding["plant_type_14_episodes"] == [{
        "slot": 0, "creation_frame": 42, "retirement_frame": None}]
    assert [(event["movie_frame"], event["slot"], event["fields"]["hp"])
            for event in finding["actor_hp_boundaries"]] == [
        (398, 0, {"before": 2, "after": 999}),
        (448, 0, {"before": 999, "after": 0}),
    ]
    assert finding["quota_values"] == [9]
    hit = finding["action2_hit_boundaries"]
    assert len(hit) == 1 and hit[0]["movie_frame"] == 398
    assert {key: hit[0]["contact"][key] for key in
            ("action", "raw_u16_24", "kind", "flags", "lifetime")} == {
        "action": 2, "raw_u16_24": 110, "kind": 0,
        "flags": 229, "lifetime": 1,
    }
    assert hit[0]["correlations"] == {
        "plant_pool_changed": True, "actor_pool_changed": True,
        "contact_pool_changed": True, "quota_changed": False,
        "vram_changed": True, "spu_ram_changed": True,
    }


def test_b12_retains_type13_raw124_two_actor_boundaries_and_constant_quota():
    finding = load(SUMMARY)["derived_findings"]["B12_homing_shooter"]
    assert finding["plant_type_13_episodes"] == [{
        "slot": 1, "creation_frame": 288, "retirement_frame": None}]
    assert [(event["movie_frame"], event["slot"], event["fields"]["hp"])
            for event in finding["actor_hp_boundaries"]] == [
        (668, 26, {"before": 1, "after": 999}),
        (716, 26, {"before": 999, "after": 0}),
        (1216, 6, {"before": 3, "after": 999}),
        (1218, 6, {"before": 999, "after": 0}),
    ]
    assert finding["quota_values"] == [26]
    assert [(event["movie_frame"], event["contact"]["action"],
             event["contact"]["raw_u16_24"], event["contact"]["flags"],
             event["contact"]["lifetime"])
            for event in finding["action2_hit_boundaries"]] == [
        (668, 2, 124, 237, 1), (1216, 2, 124, 237, 1)]
    assert all(not event["correlations"]["quota_changed"]
               for event in finding["action2_hit_boundaries"])


def test_b13_retains_two_episode_contrast_and_dedicated_negative_observation():
    finding = load(SUMMARY)["derived_findings"]["B13_mine_plant"]
    assert finding["plant_type_11_episodes"] == [
        {"slot": 5, "creation_frame": 1758, "retirement_frame": 1852},
        {"slot": 6, "creation_frame": 2034, "retirement_frame": 2518},
    ]
    assert [(event["movie_frame"], event["before"], event["after"])
            for event in finding["shared_quota_boundaries"]] == [(1848, 15, 14)]
    assert finding["shared_quota_boundaries"][0]["correlations"]["quota_changed"]
    assert [(event["movie_frame"], event["slot"], event["fields"]["hp"])
            for event in finding["shared_actor_hp_boundaries"]] == [
        (1848, 10, {"before": 2, "after": 999})]
    assert finding["dedicated_type_11_episodes"] == []
    assert finding["dedicated_quota_boundaries"] == []
    assert finding["dedicated_actor_hp_boundaries"] == []
    conclusions = " ".join(load(SUMMARY)["bounded_conclusions"])
    assert "does not attribute an exact CPU writer" in conclusions
    assert load(SUMMARY)["live_escalation"] is None


def test_source_guard_rejects_rank_drift_and_missing_selected_evidence():
    queue = load(QUEUE)
    capsules = load(CAPSULES)
    drifted = deepcopy(queue)
    row = next(row for row in drifted["rows"]
               if row["row_id"] == "B11_blue_berry_shooter")
    row["classification"] = "offline_ready"
    row["prior_offline_analysis"] = []
    row["priority"]["rank"] = 99
    errors, _, _ = batch.source_errors(drifted, capsules)
    assert any("rank changed" in error for error in errors)

    missing = deepcopy(capsules)
    missing["capsules"] = [row for row in missing["capsules"]
                           if row["movie"] !=
                           "movies/Phase4/B13_mine_enemy.movie.json"]
    errors, selected, _ = batch.source_errors(queue, missing)
    assert errors
    assert selected == []
