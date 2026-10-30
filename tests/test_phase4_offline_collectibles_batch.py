"""Falsifiable guards for the Phase-4 collectibles/equipment offline batch."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_offline_collectibles_batch as batch  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_collectibles_batch.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_batch_is_the_selected_four_row_coherent_cluster():
    document = load(SUMMARY)
    assert document["schema"] == "abl-phase4-offline-collectibles-batch/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["queue_counts"] == {
        "rows": 107, "complete": 16, "open": 91,
        "offline_ready": 21, "offline_partial": 12,
        "live_required": 6, "no_capsule": 68,
    }
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "C01_grain_pickup", "C02_fifty_grain_reward",
        "C13_grain_harvester", "C14_telescope",
    ]
    assert [row["queue_rank"] for row in document["selected_rows"]] == [1, 2, 3, 4]
    assert all(row["classification"] == "offline_ready"
               for row in document["selected_rows"])
    assert document["offline_batch"]["capsule_count"] == 4
    assert document["offline_batch"]["reconstructed_records"] == 2354
    assert len(document["capsule_summaries"]) == 4
    assert sum(row["records"] for row in document["capsule_summaries"]) == 2354
    assert {row: len(queries) for row, queries in
            document["offline_batch"]["exact_queue_queries"].items()} == {
        "C01_grain_pickup": 8,
        "C02_fifty_grain_reward": 10,
        "C13_grain_harvester": 8,
        "C14_telescope": 8,
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
        assert summary["capsule_manifest_sha256"] == capsule["capsule_manifest_sha256"]
        assert summary["capsule_tree_sha256"] == capsule["capsule_tree_sha256"]
    for relative, expected in document["source_dependencies"].items():
        assert phase4_common.sha256(ROOT / relative) == expected
    external = document["external_index"]
    external_path = Path(external["absolute_path"])
    assert external["media_class"] == "external game-derived evidence; never commit"
    assert external["preservation_required"] is True
    assert external_path.stat().st_size == external["bytes"]
    assert phase4_common.sha256(external_path) == external["sha256"]


def test_c01_and_c02_retain_bounded_grain_and_effect_signatures():
    findings = load(SUMMARY)["derived_findings"]
    c01 = findings["C01_grain_pickup"]
    assert (c01["grain_initial"], c01["grain_final"]) == (10, 12)
    assert c01["grain_event_frames"] == [196, 540]
    assert all(len(event["effect_record_resets"]) == 5 for event in c01["grain_events"])
    assert all(all(event["correlations"].values()) for event in c01["grain_events"])
    assert all(event["fields"]["grain"]["after"]
               - event["fields"]["grain"]["before"] == 1
               for event in c01["grain_events"])

    c02 = findings["C02_fifty_grain_reward"]
    assert (c02["grain_initial"], c02["grain_final"]) == (49, 50)
    assert c02["grain_event_frames"] == [160]
    assert len(c02["grain_events"][0]["effect_record_resets"]) == 5
    assert c02["grain_events"][0]["correlations"]["spu_ram_changed"] is False
    assert (c02["health_initial"], c02["health_final"]) == (4, 4)
    assert c02["health_display_values"] == list(range(8))
    assert c02["health_display_event_count"] == 218
    assert c02["health_display_at_grain_boundary"] == {
        "movie_frame": 160, "before": 1, "after": 2}


def test_c13_retains_nine_one_for_one_action20_correlations():
    finding = load(SUMMARY)["derived_findings"]["C13_grain_harvester"]
    assert (finding["grain_initial"], finding["grain_final"]) == (0, 9)
    assert finding["grain_event_frames"] == [211, 227, 247, 281, 339, 485, 507, 535, 561]
    assert finding["action20_transition_count"] == 9
    for event in finding["grain_events"]:
        assert event["fields"]["grain"]["after"] - event["fields"]["grain"]["before"] == 1
        assert all(event["correlations"].values())
        assert len(event["action20_collection_transitions"]) == 1
        transition = event["action20_collection_transitions"][0]
        assert transition["before_active_gate"] > 1
        assert transition["after_active_gate"] == 1
        assert (transition["before_state"], transition["after_state"]) == (22, 16)
        assert transition["distance_squared_to_player"] > 0


def test_c14_retains_camera_transition_without_ownership_overclaim():
    document = load(SUMMARY)
    finding = document["derived_findings"]["C14_telescope"]
    assert finding["player_outcome_events"] == []
    assert finding["manual_mode_values"] == [0]
    assert finding["stable_control_values"] == {
        "distance": [900],
        "object_pointer": ["0x80081d98"],
        "orbit_bias": [0],
        "orbit_yaw": [2454],
        "pitch_scale": [32],
        "profile_suppression": [1],
        "vertical_angle": [0],
        "vertical_target": [12288],
    }
    assert finding["target_change_frames"] == [65]
    assert finding["target_transition"] == {
        "before": [-1192, -66136, 480308],
        "after": [-1360, -65770, 481441],
    }
    assert finding["position_change_frames"] == list(range(65, 149, 2))
    assert finding["position_transition_last"]["movie_frame"] == 147
    joined = " ".join(document["bounded_conclusions"])
    assert "does not identify telescope ownership" in joined
    assert "does not identify the pickup/reward owner or exact writer" in joined
    assert document["live_escalation"] is None


def test_source_guard_rejects_ineligible_or_missing_selected_evidence():
    queue = load(ROOT / "analysis/phase4_offline_opportunity_queue.json")
    capsules = load(CAPSULES)
    mutated = deepcopy(queue)
    row = next(row for row in mutated["rows"] if row["row_id"] == "C01_grain_pickup")
    row["classification"] = "no_capsule"
    row["prior_offline_analysis"] = []
    errors, _, _ = batch.source_errors(mutated, capsules)
    assert any("not current open batch evidence" in error for error in errors)

    missing = deepcopy(capsules)
    missing["capsules"] = [
        row for row in missing["capsules"]
        if row["movie"] != "movies/Phase4/C01_grain_pickup.movie.json"]
    errors, selected, _ = batch.source_errors(queue, missing)
    assert errors
    assert selected == []
