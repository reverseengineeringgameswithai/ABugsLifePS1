"""Guards for D17's re-derived defeat transition.

See ObsidianVault/Experiments/EXP_2026-08-04_phase4_d17_bird_defeat.md.

The row previously described defeat as an IP jump to "park_arrive_stop" and the HP as
"frozen in the 18-22 range". The jump is real; the label was fiction and the freeze was a
two-phase fight. These guard the corrected account AND the fact that the old one was wrong.
"""

import json
import struct
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis" / "phase4_d17_defeat.json"
TOOL = ROOT / "tools" / "phase4_d17_defeat_trace.py"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"
CANON = ROOT / "ObsidianVault" / "Canon" / "Systems" / "SYS_bird_boss.md"

HALT_LO, HALT_HI = 0x800776AC, 0x800776B4
SHARED_TAIL = 0x8004C818


def art():
    return json.loads(ART.read_text())


def rows():
    doc = yaml.safe_load(REGISTRY.read_text())
    for v in doc.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {r["id"]: r for r in v}
    raise AssertionError("no row list")


def u16(va):
    return struct.unpack_from("<H", EXE.read_bytes(), 0x800 + (va - 0x80010000))[0]


def u32(va):
    return struct.unpack_from("<I", EXE.read_bytes(), 0x800 + (va - 0x80010000))[0]


def test_the_defeat_program_really_is_a_null_loop():
    """Load-bearing: 0x800776AC dispatches to the interpreter's loop tail (no body) and
    0x800776AE jumps back to it. If either changes, the 'halt' reading is void."""
    v = u16(HALT_LO)
    stream = v - 0x10000 if v & 0x8000 else v
    assert u32(0x8001B2F4 + (stream + 1) * 4) == SHARED_TAIL
    nxt = u16(HALT_LO + 2)
    assert (nxt - 0x10000 if nxt & 0x8000 else nxt) == -1, "0x800776AE is not jump_back"


def test_trace_ring_did_not_truncate():
    assert art()["ring_truncated"] is False


def test_defeat_parks_the_vm_in_the_halt_program():
    f = art()["findings"]["1_defeat_installs_a_halt_program"]
    assert f["first_halt_frame"] is not None
    assert f["installed_by_pc"] == "0x800b4158"
    assert any(int(v, 16) in (HALT_LO, HALT_LO + 2) for v in f["ip_values_seen"])
    assert "HALTED" in f["verdict"]


def test_damage_pc_is_closed_and_is_the_same_one_thumper_uses():
    """The row recorded -4/hit as behavioural and 'not traced'."""
    g = art()["findings"]["2_damage_instruction"]
    assert g["distinct_damage_pcs"] == ["0x800590e4"]
    assert set(g["deltas"]) == {-3, -4}, g["deltas"]


def test_the_hp_freeze_was_a_per_hit_restore():
    """Nine -3 hits restored to 50; -4 hits stick and accumulate to the threshold."""
    g = art()["findings"]["2_damage_instruction"]
    dec = g["hp_decrements"]
    restored = [d for d in dec if d["from"] == 50 and d["delta"] == -3]
    assert len(restored) >= 5, "expected a run of restored -3 hits"
    lethal = [d for d in dec if d["delta"] == -4]
    assert lethal and lethal[-1]["to"] <= 20, lethal[-1]


def test_post_halt_motion_is_overlay_driven():
    f = art()["findings"]["3_what_moves_the_bird_after_the_halt"]
    ys = f["position_writers_after_halt"].get("position Y") or []
    assert any(pc.startswith("0x800b") for pc, _ in ys), ys


def test_registry_supersedes_the_park_arrive_stop_reading():
    b = " ".join(rows()["D17_bird"]["bindings"])
    assert "DEFEAT RE-DERIVED" in b
    assert "supersedes the park_arrive_stop" in b
    assert "0x800590e4" in b.lower()
    assert "SHARED TEMPLATE" in b


def test_the_phase_framing_was_retracted_not_left_standing():
    """This was first written up as a 'two-phase fight' with an open transition
    condition. It is neither: the restore is a per-hit gate on the damage value. The
    superseded framing and the mistyped counter address must be gone from every surface,
    not just corrected in the newest section."""
    b = " ".join(rows()["D17_bird"]["bindings"])
    assert "PER-HIT RESTORE" in b
    assert "NOT a phase change" in b
    assert "0x800B47BC" not in b, "the mistyped counter address survived"
    assert "0x800B441C" in b
    exp = (ROOT / "ObsidianVault" / "Experiments" /
           "EXP_2026-08-04_phase4_d17_bird_defeat.md").read_text()
    assert "0x800B47BC" not in exp
    assert "This is not two phases" in exp


def test_canon_and_surfaces_exist():
    assert ART.exists() and TOOL.exists() and CANON.exists()
    t = CANON.read_text()
    assert "halted" in t.lower() and "0x800776AC" in t


# ---------------------------------------------------- the damage law (D17) --

LAW = ROOT / "analysis" / "phase4_d17_damage_law.json"


def law():
    return json.loads(LAW.read_text())


def test_the_berry_index_hypothesis_is_recorded_as_REFUTED():
    """I hypothesised 0x800A6597 drove the -3/-4 split and traced it. It holds 3 for
    BOTH. The tool must report NOT SEPARABLE, never a manufactured confirmation."""
    f = law()["findings"]
    assert f["damage_deltas_to_berry_indices"]["-3"] == [3]
    assert f["damage_deltas_to_berry_indices"]["-4"] == [3]
    assert "NOT SEPARABLE" in f["verdict"]


def test_the_knockup_counter_caps_at_five_while_restores_continue():
    f = law()["findings"]
    assert max(f["knockup_counter_values"]) == 5
    assert f["restore_count"] > 5, "restores must outlive the counter cap"


def test_the_damage_table_is_a_berry_type_branch_chain():
    """Damage is selected by a berry-TYPE value in v1, not by the side-table index."""
    b = " ".join(rows()["D17_bird"]["bindings"])
    assert "type 127 -> -4" in b and "type 128 -> -3" in b
    assert "SIDE-TABLE index" in b
    assert "REFUTED" in b


def test_the_damage_table_and_the_immunity_gate_are_recorded():
    """The HP>=100 gate explains the row's own unexplained Cliffside observation."""
    b = " ".join(rows()["D17_bird"]["bindings"])
    assert "projectile+0x2C" in b
    assert "0x800B0D18" in b
    assert "slti v0,v0,100" in b
    assert "101 >= 100" in b


def test_berry_types_are_closed_live():
    """127 -> -4, 128 -> -3, captured at a breakpoint on the PHYSICAL address."""
    art = json.loads((ROOT / "analysis" / "phase4_d17_berry_types.json").read_text())
    assert art["hit_count"] == 19
    bird = [h for h in art["hits"] if h["target_actor"] == "0x800A02A8"]
    t128 = [h for h in bird if h["berry_type"] == 128]
    t127 = [h for h in bird if h["berry_type"] == 127]
    assert len(t128) == 9 and all(h["new_hp"] == 47 for h in t128)
    assert len(t127) == 8 and t127[-1]["new_hp"] == 18
    # the switch is what ends the restores
    assert max(h["f"] for h in t128) < min(h["f"] for h in t127)


def test_the_breakpoint_retraction_is_recorded():
    """I claimed breakpoints never fire and that CLAUDE.md was wrong. Both false: the
    address must be PHYSICAL. The retraction must stay visible, not be quietly dropped."""
    b = " ".join(rows()["D17_bird"]["bindings"])
    assert "RETRACTION" in b
    assert "must be PHYSICAL" in b
    assert "That was MY error" in b
    assert "EXECUTE BREAKPOINTS NEVER FIRE" in b, "keep the wrong claim visible as history"
    assert "hit_count > 0 before trusting" in b
    exp = (ROOT / "ObsidianVault" / "Experiments" /
           "EXP_2026-08-04_phase4_d17_bird_defeat.md").read_text()
    assert "RETRACTED" in exp and "0x0004c834" in exp
