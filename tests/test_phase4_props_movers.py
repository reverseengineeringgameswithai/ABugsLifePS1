"""Falsification and retained-evidence guards for the active Phase-4 E08 campaign."""
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
import phase4_coverage  # noqa: E402
import phase4_props_movers as props  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_props_movers.json"
ARTIFACT_SHA256 = "dd1fbe1d9c64805697cbc2ded6cd1b265ec0eb2609ff555ed9a878531df7bc10"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps = props.static_census_gaps(doc["static_census"])
    cold = doc["live"]["cold_boot"]
    if cold["started"]["reproducible"] is not True or \
            cold["status"]["reproducible"] is not True or \
            cold["status"]["truncated"] is not False or \
            cold["status"]["playback_index"] != 8580 or \
            (cold["before"]["scene"], cold["after"]["scene"]) != (1, 1):
        gaps.append("cold-boot pass-table oracle changed")

    summary = doc["live"]["breadth"]["summary"]
    if summary["anchors"] != 19 or len(summary["scenes"]) != 16 or \
            summary["actor_ids"] != list(range(1, 42)) or \
            summary["mover_trace_events"] <= 0 or \
            not summary["naturally_moving_labels"]:
        gaps.append("whole-game actor/mover breadth changed")

    clusters = doc["live"]["source_actor_clusters"]
    cluster_summary = clusters["summary"]
    if cluster_summary != {
            "observations": 605,
            "behavior_classes": 54,
            "authored_variants": 283,
            "actor_ids": list(range(1, 42)),
            "program_selectors": [
                0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16,
                17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                30, 31, 32, 33, 34, 36, 37, 38, 39],
            "nonzero_callbacks": [
                "0x80049E88", "0x8004A02C", "0x8004A0A0",
                "0x8004A0F4", "0x8004A11C", "0x8004A144",
                "0x8004A180", "0x8004A20C", "0x8004A234",
                "0x8004A2B0"],
            "confirmed_downstream_actor_ids": [11, 14, 16, 36],
            "unclassified_behavior_classes": 47,
            "unclassified_authored_variants": 257,
            "all_actor_source_ids_match": True,
    }:
        gaps.append("actor/source cluster census changed")
    if len(clusters["behavior_classes"]) != 54 or \
            len(clusters["authored_variants"]) != 283:
        gaps.append("actor/source cluster rows changed")
    for row in clusters["behavior_classes"]:
        expected_type = (row["program_selector"] << 8) | row["actor_id"]
        if int(row["type_word"], 16) != expected_type:
            gaps.append("actor/source type-word join changed")
            break

    focused = doc["live"]["focused_controls"]
    expected_focus = {
        "wooden_fence.sav": (1, 484, 140, 32),
        "offering_stone_and_ramp.sav": (1, 484, 140, 32),
    }
    observed_focus = {
        row["save"]: (
            row["before"]["scene"], row["before"]["pass1"]["count"],
            row["before"]["pass3"]["count"],
            row["before"]["actors"]["live_count"])
        for row in focused["controls"]
    }
    if focused["count"] != 2 or observed_focus != expected_focus or \
            any(row["trace"]["truncated"] for row in focused["controls"]):
        gaps.append("focused E08 fixture controls changed")

    controls = doc["live"]["render_controls"]
    expected_pixels = {
        "pass1_payload_swap": 2872,
        "pass3_bitmap_disable": 5938,
        "pass3_anchor_nudge_negative": 0,
    }
    if {name: row["frame_diff"]["changed_pixels"]
            for name, row in controls.items()} != expected_pixels:
        gaps.append("phase-matched render deltas changed")
    for name, row in controls.items():
        if row["control"]["after"]["collision"] != \
                row["edited"]["after"]["collision"] or \
                row["control"]["after"]["player"] != \
                row["edited"]["after"]["player"]:
            gaps.append(f"{name} escaped the render-only boundary")
    negative = controls["pass3_anchor_nudge_negative"]
    target = negative["edited"]["writes"][0]["record"]
    if target != 61 or target not in negative["control"]["after"][
            "pass3_visible_indices"] or target not in negative["edited"][
            "after"]["pass3_visible_indices"]:
        gaps.append("pass-3 negative did not preserve cull visibility")

    pause = doc["live"]["pause_resume"]
    if (pause["paused"]["pause_flag"], pause["frozen"]["pause_flag"],
            pause["resumed"]["pause_flag"]) != (1, 1, 0) or \
            pause["paused"]["actors"]["raw_sha256"] != \
            pause["frozen"]["actors"]["raw_sha256"] or \
            pause["post_resume_trace"]["returned"] <= 0:
        gaps.append("pause/resume actor-mover boundary changed")
    reuse = doc["live"]["scene_reuse"]
    if reuse["level01_rebuilt_identically"] is not True or \
            reuse["level02_distinct"] is not True:
        gaps.append("scene-owned pass-table/actor rebuild changed")
    return gaps


def test_static_props_movers_census_recomputes_from_every_pinned_dat():
    retained = load_artifact()["static_census"]
    recomputed = props.build_static_census()
    assert recomputed == retained
    assert props.static_census_gaps(recomputed) == []
    assert recomputed["catalog"]["summary"]["files"] == 21
    assert recomputed["catalog"]["summary"]["pass1_rows"] == 9097
    assert recomputed["catalog"]["summary"]["pass3_rows"] == 1684
    assert len(recomputed["catalog"]["files"]) == 21


def test_static_and_live_leaf_mutations_turn_the_e08_proof_red():
    static = props.build_static_census()
    mutated = copy.deepcopy(static)
    mutated["catalog"]["summary"]["pass1_rows"] -= 1
    assert "census drifted" in " ".join(props.static_census_gaps(mutated))
    mutated = copy.deepcopy(static)
    mutated["catalog"]["summary"]["payload_classes"][
        "external_relative_negative"] -= 1
    assert "payload-pointer" in " ".join(props.static_census_gaps(mutated))

    executable = bytearray(props.EXE_PATH.read_bytes())
    executable[props._va_offset(props.FUNCTION_REGIONS["pass3_culler"][0])] ^= 1
    with pytest.raises(SystemExit):
        props.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["render_controls"]["pass3_bitmap_disable"][
        "frame_diff"]["changed_pixels"] = 0
    assert "render deltas" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["pause_resume"]["frozen"]["pause_flag"] = 0
    assert "pause/resume" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["source_actor_clusters"]["summary"][
        "all_actor_source_ids_match"] = False
    assert "cluster census" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["focused_controls"]["controls"][0]["before"][
        "actors"]["live_count"] = 31
    assert "focused E08" in " ".join(evidence_gaps(mutated))


def test_retained_active_e08_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert doc["campaign_state"] == "active_partial"
    assert evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_props_movers.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["duckstation"]["revision"] == (
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5")
    assert run["duckstation"]["binary_sha256"] == (
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec")
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_e08_campaign_remains_active_and_cannot_confer_completion():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "props_movers_gates")
    assert campaign["status"] == "active"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "props_movers_gates: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["E08_props_movers_gates"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_props_movers_schema_matches_static_and_mod_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_props_movers.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-props-movers/5"
    assert schema["campaign_state"] == "active_partial"
    assert schema["pristine_census"]["pass1_rows"] == \
        static["catalog"]["summary"]["pass1_rows"]
    assert schema["pristine_census"]["pass3_rows"] == \
        static["catalog"]["summary"]["pass3_rows"]
    assert schema["actor_mover_contract"]["table"] == {
        "address": 0x8009FD80, "stride": 0x84, "capacity": 64}
    assert schema["actor_source_contract"]["table"] == {
        "address": 0x80094A38, "stride": 0x1C, "capacity": 64}
    assert schema["actor_source_contract"]["observed"] == {
        "records": 605, "behavior_classes": 54, "authored_variants": 283,
        "actor_ids": 41, "program_selectors": 37,
        "nonzero_callbacks": 10, "unclassified_behavior_classes": 47,
    }
    semantic = {
        row["id"]: row
        for row in yaml.safe_load(
            (ROOT / "config/semantic_state.yaml").read_text())["entries"]
    }
    assert semantic["original.pass1_instance_table_pointer"]["address"] == 0x800824AC
    assert semantic["original.pass3_cull_table_pointer"]["address"] == 0x80082508
    assert semantic["original.enemy_spawn_source_table"]["address"] == 0x80094A38
    assert semantic["original.enemy_spawn_source_table"]["owner"] == \
        "original_game.level_actors"
    assert all(
        semantic[state_id]["owner"] == "original_game.scenery"
        for state_id in (
            "original.pass1_instance_table_pointer",
            "original.pass3_cull_table_pointer",
            "original.pass3_decor_visibility_bitmap",
        )
    )
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
