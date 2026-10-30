"""Hard, mutation-oriented guards for acceleration investments 10-12."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_movie_priority as priority  # noqa: E402
import phase4_scheduler_policy as scheduler  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def policy() -> dict:
    return common.load_yaml(scheduler.POLICY_PATH)


@pytest.fixture(scope="module")
def queue() -> dict:
    return load(priority.OUTPUT)


def debt_snapshots(packet: dict, *, reduced: bool = False) -> tuple[bytes, bytes]:
    before = load(ROOT / "analysis/phase4_closure_debt.json")
    before["scheduler"]["selected_campaigns"] = [{
        "campaign_id": packet["selected_batch"]["batch_id"],
        "rows": deepcopy(packet["selected_batch"]["rows"]),
    }]
    after = deepcopy(before)
    if reduced:
        selected = set(packet["selected_batch"]["rows"])
        target = next(item for item in after["rows"]
                      if item["row_id"] in selected)
        dimension = next(name for name, detail in target["dimensions"].items()
                         if detail["state"] in {"gap", "partial"})
        target["dimensions"][dimension]["state"] = "met"
        refresh_debt_counts(after)
    return scheduler.json_bytes(before), scheduler.json_bytes(after)


def refresh_debt_counts(document: dict) -> None:
    dimensions = {"gap": 0, "partial": 0, "met": 0}
    for row in document["rows"]:
        states = [detail["state"] for detail in row["dimensions"].values()]
        row["counts"] = {
            "met": states.count("met"),
            "not_applicable": 0,
            "remaining": states.count("gap") + states.count("partial"),
        }
        for state in states:
            dimensions[state] += 1
    document["counts"]["dimensions"] = dimensions


def attempt(packet: dict, *, reduced: bool = False) -> tuple[dict, bytes, bytes]:
    before, after = debt_snapshots(packet, reduced=reduced)
    progress = scheduler.derive_progress(
        before, after, len(packet["attempt_history"]) + 1)
    return progress, before, after


def next_packet(queue: dict, policy: dict, previous: dict,
                *, reduced: bool = False) -> dict:
    progress, before, after = attempt(previous, reduced=reduced)
    return scheduler.packet(
        queue, policy, previous, progress, queue, before, after)


def row(queue: dict, row_id: str) -> dict:
    return next(item for item in queue["rows"] if item["row_id"] == row_id)


def test_reviewed_policy_is_exact_typed_and_non_promoting(policy):
    assert scheduler.validate_policy(policy) == []
    assert policy["cooldown"] == {
        "consecutive_no_reduction_threshold": 2,
        "rotate_after_first_no_reduction": True,
        "scope": "selected_rows_union",
        "release": "completed_disjoint_iteration_or_any_debt_reduction",
        "exhaustion": "fail_closed",
        "max_retained_attempts": 32,
    }
    assert all(value is True for value in policy["authority"].values())
    assert policy["authority"]["closure_promotion_forbidden"] is True
    assert policy["authority"]["live_authorization_forbidden"] is True


@pytest.mark.parametrize("mutation", [
    lambda p: p["cooldown"].__setitem__(
        "consecutive_no_reduction_threshold", True),
    lambda p: p["cooldown"].__setitem__(
        "consecutive_no_reduction_threshold", 3),
    lambda p: p["cooldown"].__setitem__("release", "manual"),
    lambda p: p["expected_value"]["benefit_weights"].__setitem__(
        "dependency_unlock", True),
    lambda p: p["expected_value"]["dimension_readiness"]["static"].reverse(),
    lambda p: p["fixture_cover"].__setitem__("frames_per_cost_unit", 0),
    lambda p: p["fixture_cover"]["capsule_domains"].pop(),
    lambda p: p["authority"].__setitem__("ranking_only", False),
    lambda p: p.__setitem__("unknown", True),
])
def test_policy_rejects_authority_type_shape_and_value_drift(policy, mutation):
    changed = deepcopy(policy)
    mutation(changed)
    assert scheduler.validate_policy(changed)


def test_retained_expected_value_is_integer_exact_and_rederived(queue, policy):
    eligible = [item for item in queue["rows"]
                if item["eligibility"]["eligible"]
                and item["selection"]["selectable"]]
    assert eligible
    for item in eligible:
        expected = scheduler.expected_value(item, policy)
        assert item["expected_value"] == expected
        assert type(expected["benefit_units"]) is int
        assert type(expected["cost_units"]) is int
        assert type(expected["score_per_1000"]) is int
        assert expected["ranking_only"] is True
        assert set(expected["benefit_inputs"][
            "candidate_reducible_dimensions"]) <= set(
                scheduler.EXPECTED_DIMENSIONS)
    batches = queue["candidate_batches"]
    ratios = [Fraction(item["expected_value"]["benefit_units"],
                       item["expected_value"]["cost_units"])
              for item in batches]
    assert ratios == sorted(ratios, reverse=True)
    assert queue["selected_batch"] == batches[0]


@pytest.mark.parametrize(("field", "value"), [
    ("dependency_unlock_count", True),
    ("derived_remaining", True),
])
def test_expected_value_rejects_boolean_authoritative_numbers(
        queue, policy, field, value):
    target = deepcopy(next(item for item in queue["rows"]
                           if item.get("expected_value")))
    target[field] = value
    with pytest.raises(ValueError, match="non-negative integer"):
        scheduler.expected_value(target, policy)


@pytest.mark.parametrize("field", [
    "capsule_availability", "derived_indexes", "prior_offline_analysis",
    "movie_anchors",
])
def test_expected_value_rejects_boolean_readiness_collections(
        queue, policy, field):
    target = deepcopy(next(item for item in queue["rows"]
                           if item.get("expected_value")))
    target[field] = True
    with pytest.raises(ValueError, match="list of objects"):
        scheduler.expected_value(target, policy)


def test_packet_rejects_readiness_type_drift_even_on_ineligible_rows(
        queue, policy):
    for field in ("capsule_availability", "derived_indexes",
                  "prior_offline_analysis", "movie_anchors"):
        changed = deepcopy(queue)
        target = next(item for item in changed["rows"]
                      if item["eligibility"]["eligible"] is False)
        target[field] = True
        with pytest.raises(ValueError):
            scheduler.packet(changed, policy)
    changed = deepcopy(queue)
    target = next(item for item in changed["rows"]
                  if item["eligibility"]["eligible"] is False)
    target["dimension_states"] = True
    with pytest.raises(ValueError):
        scheduler.packet(changed, policy)


def test_candidate_reducibility_is_surface_bounded_not_a_success_claim(
        queue, policy):
    target = deepcopy(row(queue, "E08_props_movers_gates"))
    original = scheduler.candidate_reducible_dimensions(target, policy)
    assert original
    assert all(target["dimension_states"][name] in {"gap", "partial"}
               for name in original)
    target["static_ownership"] = {
        key: 0 for key in (
            "function_count", "typed_state_count", "reader_group_count",
            "writer_group_count")}
    target["capsule_availability"] = []
    target["derived_indexes"] = []
    target["prior_offline_analysis"] = []
    target["movie_anchors"] = []
    assert scheduler.candidate_reducible_dimensions(target, policy) == []


def test_weighted_fixture_cover_is_complete_current_and_costed(queue):
    fixture_pins = load(ROOT / "analysis/phase0_2_external_fixture_set.json")[
        "entries"]
    for batch in queue["candidate_batches"]:
        cover = batch["fixture_cover"]
        assert cover["algorithm"] == \
            "deterministic_weighted_greedy_set_cover"
        assert cover["complete"] is True
        assert cover["uncovered"] == []
        assert cover["covered_weight"] == cover["total_weight"]
        assert cover["chosen_fixtures"]
        assert cover["total_cost_units"] == sum(
            item["cost_units"] for item in cover["chosen_fixtures"])
        universe = {item["id"] for item in cover["universe"]}
        covered = set().union(*(
            set(item["covers"]) for item in cover["chosen_fixtures"]))
        assert universe <= covered
        for item in cover["chosen_fixtures"]:
            movie = item["movie"]
            state = item["start_state"]
            assert fixture_pins[movie["path"]]["sha256"] == movie["sha256"]
            assert fixture_pins[state["path"]]["sha256"] == state["sha256"]
            assert common.sha256(ROOT / movie["path"]) == movie["sha256"]
            assert common.sha256(ROOT / state["path"]) == state["sha256"]


def test_weighted_cover_prefers_one_shared_low_cost_fixture(policy):
    def anchor(path: str, frames: int) -> dict:
        return {
            "movie": {"path": path, "sha256": "1" * 64,
                      "frame_count": frames},
            "start_state": {"path": path + ".sav", "sha256": "2" * 64},
            "capsule": {
                "capsule_manifest_sha256": "3" * 64,
                "capsule_tree_sha256": "4" * 64,
                "frames": frames,
                "control_match": True,
                "independent_control_verified": True,
                "verified_domains": list(
                    policy["fixture_cover"]["capsule_domains"]),
                "preservation_verified": True,
            },
            "verified": True,
        }
    shared = anchor("movies/Phase4/shared.movie.json", 120)
    rows = [{
        "row_id": "X01", "family": "family", "movie_anchors": [
            deepcopy(shared), anchor("movies/Phase4/x.movie.json", 1200)],
    }, {
        "row_id": "X02", "family": "family", "movie_anchors": [
            deepcopy(shared), anchor("movies/Phase4/y.movie.json", 1200)],
    }]
    result = scheduler.weighted_fixture_cover(rows, policy)
    assert result["complete"] is True
    assert [item["movie"]["path"] for item in result["chosen_fixtures"]] == [
        "movies/Phase4/shared.movie.json"]


def test_weighted_cover_rejects_conflicting_shared_path_identity(policy):
    def row(row_id: str, state_hash: str) -> dict:
        return {
            "row_id": row_id,
            "family": "family",
            "movie_anchors": [{
                "movie": {"path": "movies/Phase4/shared.movie.json",
                          "sha256": "1" * 64, "frame_count": 5},
                "start_state": {"path": "movies/Phase4/shared.movie.sav",
                                "sha256": state_hash},
                "capsule": None,
                "verified": True,
            }],
        }
    with pytest.raises(ValueError, match="conflicting.*identity alias"):
        scheduler.weighted_fixture_cover(
            [row("R1", "2" * 64), row("R2", "3" * 64)], policy)


@pytest.mark.parametrize(("domains", "control"), [
    ([], True),
    (list(scheduler.EXPECTED_DIMENSIONS[:1]), True),
    (None, False),
])
def test_capsule_requirements_remain_uncovered_without_verified_evidence(
        policy, domains, control):
    capsule = {
        "capsule_manifest_sha256": "3" * 64,
        "capsule_tree_sha256": "4" * 64,
        "frames": 10,
        "control_match": control,
        "independent_control_verified": control,
        "verified_domains": domains,
        "preservation_verified": True,
    }
    result = scheduler.weighted_fixture_cover([{
        "row_id": "R1", "family": "family", "movie_anchors": [{
            "movie": {"path": "movies/Phase4/r.movie.json",
                      "sha256": "1" * 64, "frame_count": 10},
            "start_state": {"path": "movies/Phase4/r.movie.sav",
                            "sha256": "2" * 64},
            "capsule": capsule,
            "verified": True,
        }],
    }], policy)
    assert result["complete"] is False
    assert result["uncovered"]
    universe = {item["id"] for item in result["universe"]}
    assert "row:R1:independent_control" in universe
    assert all(f"row:R1:domain:{domain}" in universe
               for domain in policy["fixture_cover"]["capsule_domains"])


def test_capsule_availability_cannot_shrink_out_of_cover_universe(queue, policy):
    target = deepcopy(next(item for item in queue["rows"]
                           if item["capsule_availability"]))
    assert target["movie_anchors"]
    for anchor in target["movie_anchors"]:
        anchor["capsule"] = None
    with pytest.raises(ValueError, match="availability does not match anchors"):
        scheduler.weighted_fixture_cover([target], policy)


def test_first_no_reduction_rotates_and_second_activates_union_cooldown(
        queue, policy):
    first = scheduler.packet(queue, policy)
    second = next_packet(queue, policy, first)
    assert second["rotation"]["required"] is True
    assert second["cooldown"]["active"] is False
    assert set(first["selected_batch"]["rows"]).isdisjoint(
        second["selected_batch"]["rows"])

    third = next_packet(queue, policy, second)
    cooled = set(first["selected_batch"]["rows"]) | set(
        second["selected_batch"]["rows"])
    assert third["cooldown"] == {
        "threshold": 2,
        "active": True,
        "excluded_rows": sorted(cooled),
        "release": "completed_disjoint_iteration_or_any_debt_reduction",
    }
    assert cooled.isdisjoint(third["selected_batch"]["rows"])
    assert len(third["attempt_history"]) == 2

    released = next_packet(queue, policy, third, reduced=True)
    assert released["cooldown"]["active"] is False
    assert released["selection_diagnostics"][
        "consecutive_no_reduction_attempts"] == 0
    diagnostics = released["selection_diagnostics"]["dynamic_expected_value"]
    assert not any(item["excluded_by_rotation_or_cooldown"]
                   for item in diagnostics)


def test_historical_no_reduction_cost_is_visible_and_changes_denominator(
        queue, policy):
    first = scheduler.packet(queue, policy)
    second = next_packet(queue, policy, first)
    diagnostics = second["selection_diagnostics"]["dynamic_expected_value"]
    attempted = next(item for item in diagnostics
                     if item["batch_id"] == first["selected_batch"]["batch_id"])
    untouched = next(item for item in diagnostics
                     if item["prior_no_reduction_overlap_count"] == 0)
    assert attempted["prior_no_reduction_overlap_count"] == 1
    assert attempted["excluded_by_rotation_or_cooldown"] is True
    assert attempted["cost_units"] > first["selected_batch"][
        "expected_value"]["cost_units"]
    assert untouched["excluded_by_rotation_or_cooldown"] is False


def test_real_source_backed_debt_reduction_can_advance_to_new_queue(
        queue, policy, tmp_path, monkeypatch):
    first = scheduler.packet(queue, policy)
    progress, before, after = attempt(first, reduced=True)
    after_doc = json.loads(after)
    debt_path = tmp_path / "phase4_closure_debt.json"
    debt_path.write_bytes(after)
    monkeypatch.setitem(priority.SOURCE_PATHS, "debt", debt_path)
    new_queue = priority.build(debt=after_doc)
    assert new_queue["valid"] is True
    assert scheduler.document_sha256(new_queue) != \
        scheduler.document_sha256(queue)

    advanced = scheduler.packet(
        new_queue, policy, first, progress, queue, before, after)
    assert advanced["rotation"]["required"] is False
    assert advanced["cooldown"]["active"] is False
    assert advanced["attempt_history"][0]["debt_reduced"] is True


def test_historical_queue_rebuild_uses_bound_ownership_snapshot(
        queue, policy, tmp_path, monkeypatch):
    first = scheduler.packet(queue, policy)
    progress, before, after = attempt(first)
    ownership = load(priority.OWNERSHIP_PATH)
    target = first["selected_batch"]["rows"][0]
    ownership["rows"][target].setdefault("functions", []).append({
        "function_start": "0x8ffff100",
        "name": "historical_snapshot_mutation",
    })
    raw = scheduler.json_bytes(ownership)
    ownership_path = tmp_path / "phase3_ownership_graph.json"
    ownership_path.write_bytes(raw)
    monkeypatch.setitem(priority.SOURCE_PATHS, "ownership", ownership_path)
    new_queue = priority.build(ownership=ownership)
    assert new_queue["valid"] is True
    assert scheduler.document_sha256(new_queue) != \
        scheduler.document_sha256(queue)

    continued = scheduler.packet(
        new_queue, policy, first, progress, queue, before, after)
    assert len(continued["attempt_history"]) == 1
    assert continued["attempt_history"][0]["debt_reduced"] is False


def test_packet_rejects_fabricated_or_type_drifted_progress(queue, policy):
    first = scheduler.packet(queue, policy)
    legitimate, before, after = attempt(first)
    mutations = []
    wrong_rows = deepcopy(legitimate)
    wrong_rows["row_ids"] = ["E15_fmv"]
    mutations.append(wrong_rows)
    boolean_iteration = deepcopy(legitimate)
    boolean_iteration["iteration"] = True
    mutations.append(boolean_iteration)
    demotion = deepcopy(legitimate)
    demotion["demotions"] = [["X", "row", "met", "gap"]]
    mutations.append(demotion)
    extra = deepcopy(legitimate)
    extra["accepted"] = True
    mutations.append(extra)
    forged_reduction = deepcopy(legitimate)
    forged_reduction["row_transitions"] = [[
        "NOT_SELECTED", "open", "campaign_complete"]]
    mutations.append(forged_reduction)
    for changed in mutations:
        with pytest.raises(ValueError):
            scheduler.packet(queue, policy, first, changed, queue, before, after)
    tampered = deepcopy(first)
    tampered["schema"] = "abl-phase4-movie-ready-packet/1"
    with pytest.raises(ValueError):
        scheduler.packet(queue, policy, tampered, legitimate, queue, before, after)


def test_packet_rejects_history_reset_truncation_and_selected_batch_forgery(
        queue, policy):
    first = scheduler.packet(queue, policy)
    second = next_packet(queue, policy, first)
    progress, before, after = attempt(second)
    mutations = []
    cleared = deepcopy(second)
    cleared["attempt_history"] = []
    cleared["attempt_history_sha256"] = scheduler.document_sha256([])
    mutations.append(cleared)
    changed_selection = deepcopy(second)
    changed_selection["selected_batch"] = deepcopy(queue["candidate_batches"][0])
    mutations.append(changed_selection)
    changed_cover = deepcopy(second)
    changed_cover["selected_fixture_cover"]["complete"] = False
    mutations.append(changed_cover)
    broken_chain = deepcopy(second)
    broken_chain["attempt_history"][0]["previous_attempt_sha256"] = "f" * 64
    mutations.append(broken_chain)
    for changed in mutations:
        with pytest.raises(ValueError):
            scheduler.packet(
                queue, policy, changed, progress, queue, before, after)


def test_equal_debt_snapshots_cannot_claim_a_reduction(queue, policy):
    first = scheduler.packet(queue, policy)
    exact, before, after = attempt(first)
    assert before == after
    forged = deepcopy(exact)
    forged["dimension_transitions"] = [[
        first["selected_batch"]["rows"][0], "typed_state", "gap", "met"]]
    with pytest.raises(ValueError, match="does not exactly derive"):
        scheduler.packet(queue, policy, first, forged, queue, before, after)


def test_debt_snapshot_campaign_must_match_attempted_packet(queue, policy):
    first = scheduler.packet(queue, policy)
    before, after = debt_snapshots(first)
    changed = json.loads(before)
    changed["scheduler"]["selected_campaigns"][0]["campaign_id"] = "FORGED"
    changed_raw = scheduler.json_bytes(changed)
    progress = scheduler.derive_progress(changed_raw, after, 1)
    with pytest.raises(ValueError, match="does not match"):
        scheduler.packet(
            queue, policy, first, progress, queue, changed_raw, after)


def test_debt_snapshots_require_canonical_rows_and_consistent_counts(queue, policy):
    first = scheduler.packet(queue, policy)
    before, after = debt_snapshots(first)
    forged = json.loads(before)
    for index, row in enumerate(forged["rows"][:105]):
        row["row_id"] = f"FORGED_{index:03d}"
    forged_raw = scheduler.json_bytes(forged)
    with pytest.raises(ValueError, match="canonical 107-row universe"):
        scheduler.derive_progress(forged_raw, forged_raw, 1)

    stale = json.loads(after)
    target = next(item for item in stale["rows"]
                  if item["row_id"] == first["selected_batch"]["rows"][0])
    dimension = next(detail for detail in target["dimensions"].values()
                     if detail["state"] in {"gap", "partial"})
    dimension["state"] = "met"
    stale_raw = scheduler.json_bytes(stale)
    with pytest.raises(ValueError, match="counts disagree"):
        scheduler.derive_progress(before, stale_raw, 1)


@pytest.mark.parametrize("mutation", [
    lambda batch: batch.__setitem__("rank", True),
    lambda batch: batch["expected_value"].__setitem__("benefit_units", True),
    lambda batch: batch.__setitem__("score_total", True),
    lambda batch: batch.__setitem__("coupling", [{
        "row_id": "FORGED", "reasons": ["forged"]}]),
])
def test_packet_rejects_forged_batch_metadata_and_coupling(
        queue, policy, mutation):
    changed = deepcopy(queue)
    mutation(changed["candidate_batches"][0])
    changed["selected_batch"] = deepcopy(changed["candidate_batches"][0])
    with pytest.raises(ValueError, match="batches are not fully reproducible"):
        scheduler.packet(changed, policy)


def test_packet_rejects_coordinated_self_consistent_queue_provenance_forgery(
        queue, policy):
    changed = deepcopy(queue)
    target = next(item for item in changed["rows"]
                  if item["selection"]["selectable"])
    component = next(value for value in target["score"]["components"].values()
                     if value["points"] < value["maximum"])
    component["points"] += 1
    target["score"]["total"] += 1
    target["expected_value"] = scheduler.expected_value(target, policy)
    ranked = sorted(
        (item for item in changed["rows"]
         if item["selection"]["selectable"]),
        key=lambda item: (
            -Fraction(item["expected_value"]["benefit_units"],
                      item["expected_value"]["cost_units"]),
            -item["dependency_unlock_count"], item["derived_remaining"],
            item["row_id"],
        ))
    for rank, item in enumerate(ranked, 1):
        item["rank"] = rank
    changed["candidate_batches"] = scheduler._expected_batches(ranked, policy)
    changed["selected_batch"] = deepcopy(changed["candidate_batches"][0])
    with pytest.raises(ValueError, match="authoritative source regeneration"):
        scheduler.packet(changed, policy)


def test_packet_requires_exact_evidence_for_every_historical_attempt(
        queue, policy):
    first = scheduler.packet(queue, policy)
    second = next_packet(queue, policy, first)
    third = next_packet(queue, policy, second)
    assert len(third["attempt_history"]) == \
        len(third["attempt_evidence"]) == 2
    progress, before, after = attempt(third)

    forged = deepcopy(third)
    forged["attempt_evidence"] = []
    forged["attempt_evidence_sha256"] = scheduler.document_sha256([])
    with pytest.raises(ValueError, match="evidence must exactly cover"):
        scheduler.packet(queue, policy, forged, progress, queue, before, after)

    drifted = deepcopy(third)
    drifted["attempt_evidence"][0]["debt_after_zlib_base64"] += " "
    drifted["attempt_evidence_sha256"] = scheduler.document_sha256(
        drifted["attempt_evidence"])
    with pytest.raises(ValueError):
        scheduler.packet(queue, policy, drifted, progress, queue, before, after)


def test_attempt_history_capacity_fails_closed_without_truncation(queue, policy):
    current = scheduler.packet(queue, policy)
    for _ in range(policy["cooldown"]["max_retained_attempts"]):
        if len(current["attempt_history"]) == \
                policy["cooldown"]["max_retained_attempts"]:
            break
        current = next_packet(queue, policy, current, reduced=True)
    assert len(current["attempt_history"]) == 32
    progress, before, after = attempt(current, reduced=True)
    with pytest.raises(ValueError, match="capacity exhausted"):
        scheduler.packet(
            queue, policy, current, progress, queue, before, after)


def test_retained_queue_binds_scheduler_policy_helper_and_no_authority(queue):
    assert queue["scheduler_policy_schema"] == scheduler.SCHEMA
    assert queue["inputs"]["scheduler_policy_sha256"] == common.sha256(
        scheduler.POLICY_PATH)
    assert queue["inputs"]["scheduler_helper_sha256"] == common.sha256(
        ROOT / "tools/phase4_scheduler_policy.py")
    assert "complete" not in queue["selected_batch"]["expected_value"]
    assert queue["non_closure_meaning"].startswith(
        "Ranks currently preserved movie-backed work")
