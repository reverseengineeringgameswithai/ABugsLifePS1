"""Guards for E13 (HUD and results screens), steps 1-3.

See ObsidianVault/Experiments/EXP_2026-08-04_phase4_e13_hud_results.md.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_e13_hud_results.json"
TOOL = ROOT / "tools" / "phase4_e13_ingame_hud.c"
ANIM_TOOL = ROOT / "tools" / "phase4_e13_hud_anim_phases.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load():
    return json.loads(ARTIFACT.read_text())


def test_census_correction_is_explicit_and_says_why_twice():
    c = load()["STEP1_INGAME_HUD_RENDERER_2026-08-04"]["census_name_is_wrong_twice"]
    assert "0x800526F4" in c and "0x800526FC" in c
    assert "not a function ENTRY" in c
    assert "FUNC_800B7DA0" in c and "0x8009B878" in c


def test_hud_renderer_identity_rests_on_caller_and_reads():
    s = load()["STEP1_INGAME_HUD_RENDERER_2026-08-04"]
    assert "0x8004ECD4" in s["what_it_is"] and "0x8004F3E4" in s["what_it_is"]
    for addr in ("0x800A65A1", "0x800A65A2", "0x800A658E", "0x80082258", "0x800A65A0"):
        assert addr in s["what_it_is"], addr
    assert "0x10-0x13" in s["flik_letters"]
    assert "Caller checked" in s["naming_discipline"]


def test_results_half_is_synthesis_and_answers_save_consequences():
    s = load()["STEP2_RESULTS_HALF_BY_SYNTHESIS_2026-08-04"]
    assert "No new work" in s["note"]
    ans = s["save_consequences_ANSWERED"]
    assert "0x800823E4" in ans and "SAVE TRIGGER" in ans
    assert "0x8009EC68" in ans
    assert "no save happens" in ans


def test_mode_selector_pinned_but_presentation_flagged_unknown():
    s = load()["STEP3_PANEL_MODE_SELECTOR_2026-08-04"]
    assert "0x800823A0" in s["finding"]
    assert "tile 54" in s["finding"] and "tile 55" in s["finding"]
    # the honest boundary must survive
    assert "Only the SELECTOR is pinned" in s["what_is_NOT_established"]
    assert "Flagged rather than asserted" in s["what_is_NOT_established"]


def test_row_is_bounded_exhausted_with_residuals_outside_scope():
    """Steps 1-5 close every question the row named."""
    st = load()["status"]
    assert "BOUNDED EXHAUSTED" in st
    assert "0x8004F478" in load()["STILL_OPEN"]


def test_boss_question_answered_by_an_exhaustive_global_set():
    s = load()["STEP5_PRESENTATION_CLOSED_2026-08-04"]["boss_question_answered_statically"]
    assert "COMPLETE global" in s["method"] and "not a sample" in s["method"]
    assert "NO BOSS-SPECIFIC INPUT" in s["result"]
    # the specific boss globals ruled out must be named, not hand-waved
    assert "0x80090BEE" in s["result"] and "0x800B4BA8" in s["result"]
    assert "artifact" in s["caveat"]


def test_tile55_variant_is_level_total_with_its_limits_stated():
    s = load()["STEP5_PRESENTATION_CLOSED_2026-08-04"]["tile55_variant_identified_live"]
    assert "level complete" in s["result"] and "LEVEL TOTAL" in s["result"]
    # the honest limits must survive: diff count is not the evidence, and it was forced
    assert "not the evidence" in s["honest_limit"]
    assert "forced latch" in s["honest_limit"] or "forcing the latch" in s["honest_limit"]


def test_hud_animation_phases_decoded_with_per_element_pairing():
    s = load()["STEP4_HUD_ANIMATION_PHASES_2026-08-04"]
    assert "0x800B0188" in s["closes"]
    per = s["per_element"]
    assert "0x800A65A0" in per["0x800B0188"] and "LIVES" in per["0x800B0188"]
    assert "0x800A65A1" in per["0x800B018C"] and "GRAIN" in per["0x800B018C"]
    # the third is explicitly NOT a latch -- easy to over-generalise
    assert "NOT a latch" in per["0x800B0190"]
    assert "RAMP" in per["0x800B0190"]
    assert "FOURTH instance" in s["fourth_instance_of_the_head_idiom"]


def test_anim_tool_pins():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(ANIM_TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(EXE)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "19/19 pins OK" in r.stdout
        assert "ANIMATION PHASE COUNTERS" in r.stdout
    finally:
        os.remove(out)


def test_tool_compiles_and_pins():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(EXE)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "22/22 pins OK" in r.stdout
        assert "IN-GAME HUD render stage" in r.stdout
    finally:
        os.remove(out)


def test_registry_row_updated_and_still_partial():
    text = REGISTRY.read_text()
    s = text.index("  - id: E13_hud_results")
    e = text.index("\n  - id:", s + 10)
    block = text[s:e]
    for needle in ("IN-GAME HUD RENDERER IDENTIFIED 2026-08-04",
                   "RESULTS HALF CLOSED BY SYNTHESIS FROM C05",
                   "PANEL-MODE SELECTOR PINNED 2026-08-04",
                   "HUD ANIMATION PHASES DECODED 2026-08-04",
                   "PRESENTATION CLOSED 2026-08-04"):
        assert needle in block, needle
    row = yaml.safe_load("rows:\n" + block)["rows"][0]
    assert row["status"] == "partial"
    assert "BOUNDED EXHAUSTED" in row["next"]
