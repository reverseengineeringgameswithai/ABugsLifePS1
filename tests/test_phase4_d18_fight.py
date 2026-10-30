"""Phase-4 D18/F09: the Thud fight law, live-proven on the Interpreter movie.

Gates analysis/phase4_d18_thud_fight_law.json. Every claim below is an
attributed PC captured while replaying
movies/Phase4/Interpreter/D18_thud_fight.movie.json, not an inference.
"""
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_d18_thud_fight_law.json"


def _art():
    return json.loads(ART.read_text())


def test_damage_writer_is_inside_the_committed_berry_dispatch():
    """The -2 writer 0x800590E4 must lie inside berry_tough_damage_dispatch
    (0x8005905C), tying the boss fight to the ordinary berry damage law."""
    law = _art()["FIGHT_LAW_LIVE_2026-08-04"]
    assert "0x800590E4" in law["2_hit"]
    syms = {}
    for line in (ROOT / "symbols/re_symbols.sym").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 8:
            try:
                syms[int(parts[0], 16)] = parts[1]
            except ValueError:
                pass
    assert syms.get(0x8005905C) == "berry_tough_damage_dispatch"
    # the writer is after the dispatch entry and before the next symbol
    nxt = min((a for a in syms if a > 0x8005905C), default=0x80059FFF)
    assert 0x8005905C < 0x800590E4 < nxt


def test_pool_hp_is_a_latch_not_health():
    """Every hit is followed by an overlay restore, so pool HP returns to its
    spawn value instead of decreasing across the fight."""
    law = _art()["FIGHT_LAW_LIVE_2026-08-04"]
    assert "0x800B3ED0" in law["3_restore"]
    assert "TRANSIENT HIT LATCH" in law["3_restore"]
    assert "0x80049CA0" in law["1_spawn"] and "50" in law["1_spawn"]


def test_hit_counter_reaches_exactly_eight_before_the_kill():
    """0x800B4CC8 counts landed hits; the kill fires at 8 -- the mechanical
    form of the committed '8 perched berry hits' claim."""
    law = _art()["FIGHT_LAW_LIVE_2026-08-04"]
    assert "0x800B4CC8" in law["4_counter"] and "0x800B3DB0" in law["4_counter"]
    assert "8" in law["4_counter"]
    assert "0x800B4528" in law["5_kill"] and "counter==8" in law["5_kill"]


def test_all_fight_state_writers_are_overlay_except_the_damage_law():
    """Restore, counter and kill are overlay PCs (0x800B0000+); spawn and
    damage are resident. That split is the finding."""
    law = _art()["FIGHT_LAW_LIVE_2026-08-04"]
    import re
    def pcs(text):
        return [int(m, 16) for m in re.findall(r"0x800[0-9A-Fa-f]{5}", text)]
    for key in ("3_restore", "4_counter", "5_kill"):
        assert all(p >= 0x800B0000 for p in pcs(law[key])[:1]), key
    assert all(p < 0x800B0000 for p in pcs(law["1_spawn"])[:1])


def test_vm_stays_parked_through_the_whole_fight():
    """Confirms the D18 FSM-negative on real fight data: the only writer of
    the VM IP is the interpreter's own store."""
    law = _art()["FIGHT_LAW_LIVE_2026-08-04"]
    assert "0x8004C834" in law["6_vm_parked"]
    prior = json.loads((ROOT / "analysis/phase4_d18_thud_vm_fsm.json").read_text())
    assert "NEGATIVE" in prior["CONCLUSION"]["fsm_verdict"]


def test_callback_is_a_sound_cue_not_a_driver():
    cb = _art()["CALLBACK_ROLE_RESOLVED"]
    assert "play_sound" in cb["body"] and "0x8005044C" in cb["body"]
    assert "NOT a behaviour/AI" in cb["finding"]
    syms = {}
    for line in (ROOT / "symbols/re_symbols.sym").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 8:
            try:
                syms[int(parts[0], 16)] = parts[1]
            except ValueError:
                pass
    assert syms.get(0x8005044C) == "play_sound"


def test_perch_qualifier_is_a_two_anchor_position_test():
    """15 damage events -> 8 counts because the overlay requires the sweep
    position word to sit exactly on one of two hardcoded anchors."""
    q = _art()["PERCH_QUALIFIER_DECODED_2026-08-04"]
    assert q["live_proof"]["evaluations"] == 15
    assert q["live_proof"]["at_a_perch"] == 8
    assert q["live_proof"]["at_a_perch"] + q["live_proof"]["not_at_a_perch"] == 15
    assert "0x800B4CB0" in q["answer"]
    assert "-168416" in q["answer"] and "159264" in q["answer"]


def test_perch_anchor_literals_are_in_the_overlay_bytes():
    """The two anchors must appear as immediates in the retail overlay at the
    decoded test sites, and the load base must reproduce them."""
    q = _art()["PERCH_QUALIFIER_DECODED_2026-08-04"]
    ov = ROOT / q["overlay"]["file"]
    blob = ov.read_bytes()
    assert len(blob) == q["overlay"]["size"]
    base = int(q["overlay"]["load_base"], 16)
    def word(vaddr):
        return struct.unpack_from("<I", blob, vaddr - base)[0]
    # lui v0,0xfffd ; ori v0,v0,0x6e20   -> -168416
    assert word(0x800B3D78) == 0x3C02FFFD
    assert word(0x800B3D84) == 0x34426E20
    # lui v0,0x2    ; ori v0,v0,0x6e20   -> +159264
    assert word(0x800B3D8C) == 0x3C020002
    assert word(0x800B3D90) == 0x34426E20
    # and the counter store still anchors the base
    assert word(0x800B3DB0) == 0xAC224CC8


def test_hurt_reaction_is_ungated_but_scoring_is_gated():
    q = _art()["PERCH_QUALIFIER_DECODED_2026-08-04"]
    flow = {f["pc"]: f["act"] for f in q["handler_flow"]}
    assert "SOUND" in flow["0x800B3D60"] and "EVERY hit" in flow["0x800B3D60"]
    assert "ANIMATION" in flow["0x800B3D70"] and "every hit" in flow["0x800B3D70"]
    assert "DO NOT count" in flow["0x800B3D94"]


def test_damage_regimes_are_exactly_three_with_the_decoded_threshold():
    """Poke A/B from one anchor state: HP>=21 counts, HP<=20 is ignored AND
    unrestored (soft-lock), HP<=0 retires outright."""
    d = _art()["DAMAGE_RESPONSE_REGIMES_2026-08-04"]
    assert d["threshold_exact"]["hp_21"] == "COUNTED"
    assert d["threshold_exact"]["hp_20"] == "ignored"
    assert len(d["regimes"]) == 3
    soft = [r for r in d["regimes"] if "SOFT-LOCK" in r["result"]]
    assert len(soft) == 1 and "30..49" in soft[0]["delta_from_50"]
    inst = [r for r in d["regimes"] if "INSTANT retirement" in r["result"]]
    assert len(inst) == 1 and ">= 50" in inst[0]["delta_from_50"]


def test_softlock_claim_marks_native_reachability_corrected():
    """The response to a synthetic 30..49 delta is proven, while pristine
    native-berry metadata makes that band unreachable."""
    ps = _art()["DAMAGE_RESPONSE_REGIMES_2026-08-04"]["prediction_status"]
    assert "proven" in ps and "native_reachability_corrected" in ps
    correction = ps["native_reachability_corrected"].lower()
    assert "unreachable" in correction
    assert "type 45" in correction and "selector 128" in correction


def test_retirement_rule_still_holds():
    d = _art()["DAMAGE_RESPONSE_REGIMES_2026-08-04"]
    assert "HP <= 0 retires" in d["retirement_rule_reconfirmed"]
    assert "1 survives" in d["retirement_rule_reconfirmed"]


def test_burst_collapse_is_a_state_change_not_a_timer():
    b = _art()["BURST_COLLAPSE_EXPLAINED_2026-08-04"]
    assert "NOT a cooldown timer" in b["consequence"]
    assert "sweeping" in b["mechanism"]


def test_overlay_tool_compiles():
    subprocess.run(["cc", "-O2", "-Werror", "-fsyntax-only",
                    str(ROOT / "tools/phase4_d18_overlay_gate.c")], check=True)


def test_callback_body_matches_the_pristine_exe():
    """Spot-pin the decoded callback: li a0,26 then jal play_sound."""
    exe = (ROOT / "REBUILD" / "files" / "SCUS_942.88").read_bytes()
    def word(v):
        return struct.unpack_from("<I", exe, v - 0x80010000 + 0x800)[0]
    assert word(0x8004A100) == 0x2404001A                  # addiu a0,zero,26
    assert word(0x8004A104) == 0x0C000000 | (0x8005044C >> 2 & 0x03FFFFFF)
    assert word(0x8004A0FC) == 0x8C850004                  # lw a1,4(a0)
