"""Guards for the C05 (three success tokens) evidence, including the corrections it
forced in C04 and C17.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_c05_three_tokens.md.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c05_three_tokens.json"
C04 = ROOT / "analysis" / "phase4_c04_enemy_token.json"
C17 = ROOT / "analysis" / "phase4_c17_movie_viewer.json"
TOOL = ROOT / "tools" / "phase4_c05_tokens_static.c"
MARKER_TOOL = ROOT / "tools" / "phase4_c05_marker_stage.c"
LOCATE_TOOL = ROOT / "tools" / "phase4_c05_results_overlay_locate.c"
COUNTER_TOOL = ROOT / "tools" / "phase4_c05_counter_animation.c"
SEMI_TOOL = ROOT / "tools" / "phase4_c05_marker_semitransparency.c"
FLAG_TOOL = ROOT / "tools" / "phase4_c05_newly_earned_flag.c"
MEMORY_BIN = ROOT / "REBUILD" / "files" / "BITS" / "MEMORY.BIN"
FILES = ROOT / "REBUILD" / "files"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load(p):
    return json.loads(p.read_text())


def test_bit_map_is_complete_and_sums_to_seven():
    m = load(ARTIFACT)["TOKEN_BIT_MAP_C_PINNED_2026-08-03"]["mapping"]
    assert set(m) == {"bit_0x01", "bit_0x02", "bit_0x04"}
    assert 0x01 | 0x02 | 0x04 == 7
    assert "0x80090B80" in m["bit_0x01"] and "grain" in m["bit_0x01"]
    assert "0x800B3988" in m["bit_0x02"] and "FLIK" in m["bit_0x02"]
    assert "0x80090B68" in m["bit_0x04"] and "enemies" in m["bit_0x04"]


def test_c17_hedge_closed_and_third_axis_corrected():
    doc = load(ARTIFACT)["TOKEN_BIT_MAP_C_PINNED_2026-08-03"]["closes_c17_hedge"]
    assert "ENEMIES, not seeds" in doc
    # and C17 itself must carry the correction
    c17 = load(C17)
    corr = c17["CORRECTION_2026-08-03_third_axis_is_enemies_not_seeds"]
    assert "not proven bit-by-bit" in corr["what_was_hedged"]
    assert "0x04 = ENEMIES" in corr["now_proven"]
    assert "NOT seeds" in corr["now_proven"]


def test_c04_correction_is_explicit_in_both_artifacts():
    c05 = load(ARTIFACT)["CORRECTION_TO_C04_2026-08-03"]
    assert "WRONG" in c05["what_was_wrong"]
    assert "21" in c05["correct_value"]
    assert "still stands" in c05["what_still_stands"].lower() or "unaffected" in c05["what_still_stands"]
    c04 = load(C04)
    corr = c04["CORRECTION_2026-08-03_level01_quota_was_wrong"]
    assert "21" in corr["correct_value"]
    assert "0x80046c64" in corr["what_still_stands"]


def test_correction_cites_two_independent_precommitted_sources():
    """The correction must not rest on my own re-read alone."""
    c05 = load(ARTIFACT)["CORRECTION_TO_C04_2026-08-03"]["correct_value"]
    assert "phase2_lifecycle_oracle" in c05
    assert "21->22" in c05 or "21→22" in c05
    # and the oracle really does say 21
    oracle = json.loads((ROOT / "analysis" / "phase2_lifecycle_oracle.json").read_text())
    assert oracle["experiments"]["teleport_recovery"]["before"]["enemy_quota"] == 21


def test_counter_correspondence_flagged_as_inference_not_proof():
    c = load(ARTIFACT)["CORRECTION_TO_RESULTS_SCREEN_LABELING_2026-08-03"]
    assert "strong inference" in c["confidence"]
    assert "not instruction-traced" in c["confidence"]


def test_c_tool_compiles_and_pins_verify():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(EXE)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "25/25 OK" in r.stdout
        assert "bit 0x04  enemies" in r.stdout
    finally:
        os.remove(out)


def test_venue_correction_is_recorded_and_does_not_touch_the_bit_map():
    """2026-08-04: fcn.80051b84 is an in-world marker stage, not a results-screen
    renderer. The correction must be explicit, and the bit map must survive it."""
    c = load(ARTIFACT)["CORRECTION_2026-08-04_venue_was_wrong"]
    assert "BOTH CLAIMS ARE WRONG" in c["what_was_wrong"]
    assert "0x8004ECD4" in c["what_it_actually_is"]
    assert "TINT" in c["what_the_bit_actually_does"].upper()
    assert "0x0004C8FF" in c["what_the_bit_actually_does"]
    # the map itself must be asserted as unchanged, and C17's hedge still closed
    assert "unchanged" in c["what_is_unchanged"]
    assert "NOT seeds" in c["what_is_unchanged"]
    # and the results-screen renderers must be reopened, not left claimed
    assert "untraced" in load(ARTIFACT)["STILL_OPEN"]


def test_marker_tool_compiles_and_pins_the_corrected_reading():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(MARKER_TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(EXE)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "47/47 OK" in r.stdout
        assert "NOT a results-screen renderer" in r.stdout


    finally:
        os.remove(out)


def test_canon_page_was_renamed_away_from_the_wrong_name():
    fns = ROOT / "ObsidianVault" / "Canon" / "Functions"
    assert not (fns / "FUNC_80051B84_results_screen_token_renderer.md").exists()
    page = fns / "FUNC_80051B84_reward_token_marker_stage.md"
    assert page.exists()
    text = page.read_text()
    assert "published on 2026-08-03 under the wrong name" in text
    assert "0x8004ECD4" in text


def test_registry_rows_updated():
    text = REGISTRY.read_text()
    for rid, needle in [("C05_three_tokens", "TOKEN BIT MAP C-PINNED 2026-08-03"),
                        ("C05_three_tokens", "CORRECTION 2026-08-04"),
                        ("C04_enemy_token", "CORRECTION 2026-08-03")]:
        s = text.index(f"  - id: {rid}")
        e = text.index("\n  - id:", s + 10)
        block = text[s:e]
        assert needle in block, f"{rid} missing {needle}"
        row = yaml.safe_load("rows:\n" + block)["rows"][0]
        assert row["status"] == "partial"


def test_results_screen_evaluator_is_banked_with_the_three_conditions():
    """Item 1: the real results screen, found 2026-08-04. It is also the bit setter,
    which is what makes the enemies axis PROVEN rather than inferred."""
    r = load(ARTIFACT)["RESULTS_SCREEN_EVALUATOR_FOUND_2026-08-04"]
    conds = r["the_three_conditions_proven_by_construction"]
    assert "0x800A65A1" in conds["grain"] and "50" in conds["grain"]
    assert "0x800A65A2" in conds["flik"] and "0x0F" in conds["flik"]
    assert "0x800A658E" in conds["enemies"] and "== 0" in conds["enemies"]
    assert "PROVES" in conds["significance"]
    # the setter, and why C17 saw an atomic 0->7
    assert "ATOMICALLY" in r["what_it_actually_is"].upper()
    # provenance honesty: the overlay identity was NOT new
    assert "was already committed" in r["overlay_identity_was_already_committed"].lower() \
        or "NOT new" in r["overlay_identity_was_already_committed"]
    assert "level_complete_results_800b7da0.c" in r["overlay_identity_was_already_committed"]


def test_locate_tool_finds_exactly_one_overlay_and_pins_it():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(LOCATE_TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(FILES)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "BITS/MEMORY.BIN" in r.stdout
        assert "30/30 overlay pins OK" in r.stdout
        assert "The third axis is ENEMIES by construction" in r.stdout
        # exactly one block per bit -> one shipped overlay, not per-level copies
        for line in ("bit 0x01 blocks: 1", "bit 0x02 blocks: 1", "bit 0x04 blocks: 1"):
            assert line in r.stdout, line
    finally:
        os.remove(out)


def test_misnamed_canon_page_was_renamed_and_indexes_retargeted():
    fns = ROOT / "ObsidianVault" / "Canon" / "Functions"
    assert not (fns / "FUNC_800B7DA0_popcount8.md").exists()
    page = fns / "FUNC_800B7DA0_results_screen_evaluate_and_draw.md"
    assert page.exists()
    text = page.read_text()
    assert "popcount8" in text          # kept as an alias so old links resolve
    assert "BITS/MEMORY.BIN" in text
    idx = ROOT / "ObsidianVault" / "Canon" / "Indexes"
    for name in ("Address Index.md", "Canon Index.md"):
        assert "FUNC_800B7DA0_popcount8" not in (idx / name).read_text()


def test_counter_animation_is_banked_with_its_caveat():
    c = load(ARTIFACT)["COUNTER_ANIMATION_CLOSED_2026-08-04"]
    assert "30 Hz" in c["increment_law"]
    assert "DEFEATED" in c["three_numerators"]["enemies"]
    assert "0x800BE444" in c["three_numerators"]["flik"]
    # the universal-50 conclusion must rest on the literal glyphs, not a guess
    assert "LITERAL" in c["grain_denominator_is_universal"]
    assert "EVERY level" in c["grain_denominator_is_universal"]
    # fast-forward, not skip
    assert "SNAPPED" in c["skip_is_a_fast_forward_not_a_skip"]
    # the mutable-tail caveat must be stated, not quietly dropped
    assert "runtime-mutable tail" in c["popcount_table"]
    assert "Flagged, not asserted" in c["popcount_table"]


def test_counter_tool_pins_offline_against_memory_bin():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(COUNTER_TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(MEMORY_BIN)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "46/46 pins OK" in r.stdout
        assert "popcount(0..15) match: YES" in r.stdout
        assert "50 on EVERY level" in r.stdout
    finally:
        os.remove(out)


def test_item2_dimmed_token_confirmed_with_its_negative_control():
    c = load(ARTIFACT)["ITEM2_DIMMED_TOKEN_CONFIRMED_2026-08-04"]
    assert "0x800823E4 stayed 0" in c["state_result"]
    assert "42,185" in c["visual_result"]
    assert "ZERO" in c["visual_result"]          # row 3 = the built-in negative control
    assert "changed by exactly 0 pixels" in c["built_in_negative_control"]
    assert c["conclusion"].startswith("CONFIRMED")
    assert "no new fixture" in c["method"].lower()


def test_item3_tint_claim_is_retracted_not_quietly_softened():
    """The intermediate retraction must survive as history, even though it was
    later superseded -- the wrong-turn record is part of the evidence."""
    c = load(ARTIFACT)["ITEM3_MARKER_TINT_INCONCLUSIVE_2026-08-04"]
    assert "INFERENCE stated as fact" in c["what_was_overclaimed"]
    assert "0x8009E8E0" in c["what_was_overclaimed"]
    assert "PIXEL-IDENTICAL" in c["why_it_was_inconclusive"]


def test_item3_is_resolved_as_semitransparency_with_the_right_direction():
    c = load(ARTIFACT)["ITEM3_RESOLVED_2026-08-04_semitransparency_not_tint"]
    assert "ITEM3_MARKER_TINT_INCONCLUSIVE_2026-08-04" in c["supersedes"]
    assert "SEMI-TRANSPARENCY SELECTOR" in c["RESULT"]
    # direction matters and is easy to invert: already-earned => translucent
    assert "ALREADY earned" in c["RESULT"] and "SEMI-TRANSPARENT" in c["RESULT"]
    assert "OPAQUE" in c["RESULT"]
    # the search method, which is the transferable part
    assert "0x80082374" in c["how_it_was_found"]
    assert "0x80023ABC" in c["how_it_was_found"]
    assert "0x8009E8D0" in c["why_the_first_search_missed_it"]
    page = (ROOT / "ObsidianVault" / "Canon" / "Functions"
            / "FUNC_80051B84_reward_token_marker_stage.md").read_text()
    assert "semi-transparency selector" in page
    assert "0x8009E8D0" in page
    results = (ROOT / "ObsidianVault/Canon/Systems/SYS_level_results_screen.md").read_text()
    assert "read the same bits to tint a" not in results
    assert "earned markers are translucent" in results


def test_semitransparency_tool_pins_the_full_producer_to_consumer_chain():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(SEMI_TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(EXE)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "21/21 pins OK" in r.stdout
        assert "SEMI-TRANSPARENCY selector, not a tint" in r.stdout
        assert "OPAQUE marker" in r.stdout
    finally:
        os.remove(out)


def test_newly_earned_flag_is_the_save_trigger():
    c = load(ARTIFACT)["LAST_LOOSE_END_CLOSED_2026-08-04_newly_earned_flag_is_the_save_trigger"]
    assert "SAVE TRIGGER" in c["what_it_is"]
    assert "0x80055478" in c["what_it_is"] and "0x80055538" in c["what_it_is"]
    assert "0x8009EC68" in c["the_save_buffer"]
    # the replay consequence is the point, not a footnote
    assert "never set" in c["why_it_matters"] and "skips the entire save block" in c["why_it_matters"]
    # the wrong hypothesis must stay on the record
    assert "WRONG" in c["corrects_my_own_hypothesis"]
    assert "UNTESTED" in c["corrects_my_own_hypothesis"]


def test_flag_tool_pins_the_save_path():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(FLAG_TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(MEMORY_BIN)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "20/20 pins OK" in r.stdout
        assert "SAVE TRIGGER" in r.stdout
        assert "never saves" in r.stdout
    finally:
        os.remove(out)
