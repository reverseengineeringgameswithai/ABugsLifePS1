#!/usr/bin/env python3
"""Guards for F10 Clover Forest -- the five mechanical bits.

The row was completely untouched before this pass. Two things here are the kind that
decay first, so both are pinned against the image rather than the prose:

  * the objective is a BITMASK completing at 0x1F, not a counter. In a linear
    playthrough the two are indistinguishable; only the out-of-order collection in
    the retained run separates them, so that evidence is guarded explicitly.
  * a RESIDENT function reads an OVERLAY-LOCAL address, valid only because it is
    scene-gated. Anyone editing region A needs that to still be recorded.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/phase4_f10_clover_objective.c"
ART = ROOT / "analysis/phase4_f10_clover_objective.json"
RESIDENT_CENSUS = ROOT / "analysis/phase4_f10_clover_mask_resident_census.json"
OVERLAY_CENSUS = ROOT / "analysis/phase4_f10_clover_mask_overlay_census.json"
CANON = ROOT / "ObsidianVault/Canon/Systems/SYS_clover_forest_objective.md"


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
def tool(tmp_path_factory):
    exe = tmp_path_factory.mktemp("f10") / "f10"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL)], check=True, cwd=ROOT)
    return subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)


@pytest.fixture(scope="module")
def art():
    return json.loads(ART.read_text())


def test_tool_builds_and_every_pin_holds(tool):
    assert tool.returncode == 0, tool.stdout[-3000:]
    assert "0 failed" in tool.stdout


def test_stage_target_is_derived_not_assumed(tool):
    """Ordinal 10 -> scene 7, cross-checked against two rows already solved."""
    assert "0x80077FA0[10] == 7" in tool.stdout
    assert "[11] == 12" in tool.stdout and "[3] == 2" in tool.stdout


def test_direct_reference_claim_is_scoped_to_overlay_local(tool):
    assert "four references, two of them stores" in tool.stdout
    assert "READS it five times and never writes it" in tool.stdout
    assert "no other resolved fixed-form overlay reference was found" in tool.stdout
    assert "pointer-derived accesses remain open" in tool.stdout


def test_general_censuses_pin_direct_sets_and_open_residuals():
    resident = json.loads(RESIDENT_CENSUS.read_text())
    overlay = json.loads(OVERLAY_CENSUS.read_text())
    assert resident["writers"] == []
    assert [x["pc"] for x in resident["readers"]] == [
        "0x800532E0", "0x80053308", "0x80053334", "0x80053360", "0x8005338C",
    ]
    assert resident["residual"]["unresolved_accesses_total"] == 12956
    assert resident["residual"]["indirect_calls_unresolved"] == 149

    level07 = next(x for x in overlay["overlays"] if x["overlay"] == "LEVEL07_LEVEL")
    assert [(x["pc"], x["kind"]) for x in level07["hits"]] == [
        ("0x800B3E9C", "write"),
        ("0x800B4220", "read"),
        ("0x800B4244", "write"),
        ("0x800B4484", "read"),
    ]
    assert level07["unresolved_base_accesses"] == 180
    assert sum(x["unresolved_base_accesses"] for x in overlay["overlays"]) == 4967


def test_canon_and_tool_do_not_reassert_closure():
    canon = CANON.read_text()
    source = TOOL.read_text()
    assert "## Domain closure, scoped correctly" not in canon
    assert "- **In every other overlay**: none. No other overlay references that VA." not in canon
    assert "claim(other == 0,\n              \"and NO other overlay references" not in source
    assert "fixed-form effective addresses" in canon


def test_resident_hud_reads_overlay_memory_under_a_scene_gate(tool):
    assert "compares it against 7" in tool.stdout
    assert "hard-codes an overlay-local address" in tool.stdout
    assert "one HUD icon per piece" in tool.stdout


def test_completion_is_the_mask_reaching_1f(tool):
    assert "compare against 0x1F" in tool.stdout
    assert "latch 0x800823A0 := 1" in tool.stdout
    assert "fade 0x80082470 := 120" in tool.stdout


# --------------------------------------------------------------------- live --

def test_live_run_reached_the_completion_mask(art):
    assert art["mask_reached_1f"] is True


def test_five_DISTINCT_bits_were_set(art):
    bits = [int(b["new_bit"], 16) for b in art["distinct_bits_set"]]
    assert len(bits) == 5
    assert sorted(bits) == [0x01, 0x02, 0x04, 0x08, 0x10]


def test_the_bits_were_set_OUT_OF_ORDER(art):
    """This is the whole reason the mask reading is safe. In a linear run a counter
    and a mask look identical; the retained run collects out of order, so it
    discriminates them. If a future fixture replaces this one with a linear run, the
    discriminating evidence is gone and this guard should fail loudly."""
    bits = [int(b["new_bit"], 16) for b in art["distinct_bits_set"]]
    assert bits != sorted(bits), bits
    assert bits[0] == 0x10 and bits[-1] == 0x01


def test_the_parallel_word_counts_five_down_to_zero(art):
    vals = [c["v"] for c in art["count_writes"]]
    assert vals[:6] == [5, 4, 3, 2, 1, 0], vals[:6]


def test_the_latch_was_set_by_the_pinned_pc(art):
    setters = [l for l in art["latch_writes"] if l["v"] == 1]
    assert setters and setters[0]["pc"] == "0x800b44b0"


# --------------------------------------------------------------- row + canon --

def test_row_records_mask_not_counter():
    b = " ".join(rows()["F10_clover_forest"]["bindings"])
    assert "BITMASK, NOT A COUNTER" in b
    assert "0x800B5774" in b and "0x1F" in b
    assert "OUT OF ORDER" in b


def test_row_states_what_is_actually_left():
    """Both originally-named items (piece/bit mapping, the 0x04 gate) are now closed,
    so this guard tracks the CURRENT residual instead of the old one. It replaced a
    version that asserted those two were still open -- which failed the moment they
    were closed, which is the guard working."""
    m = rows()["F10_clover_forest"]["missing"]
    assert "hazards and route" in m
    assert "Which physical piece each bit corresponds to" not in m


def test_canon_flags_the_region_a_hazard():
    t = flat(CANON)
    assert "resident function hard-codes an overlay-local address" in t
    assert "before anyone edits region A" in t


def test_canon_records_the_fade_length_is_per_site():
    t = flat(CANON)
    assert "fade length is **per-site**" in t


# ------------------------------------------------------------- the polish --

def test_the_five_pieces_are_enumerated_not_assumed(tool):
    """Which piece is which bit is a property of the CALL SITES, since the collect
    block takes the bit in a register."""
    assert "exactly five call sites of the per-piece update" in tool.stdout
    assert "each passes a DISTINCT bit in a2" in tool.stdout
    assert "uniform 0x18 stride" in tool.stdout


def test_record_layout_is_read_from_the_proximity_test(tool):
    """The first three words are the piece position -- established from the code that
    consumes them, not from simulating the init block's registers (which produced a
    wrong answer first)."""
    assert "the record's first three words are the piece's world position" in tool.stdout


def test_the_varying_a2_offset_is_searched_not_assumed():
    """A fixed -8 offset matched one call site and failed the other four. The pin
    caught it; the fix must not regress to a fixed distance."""
    src = TOOL.read_text()
    assert "search a window rather than assume" in src
    assert "for (back = 4; back <= 0x24; back += 4)" in src


def test_the_power_word_gate_attribution_stays_retracted(tool):
    """It was banked as 'exactly one setter, means the player is dying'. A live 0->1
    edge trace refuted both halves. The retraction must not quietly heal."""
    assert "RETRACTED attribution" in tool.stdout
    assert "not about the bit" in tool.stdout
    assert "0x8004EB6C is the site that actually fires" in tool.stdout
    assert "cutscene/cinematic state than death" in tool.stdout


def test_encoding_specific_scans_are_flagged_as_unable_to_close_a_domain(tool):
    """The root cause: the scan matched only the lui-formed absolute store, so it
    reported 'exactly one' where there are at least two."""
    assert "an encoding-specific scan CANNOT close this domain" in tool.stdout


def test_live_capture_confirms_bit_to_record_mapping():
    d = json.loads((ROOT / "analysis/phase4_f10_clover_pieces_live.json").read_text())
    valid = [m for m in d["piece_mapping_observed"] if m.get("record_index") is not None]
    assert valid, "no hit landed on a real record"
    assert all(m["bit_matches_index"] for m in valid), valid


def test_live_capture_gated_out_foreign_overlay_hits():
    """An execute breakpoint in the shared region-A window fires for whatever overlay
    is resident. Without the scene gate the capture is of another level's code."""
    d = json.loads((ROOT / "analysis/phase4_f10_clover_pieces_live.json").read_text())
    assert d.get("foreign_overlay_hits", 0) >= 1
    src = (ROOT / "tools/phase4_f10_clover_pieces_live.py").read_text()
    assert "scene != 7" in src


BIT04 = ROOT / "tools/phase4_f10_bit04_meaning.c"


@pytest.fixture(scope="module")
def bit04(tmp_path_factory):
    exe = tmp_path_factory.mktemp("bit04") / "bit04"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(BIT04)], check=True, cwd=ROOT)
    return subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)


def test_bit04_named_from_a_complete_census(bit04):
    """Named from ALL readers and setters, not one site's neighbourhood -- which is
    how the retracted 'player is dying' reading was produced."""
    assert bit04.returncode == 0, bit04.stdout[-2000:]
    assert "0 failed" in bit04.stdout
    assert "five readers in the resident EXE" in bit04.stdout
    assert "MORE THAN ONE" in bit04.stdout


def test_bit04_argument_rests_on_uniform_branch_sense(bit04):
    """If some readers acted when SET and others when CLEAR it would be a mode
    selector and the name would not follow. They are all bne+forward."""
    assert "every one is `bne`" in bit04.stdout
    assert "every branch goes FORWARD" in bit04.stdout
    assert "GAMEPLAY-SUSPENDED flag" in bit04.stdout


def test_bit04_is_not_narrowed_to_cutscene_or_death(bit04):
    assert "NOT narrowed" in bit04.stdout or "not as a name read off one site" in bit04.stdout


def test_row_missing_never_asserts_the_retracted_claim():
    """The `missing` field once said bit 0x04 "is the player-is-dying flag" -- the
    exact claim that had been retracted, sitting in the field that is supposed to
    record what is still open. A row that misstates its own state is worse than a
    row that is merely incomplete."""
    r = rows()["F10_clover_forest"]
    blob = (r["missing"] + " " + r["next"]).lower()
    assert "is the player-is-dying flag" not in blob
    assert "retracted" in blob
    assert "46" in r["next"], "pin count must track the tool"


def test_row_records_bit04_as_gameplay_suspended():
    b = " ".join(rows()["F10_clover_forest"]["bindings"])
    assert "GAMEPLAY SUSPENDED" in b
    assert "BRANCH SENSE IS UNIFORM" in b
    assert "NOT narrowed to cutscene or death" in b


def test_row_state_now_that_bit04_is_named():
    """State has moved twice: named wrongly, retracted, then named from a complete
    census. The row must reflect the CURRENT position -- and the earlier wrong name
    must not survive anywhere in it."""
    r = rows()["F10_clover_forest"]
    b = " ".join(r["bindings"])
    assert "THE FIVE PIECES" in b
    assert "GAMEPLAY SUSPENDED" in b
    assert "RETRACTED" in b, "the correction history must stay visible"
    assert "means the player is dying" not in b
    assert "hazards and route" in r["missing"]


def test_canon_has_no_duplicated_sections():
    """An edit spliced on `t.index('## Verified')`, which found the FIRST occurrence
    and re-appended everything after it. The page ended up 232 lines with five
    duplicated sections AND the retracted claim restored as a standalone heading.
    Every content guard still passed, because they all checked that the NEW text was
    present and none checked that the OLD text was gone."""
    heads = [l for l in CANON.read_text().splitlines() if l.startswith("## ")]
    assert len(heads) == len(set(heads)), [h for h in heads if heads.count(h) > 1]


def test_canon_does_not_reassert_the_retracted_naming():
    """The retracted reading may appear ONLY inside the correction history, quoted as
    wrong -- never as a heading or a standalone claim."""
    text = CANON.read_text()
    assert "## `0x800A6590 & 0x04` means the player is dying" not in text
    for line in text.splitlines():
        if "player is dying" in line:
            assert "*" in line or "wrong" in line or "retracted" in line.lower(), line


def test_canon_carries_the_name_its_history_and_the_piece_table():
    """Canon must state the current name, keep the record of how it was got wrong,
    and refuse the narrower readings that were the original error."""
    t = flat(CANON)
    assert "GAMEPLAY-SUSPENDED flag" in t
    assert "Correction history" in t
    assert "the naming was retracted" in t
    assert "not* narrowed to" in t
    assert "0x800B56D8" in t and "0x800B5738" in t
    assert "doubles as a tombstone" in t
