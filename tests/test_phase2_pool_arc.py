"""Offline validation of the pool/arc oracle artifact: contact-pool layout,
berry-arc sentinel, per-anchor pool digests, capacity stress, action attempts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase2_pool_arc_oracle.json").read_text())


def test_pool_layout():
    p = DOC["pool_layout"]
    assert p["base"] == "0x800B0D18"   # Canon MEM_800B0D18 frame
    assert p["slots"] == 64 and p["stride"] == "0x38"


def test_arc_sentinel():
    a = DOC["arc_sentinel"]
    assert a["projectile_slot"] == 52
    assert a["deterministic_across_reloads"] is True
    assert len(a["trajectory"]) == 20
    assert len(a["flight_frame_hashes"]) == 3
    # ballistic: Y (down-positive) deltas increase by a constant gravity step
    assert a["gravity_constant_estimate"] == 128
    # a real arc moves: horizontal displacement across the sample must be large
    dx = a["trajectory"][-1][0] - a["trajectory"][0][0]
    assert abs(dx) > 10000


def test_pool_census_all_anchors_with_digests():
    census = DOC["pool_census"]
    assert len(census) == 19
    digests = set()
    for lbl, e in census.items():
        # the pool holds PROXIMITY-ACTIVE contacts: 0 at some anchors is valid
        assert 0 <= e["active_slots"] <= 64, lbl
        assert len(e["pool_sha256"]) == 64, lbl
        digests.add(e["pool_sha256"])
        for slot in e["slots"]:
            assert slot["active_type"] > 0, f"{lbl}/{slot['slot']}"
    assert len(digests) == len(census), "two anchors share a pool digest"
    assert any(e["active_slots"] >= 10 for e in census.values())
    # dual gate semantics (walker disasm): typed vs walker-enabled both recorded
    for lbl, e in census.items():
        assert e["walker_enabled_slots"] <= e["typed_slots"], lbl
    # NOTE: the earlier "64/64 saturation in normal play" claim was an artifact of
    # a misaligned base + coincidental signature (external review); retracted.


def test_allocator_cursor_semantics():
    cur = DOC["allocator_cursor"]
    assert cur["cursor_address"] == "0x8008234C"
    assert cur["wrap_modulus"] == 0x40
    # corrected semantics (src_re/contact_alloc_80059e44.c): round-robin
    # free-slot search, skip-occupied, NO full-array escape (hang risk);
    # wraps prove >64 allocations over time — churn, not overwrite-oldest
    assert "free-slot search" in cur["semantics"]
    assert "SPINS" in cur["semantics"]
    assert cur["valid_wraps_observed"] >= 1
    # invalid pre-game cursor values are excluded from wrap counting
    assert any(not s["valid"] for s in cur["series"][:6])
    assert all(s["cursor"] < 0x40 for s in cur["series"] if s["valid"])


def test_capacity_stress_stable():
    s = DOC["capacity_stress"]
    assert s["throw_attempts"] == 40
    assert s["stable"] is True
    assert s["max_in_flight_observed"] >= 1


def test_action_attempts_recorded_honestly():
    a = DOC["action_attempts"]
    assert len(a["training_seed_square"]) >= 6
    # nulls are recorded, not hidden: every attempt carries before/during blocks
    for att in a["training_seed_square"]:
        assert "state_block_changed" in att
    assert "note" in a["canyon_slide_attempt"]
