#!/usr/bin/env python3
"""Measure F03_council_chamber's nine DoD dimensions against the bars AS WRITTEN.

Standard: `engineering-specs/phase4-measurement-standard-ruling.md`. Measurement is
per-dimension against each bar as written -- canonical item 2 asks the frontier be
ENUMERATED (scoped to relevant), the exit gate asks that anything unresolved be
EXPLICITLY BOUNDED (not absent), and "bounded-exhausted" is a STOP DECISION that never
counts as met. The exemplar this follows is
`tools/phase4_f01_written_bar_assessment.py`.

Design, copied from the exemplar:
  * every FACT is derived from a cited artifact at run time and the artifact is
    sha256-pinned, so a stale citation fails loudly instead of aging silently;
  * every JUDGMENT is authored and attributable, and carries `written_bar`, `basis`
    and `gap`;
  * `unmeasured` is a legitimate state -- absent evidence is reported as absent, never
    stretched to fill a cell;
  * this tool assesses. It does not promote, and it does not edit the registry.

Two extras over the exemplar, both cheap and both about not trusting prose:
  * the nine `written_bar` strings are PARSED from the roadmap hub's own
    "Definition of Done" list rather than paraphrased here, so the bar text is pinned
    to the page that owns it;
  * the two C pin tools this row rests on are recompiled and rerun (offline, no
    emulator) and their output hashes compared to the pins recorded on 2026-08-04.
    Compiled C owns instruction decoding; this file never decodes an instruction.

F03 note verified rather than assumed: the D16 campaign's correction -- 0x80090BEE is
the cinematic-camera FLAGS field, a caller-supplied argument, NOT a Thumper defeat
latch -- is confirmed from `analysis/phase4_d16_f03.json`, the baseline row's own
RETRACTED binding, and the recompiled pin tool. Boss mechanics closed in a D row do not
close this STAGE row's objective/layout claims, and the measurement below keeps them
apart.

Usage: python3 tools/phase4_f03_written_bar_assessment.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW_ID = "F03_council_chamber"

# The row's evidence surfaces, as the F-row census inventoried them plus the two
# vault pages the row's own artifact declares.
ROW_ARTIFACTS = (
    "analysis/phase4_d16_f03.json",
    "analysis/phase4_d16_f03_oracle.json",
    "analysis/phase4_d16_f03_trace.json",
    "analysis/phase4_d16_fight.json",
    "analysis/phase4_d16_arena.json",
    "analysis/phase4_f03_council_chamber.json",
    "analysis/phase4_f08_scene_binding.json",
)
ROW_VAULT_PAGES = (
    "ObsidianVault/Experiments/EXP_2026-08-04_phase4_f03_council_chamber.md",
    "ObsidianVault/Experiments/EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber.md",
)
ROW_CANON_PAGES = (
    "ObsidianVault/Canon/Systems/Thumper_boss_fight.md",
    "ObsidianVault/Canon/Systems/SYS_cinematic_camera.md",
)
RESIDENT_OVERLAY_IMAGE = "LEVEL02_LEVEL"          # index key
RESIDENT_OVERLAY_BLOB = "REBUILD/files/LEVEL02/LEVEL.BIN"
GOVERNING_FUNCTION = "level_completion_handler"
GOAL_LATCH = "0x800823a0"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(ROOT / "analysis/phase4_f03_written_bar_assessment.json"))
    args = ap.parse_args()

    pins: list[dict] = []
    facts: dict[str, object] = {}
    seen: set[str] = set()

    def pin(rel: str) -> Path:
        p = ROOT / rel
        if rel not in seen:
            seen.add(rel)
            pins.append({"path": rel, "sha256": sha256_file(p) if p.exists() else None,
                         **({} if p.exists() else {"exists": False})})
        return p

    def derive_json(rel: str) -> dict:
        return json.loads(pin(rel).read_text())

    def derive_text(rel: str) -> str:
        return pin(rel).read_text()

    # ------------------------------------------------------------------ the bars
    # Parsed from the page that owns them rather than paraphrased here.
    hub = derive_text("ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction "
                      "to Reliable Modding.md")
    block = hub.split("## Definition of Done for a solved subsystem", 1)[1]
    block = block.split("\n## ", 1)[0]
    dod_items: dict[int, str] = {}
    for m in re.finditer(r"^(\d)\. \*\*(.+?):\*\*\s*(.+?)(?=^\d\. \*\*|\Z)",
                         block, re.M | re.S):
        # the ninth item is followed by the section's closing paragraph; keep the
        # numbered item only (the closing sentence is measured separately).
        body = m.group(3).split("\n\n", 1)[0]
        dod_items[int(m.group(1))] = " ".join((m.group(2) + ": " + body).split())
    facts["dod_items_parsed"] = len(dod_items)
    facts["dod_no_single_demonstration_clause"] = (
        "Passing one demonstration" in block)
    BAR = {  # canonical ordinal -> our dimension key
        1: "original_oracle", 2: "complete_frontier", 3: "typed_state",
        4: "lifecycle", 5: "original_interfaces", 6: "campaign_breadth",
        7: "cross_system_behavior", 8: "source_closure", 9: "durable_evidence",
    }
    if sorted(dod_items) != list(range(1, 10)):
        print("FATAL: could not parse the nine written bars from the roadmap hub",
              file=sys.stderr)
        return 2
    pin("engineering-specs/phase4-measurement-standard-ruling.md")
    pin("engineering-specs/phase4-item2-bar-ruling.md")

    # ------------------------------------------- durable_evidence: carried forward
    census = derive_json("analysis/phase4_f_row_measured_census.json")
    crow = census["rows"][ROW_ID]
    facts["census_durable_state"] = crow["durable_evidence"]["state"]
    facts["census_durable_fraction"] = crow["durable_evidence"]["intact_pinned"]
    facts["census_declared_fixtures"] = [f["path"] for f in
                                         crow["durable_evidence"]["fixtures"]]
    facts["census_analysis_artifacts"] = len(
        crow["evidence_inventory"]["analysis_artifacts"])
    facts["census_vault_pages"] = len(crow["evidence_inventory"]["vault_pages"])
    facts["census_source_files"] = len(crow["evidence_inventory"]["source_files"])
    facts["census_source_closure_triage"] = crow["measurability_triage"]["source_closure"]
    facts["census_baseline_sha256"] = census["baseline_sha256"]

    # ------------------------------------------------------- the baseline row text
    baseline_p = pin("analysis/mechanics_baseline.yaml")
    brow = next(r for r in yaml.safe_load(baseline_p.read_text())["rows"]
                if r["id"] == ROW_ID)
    bindings_text = " ".join(brow["bindings"])
    facts["baseline_row_status"] = brow["status"]
    facts["baseline_bindings"] = len(brow["bindings"])
    facts["baseline_declared_fixtures"] = len(brow["fixture_have"])
    facts["baseline_records_80090bee_retraction"] = bool(
        "RETRACTED" in bindings_text and "0x80090BEE" in bindings_text
        and "cinematic-camera FLAGS" in bindings_text)
    facts["baseline_missing_still_lists_0x80082388"] = "0x80082388" in brow["missing"]
    facts["baseline_still_requests_interpreter_retake"] = (
        "Interpreter-recorded re-take" in brow["fixture_need"])
    facts["baseline_sha256_matches_census_pin"] = (
        sha256_file(baseline_p) == census["baseline_sha256"])

    # ------------------------------------------------- the row's evidence artifact
    f03 = derive_json("analysis/phase4_f03_council_chamber.json")
    facts["f03_status"] = f03["status"]
    facts["f03_closure"] = f03["closure"]
    facts["f03_disposition"] = f03["disposition"]
    scen = f03["full_stage_scenario"]
    facts["f03_scenario_status"] = scen["status"]
    facts["f03_scenario_assertions_passed"] = scen["assertions_passed"]
    facts["f03_scenario_assertions_failed"] = scen["assertions_failed"]
    facts["f03_scenario_report_retained"] = Path(scen["report_path"]).exists()
    facts["f03_damage_commits_observed"] = \
        scen["observations"]["completion"]["generic_damage_commit_hits"]
    facts["f03_damage_threshold_asserted"] = \
        scen["observations"]["completion"]["threshold_assertion"]
    facts["f03_goal_store_hits"] = scen["observations"]["completion"]["goal_store_hits"]
    facts["f03_results_entry_hits"] = \
        scen["observations"]["completion"]["results_entry_hits"]
    facts["f03_results_finalizer_hits"] = \
        scen["observations"]["completion"]["results_finalizer_hits"]
    facts["f03_bounded_residuals"] = len(f03["bounded_residuals_outside_row_scope"])
    facts["f03_self_claimed_met_dimensions"] = sum(
        1 for v in f03["phase4_metrics"].values() if str(v).startswith("met"))
    facts["f03_self_claimed_dimensions"] = len(f03["phase4_metrics"])
    facts["f03_cold_boot_requirement"] = f03["cold_boot_requirement"]
    stage_movie = f03["identities"]["full_stage_movie"]
    facts["f03_stage_movie_frames"] = stage_movie["frames"]
    facts["f03_stage_movie_version"] = stage_movie["movie_version"]
    facts["f03_stage_movie_execution_mode"] = stage_movie["execution_mode"]
    facts["f03_stage_movie_armed_while_paused"] = stage_movie["armed_while_paused"]
    facts["f03_stage_movie_anchor_frame"] = stage_movie["anchor_frame"]

    # prior-evidence chain and tool pins, re-checked byte for byte
    chain = {k: (sha256_file(ROOT / k) == v if (ROOT / k).exists() else None)
             for k, v in f03["prior_evidence_hashes"].items()}
    facts["prior_evidence_hashes_checked"] = len(chain)
    facts["prior_evidence_hashes_matching"] = sum(1 for v in chain.values() if v)
    tool_pins = {
        f03["c_static_verification"]["camera_exit_tool"]["path"]:
            f03["c_static_verification"]["camera_exit_tool"]["source_sha256"],
        f03["c_static_verification"]["fight_species_tool"]["path"]:
            f03["c_static_verification"]["fight_species_tool"]["source_sha256"],
        scen["path"]: scen["sha256"],
    }
    facts["tool_and_scenario_pins_checked"] = len(tool_pins)
    facts["tool_and_scenario_pins_matching"] = sum(
        1 for k, v in tool_pins.items()
        if (ROOT / k).exists() and sha256_file(ROOT / k) == v)

    # ---------------------------------------------------- D16 frontier census facts
    d16 = derive_json("analysis/phase4_d16_f03.json")
    cam = d16["FINDING_0x80090BEE_IS_THE_CINEMATIC_CAMERA_FLAGS_FIELD"]
    facts["camflags_is_cinematic_camera_field"] = cam["what_it_is"].startswith(
        "the FLAGS halfword")
    facts["camflags_value2_is_caller_argument"] = (
        "CALLER-SUPPLIED argument" in cam["why_the_value_2_is_not_a_defeat_code"])
    facts["camflags_writers_enumerated"] = len(cam["writers"])
    facts["camflags_readers_enumerated"] = len(cam["readers"])
    facts["camflags_dataflow_hits"] = len(d16["census_0x80090BEE"]["dataflow_hits"])
    facts["camflags_immediate_candidates"] = \
        d16["census_0x80090BEE"]["immediate_candidates"]
    facts["camflags_false_positives_resolved"] = len(
        d16["census_0x80090BEE"]["immediate_false_positives_resolved_elsewhere"])
    facts["camflags_census_second_implementation_agrees"] = \
        d16["second_implementation_agrees"]
    facts["camflags_census_disagreements"] = d16["disagreements"]
    facts["camflags_census_declared_blind_spot"] = \
        d16["census_0x80090BEE"]["known_blind_spot"]
    facts["exit_is_a_different_store"] = \
        d16["FINDING_THE_LEVEL_EXIT_IS_A_DIFFERENT_STORE"]["the_level_exit"]
    facts["exit_no_path_from_the_flags_word"] = \
        d16["FINDING_THE_LEVEL_EXIT_IS_A_DIFFERENT_STORE"]["no_path_from_the_flags_word"]

    # ------------------------------------------------------------- the poll oracle
    orc = derive_json("analysis/phase4_d16_f03_oracle.json")
    facts["oracle_checks"] = len(orc["checks"])
    facts["oracle_checks_passed"] = sum(1 for c in orc["checks"].values() if c["pass"])
    facts["oracle_pass"] = orc["pass"]
    facts["oracle_execution_mode"] = orc["execution_mode"]
    facts["oracle_from_boot"] = orc["from_boot"]
    facts["oracle_frames"] = orc["frames"]
    facts["oracle_distinct_states"] = orc["distinct_states"]
    facts["oracle_scene_timeline"] = orc["scene_timeline"]
    facts["oracle_hp_min_max"] = [orc["hp_min"], orc["hp_max"]]

    # ------------------------------------------------------------- the armed trace
    tr = derive_json("analysis/phase4_d16_f03_trace.json")
    facts["trace_watches"] = len(tr["watches"])
    facts["trace_frames"] = tr["frames"]
    facts["trace_event_total"] = tr["event_total"]
    facts["trace_ring_truncated"] = tr["ring_truncated"]
    facts["trace_execution_mode"] = tr["execution_mode"]
    full = [a for a, v in tr["by_address"].items()
            if v["writes"] == len(v["value_sequence"])]
    sampled = [a for a, v in tr["by_address"].items()
               if v["writes"] > len(v["value_sequence"])]
    facts["trace_fields_with_complete_value_sequence"] = len(full)
    facts["trace_fields_sampled_only"] = len(sampled)
    facts["trace_sampled_only_addresses"] = sorted(sampled)
    facts["trace_goal_latch_writes"] = tr["by_address"]["0x800823A0"]["writes"]
    facts["trace_goal_latch_writer_pcs"] = tr["by_address"]["0x800823A0"]["writer_pcs"]
    facts["trace_hp_writes"] = tr["by_address"]["0x8009FE72"]["writes"]
    facts["trace_hp_arc_verdict"] = \
        tr["findings"]["BONUS_hp_arc_at_instruction_level"]["verdict"]
    facts["trace_0x80082388_verdict"] = tr["findings"]["Q2_what_0x80082388_is"]["verdict"]

    # ------------------------------------------------------------ fight and arena
    fight = derive_json("analysis/phase4_d16_fight.json")
    facts["fight_fields_watched"] = len(fight["watched"])
    facts["fight_fields_never_written"] = len(fight["never_written"])
    facts["fight_ring_truncated"] = fight["ring_truncated"]
    vd = fight["verdicts_on_the_archived_note"]
    facts["fight_archived_note_verdicts"] = {
        "confirmed": sum(1 for k in vd if k.startswith("CONFIRMED")),
        "refuted": sum(1 for k in vd if k.startswith("REFUTED")),
        "not_confirmed": sum(1 for k in vd if k.startswith("NOT_CONFIRMED")),
        "resolved": sum(1 for k in vd if k.startswith("RESOLVED")),
    }
    arena = derive_json("analysis/phase4_d16_arena.json")
    facts["arena_predicted_bound"] = arena["predicted_max_offset_from_anchor"]
    facts["arena_observed_max"] = arena["max_observed_offset"]
    facts["arena_target_samples"] = arena["target_samples"]

    # ------------------------------------------------------- the declarative scenario
    scn = yaml.safe_load(pin("tools/scenarios/duckstation/phase4_f03_council_chamber.yaml")
                         .read_text())
    assertions = [a["id"] for ph in scn["phases"] for a in ph["assertions"]]
    facts["scenario_phases"] = len(scn["phases"])
    facts["scenario_assertions"] = len(assertions)
    facts["scenario_assertion_ids"] = assertions
    facts["scenario_exec_trace_pcs"] = sorted(
        hex(a["pc"]) for ph in scn["phases"] for a in ph.get("after", [])
        if a["type"] == "exec_trace_start")
    facts["scenario_requires_reproducible"] = scn["playback"]["require_reproducible"]
    facts["scenario_loads_start_state"] = scn["playback"]["load_start_state"]
    facts["scenario_disc_pin_matches_row_identity"] = (
        scn["target"]["expected_sha256"] == f03["identities"]["retail_cue_sha256"])
    facts["scenario_asserted_scene_id"] = next(
        a["expected"] for ph in scn["phases"] for a in ph["assertions"]
        if a.get("semantic_id") == "original.current_scene_id")

    # --------------------------------- the C pin tools, recompiled and rerun offline
    def rerun_c(src: str, argv: list[str], pinned_out: str) -> dict:
        out: dict[str, object] = {"source": src, "pinned_output_sha256": pinned_out}
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "tool"
            cc = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                                 str(ROOT / src), "-o", str(exe)],
                                capture_output=True, text=True)
            out["compiled"] = cc.returncode == 0
            if cc.returncode != 0:
                out["compile_stderr_tail"] = cc.stderr.strip().splitlines()[-1:] or None
                return out
            run = subprocess.run([str(exe), *argv], cwd=ROOT,
                                 capture_output=True, text=True)
            out["exit_code"] = run.returncode
            out["output_sha256"] = hashlib.sha256(run.stdout.encode()).hexdigest()
            out["output_matches_pin"] = out["output_sha256"] == pinned_out
            m = re.search(r"(\d+)/(\d+) pins OK", run.stdout)
            out["pins_ok"] = f"{m.group(1)}/{m.group(2)}" if m else None
            out["resident_overlay_pin_lines"] = sum(
                1 for line in run.stdout.splitlines()
                if line.strip().startswith("ok") and "LEVEL02/LEVEL.BIN" in line)
        return out

    if subprocess.run(["which", "cc"], capture_output=True).returncode == 0:
        facts["c_camera_exit_recheck"] = rerun_c(
            "tools/phase4_d16_f03_static.c", [],
            f03["c_static_verification"]["camera_exit_tool"]["output_sha256"])
        facts["c_fight_species_recheck"] = rerun_c(
            "tools/phase4_d16_fight_static.c", ["REBUILD/files/SCUS_942.88"],
            f03["c_static_verification"]["fight_species_tool"]["output_sha256"])
    else:
        facts["c_camera_exit_recheck"] = {"status": "unavailable: no cc on PATH"}
        facts["c_fight_species_recheck"] = {"status": "unavailable: no cc on PATH"}

    # ------------------------------- fixtures: declared vs pinned-and-name-matching
    fixset = derive_json("analysis/phase0_2_external_fixture_set.json")["entries"]
    declared = set(facts["census_declared_fixtures"])
    cited = {stage_movie["path"], stage_movie["save_path"],
             f03["identities"]["boss_trace_movie"]["path"],
             f03["identities"]["boss_trace_movie"]["save_path"]}
    # name-matched: the movie corpus names runs by STAGE ordinal, a convention the
    # Phase-2 completion oracle pins independently below (LEVEL03 -> target_scene 2).
    named = {k for k in fixset
             if re.search(r"CouncilChamber|thumper", k, re.I)}
    candidates = sorted(declared | cited | named)

    def fixture_row(relpath: str) -> dict:
        p = ROOT / relpath
        ent = fixset.get(relpath)
        ok = bool(p.exists() and ent and ent.get("sha256")
                  and sha256_file(p) == ent["sha256"])
        return {"path": relpath, "exists": p.exists(), "centrally_pinned": bool(ent),
                "bytes_match_pin": ok,
                "declared_by_row": relpath in declared,
                "cited_by_row_artifact": relpath in cited}

    fixtures = [fixture_row(c) for c in candidates]
    facts["stage_fixtures_examined"] = len(fixtures)
    facts["stage_fixtures_intact"] = sum(1 for f in fixtures if f["bytes_match_pin"])
    facts["stage_fixtures_declared_by_row"] = sum(1 for f in fixtures
                                                  if f["declared_by_row"])
    facts["stage_fixtures_cited_by_row_artifact"] = sum(1 for f in fixtures
                                                        if f["cited_by_row_artifact"])
    facts["stage_fixtures_intact_but_unregistered"] = sorted(
        f["path"] for f in fixtures
        if f["bytes_match_pin"] and not f["declared_by_row"]
        and not f["cited_by_row_artifact"])
    facts["unregistered_movie_fixture_paths"] = [
        p for p in facts["stage_fixtures_intact_but_unregistered"]
        if p.endswith(".movie.json")]
    facts["stage_fixture_detail"] = fixtures

    # -------------------------------------- the cold-boot fixture nobody registered
    p2 = derive_json("analysis/phase2_completion_oracle.json")
    st = p2["stages"]["stage03_council_chamber"]
    cb_rel = st["movie"]
    cb = json.loads(pin(cb_rel).read_text())
    facts["coldboot_movie"] = cb_rel
    facts["coldboot_target_scene"] = st["target_scene"]
    facts["coldboot_frames"] = st["frames"]
    facts["coldboot_pristine_replay_accepted"] = st["pristine_replay_accepted"]
    facts["coldboot_entered_stage_frame"] = st["entered_stage_frame"]
    facts["coldboot_stage_exited_by_movie_end"] = st["stage_exited_by_movie_end"]
    facts["coldboot_scene_timeline"] = [b["scene"] for b in st["scene_timeline"]]
    facts["coldboot_movie_declares_from_boot"] = cb["start_state"]["from_boot"]
    facts["coldboot_movie_hash_matches_oracle_and_central_pin"] = (
        sha256_file(ROOT / cb_rel) == st["movie_sha256"]
        == (fixset.get(cb_rel) or {}).get("sha256"))
    facts["coldboot_last_in_stage_snapshot_keys"] = sorted(st["last_in_stage"]["snapshot"])
    row_text = "".join((ROOT / a).read_text() for a in ROW_ARTIFACTS) + \
               "".join((ROOT / v).read_text() for v in ROW_VAULT_PAGES)
    facts["coldboot_movie_cited_by_row_evidence"] = cb_rel in row_text
    facts["coldboot_asserts_row_mechanism"] = any(
        tok in json.dumps(st) for tok in ("0x800823A0", "0x8009FE72", "thumper"))
    # bound to THIS row by scene id, not by filename: the corpus names runs by STAGE
    # ordinal while disc dirs are keyed by SCENE id, and for stages 2/3 they cross.
    facts["coldboot_scene_matches_row_scene"] = (
        st["target_scene"] == facts["scenario_asserted_scene_id"])
    f08 = derive_json("analysis/phase4_f08_scene_binding.json")
    dirmap = {str(k): v for k, v in f08["scene_id_to_level_data_dir"].items()}
    facts["stage_ordinal_vs_disc_dir"] = {
        s: {"target_scene": p2["stages"][s]["target_scene"],
            "level_data_dir": dirmap[str(p2["stages"][s]["target_scene"])]}
        for s in ("stage02_tunnels", "stage03_council_chamber")}
    facts["stage_and_disc_dir_numbering_cross"] = (
        p2["stages"]["stage02_tunnels"]["target_scene"] == 3
        and p2["stages"]["stage03_council_chamber"]["target_scene"] == 2)

    # ----------------------- the exit latch's corpus-wide frontier (owned by F01)
    fres = derive_json("analysis/phase4_f01_frontier_result.json")
    facts["latch_frontier_universe"] = {
        k: v["enumerated_records"] for k, v in fres["universe"]["categories"].items()}
    facts["latch_frontier_images"] = fres["universe"]["images"]
    facts["latch_frontier_image_census_complete"] = fres["universe"]["image_census_complete"]
    fresolve = derive_json("analysis/phase4_f01_frontier_resolve.json")
    facts["latch_corpus_accesses_examined"] = fresolve["corpus"]["memory_accesses_examined"]
    facts["latch_corpus_extents"] = fresolve["corpus"]["extents"]
    facts["latch_corpus_unresolved_store_sites"] = \
        fresolve["corpus"]["unresolved_store_sites"]
    facts["latch_window_touching_unresolved_store_sites"] = \
        fresolve["UNRESOLVED_STORE_SITES"]
    facts["latch_corpus_new_writers_found"] = \
        fresolve["corpus"]["resolved_writers_not_previously_enumerated"]
    hits = fresolve["resolved_hits"]
    facts["latch_resolved_store_sites"] = sum(
        1 for h in hits if h["store"] and h["ea"] == GOAL_LATCH)
    own = [h for h in hits if h["image"] == RESIDENT_OVERLAY_IMAGE]
    facts["latch_accesses_in_resident_overlay"] = len(own)
    facts["latch_f03_exit_store_enumerated"] = any(
        h["pc"] == "0x800b4190" and h["store"] and h["already_enumerated"] for h in own)
    facts["latch_resident_overlay_access_pcs"] = [
        {"pc": h["pc"], "ea": h["ea"], "store": h["store"], "function": h["function"]}
        for h in own]
    facts["latch_frontier_cited_by_row_evidence"] = "phase4_f01_frontier" in row_text
    facts["latch_writer_set_completeness_claim"] = fresolve["claim"]

    # ------------------------- the resident overlay's own code universe (denominator)
    idx = derive_json("analysis/functions.json")
    recs = [f for f in idx["functions"] if f.get("overlay") == RESIDENT_OVERLAY_IMAGE]
    code = [f for f in recs if f["range_type"] == "code"]
    blob = pin(RESIDENT_OVERLAY_BLOB)
    facts["resident_overlay_blob_bytes"] = blob.stat().st_size
    facts["resident_overlay_index_records"] = len(recs)
    facts["resident_overlay_code_records"] = len(code)
    facts["resident_overlay_code_bytes"] = sum(f["size"] for f in code)
    gov = next(f for f in code if f["name"] == GOVERNING_FUNCTION)
    facts["governing_function"] = GOVERNING_FUNCTION
    facts["governing_function_extent"] = [gov["start"], gov["end"]]
    facts["governing_function_instructions"] = gov["size"] // 4
    # VA containment only: region A is a shared swap buffer, so an address does NOT
    # by itself prove which blob it belongs to. Counted as citations in the window.
    cited_addrs = {int(x, 16) for x in re.findall(r"0x800[bB][0-9a-fA-F]{4}", row_text)}
    facts["row_cited_overlay_window_addresses"] = len(cited_addrs)
    per_record = {}
    for f in code:
        s, e = int(f["start"], 16), int(f["end"], 16)
        per_record[f["name"]] = sum(1 for a in cited_addrs if s <= a < e)
    facts["row_cited_addresses_by_code_record"] = per_record
    facts["resident_overlay_code_records_never_cited"] = sum(
        1 for n, c in per_record.items() if c == 0)

    # ------------------------------------------------- source closure, measured
    # The F-row census looked only at src_re/ and asm/hand_written/ and concluded
    # "no byte-matched source registered". The OVERLAY track is a separate registry
    # (config/overlays.yml -> src/overlays/, built by tools/build_overlay.py), and it
    # does hold one validated match in this row's resident blob. Measure that, and
    # record the correction rather than repeating the census string.
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True).stdout.split()
    ovl_cfg = yaml.safe_load(pin("config/overlays.yml").read_text())
    ovl_entry = ovl_cfg["overlays"][RESIDENT_OVERLAY_IMAGE]
    prog = derive_json("analysis/overlay_decomp_progress.json")
    res = next(r for r in prog["results"] if r["overlay"] == RESIDENT_OVERLAY_IMAGE)
    sha1 = hashlib.sha1()
    with blob.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            sha1.update(c)
    facts["overlay_track_registry"] = "config/overlays.yml"
    facts["overlay_track_blob_pin_matches_disc"] = sha1.hexdigest() == ovl_entry["sha1"]
    facts["overlay_track_rebuild_validated"] = res["validated"]
    facts["overlay_track_rebuilt_sha1_equals_pin"] = res["rebuilt_sha1"] == res["sha1"]
    facts["overlay_track_matched_functions"] = res["matched_functions"]
    facts["overlay_track_total_functions"] = \
        prog["per_overlay_totals"][RESIDENT_OVERLAY_IMAGE]
    facts["overlay_track_matched_bytes"] = sum(a["bytes"] for a in res["attempted"]
                                               if a["matched"])
    facts["overlay_track_matched_sources"] = [a["source"] for a in res["attempted"]
                                              if a["matched"]]
    facts["overlay_track_matched_covers_governing_function"] = any(
        int(gov["start"], 16) <= int(a["start"], 16) < int(gov["end"], 16)
        for a in res["attempted"] if a["matched"])
    facts["overlay_track_campaign_wide_matched_pct"] = prog["matched"]["pct_functions"]
    facts["census_triage_understates_source_closure"] = bool(
        res["matched_functions"] > 0
        and "no byte-matched source" in facts["census_source_closure_triage"])
    # why an address is not an attribution: same VA window, different blobs
    src_pool = [f for f in tracked if f.startswith(("src_re/", "asm/hand_written/"))]
    va_cited = [f for f in src_pool
                if re.search(r"0x800[bB]4[0-9a-fA-F]{3}", (ROOT / f).read_text(errors="ignore"))]
    facts["source_files_in_re_pool"] = len(src_pool)
    facts["re_pool_files_citing_the_shared_region_a_window"] = len(va_cited)
    facts["re_pool_files_naming_this_overlay"] = sum(
        1 for f in src_pool
        if RESIDENT_OVERLAY_IMAGE in (ROOT / f).read_text(errors="ignore")
        or RESIDENT_OVERLAY_BLOB.split("files/")[-1] in (ROOT / f).read_text(errors="ignore"))

    # ------------------------------------------- lifecycle phases nobody evidenced
    low = row_text.lower()
    facts["lifecycle_phase_token_hits"] = {
        tok: low.count(tok) for tok in
        ("death", "respawn", "game over", "reload", "retry", "pause menu")}
    facts["registered_movie_fixtures_for_row"] = sum(
        1 for f in fixtures if f["bytes_match_pin"] and ".movie.json" in f["path"]
        and (f["declared_by_row"] or f["cited_by_row_artifact"]))
    facts["unregistered_movie_fixtures_for_row"] = sum(
        1 for f in fixtures if f["bytes_match_pin"] and ".movie.json" in f["path"]
        and not (f["declared_by_row"] or f["cited_by_row_artifact"]))

    # --------------------------------------- what the control plane has registered
    debt = derive_json("analysis/phase4_closure_debt.json")
    drow = next(r for r in debt["rows"] if r.get("row_id") == ROW_ID)
    facts["ledger_dimension_states"] = sorted(
        {d["state"] for d in drow["dimensions"].values()})
    facts["ledger_dimension_basis"] = sorted(
        {d["basis"] for d in drow["dimensions"].values()})
    facts["ledger_met_count"] = drow["counts"]["met"]
    facts["ledger_movie_count"] = drow["movie_count"]
    facts["ledger_prior_offline_analysis_count"] = drow["prior_offline_analysis_count"]
    d16row = next(r for r in debt["rows"] if r.get("row_id") == "D16_thumper")
    facts["d16_ledger_met_count"] = d16row["counts"]["met"]
    facts["d16_ledger_next_action_is_bounded_exhausted"] = \
        d16row["next_action"].startswith("BOUNDED-EXHAUSTED")

    # -------------------------------- durable evidence surfaces beyond the fixtures
    canon_text = "".join(pin(c).read_text() for c in ROW_CANON_PAGES)
    facts["canon_pages_for_row"] = len(ROW_CANON_PAGES)
    facts["canon_records_the_exit_store"] = "0x800B4190" in canon_text
    facts["canon_records_the_camflags_correction"] = (
        "not a Thumper variable" in canon_text or "cinematic" in canon_text.lower())
    for v in ROW_VAULT_PAGES:
        pin(v)
    facts["row_evidence_files_git_tracked"] = sum(
        1 for f in (*ROW_ARTIFACTS, *ROW_VAULT_PAGES, *ROW_CANON_PAGES,
                    "tools/phase4_d16_f03_static.c", "tools/phase4_d16_fight_static.c",
                    "tools/scenarios/duckstation/phase4_f03_council_chamber.yaml")
        if f in tracked)

    # ============================ authored judgments against the WRITTEN bars =====
    cc_ok = facts["c_camera_exit_recheck"].get("output_matches_pin")
    cf_ok = facts["c_fight_species_recheck"].get("output_matches_pin")
    dims = {
        "durable_evidence": {
            "state": facts["census_durable_state"],
            "written_bar": dod_items[9],
            "basis": f"MEASURED by the F-row census and carried forward: "
                     f"{facts['census_durable_fraction']} declared fixtures exist, are "
                     f"centrally pinned and byte-match. Re-verified here: "
                     f"{facts['prior_evidence_hashes_matching']}/"
                     f"{facts['prior_evidence_hashes_checked']} prior-evidence hashes "
                     f"still match, {facts['tool_and_scenario_pins_matching']}/"
                     f"{facts['tool_and_scenario_pins_checked']} tool/scenario source "
                     f"pins match, and both C pin tools recompile -Werror and reproduce "
                     f"their pinned output hashes byte-identically "
                     f"(camera/exit {cc_ok}, fight/species {cf_ok}). Canon holds the "
                     f"corrected behaviour ({facts['canon_pages_for_row']} pages, exit "
                     f"store present: {facts['canon_records_the_exit_store']}), "
                     f"Experiments hold {facts['census_vault_pages']} reproduction "
                     f"pages, and {facts['row_evidence_files_git_tracked']} evidence "
                     f"files are git-tracked",
            "gap": f"the passing scenario's report is NOT retained "
                   f"(retained={facts['f03_scenario_report_retained']}; transient /tmp "
                   f"per AGENTS.md, so the "
                   f"{facts['f03_scenario_assertions_passed']}/"
                   f"{facts['scenario_assertions']} pass is re-verifiable only by "
                   f"replay), and the row DECLARES "
                   f"{facts['stage_fixtures_declared_by_row']} fixtures while its own "
                   f"evidence additionally rests on "
                   f"{facts['stage_fixtures_cited_by_row_artifact']} more pinned files "
                   f"cited only inside the artifact. Neither moves the measured "
                   f"fraction; both are registration debt",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": dod_items[1],
            "basis": f"deterministic reproduction, media identity and observable "
                     f"assertions are all present and none of them injects state: the "
                     f"declarative scenario passes "
                     f"{facts['f03_scenario_assertions_passed']}/"
                     f"{facts['f03_scenario_assertions_passed'] + facts['f03_scenario_assertions_failed']} "
                     f"assertions over {facts['scenario_phases']} phases with "
                     f"require_reproducible={facts['scenario_requires_reproducible']} "
                     f"and the disc pinned to the row's own retail hash "
                     f"({facts['scenario_disc_pin_matches_row_identity']}), and the "
                     f"independent poll oracle passes {facts['oracle_checks_passed']}/"
                     f"{facts['oracle_checks']} checks over "
                     f"{facts['oracle_frames']} frames. But the written bar says "
                     f"COLD-BOOT, and both fixtures are state-anchored "
                     f"(stage movie anchor frame {facts['f03_stage_movie_anchor_frame']}; "
                     f"poll oracle from_boot={facts['oracle_from_boot']}). The row's "
                     f"artifact answers this by decision, not by evidence: "
                     f"\"{facts['f03_cold_boot_requirement']}\"",
            "gap": f"a cold-boot fixture for THIS stage already exists, is pinned and "
                   f"byte-matches ({facts['coldboot_movie']}, from_boot="
                   f"{facts['coldboot_movie_declares_from_boot']}, "
                   f"{facts['coldboot_frames']} frames, target_scene "
                   f"{facts['coldboot_target_scene']} = the scene id this row's own "
                   f"scenario asserts "
                   f"({facts['coldboot_scene_matches_row_scene']}, so the binding is by "
                   f"scene id, not by filename), scene timeline "
                   f"{facts['coldboot_scene_timeline']}, pristine_replay_accepted="
                   f"{facts['coldboot_pristine_replay_accepted']}) and no F03/D16 "
                   f"evidence surface cites it "
                   f"(cited={facts['coldboot_movie_cited_by_row_evidence']}). Its "
                   f"registered assertions are the generic Phase-2 completion snapshot, "
                   f"not this row's HP/latch mechanism "
                   f"(asserts_row_mechanism="
                   f"{facts['coldboot_asserts_row_mechanism']}). Replaying the row's "
                   f"poll-safe assertions against it is the named, cheap path to met; "
                   f"it is a v3 CachedInterpreter-era movie, so poll-only",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": dod_items[2],
            "bar_reading": "per engineering-specs/phase4-measurement-standard-ruling.md: "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved "
                           "set; residuals explicitly bounded, not absent",
            "basis": f"two of the row's decisive addresses have enumerated frontiers. "
                     f"(a) The cinematic-camera flags word: dual-implemented census "
                     f"(C + independent Python, sets compared, agree="
                     f"{facts['camflags_census_second_implementation_agrees']}, "
                     f"disagreements={facts['camflags_census_disagreements']}) over the "
                     f"EXE plus every level/MEMORY overlay image, "
                     f"{facts['camflags_writers_enumerated']} writers + "
                     f"{facts['camflags_readers_enumerated']} readers, "
                     f"{facts['camflags_false_positives_resolved']} immediate false "
                     f"positives resolved, and a DECLARED blind spot "
                     f"(\"{facts['camflags_census_declared_blind_spot']}\") -- which is "
                     f"what closes the note's question: the value 2 is a caller "
                     f"argument and no consumer of the flags word touches the exit "
                     f"path. (b) The exit latch itself is enumerated CORPUS-WIDE by "
                     f"F01's frontier artifacts -- "
                     f"{facts['latch_frontier_universe']} across "
                     f"{facts['latch_frontier_images']} images -- and F03's own store "
                     f"0x800b4190 appears there as an already-enumerated writer inside "
                     f"{GOVERNING_FUNCTION} "
                     f"(enumerated={facts['latch_f03_exit_store_enumerated']}), with "
                     f"{facts['latch_accesses_in_resident_overlay']} accesses in the "
                     f"resident overlay. The residual is explicitly bounded and "
                     f"quantified: {facts['latch_corpus_unresolved_store_sites']} "
                     f"unresolved corpus stores, "
                     f"{facts['latch_window_touching_unresolved_store_sites']} of them "
                     f"window-touching, image_census_complete="
                     f"{facts['latch_frontier_image_census_complete']}",
            "gap": f"what is NOT enumerated is the row's own STAGE frontier. The "
                   f"governing function is {facts['governing_function_instructions']} "
                   f"instructions and the row's evidence cites "
                   f"{per_record[GOVERNING_FUNCTION]} addresses inside it (VA "
                   f"containment only -- region A is a shared swap buffer, so an "
                   f"address does not prove a blob); "
                   f"{facts['resident_overlay_code_records_never_cited']} of "
                   f"{facts['resident_overlay_code_records']} code records in the "
                   f"resident overlay are never cited at all; the fight owner is named "
                   f"only as \"shared mover VM plus overlay logic\"; one branch INSIDE "
                   f"the governing block (0x800B4158, gated on [0x800A6597]==3) is an "
                   f"open residual; and the baseline row's own `missing` says the "
                   f"stage's route/collectibles/hazards are unaddressed. A verifier "
                   f"who scopes `relevant` to the defeat objective alone could read "
                   f"this as a met-candidate; scoped to the STAGE row as written, it "
                   f"is partial",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": dod_items[3],
            "basis": f"the decisive fields are typed with width, signedness, "
                     f"initialization and a measured domain: Thumper HP is the signed "
                     f"halfword at actor+0x6E, initialized to 50 and driven to "
                     f"{facts['oracle_hp_min_max'][0]} "
                     f"(\"{facts['trace_hp_arc_verdict'][:96]}...\"); the camera flags "
                     f"field's ACCESS WIDTH was corrected to lhu/sh with its two bits "
                     f"given semantics; the goal latch is a halfword whose reset rule "
                     f"is visible in the same run "
                     f"({facts['trace_goal_latch_writes']} writes from "
                     f"{len(facts['trace_goal_latch_writer_pcs'])} PCs: the setter plus "
                     f"two zeroing sites). Coverage is real but partial: of "
                     f"{facts['trace_watches']} watched fields "
                     f"{facts['trace_fields_with_complete_value_sequence']} carry a "
                     f"COMPLETE observed value sequence and "
                     f"{facts['trace_fields_sampled_only']} are sampled only "
                     f"({facts['trace_sampled_only_addresses']}), so their domains are "
                     f"not bounded; the fight pass watched "
                     f"{facts['fight_fields_watched']} more fields with "
                     f"{facts['fight_fields_never_written']} never written",
            "gap": "no typed-state or region-provenance artifact exists for this row "
                   "(the census registers none), so ownership and reset rules are "
                   "per-field prose rather than a machine-checked table; the three "
                   "sampled-only fields have observed prefixes, not domains; and "
                   "observation on one route is not a proved valid domain",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": dod_items[4],
            "basis": f"creation, first use, retirement and scene transition are "
                     f"evidenced end to end on one route: the scenario anchors on the "
                     f"semantic condition HP==50 rather than a frame number, then "
                     f"observes the once-only exit "
                     f"({facts['f03_goal_store_hits']} hit), results entry "
                     f"({facts['f03_results_entry_hits']}) and results finalizer "
                     f"({facts['f03_results_finalizer_hits']}), while the poll oracle "
                     f"shows the scene actually leaving the stage "
                     f"(timeline {facts['oracle_scene_timeline']}, "
                     f"{facts['oracle_distinct_states']} distinct states). Repeated use "
                     f"is structurally excluded by the once-only latch, and its reset "
                     f"writers were observed",
            "gap": f"four bar phases have no evidence anywhere on this row's surfaces: "
                   f"a token scan of all {len(ROW_ARTIFACTS) + len(ROW_VAULT_PAGES)} "
                   f"evidence files returns {facts['lifecycle_phase_token_hits']} -- no "
                   f"death/respawn during the fight, no game over, no reload, no retry, "
                   f"no pause. Cold boot is likewise unevidenced (see original_oracle), "
                   f"and the row registers {facts['registered_movie_fixtures_for_row']} "
                   f"movie fixtures against "
                   f"{facts['unregistered_movie_fixtures_for_row']} further intact "
                   f"pinned ones, so re-entry after leaving the stage is untested",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": dod_items[5],
            "basis": f"several boundary contracts are pinned at instruction level, not "
                     f"asserted in prose: the cinematic-camera entry points take the "
                     f"flags value as a CALLER argument in a named stack slot (arg7 for "
                     f"cinematic_camera_start, arg8 for the polar variant) -- verified "
                     f"by the recompiled pin tool, {facts['c_camera_exit_recheck'].get('pins_ok')} "
                     f"pins, output hash equal to the 2026-08-04 pin "
                     f"({cc_ok}); the species-callback contract at actor+0x7C was "
                     f"confirmed live against statically pinned pointers "
                     f"({facts['c_fight_species_recheck'].get('pins_ok')} pins, {cf_ok}); "
                     f"the overlay contract is explicit (region A is a shared swap "
                     f"buffer, identity taken from the executing writer PC); and the "
                     f"asset-load contract for this scene is pinned arithmetic in the "
                     f"F08 binding artifact",
            "gap": "the bar asks for contracts at EVERY boundary the subsystem "
                   "crosses, and the boundary set is not enumerated for this row: no "
                   "ABI/interface ledger exists (compare F01's 764-row ledger), and "
                   "hi/lo, GTE, delay-slot and memory-effect contracts are not stated "
                   "for the governing overlay at all. Unknowns are named "
                   f"({facts['f03_bounded_residuals']} bounded residuals) but not "
                   "paired with obstructions the way the bar's enumeration expects",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": dod_items[6],
            "basis": f"the evidence is one stage, one route, one boss: "
                     f"{facts['registered_movie_fixtures_for_row']} registered movie "
                     f"fixtures, all of the same Any%/boss shape, and the row's own "
                     f"artifact self-reports breadth as "
                     f"\"{f03['phase4_metrics']['campaign_breadth']}\". The DoD's "
                     f"closing sentence forecloses exactly that reading (\"Passing one "
                     f"demonstration ... does not satisfy this definition\", present in "
                     f"the pinned page: "
                     f"{facts['dod_no_single_demonstration_clause']}). No applicability "
                     f"universe (routes x deaths x retries x actor variants x "
                     f"exceptional paths) is enumerated for the stage, so \"every "
                     f"applicable\" has no denominator -- the same shape that fails F01. "
                     f"The row's own artifact concedes one variant axis outright: the "
                     f"arena radius is measured for Thumper only "
                     f"({facts['arena_observed_max']} vs the predicted "
                     f"{facts['arena_predicted_bound']} over "
                     f"{facts['arena_target_samples']} samples)",
            "gap": f"{facts['unregistered_movie_fixtures_for_row']} intact, centrally "
                   f"pinned movie fixtures matching this stage or this boss are used by "
                   f"no artifact and declared on no row: "
                   f"{facts['unregistered_movie_fixture_paths']} -- including a "
                   f"100% route for this stage (name-matched; the corpus names runs by "
                   f"stage ordinal) and, separately, the from-boot completion run bound "
                   f"to this row by SCENE ID rather than by name "
                   f"({facts['coldboot_movie']}, scene match "
                   f"{facts['coldboot_scene_matches_row_scene']}). Enumerating the "
                   f"applicability set and consuming those would move this dimension "
                   f"with no new recording",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": dod_items[7],
            "basis": f"the row crosses more systems than most: player power word "
                     f"(the cinematic holds suppression bit 0x04 for its duration), HUD "
                     f"(flags bit 0x01 swaps hud_draw for the letterbox quads at two "
                     f"state-machine sites -- statically pinned), objectives (the goal "
                     f"latch), scene transition (timeline "
                     f"{facts['oracle_scene_timeline']} plus the paired countdown store "
                     f"observed in the same block), audio (the species callback is a "
                     f"play_sound(26) wrapper), and the results overlay in a different "
                     f"region (entry and finalizer each executed exactly once). The "
                     f"armed trace carried {facts['trace_watches']} watches with "
                     f"ring_truncated={facts['trace_ring_truncated']}, so these are "
                     f"co-observed in one run rather than stitched",
            "gap": "physics/animation and save-load are untouched, no player-damage or "
                   "death interaction is exercised during the fight, and there is no "
                   "registered combination matrix -- the interactions are individually "
                   "evidenced, never enumerated as a set",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": dod_items[8],
            "basis": f"measured, and the measurement corrects the census. The overlay "
                     f"decomp track (config/overlays.yml -> src/overlays/, built by "
                     f"tools/build_overlay.py) holds "
                     f"{facts['overlay_track_matched_functions']} byte-matched function "
                     f"of {facts['overlay_track_total_functions']} in this row's "
                     f"resident blob -- {facts['overlay_track_matched_bytes']} bytes of "
                     f"{facts['resident_overlay_code_bytes']} code bytes -- with the "
                     f"rebuilt blob SHA-1-identical to the pin "
                     f"(validated={facts['overlay_track_rebuild_validated']}, pin still "
                     f"matches the staged blob: "
                     f"{facts['overlay_track_blob_pin_matches_disc']}). It does NOT "
                     f"cover the governing function "
                     f"(covers_governing={facts['overlay_track_matched_covers_governing_function']}): "
                     f"the match is a 5-instruction state setter whose own source "
                     f"comment records the global's meaning as unknown, so it is a byte "
                     f"match, not reviewed semantic source. Against that, the governing "
                     f"function is {facts['governing_function_instructions']} "
                     f"instructions and the recompiled pin tool reproduces "
                     f"{facts['c_camera_exit_recheck'].get('pins_ok')} pins of which "
                     f"{facts['c_camera_exit_recheck'].get('resident_overlay_pin_lines')} "
                     f"are in the resident overlay. Neither matching nor reviewed "
                     f"semantic source represents the complete behaviour",
            "gap": f"the F-row census's triage string for this row "
                   f"(\"{facts['census_source_closure_triage']}\") is understated: it "
                   f"searches src_re/ and asm/hand_written/ only and does not see the "
                   f"overlay track "
                   f"(understated={facts['census_triage_understates_source_closure']}). "
                   f"The residual is bounded in prose (\"compiler-match the complete "
                   f"fight overlay and shared mover-VM implementation\") and is now "
                   f"quantified: {facts['resident_overlay_code_bytes']} code bytes in "
                   f"{facts['resident_overlay_code_records']} records, blob "
                   f"{facts['resident_overlay_blob_bytes']} bytes, campaign-wide "
                   f"overlay track at {facts['overlay_track_campaign_wide_matched_pct']}%",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F03_council_chamber measured against the nine DoD bars AS WRITTEN "
                    "(item 2 = enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f03_written_bar_assessment.py",
        "schema": "abl-phase4-row-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": ROW_ID,
        "row_name": crow["name"],
        "standard": {
            "ruling": "engineering-specs/phase4-measurement-standard-ruling.md",
            "bars_parsed_from": "ObsidianVault/Playbooks/Game Solving Roadmap - From "
                                "Reconstruction to Reliable Modding.md (Definition of "
                                "Done, items 1-9, quoted verbatim per dimension)",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads as "
                          "met; this assessment publishes measurement, not disposition",
            "states": {
                "met": "the written bar is satisfied and was measured",
                "met_candidate": "a submission for a fresh verifier, not a met",
                "partial": "some elements of the bar measured satisfied, others not",
                "not_met": "measured, and the bar's elements are absent",
                "unmeasured": "no evidence bears on the bar; not stretched to fit",
            },
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "edits_mechanics_baseline": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the row's own evidence artifact and Experiment page "
                               f"self-report {facts['f03_self_claimed_met_dimensions']} "
                               f"of {facts['f03_self_claimed_dimensions']} dimensions as "
                               "met under a blanket 'bounded_exhausted / move_on' "
                               "disposition; this assessment measures the same evidence "
                               "against the written bars and disagrees on eight of "
                               "them. The assessor did not author that evidence, but "
                               "the disagreement is a judgment and is challengeable. "
                               "Nothing here changes a registry, a row, or a status.",
            "disposition_vs_measurement": {
                "row_artifact_closure": facts["f03_closure"],
                "row_artifact_disposition": facts["f03_disposition"],
                "ledger_met_count": facts["ledger_met_count"],
                "ledger_dimension_basis": facts["ledger_dimension_basis"],
                "note": "the closure-debt ledger scores this row 0/9 with basis 'no "
                        "active child campaign' and movie_count 0 while the row "
                        "demonstrably holds pinned movies and analysis artifacts -- a "
                        "REGISTRATION artifact, not a measurement, in both directions",
            },
        },
        "method_notes": {
            "address_is_not_an_attribution": (
                "Region A is a shared swap buffer, so a 0x800Bxxxx address does not "
                "identify a blob. Every per-record citation count above is VA "
                f"containment only. {facts['re_pool_files_citing_the_shared_region_a_window']} "
                f"tracked src_re/asm files cite addresses in that window and "
                f"{facts['re_pool_files_naming_this_overlay']} of them name this "
                "overlay; src_re/level02_grain_gate_update.c is the worked example -- "
                "its window falls inside this row's governing extent by address, while "
                "its fixture is named for a different stage."),
            "stage_ordinal_vs_scene_id": (
                "The movie/save corpus is named by STAGE ordinal; disc data dirs are "
                "keyed by SCENE id, and for these two stages they CROSS "
                f"({facts['stage_ordinal_vs_disc_dir']}, crossing="
                f"{facts['stage_and_disc_dir_numbering_cross']}). Any filename-based "
                "attribution on this row is exposed to that swap, which is why the "
                "cold-boot fixture above is bound by asserted scene id instead."),
        },
        "verified_row_note": {
            "claim": "0x80090BEE is the cinematic-camera FLAGS field (caller-supplied "
                     "argument), not a Thumper defeat latch",
            "confirmed": bool(facts["camflags_is_cinematic_camera_field"]
                              and facts["camflags_value2_is_caller_argument"]
                              and facts["baseline_records_80090bee_retraction"]),
            "how": "dual-implemented census in analysis/phase4_d16_f03.json, the "
                   "baseline row's own RETRACTED binding, and the pin tool recompiled "
                   "and rerun here",
            "and_yet": "D16's closure of the boss mechanics does not close this STAGE "
                       "row: campaign_breadth and source_closure measure not_met and "
                       "six dimensions measure partial on the stage's own claims.",
        },
        "facts": facts,
        "evidence_pins": pins,
        "dimensions": dims,
        "counts": counts,
        "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                   f"met-candidate, {counts.get('partial', 0)} partial, "
                   f"{counts.get('not_met', 0)} not met, "
                   f"{counts.get('unmeasured', 0)} unmeasured -- against the WRITTEN "
                   f"bars. Compare: the row's own artifact claims "
                   f"{facts['f03_self_claimed_met_dimensions']}/"
                   f"{facts['f03_self_claimed_dimensions']} met by blanket "
                   f"disposition, and the closure-debt ledger scores it "
                   f"{facts['ledger_met_count']}/9 by registration. Neither of those "
                   f"was a measurement.",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar] {ROW_ID}: {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"facts derived: {len(facts)}   evidence pins: {len(pins)}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
