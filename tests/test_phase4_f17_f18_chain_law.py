#!/usr/bin/env python3
"""Guards for the Bonus-2 / Bonus-3 chain law and the shared progress feedback.

These exist because the Bonus-1 investigation found four clears nobody had recorded
and one wrong causal model. These tests preserve the resolved sites without calling
the fixed-form scan a complete domain.

Two specific traps guarded:
  * Bonus 2's slots are five BYTES. An early revision of the runtime tracer watched
    them at stride 4 and silently captured three unrelated globals.
  * Bonus 3's "not blue" clear is at the contact handler's ENTRY, so it is about
    HOLDING blue, not about killing with it.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/phase4_f17_f18_streak_law.c"
CANON = ROOT / "ObsidianVault/Canon/Systems/SYS_bonus2_bonus3_chain_law.md"
F17 = ROOT / "analysis/phase4_F17_streak_live.json"
F18 = ROOT / "analysis/phase4_F18_streak_live.json"


def rows():
    d = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text(
        encoding="utf-8"))
    for v in d.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {x["id"]: x for x in v}
    raise AssertionError("no row list")


def flat(p):
    return " ".join(p.read_text().split())


@pytest.fixture(scope="module")
def law(tmp_path_factory):
    exe = tmp_path_factory.mktemp("f1718") / "law"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL)], check=True, cwd=ROOT)
    return subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)


def test_tool_builds_and_every_pin_holds(law):
    assert law.returncode == 0, law.stdout[-3000:]
    assert "0 failed" in law.stdout


def test_bonus3_resolved_direct_sites_are_pinned(law):
    assert "scanner resolves ONE direct read" in law.stdout
    assert "scanner resolves FIVE direct writes" in law.stdout
    assert "no fixed-form overlay candidate" in law.stdout


def test_bonus3_has_no_scene_gate(law):
    assert "Bonus 3 really has no scene gate" in law.stdout


def test_bonus3_blue_rule_is_about_holding_not_killing(law):
    assert "berry selector 0x800A6597 read at the handler's ENTRY" in law.stdout


def test_bonus3_undocumented_clear_is_named(law):
    assert "0x80057428" in law.stdout
    assert "no write to 0x8008223C in that routine" in law.stdout


def test_bonus2_slots_are_bytes(law):
    assert "EVERY store into the window is `sb`" in law.stdout


def test_bonus2_known_store_count_is_pinned_without_closure(law):
    assert "scanner reports 16 known stores" in law.stdout
    assert "does not close pointer or variable-index aliases" in law.stdout


def test_bonus_chain_canon_and_tool_do_not_restore_domain_closure():
    canon = CANON.read_text()
    source = TOOL.read_text()
    assert "**Domain closed**:" not in canon
    assert "No overlay touches it." not in canon
    assert "The domain is **16 stores**" not in canon
    assert "domain adds up with nothing left over" not in source
    assert "every access in the EXE" not in source
    assert "16 known stores" in canon


def test_bonus2_duplicate_restarts_rather_than_wipes(law):
    assert "a duplicate does NOT empty the chain, it restarts it at ONE" in law.stdout


def test_bonus2_wipe_is_attributed_to_the_grounded_guard(law):
    assert "GROUNDED and no plant in contact -> WIPE" in law.stdout
    assert "the 'consecutive' rule" in law.stdout


# --------------------------------------------------------------------- live --

def test_f17_capture_used_byte_wide_slots():
    """The corrected capture must show the five consecutive byte addresses, each with
    plausible writers -- not stride-4 addresses picking up unrelated globals."""
    d = json.loads(F17.read_text())
    got = sorted(d["b2_slot_timeline"])
    assert got == ["0x%08X" % (0x80082248 + k) for k in range(5)]
    for a, seq in d["b2_slot_timeline"].items():
        pcs = {s["pc"] for s in seq}
        assert pcs, a
        assert all(p.startswith("0x8005b") or p.startswith("0x8005c") for p in pcs), (a, pcs)


def test_f18_capture_shows_the_blue_rule_firing_constantly():
    d = json.loads(F18.read_text())
    assert d["b3_streak_writers"].get("0x80058b34", 0) > 100


def test_f18_capture_shows_the_undocumented_clear_firing():
    d = json.loads(F18.read_text())
    assert "0x80057428" in d["b3_streak_writers"]


# --------------------------------------------------------------- canon + rows --

def test_canon_states_the_progress_feedback_gate():
    t = flat(CANON)
    assert "slti v0,v0,115" in t
    assert "the first accepted step emits `114`" in t


def test_bonus2_reaches_114_118_by_seed_plus_count():
    """The 113 is a SEED, not the emitted value: the block right after the store
    walks the five slots and adds one per occupied slot. Missing that loop produced a
    confident wrong answer that the operator refuted from play."""
    exe = (ROOT / "REBUILD/files/SCUS_942.88").read_bytes()

    def word(va):
        o = 0x800 + va - 0x80010000
        return int.from_bytes(exe[o:o + 4], "little")

    for pc in (0x8005C574, 0x8005C588, 0x8005C65C):
        assert word(pc) == 0x24020071, hex(pc)      # addiu v0,zero,113  (the seed)
    assert word(0x8005C674) == 0x80222248           # lb  slot[a0]
    assert word(0x8005C67C) == 0x10430005           # beq -1 -> skip empty
    assert word(0x8005C68C) == 0x24420001           # addiu v0,v0,1
    assert word(0x8005C690) == 0xAF8206AC           # sw back to 0x80082444
    for pc in (0x8004B398, 0x800591B0):
        assert word(pc) == 0x24420072, hex(pc)      # addiu v0,v0,114
    assert word(0x80055828) == 0x28420073           # slti v0,v0,115


def test_canon_keeps_the_correction_history():
    """Two wrong claims were banked here. The page must say so, or the next reader
    re-derives the same errors."""
    t = flat(CANON)
    assert "Correction history, kept deliberately" in t
    assert "it is a *seed*" in t


def test_landing_breaks_the_bonus2_chain():
    """The wipe's FIRST guard is grounded-with-no-plant. An earlier revision named
    the block after its last guard and concluded landing was harmless."""
    exe = (ROOT / "REBUILD/files/SCUS_942.88").read_bytes()

    def word(va):
        o = 0x800 + va - 0x80010000
        return int.from_bytes(exe[o:o + 4], "little")

    assert word(0x8005C01C) == 0x84426582           # lh grounded 0x800A6582
    assert word(0x8005C02C) == 0x1282000F           # beq s4,-1 -> wipe
    assert "landing on the ground without a mushroom" in flat(CANON)


def test_bonus2_completion_is_the_progress_word_reaching_118():
    exe = (ROOT / "REBUILD/files/SCUS_942.88").read_bytes()

    def word(va):
        o = 0x800 + va - 0x80010000
        return int.from_bytes(exe[o:o + 4], "little")

    assert word(0x8005C6A0) == 0x24020076           # v0 = 118
    assert word(0x8005C6AC) == 0x1462000E           # bne -> not complete


def test_reset_capture_matches_the_operator_report():
    """Bounce 1 -> 114 and no burst; bounces 2 and 3 -> 115/116 with bursts, at the
    frames the operator reported."""
    d = json.loads((ROOT / "analysis/phase4_F17_reset_test.json").read_text())
    bursts = sorted(b["mf"] for b in d["bursts"])
    assert bursts and bursts[0] == 131
    assert 181 in bursts
    firsts = [e for e in d["progress_timeline"] if e["mf"] == 81]
    assert firsts and max(e["v"] for e in firsts) == 114
    assert not any(e["would_burst"] for e in firsts)


def test_canon_scopes_the_completeness_claim():
    """Every player-provokable reset in both chains has now been watched destroying a
    live chain. That is a strong claim, so it must stay SCOPED: the two housekeeping
    wipes are not player actions and were never observed that way. This guard exists
    because the previous two versions of it fired when their premise went stale --
    which is what a good staleness guard does."""
    t = flat(CANON)
    assert "except the two housekeeping wipes" in t
    assert "0x80057428" in t and "0x8005BC94" in t
    assert "not player actions" in t


@pytest.mark.parametrize("rid", ["F17_bonus2_mushrooms", "F18_bonus3_grasshoppers"])
def test_rows_carry_the_corrected_feedback_finding(rid):
    b = " ".join(rows()[rid]["bindings"])
    assert "0x80082444" in b
    assert "115" in b
    assert "drives the on-screen burst in ALL THREE" in b


def test_f18_row_names_the_previously_unrecorded_clear():
    b = " ".join(rows()["F18_bonus3_grasshoppers"]["bindings"])
    assert "0x80057428" in b
    assert "NOT previously recorded" in b


def test_f17_row_warns_the_slots_are_bytes():
    b = " ".join(rows()["F17_bonus2_mushrooms"]["bindings"])
    assert "FIVE BYTES" in b
    assert "stride 4" in b


# ------------------------------------------- the duplicate-restart, measured --

DUP = ROOT / "analysis/phase4_F17_duplicate_test.json"


def test_duplicate_restart_was_finally_observed():
    """The last Bonus-2 path that had only ever been read, never watched."""
    d = json.loads(DUP.read_text())
    assert d["b2_duplicate_restart_observed"] is True


def test_duplicate_restart_keeps_the_touched_identity_in_slot0():
    """It restarts at ONE, not zero: slot 0 holds the mushroom just bounced and the
    rest go to -1. A wipe-to-empty would put the NEXT mushroom in slot 0 instead."""
    d = json.loads(DUP.read_text())
    ev = d["b2_appends_and_restarts"]
    appends = [e for e in ev if e["what"] == "APPEND"]
    assert [e["v"] for e in appends[:3]] == [6, 5, 4]
    first = min(e["mf"] for e in ev if e["what"] == "DUPLICATE-RESTART")
    restart = [e for e in ev if e["what"] == "DUPLICATE-RESTART" and e["mf"] == first]
    by_slot = {e["slot"]: e["v"] for e in restart}
    assert by_slot[0] == 4, by_slot
    assert all(by_slot[k] == 255 for k in (1, 2, 3, 4)), by_slot


def test_duplicate_restart_drops_the_progress_back_to_114():
    """And therefore shows no burst -- the visible tell the operator can check."""
    d = json.loads(DUP.read_text())
    first = min(e["mf"] for e in d["b2_appends_and_restarts"]
                if e["what"] == "DUPLICATE-RESTART")
    at = [e for e in d["progress_timeline"] if e["mf"] == first]
    assert at, first
    assert max(e["v"] for e in at) == 114
    assert not any(e["would_burst"] for e in at)


# ------------------------------------ the Bonus-3 breakage, finally destructive --

B3RESET = ROOT / "analysis/phase4_F18_reset_test.json"


def test_both_bonus3_clears_destroyed_a_live_chain():
    """The whole point of this recording. A clear firing while the streak is already
    zero only proves the path executes; destroying a live chain proves it matters."""
    d = json.loads(B3RESET.read_text())
    pcs = set(d["b3_destructive_reset_pcs"])
    assert pcs == {"0x80059a0c", "0x80058b34"}, pcs
    assert all(r["lost"] == 3 for r in d["b3_destructive_resets"])


def test_acquiring_a_different_berry_is_enough_to_break_it():
    """Not throwing it -- acquiring it. That is 'be holding blue' rather than 'kill
    with blue', shown rather than argued."""
    d = json.loads(B3RESET.read_text())
    sel = [r for r in d["b3_destructive_resets"] if r["pc"] == "0x80058b34"]
    assert sel and abs(sel[0]["mf"] - 3700) < 60, sel


def test_berry_at_a_wall_triggers_case_13():
    d = json.loads(B3RESET.read_text())
    c13 = [r for r in d["b3_destructive_resets"] if r["pc"] == "0x80059a0c"]
    assert c13 and abs(c13[0]["mf"] - 820) < 60, c13


def test_canon_no_longer_claims_bonus3_resets_are_unwatched():
    t = flat(CANON)
    assert "Both Bonus-3 clears confirmed destroying a live chain" in t
    assert "except the two housekeeping wipes" in t


def test_progress_word_writer_count_is_six_not_five():
    """A closure audit found the banked count omitted Bonus 2's per-slot increment
    loop -- the same block whose omission caused the retracted 'never bursts' claim.
    The count and the mechanism must agree."""
    t = flat(CANON)
    assert "has **six** writers" in t
    assert "0x8005C690" in t
    assert "An earlier revision said **five**" in t
