import copy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_closure_debt as debt
import phase4_common as common


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_debt_has_all_rows_and_the_nine_authoritative_dimensions():
    document = load(debt.OUTPUT)
    mechanics = set(common.baseline_rows())
    assert document["schema"] == "abl-phase4-closure-debt/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert len(document["rows"]) == len(mechanics) == 107
    assert {row["row_id"] for row in document["rows"]} == mechanics
    assert document["dimension_order"] == [
        "original_oracle", "complete_frontier", "typed_state", "lifecycle",
        "original_interfaces", "campaign_breadth", "cross_system_behavior",
        "source_closure", "durable_evidence",
    ]
    assert all(set(row["dimensions"]) == set(document["dimension_order"])
               for row in document["rows"])


def test_completed_rows_are_met_and_open_rows_are_not_silently_closed():
    document = load(debt.OUTPUT)
    for row in document["rows"]:
        states = {value["state"] for value in row["dimensions"].values()}
        if row["completion_state"] in {"campaign_complete", "reviewed_absent"}:
            assert states == {"met"}
        else:
            assert row["counts"]["remaining"] > 0


def test_authored_met_claim_without_low_level_evidence_stays_unmet():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["status"] == "active")
    mutated = copy.deepcopy(registry)
    target = next(row for row in mutated["child_campaigns"]
                  if row["id"] == campaign["id"])
    target["dimension_claims"] = {
        "source_closure": {
            "claim": "met", "evidence": [], "authoritative_paths": [],
            "confidence": "confirmed", "residuals": [],
        }
    }
    document = debt.build(registry=mutated)
    affected = next(row for row in document["rows"]
                    if row["campaign_id"] == campaign["id"])
    assert affected["dimensions"]["source_closure"]["state"] != "met"
    assert any("met claim has no low-level evidence" in error
               for error in document["errors"])


def test_authored_not_applicable_claim_requires_an_absence_proof():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["status"] == "active")
    mutated = copy.deepcopy(registry)
    target = next(row for row in mutated["child_campaigns"]
                  if row["id"] == campaign["id"])
    target["dimension_claims"] = {
        "campaign_breadth": {
            "claim": "not_applicable", "evidence": [],
            "authoritative_paths": [], "confidence": "confirmed",
            "residuals": [],
        }
    }
    document = debt.build(registry=mutated)
    affected = next(row for row in document["rows"]
                    if row["campaign_id"] == campaign["id"])
    assert affected["dimensions"]["campaign_breadth"]["state"] != "not_applicable"
    assert any("not_applicable claim has no low-level evidence" in error
               for error in document["errors"])


def test_scheduler_enforces_one_campaign_and_three_row_wip():
    document = load(debt.OUTPUT)
    selected = document["scheduler"]["selected_campaigns"]
    assert len(selected) <= 1
    assert all(len(row["rows"]) <= 3 for row in selected)
    assert document["scheduler"]["stagnation_limit"] == 2
    assert document["scheduler"]["campaign_verifier_interval"] == 3


def test_movie_ready_projection_changes_only_transient_scheduler_selection():
    document = load(debt.OUTPUT)
    priority = load(debt.MOVIE_PRIORITY_PATH)
    batch = priority["selected_batch"]
    projected = debt.apply_movie_ready_selection(
        document, batch["batch_id"], batch["rows"], priority)
    assert projected["valid"] is True
    assert projected["errors"] == []
    assert projected["rows"] == document["rows"]
    assert projected["counts"] == document["counts"]
    assert projected["dimension_order"] == document["dimension_order"]
    assert projected["scheduler"]["selected_campaigns"][0]["campaign_id"] == \
        batch["batch_id"]
    assert projected["scheduler"]["selected_campaigns"][0]["rows"] == \
        batch["rows"]
    assert len(batch["rows"]) <= 3

    rejected = debt.apply_movie_ready_selection(
        document, batch["batch_id"], ["A04_kick"], priority)
    assert rejected["valid"] is False
    assert any("selected rows differ" in error for error in rejected["errors"])
    assert any("zero-debt row A04_kick" in error
               for error in rejected["errors"])
    measured = debt.apply_movie_ready_selection(
        document, "movie-ready:A04_kick", ["A04_kick"], priority,
        continuation=True)
    assert measured["valid"] is True
    assert measured["rows"] == document["rows"]
    assert "not a new work selection" in \
        measured["scheduler"]["selected_campaigns"][0]["next_action"]


def test_e15_two_pc_falsifier_returns_handoff_to_static():
    document = load(debt.OUTPUT)
    selected = document["scheduler"]["selected_campaigns"]
    assert [row["campaign_id"] for row in selected] == ["fmv_playback"]
    assert selected[0]["next_lane"] == "static"
    assert "both replacement chains" in selected[0]["next_action"]
    assert "closed staged passive control" in selected[0]["next_action"]
    assert "mutation-guarded exact-PC adapter" in selected[0]["next_action"]
    assert "closed v2 direct-command admission" in selected[0]["next_action"]
    assert "all three investigator receipts" in \
        selected[0]["next_action"]
    assert "frame-15816 anchor is now proven post-retirement" in \
        selected[0]["next_action"]
    assert "0x8004FD74 or 0x8005029C" in \
        selected[0]["next_action"]
    assert "typed two-PC first-hit boundary" in \
        selected[0]["next_action"]
    assert "tracked v2 receipt emitter and validator now admit" in \
        selected[0]["next_action"]
    assert "escapes the frame-15856 ceiling" in selected[0]["next_action"]
    assert "Re-localize an anchor before frame 15792" in \
        selected[0]["next_action"]
    row = next(row for row in document["rows"] if row["row_id"] == "E15_fmv")
    assert row["next_lane"] == "static"
    assert "Both caller-owned replacement requests are now statically complete" in \
        row["next_lane_reason"]
    assert "falsified twice" in row["next_lane_reason"]
    assert "Fresh verifier consumption remains pending" in \
        row["next_lane_reason"]
    assert "resident state-one scene-flow dispatcher" in \
        row["next_lane_reason"]
    assert "bits\\memory.bin" in \
        row["next_lane_reason"]
    assert "0x800B5788" in \
        row["next_lane_reason"]
    assert "precise full-cold-boot transfer branch has no admissible receipt" \
        in row["next_lane_reason"]
    assert "advance 15719 frames to frame 15720" in \
        row["next_lane_reason"]
    assert "DMA fact is untested" in row["next_lane_reason"]
    assert "old observer method is retired" in row["next_lane_reason"]
    assert "transfer pagination remained incomplete or" in \
        row["next_lane_reason"]
    assert "Pristine resident reconstruction now closes that decomposition" \
        in row["next_lane_reason"]
    assert "eighteen CD sectors at 0x80046078" in row["next_lane_reason"]
    assert "0x80046078 and 0x800460C4" in row["next_lane_reason"]
    assert "tracked exact-PC adapter now passes closed-plan and synthetic" in \
        row["next_lane_reason"]
    assert "current RPC/source/binary/pristine" in row["next_lane_reason"]
    assert "fresh generated escalation now binds one passive" in \
        row["next_lane_reason"]
    assert "15800..15896" in row["next_lane_reason"]
    assert "15816..15880" in row["next_lane_reason"]
    assert "candidate v2 validator now admits the direct exact-PC stream" \
        in row["next_lane_reason"]
    assert "observer-plan schema v2" in row["next_lane_reason"]
    assert "exactly one paused atomic anchor job" in row["next_lane_reason"]
    assert "tracked adapter replays every normalized result body" in \
        row["next_lane_reason"]
    assert "Three stream, anchor and page mutations fail" in \
        row["next_lane_reason"]
    assert "historical schema-v1 atomic fixture remains accepted" in \
        row["next_lane_reason"]
    assert "two-PC direct-command schema" in row["next_lane_reason"]
    assert "exact 15792..15856 bound" in row["next_lane_reason"]
    assert "65-frame, event, identity, pagination and cleanup mutations" in \
        row["next_lane_reason"]
    assert "later immutable iteration-before ledger contains exactly this " \
        "planned escalation" in \
        row["next_lane_reason"]
    assert "changes the next lane to live without claiming a DMA event or " \
        "lifecycle promotion" in \
        row["next_lane_reason"]
    assert "reaches failure frame 15857 without either managed stop" in \
        row["next_lane_reason"]
    assert "changes the binding lane back to static" in \
        row["next_lane_reason"]
    assert row["dimensions"]["original_interfaces"]["state"] == "partial"
    assert row["dimensions"]["durable_evidence"]["state"] == "met"
    assert selected[0]["counts"] == {"met": 4, "remaining": 5}


def test_teardown_evidence_cannot_promote_intersecting_original_interfaces():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    claim = campaign["dimension_claims"]["original_interfaces"]
    assert claim["claim"] == "partial"
    assert any(row["intersects_dimension"] is True
               for row in claim["residuals"])
    document = debt.build(registry=registry)
    row = next(row for row in document["rows"] if row["row_id"] == "E15_fmv")
    assert row["dimensions"]["original_interfaces"]["state"] == "partial"
    assert row["dimensions"]["original_interfaces"]["errors"] == []


def test_e15_durable_evidence_requires_current_fixtures_and_offline_index():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    claim = campaign["dimension_claims"]["durable_evidence"]
    assert claim["claim"] == "met"
    assert claim["confidence"] == "confirmed"
    assert all(row["intersects_dimension"] is False
               for row in claim["residuals"])

    document = debt.build(registry=registry)
    row = next(row for row in document["rows"] if row["row_id"] == "E15_fmv")
    assert row["dimensions"]["durable_evidence"]["state"] == "met"

    mutated = copy.deepcopy(registry)
    target = next(row for row in mutated["child_campaigns"]
                  if row["id"] == "fmv_playback")
    assertion = target["dimension_claims"]["durable_evidence"]["evidence"][0]
    assertion["sha256"] = "0" * 64
    falsified = debt.build(registry=mutated)
    row = next(row for row in falsified["rows"] if row["row_id"] == "E15_fmv")
    assert row["dimensions"]["durable_evidence"]["state"] != "met"
    assert any("assertion sha256 does not match retained bytes" in error
               for error in row["dimensions"]["durable_evidence"]["errors"])

    mutated = copy.deepcopy(registry)
    target = next(row for row in mutated["child_campaigns"]
                  if row["id"] == "fmv_playback")
    assertion = next(
        row for row in target["dimension_claims"]["durable_evidence"]["evidence"]
        if row["artifact"] == "analysis/phase4_offline_fmv_batch.json"
        and row["json_path"] == "offline_batch.query_count")
    assertion["expected"] = 9
    falsified = debt.build(registry=mutated)
    row = next(row for row in falsified["rows"] if row["row_id"] == "E15_fmv")
    assert row["dimensions"]["durable_evidence"]["state"] != "met"
    assert any("offline_batch.query_count: 18 does not satisfy eq 9" in error
               for error in row["dimensions"]["durable_evidence"]["errors"])


def test_retained_debt_is_byte_fresh():
    assert debt.OUTPUT.read_text() == debt.render(debt.build())
