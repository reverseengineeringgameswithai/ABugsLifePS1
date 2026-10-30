"""Phase-3 guard: static reader/writer xrefs (gate bullet 2, WP8).

The value of this artifact is entirely in its honesty about what a static scan
CANNOT see. 20,369 of 26,557 loads/stores go through a runtime pointer — so an
entry with no static xref means "not statically resolvable", NEVER "nothing
touches it". These tests exist to keep that distinction from eroding."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
X = json.loads((ROOT / "analysis" / "phase3_xrefs.json").read_text())
E = X["entries"]


def test_scan_is_broad_and_pinned():
    s = X["scan_stats"]
    assert s["loads"] > 10000 and s["stores"] > 5000
    assert s["pointer_based"] > s["absolute"]      # most accesses ARE pointers
    assert X["fixture_sha256"], "no EXE pin (DoF #1)"


def test_cross_checks_against_independently_known_facts():
    """The scanner was not told any of these — they come from Phase 2."""
    # the damage applier writes true health (Phase 2 found the function at
    # 0x8004A880; the store itself is a few instructions in)
    hp = E["original.player_health_true"]
    assert any(w["function"] and "damage" in (w["function"] or "").lower()
               or 0x8004A880 <= int(w["pc"], 16) <= 0x8004A8A0
               for w in hp["writers"]), hp["writers"]
    # the kick timer is written inside player_vertical_update, at the kick branch
    kick = E["original.kick_timer"]
    assert any(0x80048F00 <= int(w["pc"], 16) <= 0x80048F60
               for w in kick["writers"]), kick["writers"]
    # the scene id is read very widely and written by the transition code
    scene = E["original.current_scene_id"]
    assert scene["reader_count"] >= 20
    assert scene["writer_count"] >= 2


def test_every_hand_declared_writer_is_verified_or_explained():
    """0 REAL contradictions: each declared writer is either confirmed by the
    scan, or explained (written via a pointer / lives in overlay space / is mod
    cave code). If a real contradiction ever appears, the registry is wrong."""
    assert X["declared_writer_contradictions"] == []
    # ...and the explanations are actually recorded, not just absent
    assert X["declared_writers_via_pointer_unverifiable"]
    assert X["declared_writers_in_overlay_space"]


def test_absence_of_xrefs_is_never_reported_as_absence_of_use():
    """The load-bearing honesty check. Every entry with no static xref must say
    WHY — indexed table access (consumers live in the dispatch map) or a runtime
    pointer — never an implied 'nothing touches it'."""
    for eid in X["entries_without_static_xrefs"]:
        why = E[eid].get("no_static_xref_because")
        assert why, eid
        assert ("INDEX" in why or "POINTER" in why), (eid, why)
        assert "NOT" in why          # explicitly disclaims the wrong reading
