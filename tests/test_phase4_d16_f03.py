"""Guards for D16_thumper / F03_council_chamber.

See ObsidianVault/Experiments/EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber.md.

The finding these guard is a RETRACTION: 0x80090BEE was bound in both rows as a Thumper
defeat flag, and it is really the flags field of the shared cinematic camera. The tests
therefore protect two things that are easy to lose -- the corrected claim, and the fact
that the old one was wrong.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d16_f03.json"
ORACLE = ROOT / "analysis" / "phase4_d16_f03_oracle.json"
TOOL_C = ROOT / "tools" / "phase4_d16_f03_static.c"
CENSUS_PY = ROOT / "tools" / "phase4_d16_f03_census.py"
ORACLE_PY = ROOT / "tools" / "phase4_d16_f03_oracle.py"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"
CANON = ROOT / "ObsidianVault" / "Canon" / "Systems" / "SYS_cinematic_camera.md"
EXP = (ROOT / "ObsidianVault" / "Experiments" /
       "EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber.md")


def art():
    return json.loads(ARTIFACT.read_text())


def rows():
    doc = yaml.safe_load(REGISTRY.read_text())
    for v in doc.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {r["id"]: r for r in v}
    raise AssertionError("no row list in the registry")


# --------------------------------------------------------------- the census --

def test_pin_tool_compiles_and_every_pin_holds():
    out = ROOT / "build" / "phase4_d16_f03_static"
    out.parent.mkdir(exist_ok=True)
    subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(TOOL_C), "-o", str(out)], check=True, cwd=ROOT)
    r = subprocess.run([str(out)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-3000:]
    assert "38/38 pins OK" in r.stdout


def test_second_implementation_agrees_with_the_c_tool():
    """The census is double-implemented on purpose; a single one inflated its counts
    2x once before and the error reached a banked claim."""
    a = art()
    assert a["second_implementation_agrees"] is True
    assert a["disagreements"] is None
    assert a["pin_tool_exit_code"] == 0


def test_census_is_eleven_accesses_and_an_overlay_does_touch_it():
    """Corrects the earlier '9 accesses, all resident, no overlay touches it'."""
    c = art()["census_0x80090BEE"]
    assert len(c["dataflow_hits"]) == 11
    assert c["overlay_touching_it"] == ["REBUILD/files/LEVEL02/LEVEL1.BIN"]


def test_accesses_are_halfword_not_byte():
    """The earlier pass recorded lbu/sb. Every access is lhu/sh."""
    for h in art()["census_0x80090BEE"]["dataflow_hits"]:
        op = int(h["word"], 16) >> 26
        assert op in (0x21, 0x25, 0x29), (h, "not a halfword access")


def test_the_low_half_collision_is_resolved_not_counted():
    """0x800B0BEE collides with 0x80090BEE in the low half; a count-only census
    would have reported 13 accesses and been quietly wrong."""
    fp = art()["census_0x80090BEE"]["immediate_false_positives_resolved_elsewhere"]
    assert len(fp) == 2
    assert all(f["resolves_to"] == "0x800B0BEE" for f in fp)


def test_the_blind_spot_is_stated():
    assert "pointer" in art()["census_0x80090BEE"]["known_blind_spot"]


# ------------------------------------------------------------- the findings --

def test_the_flags_word_is_a_camera_field_written_only_from_an_argument():
    f = art()["FINDING_0x80090BEE_IS_THE_CINEMATIC_CAMERA_FLAGS_FIELD"]
    assert "0x80090BC0" in f["what_it_is"]
    assert set(f["writers"]) == {"0x8004DA7C", "0x8004DB44", "0x8004EB1C", "0x8004EBAC"}
    assert "arg7" in f["writers"]["0x8004DA7C"]
    assert "arg8" in f["writers"]["0x8004DB44"]
    assert "CALLER-SUPPLIED" in f["why_the_value_2_is_not_a_defeat_code"]


def test_bit0_swaps_the_hud_for_letterboxing_not_a_boss_health_bar():
    f = art()["FINDING_0x80090BEE_IS_THE_CINEMATIC_CAMERA_FLAGS_FIELD"]
    assert "0x80053638" in f["bit_0x01"] and "0x800526F4" in f["bit_0x01"]
    assert "letterbox" in f["bit_0x01"].lower()


def test_power_bit4_is_a_suppression_gate_not_a_power_up():
    """This one is the sharpest correction: the earlier draft called it 'a previously
    unidentified power'. Every reader branches PAST its body when it is set."""
    f = art()["FINDING_POWER_BIT_0x04_IS_A_SUPPRESSION_GATE_NOT_A_POWER_UP"]
    assert len(f["readers"]) == 5
    assert "none enables anything" in f["shape"]
    assert "unidentified power" in f["corrects"]


def test_the_exit_is_a_different_store_and_the_overlay_was_measured():
    f = art()["FINDING_THE_LEVEL_EXIT_IS_A_DIFFERENT_STORE"]
    assert f["resident_overlay_during_the_fight"] == "REBUILD/files/LEVEL02/LEVEL.BIN"
    assert "LEVEL03/LEVEL1.BIN" in f["overlay_identity_was_measured"]
    assert "wrong" in f["overlay_identity_was_measured"]
    assert "0x800823A0" in f["the_level_exit"]
    assert "0x8009FE72" in f["thumper_hp_address"]
    assert "no read or write of 0x800823A0" in f["no_path_from_the_flags_word"]


# ------------------------------------------------------------- the live run --

def test_oracle_artifact_passes_and_is_poll_only():
    o = json.loads(ORACLE.read_text())
    assert o["pass"] is True, o.get("failures")
    assert not o.get("failures")
    assert "no accessLog" in o["regime"] and "no breakpoints" in o["regime"]
    for name, c in o["checks"].items():
        assert c["pass"], name


def test_oracle_measured_the_resident_overlay():
    o = json.loads(ORACLE.read_text())
    assert "REBUILD/files/LEVEL02/LEVEL.BIN" in o["resident_region_a_overlays"]
    assert o["checks"]["resident_overlay_is_expected"]["pass"]


def test_oracle_saw_the_full_hp_arc_and_the_scene_change():
    o = json.loads(ORACLE.read_text())
    assert o["hp_max"] == 50 and o["hp_min"] == 0
    assert o["hp_crossed_threshold_in_run"] is True
    assert o["scene_timeline"][0] == 2 and o["scene_timeline"][-1] != 2


def test_oracle_does_not_reintroduce_the_unsound_ordering_assertion():
    """An earlier revision asserted an ordering that runtime polling cannot establish
    (sample() is several sequential reads, so a frame boundary tears the tuple) -- and
    it PASSED. Never encode an inference as a passing structural check."""
    src = ORACLE_PY.read_text()
    assert "goal_latch_precedes_camera_flags" not in src
    assert "UNSOUND" in src
    assert "TORN" in src
    # the honest replacement must still be there
    assert "level_exit_actually_completes" in src


def test_oracle_reports_indeterminate_rather_than_vacuously_passing():
    """A fixture that never crosses the HP threshold must not let every 'after'
    check pass on an empty list."""
    src = ORACLE_PY.read_text()
    assert "indeterminate" in src
    assert "vacuously" in src


# ------------------------------------------------------- registry + surfaces --

def test_registry_rows_carry_the_correction_and_the_retraction():
    r = rows()
    d16 = " ".join(r["D16_thumper"]["bindings"])
    f03 = " ".join(r["F03_council_chamber"]["bindings"])
    assert "CATEGORY ERROR" in d16
    assert "0x8009FE72" in d16
    assert "cinematic-camera" in d16 or "cinematic camera" in d16
    assert "NOT A POWER-UP" in d16
    assert "RETRACTED" in f03
    assert "LEVEL02/LEVEL.BIN" in f03


def test_the_old_defeat_flag_binding_is_gone():
    r = rows()
    for rid in ("D16_thumper", "F03_council_chamber"):
        for b in r[rid]["bindings"]:
            # the retraction may quote it; a live binding may not assert it
            if "0x80090BEE" in b and "->" in b and "RETRACT" not in b:
                assert "CORRECTED" in b or "flags" in b.lower(), b


def test_shared_next_is_recorded_as_closed():
    r = rows()
    for rid in ("D16_thumper", "F03_council_chamber"):
        assert "CLOSED" in r[rid]["next"]


@pytest.mark.parametrize("path", [CANON, EXP, ARTIFACT, ORACLE, TOOL_C, CENSUS_PY,
                                  ORACLE_PY])
def test_every_surface_exists(path):
    assert path.exists(), path


def test_canon_page_names_the_wrong_census_name():
    """The function census auto-names 0x8004EA8C `enemy_ai_dispatcher`; Canon must
    say so, or the next reader will trust the name."""
    t = CANON.read_text()
    assert "enemy_ai_dispatcher" in t and "wrong" in t.lower()
    assert "0x8004EA8C" in t


# ---------------------------------------------------------- the traced run --

TRACE = ROOT / "analysis" / "phase4_d16_f03_trace.json"
TRACE_PY = ROOT / "tools" / "phase4_d16_f03_trace.py"


def tr():
    return json.loads(TRACE.read_text())


def test_trace_ring_did_not_truncate():
    """Every negative below ('written only by the BIOS', 'case 3 never fires') is
    unsound if the event ring dropped events."""
    assert tr()["ring_truncated"] is False


def test_trace_ran_on_an_interpreter_movie():
    t = tr()
    assert t["execution_mode"] == "Interpreter"
    assert "D16_Thumper_Defeat" in t["movie"]
    assert t["movie_version"] == 4


def test_overlay_identity_is_proven_by_writer_pc_not_by_a_hash():
    """The blob mutates its own head at runtime, so hashing region A is only valid
    just after load. The writer PC is the real proof."""
    o = tr()["overlay_identity"]
    assert o["confirmed"] is True
    assert o["expected_pc"] == "0x800b4190"
    assert "not a memory hash" in o["method"]


def test_hp_arc_is_exactly_fifteen_hits_at_instruction_level():
    f = tr()["findings"]["BONUS_hp_arc_at_instruction_level"]
    dmg = [c for pc, c in f["writer_pcs"] if pc == "0x800590e4"]
    assert dmg == [15], f["writer_pcs"]
    vals = f["values"]
    assert 50 in vals and 20 in vals
    steps = [a - b for a, b in zip(vals, vals[1:]) if a - b == 2]
    assert len(steps) >= 14


def test_the_alleged_attack_counter_is_bios_only():
    q = tr()["findings"]["Q3_the_alleged_fight_counters"]["0x80090BF6"]
    assert q["game_writers"] == []
    assert q["bios_writers"]
    assert "REFUTED" in q["verdict"]


def test_the_alleged_phase_counter_belongs_to_the_effect_spawner():
    q = tr()["findings"]["Q3_the_alleged_fight_counters"]["0x80090BF2"]
    assert "0x8005ce6c" in q["game_writers"]
    assert "WRONG owner" in q["verdict"]


def test_the_pointer_blind_spot_was_load_bearing():
    """Static found zero stores; the trace found 38. Declaring the blind spot instead
    of claiming a clean negative is what kept this pass honest."""
    q = tr()["findings"]["Q3_the_alleged_fight_counters"]["0x80090BF2"]
    assert q["static_census_found_zero_stores"] is True
    assert "POINTER" in q["why_static_missed_it"]
    assert q["writes"] > 0


def test_camera_exit_path_never_fires_and_is_closed_as_a_negative():
    q = tr()["findings"]["Q1_the_camera_exit_path"]
    assert q["writes"] == 3
    assert not any(pc == "0x8004ebac" for pc, _ in q["writer_pcs"]), \
        "case 3's store fired; the 'never fires' finding is stale"
    assert "NEVER FIRES" in q["verdict"]


def test_0x80082388_is_identified():
    q = tr()["findings"]["Q2_what_0x80082388_is"]
    assert "0x80054AD4" in q["verdict"]
    assert q["writes"] > 0


def test_registry_carries_the_traced_findings_and_the_refutation():
    r = rows()
    d16 = " ".join(r["D16_thumper"]["bindings"])
    f03 = " ".join(r["F03_council_chamber"]["bindings"])
    assert "REFUTED" in d16 and "0x80090BF6" in d16
    assert "THROUGH A POINTER" in d16
    assert "WRITER PC, NOT BY HASHING" in d16.upper()
    assert "NEVER FIRES" in d16
    assert "D16_Thumper_Defeat.movie.json" in str(r["D16_thumper"]["fixture_have"])
    assert "0x800B4190" in f03


def test_trace_tool_exists():
    assert TRACE_PY.exists() and TRACE.exists()


def test_the_hopper_lead_is_retracted_everywhere():
    """A "lead" sourced from a chat remark is still a banked claim. "Hopper takes
    damage in the Council Chamber" was recorded on four surfaces and in a commit
    message before the operator corrected it -- they had meant Thumper, and this IS
    the Thumper stage. Labelling it "not instrumented" did not make it safe."""
    assert "Hopper" not in CANON.read_text()
    d16 = " ".join(rows()["D16_thumper"]["bindings"]) + rows()["D16_thumper"]["missing"]
    assert "RETRACTED" in d16 and "misspoken" in d16
    exp = EXP.read_text()
    assert "Retracted the same day" in exp
    assert "inference from chat is NOT" in exp


# ------------------------------------------- fight phases + mosquito (D16) --

FIGHT = ROOT / "analysis" / "phase4_d16_fight.json"
FIGHT_C = ROOT / "tools" / "phase4_d16_fight_static.c"
FIGHT_PY = ROOT / "tools" / "phase4_d16_fight_trace.py"


def fi():
    return json.loads(FIGHT.read_text())


def test_fight_static_tool_compiles_and_every_pin_holds():
    out = ROOT / "build" / "phase4_d16_fight_static"
    out.parent.mkdir(exist_ok=True)
    subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(FIGHT_C), "-o", str(out)], check=True, cwd=ROOT)
    r = subprocess.run([str(out), "REBUILD/files/SCUS_942.88"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-3000:]
    assert "40/40 pins OK" in r.stdout


def test_fight_trace_ring_did_not_truncate():
    assert fi()["ring_truncated"] is False


def test_species_callback_field_is_0x7c_confirmed_live():
    """The stores encode 0x74 against s1 = actor + 8. Reading them literally is
    wrong by exactly 8, and a first pass at this file did exactly that."""
    f = fi()
    assert f["callback_field_confirmed"]["thumper"] is True
    assert f["callback_field_confirmed"]["mosquito"] is True
    v = f["verdicts_on_the_archived_note"]["CONFIRMED_species_callback_is_at_actor_plus_0x7C"]
    assert "0x8004a5f0" in [pc for pc, _ in v["writers"]]
    assert "+0x74" in v["note"]


def test_actor_array_base_is_derived_not_assumed():
    """0x8009FE04 is SLOT 1. Assuming it was the base made the first survey empty."""
    f = fi()
    assert f["derived_array_base"] == "0x8009FD80"
    assert f["thumper"]["addr"] == "0x8009FE04"
    assert f["thumper_roster_index"] == 1
    assert "DERIVED, not assumed" in f["located_by"]


def test_one_thumper_two_mosquitoes():
    f = fi()
    assert len(f["thumper_callback_sites"]) == 1
    assert f["mosquito_count"] == 2
    assert f["derived_actor_stride"] == [0x84]


def test_thumper_callback_is_a_sound_wrapper_not_a_driver():
    v = fi()["verdicts_on_the_archived_note"][
        "REFUTED_thumper_attack_cycle_runs_in_his_species_callback"]
    assert "play_sound(26)" in v["verdict"]
    assert "Thud" in v["verdict"]


def test_thumper_has_no_phase_counter_and_runs_on_the_mover_vm():
    p = fi()["thumper_fight_phases"]
    assert "no separate Thumper phase counter" in p["verdict"]
    assert "0x80077634" in p["verdict"] and "0x8004C834" in p["verdict"]
    assert "0x800B45A4" in p["on_defeat"]


def test_the_mosquito_launcher_is_overlay_code_not_resident():
    v = fi()["verdicts_on_the_archived_note"][
        "REFUTED_launcher_is_resident_0x80049C98_to_0x80049DB8"]
    assert "mover_init_from_record" in v["verdict"]
    assert "0x800B4330" in v["verdict"]
    assert "0x800B4940" in v["verdict"]


def test_the_mosquito_one_shot_fired_from_the_pinned_instruction():
    v = fi()["verdicts_on_the_archived_note"]["CONFIRMED_the_one_shot_fires"]
    assert "0x8004a1d8" in v["plus_0x6C_writers"]


def test_the_park_in_place_claim_stays_not_confirmed():
    nc = fi()["verdicts_on_the_archived_note"][
        "NOT_CONFIRMED_thumper_program_is_park_in_place_0x800776AC"]
    assert "0x80077634" in nc["verdict"] and "BEFORE init" in nc["verdict"]


# --- the two claims the first capture left undetermined, settled by a second one ---

def res():
    return fi()["verdicts_on_the_archived_note"]["RESOLVED_2026_08_04_second_capture"]


def test_flags_transition_settled_by_a_full_distinct_value_set():
    """The first capture stored a flat 200 values against 1562 writes -- a SAMPLING GAP,
    correctly recorded as undetermined rather than as a negative."""
    f = res()["flags_0x0002_to_0x4007"]
    assert f["verdict"] == "CONFIRMED"
    assert "0x2" in f["distinct_values_seen"]
    assert "0x4007" in f["distinct_values_seen"]
    # the one-shot request bit, visible exactly where the static reading predicted
    assert "0x1007" in f["distinct_values_seen"]
    assert f["writes"] > 1000


def test_aim_offsets_reconcile_as_two_different_fields():
    a = res()["aim_offsets"]
    assert "never a contradiction" in a["verdict"]
    # the claimed setpoint fields are written, just far less than the motion fields
    assert all(v > 0 for v in a["claimed_0x34_0x38_0x3C_writes"].values())
    assert min(a["measured_0x1C_0x24_writes"].values()) > \
        max(a["claimed_0x34_0x38_0x3C_writes"].values())
    assert "0x800B3E54" in a["the_rise"] and "rise" in a["the_rise"].lower()


def test_the_index_branch_is_resolved_with_a_measured_reason():
    """"Not taken" is only worth something with the reason attached."""
    b = res()["branch_0x800B4158_on_index_eq_3"]
    assert b["branch_taken"] is False
    assert b["index_distinct"] == ["0x0", "0x1"]
    assert "never the 3" in b["verdict"]
    assert not any(pc == "0x800b4164" for pc, _ in b["quota_writers"])


def test_registry_records_the_fight_closure_and_what_is_left():
    r = rows()["D16_thumper"]
    b = " ".join(r["bindings"])
    assert "FIGHT PHASES + MOSQUITO CLOSED" in b
    assert "NO FIGHT-PHASE COUNTER" in b
    assert "OVERLAY CODE" in b
    assert "0x8009FD80" in b
    assert "RESOLVED BY A SECOND CAPTURE" in b
    assert "NOTHING from this row's original scope" in r["missing"]


def test_fight_surfaces_exist():
    assert FIGHT.exists() and FIGHT_C.exists() and FIGHT_PY.exists()


# ------------------------------------------------------------- the arena --

ARENA = ROOT / "analysis" / "phase4_d16_arena.json"
ARENA_PY = ROOT / "tools" / "phase4_d16_arena.py"


def ar():
    return json.loads(ARENA.read_text())


def test_arena_radius_is_derived_from_actor_data():
    f = ar()["findings"]["1_radius_is_per_actor_roster_data"]
    assert f["raw"] == 25
    assert f["s4"] == 400
    assert f["predicted_max_offset"] == 12800
    assert ar()["sin_amplitude_measured"] == 16384


def test_sin_amplitude_is_measured_not_assumed():
    """Assuming 4096 predicted 3200 against an observed 12800 and made a correct
    model look refuted."""
    src = ARENA_PY.read_text()
    assert "SIN_TABLE" in src
    assert "never assumed" in src
    assert "amp = max(struct.unpack" in src


def test_the_horizontal_anchor_is_fixed_and_vertical_is_overlay_driven():
    f = ar()["findings"]["2_is_the_anchor_fixed"]
    assert f["distinct_values_per_axis"]["anchor X"] <= 2
    assert f["distinct_values_per_axis"]["anchor Z"] <= 2
    assert "0x800b400c" in f["writer_pcs"]["anchor Y"]
    assert "FIXED" in f["verdict"]


def test_the_bound_is_reached_not_merely_respected():
    """A radius nothing ever approaches would be a loose upper bound, not a radius."""
    f = ar()["findings"]["3_do_targets_stay_inside_the_circle"]
    assert f["bound_is_reached"] is True
    assert f["max_observed_offset"] >= f["predicted_max"] * 0.95
    assert f["max_observed_offset"] <= f["predicted_max"] * 1.02


def test_arena_tool_reads_mid_fight_not_at_the_edges():
    """roster+0x14 reads 0 both before init and after playback ends."""
    src = ARENA_PY.read_text()
    assert "READ TIMING" in src
    assert "PRE-INIT" in src
    assert "0x800776AC" in src, "the repeat-offender example must stay documented"


def test_registry_marks_d16_bounded_exhausted():
    r = rows()["D16_thumper"]
    assert "ARENA CLOSED" in " ".join(r["bindings"])
    assert "BOUNDED-EXHAUSTED" in r["next"]
    assert "recommend moving on" in r["next"].lower()
