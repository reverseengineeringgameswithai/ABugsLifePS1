"""The locally-computed-base campaign must keep the bankable shape.

The 2026-08-06 planning correction: a boundary is bankable only over an
exactly defined eligible universe with every site processed and a per-site
failure reason retained. These tests hold the artifact to that shape -- and
deliberately do NOT pin `decided_by_proof == 0`, because a future unlock
(a falsifier firing) must not read as a test failure.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_typed_state as ts  # noqa: E402
import phase4_f01_local_base_recovery as lbr  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_f01_local_base_recovery.json"
BASELINE = ROOT / "analysis/phase4_f01_local_base_recovery_1bba2487_outcomes.json"

pytestmark = pytest.mark.skipif(not ARTIFACT.is_file(),
                                reason="campaign artifact absent")


@pytest.fixture(scope="module")
def campaign() -> dict:
    return json.loads(ARTIFACT.read_bytes())


@pytest.fixture(scope="module")
def index() -> dict:
    return json.loads(ts.INDEX_PATH.read_bytes())


@pytest.fixture(scope="module")
def verifier(index) -> ts.Verifier:
    return ts.Verifier(index)


def test_retained_artifact_is_fresh():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_f01_local_base_recovery.py"),
         "--output", str(ARTIFACT), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_pinned_outcome_baseline_rebuilds_from_the_exact_git_object():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_f01_local_base_recovery.py"),
         "--baseline-output", str(BASELINE), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    baseline = json.loads(BASELINE.read_bytes())
    assert baseline["source_commit"] == \
        "1bba2487b1b6f3e9d7669947de494ba649b99b70"
    assert baseline["source_artifact_sha256"] == \
        "0040c6c41a5189fdff6f04ecee2a6c61a5c7da10075a734cc28fb82ee9dfde47"
    assert baseline["site_count"] == len(baseline["outcomes"]) == 79


def test_every_eligible_site_is_processed_with_an_outcome(campaign):
    """No sampling, no silent drops, no site without a named result."""
    assert campaign["every_eligible_site_processed"] is True
    rows = campaign["sites"]
    assert len(rows) == campaign["eligible_universe"]["site_rows"]
    assert sum(campaign["tally"].values()) == len(rows)
    for row in rows:
        assert row["outcome"].startswith(("decided", "blocked")), row["pc"]
        if row["outcome"].startswith("blocked"):
            assert str(row.get("reason") or "").strip(), (
                f"{row['image']}:{row['pc']} has no failure reason")
        else:
            proof = row["proof"]
            interval = proof.get("store_interval") or proof.get(
                "valid_ram_store_interval")
            assert interval
            lo, hi = ts._int(interval[0]), ts._int(interval[1])
            for w_lo, w_hi in ((0x800823A0, 0x800823A2), (0x80082470, 0x80082472)):
                assert hi <= w_lo or lo >= w_hi, "a decided interval overlaps a window"


def test_universe_is_derived_from_the_fixture_and_ledger_not_declared(campaign):
    """Every fixture store the typed-state artifact left still_unresolved is
    here; nothing else is."""
    resolve = json.loads((ROOT / "analysis/phase4_f01_frontier_resolve.json").read_bytes())
    typed = json.loads((ROOT / "analysis/phase4_f01_typed_state.json").read_bytes())
    assert campaign["inputs"]["fixture_sha256"] == ts._sha(
        (ROOT / "analysis/phase4_f01_frontier_resolve.json").read_bytes())
    assert campaign["inputs"]["typed_state_sha256"] == ts._sha(
        (ROOT / "analysis/phase4_f01_typed_state.json").read_bytes())
    # ⚠️ IMAGE-QUALIFIED join, not pc-only. Twenty overlays share the same load
    # range, so a pc-set intersection counts a fixture site in one overlay
    # against a still-unresolved row in a DIFFERENT overlay -- the exact
    # aliasing bug this repository keeps rediscovering. The first draft of
    # this test did precisely that and reported 36 phantom "missing" sites,
    # every one a cross-image alias.
    still_rows = set()
    for r in typed["still_unresolved"]:
        if "pc" not in r:
            continue
        image = str(r.get("function", "")).split(":", 1)[0]
        still_rows.add((image, ts._int(r["pc"])))
    expected = set()
    for s in resolve["unresolved_sites"]:
        if not s.get("store"):
            continue
        pc = ts._int(s["pc"])
        for image, still_pc in still_rows:
            if still_pc == pc and (image.startswith(s["image"])
                                   or s["image"].startswith(image)):
                expected.add((image, pc))
    campaign_rows = {(r["image"], ts._int(r["pc"])) for r in campaign["sites"]}
    assert campaign_rows == expected, (
        f"missing: {sorted((i, hex(p)) for i, p in expected - campaign_rows)}; "
        f"extra: {sorted((i, hex(p)) for i, p in campaign_rows - expected)}")


def test_the_delay_slot_store_is_now_classified_not_invisible(campaign, verifier):
    """0x800B3EF4 is a store in a `j` delay slot. The old successor model never
    routed the reach walks through delay slots, so this site had NO observable
    definitions yet read as governed -- a vacuous, unsafe answer. The corrected
    walk must see its real definition: a global load from 0x8009FE84."""
    q = verifier.ask("LEVEL02_LEVEL:0x800B3B8C:0x800B4860:v1:0x800b3ef4")[0]
    observable = [d for d in q["definitions"] if d["observable"]]
    assert [d["class"] for d in observable] == ["global_load"]
    assert ts._int(observable[0]["address"]) == 0x8009FE84
    assert q["entry_reachable_uses"] == 0
    row = next(r for r in campaign["sites"]
               if r["image"] == "LEVEL02_LEVEL" and ts._int(r["pc"]) == 0x800B3EF4)
    assert row["outcome"] == "blocked_writer_universe_exhaustiveness"
    assert any(ts._int(c) == 0x8009FE84 for c in row["cells"])


def test_real_dispatch_and_branch_entries_replace_the_false_jalr_attribution(campaign):
    """The claimed jalr PCs are direct jals; real entry edges carry the values."""
    rows = [r for r in campaign["sites"]
            if r["function"] == "seed_plant_trampoline_handler"]
    assert rows, "the eligible universe must contain the trampoline sites"
    for row in rows:
        assert row["outcome"] == "blocked_index_interval_unproved_instruction"
        assert [(source["kind"], source["pc"])
                for source in row["established_entry_sources"]] == [
                    ("proved_jr", "0x8005C108")]
        assert row["entry_value_typing"][0]["definition_classes"] == ["opaque"]
        definition = row["entry_value_typing"][0]["definitions"][0]
        assert definition["table_address_failure"] == {
            "pc": "0x8005c108", "word": "0x00400008",
            "reason": "unresolved_indirect_jump_may_enter_query_extent"}
        assert row["prior_outcome"] == "blocked_index_sign_needs_convention"
        assert row["breaking_instructions"][0] == {
            "pc": "0x8005c108", "word": "0x00400008",
            "reason": "unresolved_indirect_jump_may_enter_query_extent"}
    berry = [r for r in campaign["sites"]
             if r["function"] == "berry_tough_damage_dispatch"]
    assert len(berry) == 2
    for row in berry:
        assert row["outcome"] == "blocked_writer_universe_exhaustiveness"
        assert [(source["kind"], source["pc"])
                for source in row["established_entry_sources"]] == [
                    ("branch", "0x80058EE8"), ("branch", "0x80058F08")]


def test_campaign_movement_and_writer_falsifier_are_exact(campaign):
    movement = campaign["movement_from_1bba2487"]
    assert movement["baseline_site_rows"] == movement["shared_site_rows"] == 79
    assert movement["current_site_rows"] == 102
    assert movement["baseline_only_ids"] == []
    expected_current_only = {
        f"SCUS_942_88:0x{pc:08X}:s1" for pc in (
            0x8004AEE4, 0x8004AEF8, 0x8004AF7C, 0x8004AF8C,
            0x8004B208, 0x8004B214, 0x8004B220, 0x8004B224,
            0x8004B234, 0x8004B238, 0x8004B254, 0x8004B260,
            0x8004B274, 0x8004B2D0, 0x8004B2D8, 0x8004B2E0,
            0x8004B464, 0x8004B570, 0x8004B5D8, 0x8004B638,
            0x8004B650, 0x8004B664, 0x8004B678)}
    assert set(movement["current_only_ids"]) == expected_current_only
    assert {row["id"] for row in movement["current_only_outcomes"]} == \
        expected_current_only
    assert {row["outcome"] for row in movement["current_only_outcomes"]} == {
        "blocked_index_interval_unproved_instruction"}
    assert movement["changed_outcome_count"] == 31
    assert {row["before"] for row in movement["changed_outcomes"]} == {
        "blocked_no_direct_caller", "blocked_index_sign_needs_convention",
        "blocked_return_domain_needs_index_convention",
        "blocked_no_recovery_method",
        "blocked_writer_universe_exhaustiveness"}
    assert sum(row["after"] == "blocked_index_interval_unproved_instruction"
               for row in movement["changed_outcomes"]) == 29
    assert sum(row["after"] == "blocked_writer_universe_exhaustiveness"
               for row in movement["changed_outcomes"]) == 2
    falsifier = campaign["writer_falsifier_remeasurement"]
    assert falsifier["known_writer_set_gained"] == ["0x80049c10", "0x80049c14"]
    assert falsifier["known_writer_set_lost"] == []
    assert falsifier["resolved_writers_not_previously_enumerated"] == []
    assert falsifier["corpus_undecided_stores"] == 5012
    assert falsifier["exhaustive"] is False


def test_all_prerequisite_index_walls_are_refined_with_exact_breakers(campaign):
    movement = campaign["movement_from_b6cb61d35f9d"]
    assert movement["baseline_site_rows"] == movement["current_site_rows"] == 102
    assert movement["shared_site_rows"] == 102
    assert movement["baseline_only_ids"] == movement["current_only_ids"] == []
    assert movement["changed_outcome_count"] == 52
    gained = set(movement["outcome_site_set_movement"][
        "blocked_index_interval_unproved_instruction"]["gained_ids"])
    lost_sign = set(movement["outcome_site_set_movement"][
        "blocked_index_sign_needs_convention"]["lost_ids"])
    lost_return = set(movement["outcome_site_set_movement"][
        "blocked_return_domain_needs_index_convention"]["lost_ids"])
    lost_writer = set(movement["outcome_site_set_movement"][
        "blocked_writer_universe_exhaustiveness"]["lost_ids"])
    lost_no_recovery = set(movement["outcome_site_set_movement"][
        "blocked_no_recovery_method"]["lost_ids"])
    assert gained == lost_sign | lost_return | lost_writer | lost_no_recovery
    assert len(lost_sign) == 20 and len(lost_return) == 6
    assert len(lost_writer) == 24 and len(lost_no_recovery) == 2
    rows = [row for row in campaign["sites"] if row["id"] in gained]
    assert len(rows) == 52
    assert campaign["decided_by_proof"] == 0
    for row in rows:
        assert row["outcome"] == "blocked_index_interval_unproved_instruction"
        expected_prior = (
            "blocked_index_sign_needs_convention" if row["id"] in lost_sign
            else "blocked_return_domain_needs_index_convention"
            if row["id"] in lost_return
            else "blocked_writer_universe_exhaustiveness"
            if row["id"] in lost_writer
            else "blocked_no_recovery_method")
        assert row["prior_outcome"] == expected_prior
        assert row["index_interval_attempts"]
        assert row["breaking_instructions"]
        for breaker in row["breaking_instructions"]:
            assert breaker["pc"] and breaker["word"] and breaker["reason"]

    ratchet = campaign["breaker_movement_from_05bc6b8a251b"]
    assert ratchet["baseline_site_rows"] == ratchet["current_site_rows"] == 102
    assert ratchet["baseline_only_ids"] == ratchet["current_only_ids"] == []
    assert ratchet["changed_breaker_count"] == 46
    assert len(ratchet["changed_breaker_ids"]) == 46
    assert {row["id"] for row in ratchet["changed_breakers"]} == set(
        ratchet["changed_breaker_ids"])
    assert sum(not row["before"] for row in ratchet["changed_breakers"]) == 26
    assert sum(bool(row["before"]) for row in ratchet["changed_breakers"]) == 20
    for row in ratchet["changed_breakers"]:
        assert row["after"] == [{
            "pc": row["after"][0]["pc"],
            "reason": "locally_defined_ra_indirect_target_not_modelled",
            "word": "0x03e00008",
        }]


def test_reopened_typed_pointer_sites_retain_both_independent_blockers(campaign):
    """A stricter table-base wall must not erase the shared writer gate."""
    rows = [row for row in campaign["sites"]
            if row["id"] in set(campaign["movement_from_1bba2487"][
                "current_only_ids"])]
    assert len(rows) == 23
    for row in rows:
        assert row["outcome"] == "blocked_index_interval_unproved_instruction"
        assert row["coexisting_writer_universe_cells"] == ["0x80090748"]
        assert row["coexisting_writer_universe_exhaustive"] is False
        assert set(row["base_def_classes"]) == {"global_load", "opaque"}
        assert row["breaking_instructions"] == [{
            "pc": "0x8004b6d4", "word": "0x03e00008",
            "reason": "locally_defined_ra_indirect_target_not_modelled"}]


def test_external_entry_guard_is_image_qualified(campaign, index):
    """Only sources that can share the target's load span may appear."""
    for row in campaign["sites"]:
        for entry in row.get("external_entries") or []:
            assert ts._images_can_coexist(
                index, entry["image"], row["image"]), (
                f"external entry {entry} cannot coexist with {row['image']}")


def test_external_entry_coexistence_uses_load_spans_and_fails_closed(index):
    """Independent overlay regions coexist; one swap span and unknowns do not
    get mislabelled as proved-exclusive."""
    assert not ts._images_can_coexist(
        index, "LEVEL01_LEVEL", "LEVEL02_LEVEL1")
    assert ts._images_can_coexist(index, "LEVEL01_LEVEL", "MEMORY")
    assert ts._images_can_coexist(index, "MEMORY", "LEVEL10_LEVEL")
    assert ts._images_can_coexist(index, "SCUS_942_88", "MEMORY")
    assert ts._images_can_coexist(index, "UNKNOWN_IMAGE", "LEVEL01_LEVEL")

    def image(image_id, base, size):
        return {"image_id": image_id, "file_va_base": base, "size": size,
                "identity_verified": True}

    overlapping = {"images": [
        image("A", "0x80010000", 0x100),
        image("B", "0x80010080", 0x100),
    ]}
    assert not ts._images_can_coexist(overlapping, "A", "B")
    for field, malformed in (
            ("file_va_base", True),
            ("file_va_base", 0x80010000 + 0.5),
            ("size", True),
            ("size", 0x100 + 0.5),
            ("size", "256")):
        candidate = json.loads(json.dumps(overlapping))
        candidate["images"][0][field] = malformed
        assert ts._images_can_coexist(candidate, "A", "B"), (
            f"malformed {field}={malformed!r} was treated as proved-exclusive")

    assert ts._images_can_coexist(
        {"images": [None, *overlapping["images"]]}, "A", "B")
    for malformed_row in (
            {}, {"image_id": 7}, {"image_id": ""}, {"image_id": "   "},
            image("A", "0x80030000", 0x100)):
        assert ts._images_can_coexist(
            {"images": [*overlapping["images"], malformed_row]}, "A", "B")
    for malformed_index in (
            True, 7, 1.5, [],
            {"images": True}, {"images": 7}, {"images": 1.5},
            {"images": "not-a-catalog"}, {"images": {"image_id": "A"}}):
        assert ts._images_can_coexist(malformed_index, "A", "B")


@pytest.mark.parametrize("malformed_domain", [
    [], None, True, 7, 1.5, "0x800b7da4", [True], ["not-an-address"],
    ["0x800b7da4", "0x800b7da4"],
])
def test_empty_or_malformed_indirect_target_domain_stays_unknown(
        index, malformed_domain):
    """A present map row closes nothing unless its exact domain is valid."""
    candidate = copy.deepcopy(index)
    candidate["indirect_jump_targets"]["site_targets"][
        "0x800b3fcc"] = malformed_domain
    closure = ts._indirect_transfer_closure(candidate)
    site = next(row for row in closure["sites"]
                if row["id"] ==
                "indirect_jump:LEVEL07_LEVEL1:0x800b3fcc")
    assert site["target_domain_complete"] is False
    assert site["targets"] == []
    entries = ts._external_interior_entries(
        candidate, "MEMORY", 0x800B7DA0, 0x800B878C, closure)
    blocker = next(row for row in entries
                   if row.get("source_site_id") == site["id"])
    assert blocker["kind"] == "unknown_indirect_jump_target_domain"
    assert blocker["target_domain_complete"] is False


def test_conflicting_complete_target_maps_degrade_to_unknown(index):
    """Two individually valid domains may not win by order or abort audit."""
    candidate = copy.deepcopy(index)
    pc = "0x8001CAC4"
    candidate["indirect_jump_targets"]["site_targets"][pc] = [
        "0x8001cacc", "0x8001cc4c", "0x8001cda0"]
    candidate["indirect_jump_targets_from_gate"]["site_targets"][pc] = [
        "0x8001cacc", "0x8001cc4c"]
    closure = ts._indirect_transfer_closure(candidate)
    site = next(row for row in closure["sites"]
                if row["id"] ==
                "indirect_jump:SCUS_942_88:0x8001cac4")
    assert site["target_domain_complete"] is False
    assert site["targets"] == []
    assert site["target_provenance"] == [
        "indirect_jump_targets", "indirect_jump_targets_from_gate"]
    assert closure["complete_indirect_jump_site_count"] == 86
    assert closure["unknown_indirect_jump_site_count"] == 21

    entries = ts._external_interior_entries(
        candidate, "MEMORY", 0x800B7DA0, 0x800B878C, closure)
    assert len(entries) == 161
    blocker = next(row for row in entries
                   if row.get("source_site_id") == site["id"])
    assert blocker["kind"] == "unknown_indirect_jump_target_domain"
    assert blocker["target_domain_complete"] is False


def test_conflicting_resident_maps_cannot_certify_same_pc_in_an_overlay(index):
    """Conflicting PC-only resident receipts remain unknown for the overlay."""
    candidate = copy.deepcopy(index)
    pc = "0x800b3fcc"
    candidate["indirect_jump_targets"]["site_targets"][pc] = [
        "0x800b7da4"]
    candidate["indirect_jump_targets_from_gate"]["site_targets"][pc] = [
        "0x800b7da8"]
    closure = ts._indirect_transfer_closure(candidate)
    site = next(row for row in closure["sites"]
                if row["id"] ==
                "indirect_jump:LEVEL07_LEVEL1:0x800b3fcc")
    assert site["target_domain_complete"] is False
    assert site["targets"] == []
    assert site["target_provenance"] == []
    entries = ts._external_interior_entries(
        candidate, "MEMORY", 0x800B7DA0, 0x800B878C, closure)
    assert len(entries) == 160
    blocker = next(row for row in entries
                   if row.get("source_site_id") == site["id"])
    assert blocker["kind"] == "unknown_indirect_jump_target_domain"


def test_unknown_indirect_transfer_universe_is_never_treated_as_empty(campaign):
    closure = campaign["external_indirect_transfer_closure"]
    assert closure["site_count"] == 247
    assert closure["indirect_jump_site_count"] == 107
    assert closure["complete_indirect_jump_site_count"] == 87
    assert closure["unknown_indirect_jump_site_count"] == 20
    assert closure["indirect_call_site_count"] == 140
    assert closure["unknown_indirect_call_site_count"] == 140
    assert len(closure["unknown_transfer_site_ids"]) == 160
    assert closure["target_domains_complete"] is False


def test_resident_calls_into_overlay_interiors_fail_closed(campaign):
    """The one surviving external-entry block is REAL: resident scene-verb
    dispatch jals fixed overlay VAs that are interior addresses in
    LEVEL04_LEVEL1's layout. The proof must fail closed on it."""
    row = next(r for r in campaign["sites"]
               if r["outcome"] == "blocked_external_interior_entry")
    assert row["image"] == "LEVEL04_LEVEL1"
    sources = {e["pc"] for e in row["external_entries"]}
    assert "0x800548AC" in sources or "0x8003F54C" in sources


def test_campaign_is_staged_never_banked(campaign):
    camp = campaign["campaign"]
    assert camp["banked"] is False
    assert camp["banking_authority"] == "a fresh detached verifier only"
    assert camp["proposed_disposition"] == \
        "bounded_exhausted_locally_computed_base_recovery"
    assert len(camp["reopening_falsifiers"]) >= 4
    for falsifier in camp["reopening_falsifiers"]:
        assert "blocked_" in falsifier or "caller" in falsifier
    authority = campaign["authority"]
    assert authority["banks_the_disposition"] is False
    assert authority["closes_item_2"] is False


def test_no_convention_is_relabelled_as_proof(campaign):
    """Sites the second opinion declined must not reappear as decided merely
    because this campaign re-derived the same convention-gated shape."""
    for row in campaign["sites"]:
        if row["outcome"].startswith("decided"):
            assert "convention" not in json.dumps(row["proof"]).lower()
        if "convention" in row["outcome"]:
            assert "convention" in row["reason"]
