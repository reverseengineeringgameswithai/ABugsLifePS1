"""Guards for F11 (The Tree): the scout-found progression.

See ObsidianVault/Experiments/EXP_2026-08-04_phase4_f11_the_tree_scouts.md.
"""

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis" / "phase4_f11_scout_progression.json"
TOOL_C = ROOT / "tools" / "phase4_f11_static.c"
TOOL_PY = ROOT / "tools" / "phase4_f11_scout_progression.py"
BLOB = ROOT / "REBUILD" / "files" / "LEVEL02" / "LEVEL1.BIN"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"
EXP = (ROOT / "ObsidianVault" / "Experiments" /
       "EXP_2026-08-04_phase4_f11_the_tree_scouts.md")


def art():
    return json.loads(ART.read_text())


def rows():
    doc = yaml.safe_load(REGISTRY.read_text())
    for v in doc.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {r["id"]: r for r in v}
    raise AssertionError("no row list")


def test_pin_tool_compiles_and_every_pin_holds():
    out = ROOT / "build" / "phase4_f11_static"
    out.parent.mkdir(exist_ok=True)
    subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(TOOL_C), "-o", str(out)], check=True, cwd=ROOT)
    r = subprocess.run([str(out), str(BLOB.relative_to(ROOT))],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:]
    assert "27/27 pins OK" in r.stdout


def test_all_five_saves_are_the_same_stage_and_progressive():
    a = art()
    assert a["scene_ids"] == [12] * 5
    frames = [p["frame"] for p in a["per_save"]]
    assert frames == sorted(frames) and len(set(frames)) == 5


def test_the_counter_is_the_only_small_bounded_monotonic_candidate():
    """59 monotonic candidates; exactly one looks like a counter rather than a
    coordinate, pointer or timer."""
    a = art()
    small = [c for c in a["candidates"] if max(c["values"]) <= 16]
    assert len(small) == 1, small
    assert small[0]["addr"] == "0x800B4A48"
    assert small[0]["values"] == [5, 4, 3, 2, 1]
    assert small[0]["direction"] == "decreasing"


def test_the_candidate_scan_is_labelled_as_candidates_not_an_answer():
    """A monotonic value can be a frame or elapsed counter. The tool must say so."""
    a = art()
    assert "candidates only" in a["caveat"]
    assert "Confirm by finding the writer" in a["caveat"]


def test_registry_records_the_derived_counter():
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "0x800B4A48" in b
    assert "DERIVED not decremented" in b
    assert "0x800B49EC" in b


def test_the_one_shot_claim_is_retracted():
    """I called the found bit a one-shot from a static read, tracking the offset but
    not the base register's reassignment. Live: zero clears."""
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "Wrong actor, right instruction" in b
    assert "PERSISTENT" in b
    assert "0x800A1850" in b
    src = TOOL_C.read_text()
    assert "wrong actor, right instruction" in src.lower()


def test_the_find_event_is_player_contact():
    f = json.loads((ROOT / "analysis" / "phase4_f11_find_event.json").read_text())
    assert f["ring_truncated"] is False
    sets = f["findings"]["bit_set_events"]
    assert len(sets) == 2
    assert {s["pc"] for s in sets} == {"0x8004b464"}
    assert {s["scout"] for s in sets} == {0, 1}
    assert f["findings"]["bit_clear_events"] == [], "the bit must never be cleared"
    seq = f["findings"]["counter_values"]
    distinct = [x for i, x in enumerate(seq) if i == 0 or x != seq[i - 1]]
    assert distinct == [6, 5, 4, 3], distinct


def test_the_shared_contact_bit_convention_is_recorded():
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "actor_player_contact_resolver" in b
    assert "ONE SHARED CONVENTION" in b


def test_registry_records_the_blob_correction():
    """Second row today where the scene-asset name is not the executing overlay."""
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "NOT THE RESIDENT BLOB" in b
    assert "LEVEL02/LEVEL1.BIN at 100.0%" in b
    assert "CODE window" in b


def test_the_open_items_are_recorded_as_open():
    r = rows()["F11_the_tree"]
    b = " ".join(r["bindings"])
    assert "NOT CLOSED" in r["missing"]
    assert "ACORNS" in r["missing"] and "CLIMBING" in r["missing"]
    assert "A16_swinging" in r["missing"], "swinging's real owner must be named"


def test_surfaces_exist():
    for p in (ART, TOOL_C, TOOL_PY, EXP):
        assert p.exists(), p


# --------------------------------------------------- the exit gate / objective --

GATE = ROOT / "analysis" / "phase4_f11_exit_gate.json"


def gate():
    return json.loads(GATE.read_text())


def test_all_five_finds_and_the_counter_reaches_zero():
    g = gate()
    assert g["ring_truncated"] is False
    sets = g["findings"]["bit_set_events"]
    assert {s["scout"] for s in sets} == {0, 1, 2, 3, 4}
    assert {s["pc"] for s in sets} == {"0x8004b464"}
    assert g["findings"]["bit_clear_events"] == [], "scout bits must never be cleared"
    seq = g["findings"]["counter_values"]
    distinct = [x for i, x in enumerate(seq) if i == 0 or x != seq[i - 1]]
    assert distinct == [6, 5, 4, 3, 2, 1, 0], distinct


def test_the_exit_fires_after_the_count_hits_zero():
    g = gate()
    assert g["findings"]["counter_reached_zero"] is True
    assert "0x800b4424" in g["findings"]["goal_latch_writer_pcs"]
    assert "consistent with the count gating the exit" in g["findings"]["objective_verdict"]


def test_registry_records_the_gate_and_that_dot_was_measured():
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "bne s3,5" in b
    assert "THE GATE ACTOR IS DOT, MEASURED" in b
    assert "id 14" in b
    assert "0x800B4424" in b


def test_the_one_shot_belongs_to_dot_not_the_scouts():
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "Wrong actor, right instruction" in b
    assert "PERSISTENT" in b
    src = TOOL_C.read_text()
    assert "clears DOT's contact bit" in src


def test_row_status_reflects_the_work():
    r = rows()["F11_the_tree"]
    assert r["status"] == "partial", "no longer an external_lead"
    assert "static_code" in r["evidence"]


def test_the_summary_fields_are_not_stale_against_the_bindings():
    """The bindings kept being right while `missing`/`next` went stale. Both drifts
    happened on this row: first `missing` was compressed until it hid three mechanics,
    then `next` kept describing acorns as untouched collectibles after the bindings had
    established they are props set by overlay code. Guard the specific contradictions."""
    r = rows()["F11_the_tree"]
    b = " ".join(r["bindings"])
    # bindings say acorns are resolved and NOT collectibles
    assert "ACORNS EXIST AND ARE REUSABLE PROPS, NOT COLLECTIBLES" in b
    # Check the LIVE part of `next` -- the text before the retraction marker. The
    # retraction deliberately QUOTES the wrong phrasing, so scanning the whole field
    # would flag the correction itself.
    live = r["next"].split("⚠️ An earlier revision")[0]
    assert "both untouched" not in live
    assert "collectibles here are contact-driven" not in live
    assert "actor_player_contact_resolver" not in live
    miss = r["missing"]
    assert not ("only scouts/Dot are done" in miss and "RESOLVED" in miss), \
        "missing field contradicts itself"
    # and the retraction must be visible, not silently overwritten
    assert "gone stale against newer findings" in r["next"]


def test_the_row_is_not_claimed_bounded():
    """The row NAME lists scouts/Dot, climbing, acorns, swinging. Only scouts/Dot are
    done. An earlier revision compressed the other three into "special traversal" and
    called the row bounded -- that narrowed the recorded scope."""
    r = rows()["F11_the_tree"]
    assert "NOT CLOSED" in r["missing"]
    # each named mechanic must carry an explicit status word, not be summarised away
    for token in ("SCOUTS/DOT", "ACORNS", "CLIMBING", "SWINGING"):
        assert token in r["missing"], token
    # whatever remains open must still be NAMED -- the row may not quietly imply
    # completeness while an item is outstanding
    assert "ALSO OPEN" in r["missing"]
    assert "critical path" in r["missing"]


# ------------------------------------------- the overlay state surface / acorns --

STATE = ROOT / "analysis" / "phase4_f11_overlay_state.json"


def state():
    return json.loads(STATE.read_text())


def test_the_overlay_state_surface_is_complete_and_none_silent():
    """Eleven words is the whole surface, from a dataflow scan. If any watched word
    never fired, the 'complete and accounted for' claim is weaker than stated."""
    s = state()
    assert s["ring_truncated"] is False
    assert s["silent"] == [], s["silent"]
    overlay = [k for k in s["fields"] if k.startswith("0x800B4A")]
    assert len(overlay) == 11, overlay


def test_the_found_ordinal_and_pointer_track_the_five_finds():
    s = state()
    ordinal = s["fields"]["0x800B4A2C"]
    assert [t["v"] for t in ordinal["transitions"]] == [0, 1, 2, 3, 4]
    ptr = s["fields"]["0x800B4A38"]
    got = [t["v"] & 0xFFFFFFFF for t in ptr["transitions"]]
    assert got == [0x800A119C + n * 0x84 for n in range(5)], [hex(x) for x in got]


def test_the_acorn_negative_is_bounded_not_absolute():
    """The overlay-state negative was correctly stated as bounded -- and the bound was
    then discharged by the actor census, which found the acorns. Both must survive:
    the original hedged negative, and the resolution."""
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "ACORN NEGATIVE" in b
    assert "BOUNDED NOT" in b and "ABSOLUTE" in b
    assert "does not rule out" in b
    m = rows()["F11_the_tree"]["missing"]
    assert "ACORNS -- CLOSED" in m and "chars3" in m


# ------------------------------------------------------------------ climbing --

CLIMB = ROOT / "analysis" / "phase4_f11_climbing.json"


def climb():
    return json.loads(CLIMB.read_text())


def test_climbing_is_not_a_discrete_player_state():
    c = climb()
    assert c["ring_truncated"] is False
    assert c["state_word"]["distinct_values"] == [0, 1, 2, 3, 4, 5, 6]
    # the stage really does have vertical traversal -- that's what makes the negative
    # meaningful rather than vacuous
    assert c["flik_y"]["max"] - c["flik_y"]["min"] > 100000


def test_the_climb_negative_is_stated_as_bounded():
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "CLIMBING IS NOT A DISCRETE STATE" in b
    assert "BOUNDED CLAIM" in b
    assert "not evidence that no climbing exists" in b


def test_state_3_is_a_canon_domain_extension():
    """The documented domain omitted 3. It is real, and written by exactly one PC."""
    c = climb()
    assert 3 in c["state_word"]["distinct_values"]
    assert c["state_word"]["values_outside_documented_domain"] == [3]
    canon = (ROOT / "ObsidianVault" / "Canon" / "Systems" /
             "SYS_player_action_state_laws.md").read_text()
    assert "0x80048CFC" in canon
    assert "State 3" in canon
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "CANON DOMAIN EXTENSION" in b
    assert "A10_handstand" in b, "the owning row must be named, not annexed"


# -------------------------------------------------------------------- acorns --

CENSUS = ROOT / "analysis" / "phase4_f11_actor_census.json"
ACORNS = ROOT / "analysis" / "phase4_f11_acorns.json"


def test_the_object_roster_names_acorns_and_scouts():
    c = json.loads(CENSUS.read_text())
    assert c["scene_id"] == 12
    assert c["species_histogram"]["31"] == 7   # chars3\acorn
    assert c["species_histogram"]["32"] == 5   # chars3\bluescot -- the scouts
    assert c["species_histogram"]["14"] == 1   # chars2\dot


def test_acorns_are_reusable_props_not_collectibles():
    a = json.loads(ACORNS.read_text())
    assert a["ring_truncated"] is False
    sets = a["findings"]["bit_set_events"]
    clears = a["findings"]["bit_clear_events"]
    assert len(sets) == 10 and len(clears) == 10, (len(sets), len(clears))
    # overlay sets it, actor re-init clears it -- NOT the resident contact resolver
    assert a["findings"]["setter_pcs"] == ["0x800b41a4"]
    assert "0x8004b464" not in a["findings"]["setter_pcs"]
    assert {c["pc"] for c in clears} == {"0x80049cac"}
    # repeatable: at least one acorn fires more than once
    from collections import Counter
    assert max(Counter(s["scout"] for s in sets).values()) > 1


def test_the_campaign_wide_contact_bit_claim_is_qualified():
    """I generalised bit 0x1000 to a campaign-wide meaning. The acorns refute that."""
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "QUALIFIES THIS ROW'S OWN EARLIER CLAIM" in b
    assert "SHARED SCRATCH FLAG" in b
    assert "does not hold" in b
    # and the original claim must still be present as history
    assert "ONE SHARED CONVENTION" in b


def test_the_acorn_state_machine_is_a_measured_retirement_path():
    """Predicted from the branch, then measured -- and the prediction was stated in a
    falsifiable form before the run."""
    a = json.loads((ROOT / "analysis" / "phase4_f11_acorn_state.json").read_text())
    assert a["ring_truncated"] is False
    assert "falsifiable_as" in a, "the prediction must be recorded as falsifiable"
    f = a["findings"]
    assert "CONFIRMED" in f["verdict"]
    assert len(f["retirement_hp_zero_events"]) == 10
    assert f["plus62_values_at_retire"] == [5]
    assert len(f["acorns_retired"]) == 6


def test_registry_records_the_full_acorn_cycle():
    b = " ".join(rows()["F11_the_tree"]["bindings"])
    assert "ACORN STATE MACHINE CLOSED" in b
    assert "RETIREMENT path" in b
    assert "0x800B4218" in b and "0x800B4220" in b
    assert "0x1040" in b, "the reachability evidence must be kept"
    assert "ACORNS -- CLOSED" in rows()["F11_the_tree"]["missing"]


def test_the_stopping_decision_is_argued_not_implied():
    """The row was twice made to look complete by summarising open items away. The
    stopping decision must now carry its reasoning, and must not claim completeness."""
    n = rows()["F11_the_tree"]["next"]
    assert "DELIBERATE STOPPING POINT" in n
    assert "WHY I STOPPED" in n
    assert "WHAT IT WOULD TAKE IF SOMEONE WANTS IT" in n
    assert 'Do not read this as "the row is complete"' in n
    assert rows()["F11_the_tree"]["status"] == "partial"
