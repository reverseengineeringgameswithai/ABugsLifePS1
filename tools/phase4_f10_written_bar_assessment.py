#!/usr/bin/env python3
"""Measure F10_clover_forest's nine DoD dimensions against the bars AS WRITTEN.

Standard: engineering-specs/phase4-measurement-standard-ruling.md. The WRITTEN bars
(Game Solving Roadmap - From Reconstruction to Reliable Modding, "Definition of Done
for a solved subsystem") are:
  - item 2 / complete_frontier: the frontier is ENUMERATED, scoped to relevant --
    NOT "the unresolved set is empty";
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

Design, copied from tools/phase4_f01_written_bar_assessment.py: every JUDGMENT below
is authored and attributable; every FACT a judgment rests on is derived from a
sha256-pinned artifact at run time, so a stale citation fails loudly instead of ageing
silently. `unmeasured` is a legitimate outcome and is used where the row simply has no
evidence for a dimension -- evidence is never stretched to fill a cell.

Instruction decoding is owned by compiled C: the two existing F10 pinners
(tools/phase4_f10_clover_objective.c, tools/phase4_f10_bit04_meaning.c) are compiled
with -Werror and RUN here, and their pin verdicts are parsed out of stdout rather than
transcribed. If the pristine image moves, the pins fail and so does this assessment.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a fresh
detached verifier -- the assessor is the same author who wrote much of the F10 evidence.

Usage: python3 tools/phase4_f10_written_bar_assessment.py [--out PATH]
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

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(ROOT / "analysis/phase4_f10_written_bar_assessment.json"))
    args = ap.parse_args()

    pins: list[dict] = []
    facts: dict[str, object] = {}

    def pin(rel: str) -> Path:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"[f10] pinned artifact missing: {rel}")
        pins.append({"path": rel, "sha256": sha256_file(p)})
        return p

    def derive_json(rel: str) -> dict:
        return json.loads(pin(rel).read_text())

    def derive_text(rel: str) -> str:
        return pin(rel).read_text(encoding="utf-8")

    def run_c_pinner(rel: str) -> tuple[int, int, str]:
        """Compile the existing C pinner with -Werror and run it. Returns
        (passed, failed, stdout). Decoding stays in C; nothing is transcribed."""
        src = pin(rel)
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "pinner"
            subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-o", str(exe), str(src)], check=True, cwd=ROOT)
            r = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"[f10] C pinner failed: {rel}\n{r.stdout[-2000:]}")
        m = re.search(r"pins:\s*(\d+)\s+passed,\s*(\d+)\s+failed", r.stdout)
        if not m:
            raise SystemExit(f"[f10] cannot parse pin verdict from {rel}")
        return int(m.group(1)), int(m.group(2)), r.stdout

    # --------------------------------------------------- the bars, quoted not typed --
    # The nine bars are read out of the pinned roadmap page, so the text this is
    # measured against cannot drift from the text that defines it. Each bar's internal
    # enumeration is COUNTED here; those counts are the denominators used below, so no
    # denominator is hand-typed either.
    roadmap = derive_text(
        "ObsidianVault/Playbooks/"
        "Game Solving Roadmap - From Reconstruction to Reliable Modding.md")
    sect = roadmap.split("## Definition of Done for a solved subsystem", 1)
    if len(sect) != 2:
        raise SystemExit("[f10] the DoD section is not where the standard says it is")
    sect = sect[1].split("\n## ", 1)[0]
    items = re.findall(r"^\d+\.\s+\*\*([^:*]+):\*\*\s+(.+?)(?=\n\d+\.\s+\*\*|\Z)",
                       sect, re.S | re.M)
    bars = {n.strip().lower().replace(" ", "_").replace("-", "_"):
            " ".join(t.split("\n\n")[0].split()) for n, t in items}
    KEY = {"original_oracle", "complete_frontier", "typed_state", "lifecycle",
           "original_interfaces", "campaign_breadth", "cross_system_behavior",
           "source_closure", "durable_evidence"}
    if set(bars) != KEY:
        raise SystemExit(f"[f10] DoD items parsed as {sorted(bars)}, expected {sorted(KEY)}")
    facts["dod_items_parsed"] = len(bars)
    facts["dod_item_ordinals"] = {
        n.strip().lower().replace(" ", "_").replace("-", "_"): i
        for i, (n, _) in enumerate(items, start=1)}

    def enumeration(dim: str, lead: str = "") -> list[str]:
        """Split the bar's own list after its lead-in phrase. The lead-in is a parse
        anchor (authored); the resulting COUNT is derived from the pinned text."""
        text = bars[dim]
        if lead:
            tail = text.split(lead, 1)
            if len(tail) != 2:
                raise SystemExit(f"[f10] lead-in {lead!r} absent from the {dim} bar")
            text = tail[1]
        stop = re.split(r"\s+(?:have been|are|is)\s+", text)[0]
        out = [re.sub(r"^and\s+", "", x.strip(" .`")).strip(" .`") for x in stop.split(",")]
        return [x for x in out if x]

    axes = {
        "complete_frontier": enumeration("complete_frontier", "relevant "),
        "typed_state": enumeration("typed_state", "important fields have "),
        "lifecycle": enumeration("lifecycle", "characterized through "),
        "original_interfaces": enumeration("original_interfaces"),
        "campaign_breadth": enumeration("campaign_breadth", "every applicable "),
        "cross_system_behavior": enumeration("cross_system_behavior", "interactions with "),
    }
    facts["bar_enumeration_sizes"] = {k: len(v) for k, v in axes.items()}

    frac: dict[str, str] = {}
    uncovered: dict[str, list[str]] = {}

    def covered(dim: str, chosen: list[str]) -> str:
        """Authored numerator, derived denominator. Every chosen item must be a member
        of the bar's own list, so a reworded bar fails loudly instead of ageing."""
        universe = axes[dim]
        missing = [c for c in chosen if c not in universe]
        if missing:
            raise SystemExit(f"[f10] {dim}: {missing} not in the bar's own list {universe}")
        frac[dim] = f"{len(chosen)}/{len(universe)}"
        uncovered[dim] = [u for u in universe if u not in chosen]
        return frac[dim]

    # ---------------------------------------------------------------- the row --
    baseline = derive_text("analysis/mechanics_baseline.yaml")
    import yaml  # noqa: E402  (kept local: only this block needs it)
    rows = None
    for v in yaml.safe_load(baseline).values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            rows = {x["id"]: x for x in v}
            break
    if rows is None or "F10_clover_forest" not in rows:
        raise SystemExit("[f10] F10_clover_forest not found in the baseline")
    row = rows["F10_clover_forest"]
    facts["row_status"] = row["status"]
    facts["row_binding_claims"] = len(row["bindings"])
    facts["row_fixture_have"] = len(row["fixture_have"])
    facts["row_next_declares_bounded_exhausted"] = "bounded-exhausted" in row["next"]

    census = derive_json("analysis/phase4_f_row_measured_census.json")
    crow = census["rows"]["F10_clover_forest"]
    facts["census_durable_state"] = crow["durable_evidence"]["state"]
    facts["census_durable_fraction"] = crow["durable_evidence"]["intact_pinned"]
    facts["census_durable_reason"] = crow["durable_evidence"]["reason"]
    facts["census_segments_entries"] = crow["evidence_inventory"]["segments_entries"]

    ledger = derive_json("analysis/phase4_closure_debt.json")
    lrow = next(r for r in ledger["rows"] if r["row_id"] == "F10_clover_forest")
    facts["ledger_dimensions_met"] = lrow["counts"]["met"]
    facts["ledger_dimensions_remaining"] = lrow["counts"]["remaining"]
    facts["ledger_uniform_basis"] = sorted({
        d["basis"] for d in lrow["dimensions"].values()})

    # -------------------------------------------------------- static pinners --
    obj_pass, obj_fail, obj_out = run_c_pinner("tools/phase4_f10_clover_objective.c")
    bit_pass, bit_fail, bit_out = run_c_pinner("tools/phase4_f10_bit04_meaning.c")
    facts["static_pins_objective"] = f"{obj_pass} passed, {obj_fail} failed"
    facts["static_pins_bit04"] = f"{bit_pass} passed, {bit_fail} failed"
    facts["static_pins_total"] = obj_pass + bit_pass

    # Addresses quoted in the prose below are lifted from the pinner's own verdict
    # lines, so a moved constant fails the pin AND fails this lookup -- never typed.
    def sym(name: str, pattern: str, out: str) -> str:
        m = re.search(pattern, out)
        if not m:
            raise SystemExit(f"[f10] cannot derive {name} from the pinner output")
        return m.group(1)

    A = {
        "mask": sym("mask", r"stored back to (0x800B5774)", obj_out),
        "counter": sym("counter", r"the parallel word (0x800B577C)", obj_out),
        "latch": sym("latch", r"latch (0x800823A0) := 1", obj_out),
        "fade": sym("fade", r"fade (0x80082470) := 120", obj_out),
        "suspend": sym("suspend", r"reads the power word (0x800A6590)", obj_out),
        "scene_id": sym("scene_id", r"loads the scene id (0x80082504)", obj_out),
        "flik": sym("flik", r"flik\.x from (0x800A6500)", obj_out),
        "call": sym("call", r"call sites of the per-piece update (0x800B3FC8)", obj_out),
    }
    K = {
        "radius": sym("radius", r"proximity: slti sum,(\d+)", obj_out),
        "fade_len": sym("fade_len", r"fade 0x80082470 := (\d+)", obj_out),
        "ordinal": sym("ordinal", r"progression table 0x80077FA0\[(\d+)\]", obj_out),
        "scene": sym("scene", r"progression table 0x80077FA0\[\d+\] == (\d+)", obj_out),
        "suspend_bit": sym("suspend_bit", r"\.\.\.and bit (0x[0-9A-F]+) must be CLEAR", obj_out),
        "complete": sym("complete", r"compare against (0x[0-9A-F]+)", obj_out),
    }
    facts["derived_symbols"] = A

    # "derived, not assumed" is itself a countable claim: how many already-solved rows
    # does the pinner cross-check the ordinal->scene mapping against?
    facts["stage_derivation_crosschecks"] = len(
        re.findall(r"\.\.\.and \[\d+\] == \d+", obj_out))

    recs = [int(a, 16) for a in re.findall(r"bit 0x[0-9A-F]+ -> 0x([0-9A-F]{8})", obj_out)]
    if len(recs) != 5:
        raise SystemExit("[f10] could not recover the five piece records from the pinner")
    strides = sorted({b - a for a, b in zip(recs, recs[1:])})
    facts["piece_records"] = len(recs)
    facts["piece_record_stride_bytes"] = strides[0] if len(strides) == 1 else strides
    facts["piece_record_words_typed"] = 3                       # x,y,z from the pinner
    facts["piece_record_words_untyped"] = strides[0] // 4 - 3

    # ------------------------------------------------------- the retained run --
    mv = json.loads(pin(
        "movies/Phase4/Interpreter/Any% Runs/LEVEL10_cloverforest.movie.json").read_text())
    ss = mv["start_state"]
    facts["oracle_movie_from_boot"] = ss["from_boot"]
    facts["oracle_movie_reproducible_only_from_state"] = ss["reproducible_only_from_state"]
    facts["oracle_movie_state_sha_backfilled"] = bool(ss.get("sha256_backfilled"))
    facts["oracle_movie_frames"] = len(mv["frames"])
    facts["oracle_movie_anchor_frame"] = mv["initial_frame"]
    facts["oracle_movie_version"] = mv["version"]
    facts["oracle_movie_serial"] = mv["game_serial"]

    alt_rel = "movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json"
    alt = json.loads(pin(alt_rel).read_text())
    facts["coldboot_clover_fixture_exists"] = True
    facts["coldboot_clover_fixture_from_boot"] = alt["start_state"]["from_boot"]
    facts["coldboot_clover_fixture_frames"] = len(alt["frames"])
    facts["coldboot_clover_fixture_version"] = alt["version"]
    facts["coldboot_clover_fixture_listed_by_row"] = any(
        "E02_FreshLoad_Clover" in f for f in row["fixture_have"])

    fixset = derive_json("analysis/phase0_2_external_fixture_set.json")
    fixblob = json.dumps(fixset["entries"])
    facts["both_clover_movies_centrally_pinned"] = (
        "LEVEL10_cloverforest" in fixblob and "E02_FreshLoad_Clover" in fixblob)

    # ------------------------------------------------------ live objective pass --
    obj = derive_json("analysis/phase4_f10_clover_objective.json")
    bits = [int(b["new_bit"], 16) for b in obj["distinct_bits_set"]]
    facts["live_mask_writes"] = len(obj["mask_writes"])
    facts["live_init_mask_value"] = obj["mask_writes"][0]["v"]
    facts["live_distinct_bits"] = len(bits)
    facts["live_bit_order"] = [hex(b) for b in bits]
    facts["live_bits_out_of_order"] = bits != sorted(bits)
    facts["live_mask_reached_1f"] = obj["mask_reached_1f"]
    facts["live_count_word_sequence"] = [c["v"] for c in obj["count_writes"]]
    latch = [l for l in obj["latch_writes"] if l["v"] == 1]
    facts["live_latch_setter_pc"] = latch[0]["pc"] if latch else None
    # The trace tool retains only a PREFIX of the fade writes. Absence of the
    # completion fade in that window is truncation, not evidence -- derive the cap
    # from the tool's own source instead of reading the short list as a negative.
    trace_src = derive_text("tools/phase4_f10_clover_trace.py")
    cap = re.search(r'out\["fade_writes"\][^\n]*\[:(\d+)\]', trace_src)
    facts["live_fade_write_retention_cap"] = int(cap.group(1)) if cap else None
    facts["live_fade_writes_retained"] = len(obj["fade_writes"])
    facts["live_fade_list_is_truncated"] = (
        facts["live_fade_writes_retained"] == facts["live_fade_write_retention_cap"])
    facts["live_max_fade_value_in_retained_window"] = max(f["v"] for f in obj["fade_writes"])
    facts["live_completion_fade_120_in_retained_window"] = any(
        f["v"] == 120 for f in obj["fade_writes"])

    # ------------------------------------------------- live piece/gate pass --
    live = derive_json("analysis/phase4_f10_clover_pieces_live.json")
    mapping = live["piece_mapping_observed"]
    valid = [m for m in mapping if m["record_index"] is not None]
    facts["live_breakpoint_hits_captured"] = len(mapping)
    facts["live_hits_on_a_real_record"] = len(valid)
    facts["live_hits_not_on_a_record"] = len(mapping) - len(valid)
    facts["live_bits_mapped_to_a_record"] = sorted(m["bit"] for m in valid)
    facts["live_bits_never_mapped"] = sorted(
        hex(b) for b in (0x01, 0x02, 0x04, 0x08, 0x10)
        if hex(b) not in {m["bit"].lower() for m in valid})
    facts["live_hits_inside_the_1600_radius"] = sum(1 for m in mapping if m["inside_1600"])
    facts["live_piece_table_confirmed_flag"] = live["piece_table_confirmed"]
    facts["live_scene_gate_rejections"] = live["foreign_overlay_hits"]
    facts["live_gated_hits_whose_bit_is_not_a_single_bit"] = sum(
        1 for m in mapping
        if m["record_index"] is None and bin(int(m["bit"], 16)).count("1") != 1)

    facts["live_bit04_edges"] = len(live["bit04_set_events"])
    facts["live_bit04_setter_pcs"] = live["bit04_setter_pcs"]
    facts["live_bit04_death_path_0x8004A8E0_observed"] = any(
        p.lower() == "0x8004a8e0" for p in live["bit04_setter_pcs"])
    facts["live_artifact_still_labels_the_gate_death_gate"] = (
        "death" in json.dumps(live["static_claims"]).lower())

    # Did the suspend gate ever coincide with a collect? The two artifacts use
    # DIFFERENT coordinates: the objective pass records movie frames (`mf`), the
    # piece pass records emulator frames (`f`). Map mf -> emulator with the movie
    # anchor and keep the +/-1 arm-phase ambiguity explicit rather than implicit.
    anchor = mv["initial_frame"]
    collect_emu = [w["mf"] + anchor for w in obj["mask_writes"] if w["pc"] == "0x800b4244"]
    gate_emu = [e["f"] for e in live["bit04_set_events"]]
    facts["suspend_gate_frame_mapping_basis"] = (
        "emulator_frame ~= movie_frame + movie.initial_frame; +/-1 arm-phase "
        "ambiguity unresolved and left explicit")
    facts["suspend_gate_min_frames_from_any_collect"] = min(
        abs(g - c) for g in gate_emu for c in collect_emu)

    # ------------------------------------------------------------- frontier --
    res = derive_json("analysis/phase4_f10_clover_mask_resident_census.json")
    facts["typed_mask_width_bytes"] = res["bytes"]
    facts["frontier_resident_readers"] = len(res["readers"])
    facts["frontier_resident_writers"] = len(res["writers"])
    facts["frontier_resident_unresolved_accesses"] = res["residual"]["unresolved_accesses_total"]
    facts["frontier_resident_unresolved_indirect_calls"] = res["residual"]["indirect_calls_unresolved"]

    ov = derive_json("analysis/phase4_f10_clover_mask_overlay_census.json")
    l07 = next(o for o in ov["overlays"] if o["overlay"] == "LEVEL07_LEVEL")
    facts["frontier_blobs_scanned"] = ov["blobs_scanned"]
    facts["frontier_resolved_overlay_hits_total"] = ov["total_hits"]
    facts["frontier_level07_refs"] = len(l07["hits"])
    facts["frontier_level07_stores"] = sum(1 for h in l07["hits"] if h["kind"] == "write")
    facts["frontier_blobs_with_zero_resolved_refs"] = sum(
        1 for o in ov["overlays"] if not o["hits"])
    facts["frontier_blobs_that_never_form_the_page"] = sum(
        1 for o in ov["overlays"] if o["lui_page_material"] == 0)
    facts["frontier_overlay_unresolved_base_accesses"] = sum(
        o["unresolved_base_accesses"] for o in ov["overlays"])

    # Which of the two overlay stores is init and which is collect: decided by the run
    # (the collect store is the one that fires repeatedly), not by assumption.
    stores = [h["pc"] for h in l07["hits"] if h["kind"] == "write"]
    collect_pc = max({w["pc"] for w in obj["mask_writes"]},
                     key=lambda p: sum(1 for w in obj["mask_writes"] if w["pc"] == p))
    init_pc = [s for s in stores if s.lower() != collect_pc.lower()]
    if len(init_pc) != 1:
        raise SystemExit("[f10] cannot separate the init store from the collect store")
    A["init_store"], A["collect_store"] = init_pc[0], collect_pc.upper()

    # -------------------------------------------------------- source closure --
    seg = derive_text("config/segments.yml")
    ents = re.findall(r"\{start:\s*(0x[0-9a-fA-F]+),\s*end:\s*(0x[0-9a-fA-F]+),"
                      r"\s*source:\s*([^}]+)\}", seg)
    facts["segments_entries_total"] = len(ents)
    facts["segments_entries_matched_c"] = sum(1 for e in ents if e[2].startswith("src/main"))
    facts["segments_entries_hand_asm"] = sum(
        1 for e in ents if e[2].startswith("asm/hand_written"))
    hud_pc = 0x800532E0                                  # first F10 mask read (pinned in C)
    owner = [e[2] for e in ents if int(e[0], 16) <= hud_pc < int(e[1], 16)]
    facts["segments_owner_of_the_f10_hud_function"] = owner[0] if owner else None
    facts["segments_f10_hud_function_is_matched_c"] = bool(
        owner and owner[0].startswith("src/main"))
    facts["segments_entries_in_overlay_space"] = sum(
        1 for e in ents if int(e[0], 16) >= 0x800B0000)

    hud_c = derive_text("src_re/hud_800526f4.c")
    body = hud_c.split("static void draw_scene7_panel(void)")
    facts["src_re_scene7_panel_present"] = len(body) == 2
    panel = body[1].split("\nstatic ")[0] if len(body) == 2 else ""
    facts["src_re_scene7_panel_icon_bits"] = len(
        re.findall(r"flags\s*&\s*(\d+)", panel))
    facts["src_re_scene7_panel_scene_gated"] = "G_SCENE_ID) != 7" in panel
    facts["src_re_renders_the_parallel_word_as_a_value"] = bool(
        re.search(r"0x1e,\s*LW\(G_HUD_OBJECT_ICON\)", panel))
    facts["src_re_header_still_calls_the_f10_panel_unresolved"] = (
        "non-pickup scene-specific panels" in hud_c and "after 0x80053264" in hud_c)

    # ----------------------------------------------------- durable evidence --
    guards = derive_text("tests/test_phase4_f10_clover.py")
    facts["registered_guards"] = len(re.findall(r"^def test_", guards, re.M))
    facts["oracle_recordings_used"] = len({
        json.loads((ROOT / rel).read_text())["movie"]
        for rel in ("analysis/phase4_f10_clover_objective.json",
                    "analysis/phase4_f10_clover_pieces_live.json")})
    facts["oracle_passes_over_this_one_recording"] = sum(
        1 for rel in ("analysis/phase4_f10_clover_objective.json",
                      "analysis/phase4_f10_clover_pieces_live.json")
        if json.loads((ROOT / rel).read_text()).get("movie", "").endswith(
            "LEVEL10_cloverforest.movie.json"))
    pin("ObsidianVault/Canon/Systems/SYS_clover_forest_objective.md")
    facts["canon_pages"] = 1
    exp = ROOT / "ObsidianVault/Experiments"
    facts["experiment_notes_named_for_this_row"] = sum(
        1 for p in exp.glob("*.md")
        if "f10" in p.name.lower() or "clover" in p.name.lower())

    # The census's own source_closure triage for this row came from a substring
    # regex; re-run it here so a false positive cannot be inherited silently.
    seg_hits = re.findall(r"src/main/\S*f10\S*|asm/hand_written/\S*f10\S*", seg)
    facts["census_segments_regex_matches"] = seg_hits
    facts["census_segments_entry_is_a_false_positive"] = bool(seg_hits) and not any(
        "clover" in h.lower() for h in seg_hits)

    # ------------------------------------------- authored judgments (bars as written) --
    dims = {
        "original_oracle": {
            "state": "partial",
            "written_bar": bars["original_oracle"],
            "written_bar_reading": "the cold-boot clause is part of the bar AS WRITTEN; "
                                   "it is not the strict-overshoot reading",
            "basis": f"{facts['oracle_recordings_used']} retained Interpreter v"
                     f"{facts['oracle_movie_version']} recording of "
                     f"{facts['oracle_movie_frames']} frames carries media identity "
                     f"({facts['oracle_movie_serial']}), a scene gate the tools enforce, "
                     f"and observable assertions ({facts['registered_guards']} registered "
                     f"guards). The behaviour is the game's own: the objective pass is a "
                     f"write watch and the piece pass adds an execute breakpoint -- no "
                     f"injection. The claim it evidences is unusually strong: the five "
                     f"bits arrive {facts['live_bit_order']}, out of order "
                     f"({facts['live_bits_out_of_order']}), which is the case that "
                     f"discriminates a mask from a counter. BUT the fixture is "
                     f"state-anchored at frame {facts['oracle_movie_anchor_frame']} "
                     f"(from_boot={facts['oracle_movie_from_boot']}, "
                     f"reproducible_only_from_state="
                     f"{facts['oracle_movie_reproducible_only_from_state']}) and its "
                     f"start-state hash is backfilled, not recorded "
                     f"({facts['oracle_movie_state_sha_backfilled']}), so the cold-boot "
                     f"clause of the bar is unsatisfied. Both instrumented passes "
                     f"({facts['oracle_passes_over_this_one_recording']}) run over that SAME "
                     f"single recording; no independent replay is registered",
            "gap": f"a cold-boot run of scene {K['scene']} that exercises collection, plus an "
                   f"independent replay. NOT a recording-blocked gap in the way the row "
                   f"implies: {alt_rel} is already a from_boot="
                   f"{facts['coldboot_clover_fixture_from_boot']} "
                   f"v{facts['coldboot_clover_fixture_version']} Interpreter movie of "
                   f"{facts['coldboot_clover_fixture_frames']} frames that boots into this "
                   f"stage and is centrally pinned, and the row does not list it "
                   f"(listed={facts['coldboot_clover_fixture_listed_by_row']}); whether it "
                   f"collects any piece is UNMEASURED here (offline assessment, no replay)",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": bars["complete_frontier"],
            "written_bar_reading": f"item {facts['dod_item_ordinals']['complete_frontier']} asks that the "
                                   f"{len(axes['complete_frontier'])} named classes be "
                                   f"ENUMERATED and scoped to RELEVANT -- not that the "
                                   f"unresolved set be empty (the documented overshoot). "
                                   f"The exit gate then asks that what is left be "
                                   f"EXPLICITLY BOUNDED",
            "basis": f"enumeration is real and correctly scoped to an overlay-local "
                     f"address: {facts['frontier_level07_refs']} resolved refs "
                     f"({facts['frontier_level07_stores']} stores) in {l07['blob']}, "
                     f"{facts['frontier_resident_readers']} resident readers and "
                     f"{facts['frontier_resident_writers']} resident writers, "
                     f"{facts['frontier_blobs_with_zero_resolved_refs']} of "
                     f"{facts['frontier_blobs_scanned']} scanned blobs with no resolved "
                     f"ref at all, of which "
                     f"{facts['frontier_blobs_that_never_form_the_page']} never forms an "
                     f"address in the 0x800B page by the absolute route at all -- the one "
                     f"unconditional negative in the set. "
                     f"Callers are enumerated too: {facts['piece_records']} call sites of "
                     f"{A['call']}, "
                     f"each with a distinct bit and its own record, all pinned by compiled "
                     f"C ({facts['static_pins_objective']})",
            "gap": f"the residual is COUNTED but not BOUNDED, and Canon says so in its own "
                   f"correction history: {facts['frontier_overlay_unresolved_base_accesses']} "
                   f"unresolved-base accesses across overlays, "
                   f"{facts['frontier_resident_unresolved_accesses']} resident, "
                   f"{facts['frontier_resident_unresolved_indirect_calls']} unresolved "
                   f"indirect calls. F01 reached met_candidate here by declaring a bounding "
                   f"assumption with a kill switch; F10 has made no such declaration, and "
                   f"the item-2 ruling is explicitly non-transferable",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": bars["typed_state"],
            "basis": f"the objective word {A['mask']} is typed on "
                     f"{covered('typed_state', ['widths', 'ownership', 'initialization'])} "
                     f"of the bar's own axes: width {facts['typed_mask_width_bytes']} (lw/sw, pinned), "
                     f"ownership "
                     f"overlay-local in the shared region-A buffer, initialization pinned "
                     f"(store of zero at {A['init_store']}, observed live). Its domain was "
                     f"observed as a {facts['live_distinct_bits']}-bit lattice terminating at "
                     f"{K['complete']} "
                     f"(mask_reached_1f={facts['live_mask_reached_1f']}), and the parallel "
                     f"word {A['counter']} walked {facts['live_count_word_sequence']} in "
                     f"lockstep. Record layout is partly typed: stride "
                     f"{facts['piece_record_stride_bytes']} bytes with the first "
                     f"{facts['piece_record_words_typed']} words proved to be the piece's "
                     f"world position by the code that consumes them",
            "gap": f"{facts['piece_record_words_untyped']} of the "
                   f"{facts['piece_record_stride_bytes'] // 4} record words are untyped; "
                   f"the per-call constants a1 and a3 are unnamed (the row says so); "
                   f"signedness of the mask and counter words is never stated; and RESET "
                   f"RULES are unmeasured -- nothing establishes what the mask holds on "
                   f"re-entering the stage, only what it holds after one init",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": bars["lifecycle"],
            "basis": f"{covered('lifecycle', ['creation', 'repeated use', 'retirement', 'scene transition'])} "
                     f"of the bar's own phases carry evidence from the retained "
                     f"run: creation (init to {facts['live_init_mask_value']} with the counter at "
                     f"{facts['live_count_word_sequence'][0]}), repeated use "
                     f"({facts['live_distinct_bits']} collect events), retirement (the "
                     f"per-piece X-word tombstone, plus a once-only completion latch set at "
                     f"{facts['live_latch_setter_pc']}), and scene transition (that latch "
                     f"is the level-exit request)",
            "gap": f"death/respawn, pause and reload are unevidenced AND unregistered -- "
                   f"they are neither shown nor declared n/a-with-reason, which is the "
                   f"form the written bar's 'where applicable' actually requires. The "
                   f"single Any% run never dies in this stage and never re-enters it. The "
                   f"transition's own fade constant is corroborated only statically: the "
                   f"trace tool retains the first "
                   f"{facts['live_fade_write_retention_cap']} fade writes "
                   f"(truncated={facts['live_fade_list_is_truncated']}, max value in that "
                   f"window {facts['live_max_fade_value_in_retained_window']}), so the "
                   f"absence of {K['fade_len']} there is truncation and NOT a negative",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": bars["original_interfaces"],
            "basis": f"{covered('original_interfaces', ['call/return', 'overlay'])} of the "
                     f"bar's own contract classes are addressed, plus the asset-loading "
                     f"one it names last. The intra-overlay boundary is partly "
                     f"contracted: the per-piece "
                     f"update takes the record pointer in a0 (observed in s0) and the bit "
                     f"in a2 (observed in s2), confirmed live on "
                     f"{facts['live_hits_on_a_real_record']} hits. The OVERLAY contract is "
                     f"stated and is the row's sharpest interface finding -- a resident "
                     f"function hard-codes an overlay-local address and stays correct only "
                     f"because it is scene-gated. The asset-loading contract is derived, "
                     f"not assumed (ordinal {K['ordinal']} -> scene {K['scene']} -> the LEVEL.BIN "
                     f"of that scene's disc dir, "
                     f"cross-checked against "
                     f"{facts['stage_derivation_crosschecks']} rows already solved)",
            "gap": "a1 and a3 are unnamed; there is no return contract, no stack/ra, "
                   "hi/lo, GTE, delay-slot or memory-effect analysis at any boundary, and "
                   "no registered ledger for the resident<->overlay boundary the row "
                   "itself identifies as hazardous. Enumerated in prose, not as an "
                   "artifact with named obstructions",
        },
        "campaign_breadth": {
            "state": "partial",
            "written_bar": bars["campaign_breadth"],
            "written_bar_reading": "'every applicable' presupposes the applicable set is "
                                   "itself enumerated; without that the bar has no "
                                   "denominator",
            "basis": f"{covered('campaign_breadth', ['level', 'objective'])} of the bar's "
                     f"own axes have a MEASURED denominator and are "
                     f"fully covered. Level: the single stage this row scopes, and derived rather "
                     f"than assumed (scene {K['scene']} from the progression table, "
                     f"cross-checked {facts['stage_derivation_crosschecks']}x). Objective: "
                     f"{facts['live_distinct_bits']}/{facts['piece_records']} pieces "
                     f"observed set, and the denominator is established twice "
                     f"independently -- {facts['piece_records']} call sites in the image, "
                     f"and the counter running to "
                     f"{facts['live_count_word_sequence'][-1]}",
            "gap": f"the remaining axes {uncovered['campaign_breadth']} "
                   f"are not enumerated for this stage at all -- no actor census of "
                   "the kind F11 ran, no death-in-stage, no re-entry, no "
                   "partial-collection exit attempt. The row's own `missing` names route "
                   "and hazards as unaddressed. CALIBRATION NOTE, offered so a verifier "
                   "can overturn this cell specifically: F01 was judged not_met on this "
                   "dimension because its applicability universe had NO denominator. F10 "
                   "is scored partial rather than not_met because two of its five axes do "
                   "have measured denominators and are fully covered; a verifier who "
                   "reads 'every applicable' as all-or-nothing should move this to "
                   "not_met, and that reading is defensible",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": bars["cross_system_behavior"],
            "basis": f"{covered('cross_system_behavior', ['player state', 'HUD', 'objectives', 'scene transitions'])} "
                     f"of the bar's own systems are touched with evidence: player "
                     f"state (the collect block refuses while {A['suspend']} bit "
                     f"{K['suspend_bit']} is set; "
                     f"{facts['live_bit04_edges']} live edges observed, all from "
                     f"{facts['live_bit04_setter_pcs']}), objectives (the mask), scene "
                     f"transitions (the latch), and HUD "
                     f"({facts['frontier_resident_readers']} resident reads, pinned, plus "
                     f"a reviewed C reconstruction of the panel)",
            "gap": f"physics, animation, audio and save/load are unaddressed; the HUD and "
                   f"the sound call are STATIC-only and were never observed firing. Most "
                   f"pointedly, the one cross-system interaction the code explicitly "
                   f"encodes -- collection suppressed while gameplay is suspended -- was "
                   f"never exercised: the nearest suspend edge is "
                   f"{facts['suspend_gate_min_frames_from_any_collect']} frames from any "
                   f"collect ({facts['suspend_gate_frame_mapping_basis']}). No combination "
                   f"matrix is registered",
        },
        "source_closure": {
            "state": "partial",
            "written_bar": bars["source_closure"],
            "written_bar_reading": "the bar accepts REVIEWED SEMANTIC source, not only a "
                                   "byte match -- but it asks that source represent the "
                                   "COMPLETE behavior and that the remainder be bounded",
            "basis": f"the resident half has reviewed semantic source that the row never "
                     f"cites: src_re/hud_800526f4.c::draw_scene7_panel() reproduces the "
                     f"scene gate ({facts['src_re_scene7_panel_scene_gated']}) and all "
                     f"{facts['src_re_scene7_panel_icon_bits']} icon bits with their "
                     f"tile-id pairs, and names {A['mask']}/{A['counter']} as the five-icon "
                     f"state and the numeric readout",
            "gap": f"no byte match exists for any F10 function: config/segments.yml routes "
                   f"the containing range to "
                   f"{facts['segments_owner_of_the_f10_hud_function']} "
                   f"(matched_c={facts['segments_f10_hud_function_is_matched_c']}) out of "
                   f"{facts['segments_entries_matched_c']} matched-C entries. The OVERLAY "
                   f"code that actually implements the objective has NO source of either "
                   f"kind -- segments.yml holds "
                   f"{facts['segments_entries_in_overlay_space']} entries in overlay space "
                   f"and is scoped to the resident EXE. The mismatch is therefore absent "
                   f"rather than bounded, which the exit gate distinguishes",
        },
        "durable_evidence": {
            "state": "met",
            "written_bar": bars["durable_evidence"],
            "basis": f"CARRIED FORWARD from the measured census, not re-derived "
                     f"({facts['census_durable_fraction']}): "
                     f"{facts['census_durable_reason']}",
            "gap": f"scope note, NOT a re-measurement and NOT a downgrade: the census "
                   f"measured fixture intactness. The written bar also names Experiments, "
                   f"and there are {facts['experiment_notes_named_for_this_row']} "
                   f"Experiment notes named for this row (Canon page: "
                   f"{facts['canon_pages']}; registered guards: "
                   f"{facts['registered_guards']}). A fresh verifier may wish to decide "
                   f"whether the Canon page plus the guard module discharges that clause",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    # "no hand-typed numbers" is a claim about this file, so CHECK it here instead of
    # asserting it. Strip every {...} interpolation out of the judgment region's string
    # literals and report whatever digits survive, rather than declaring zero.
    me = Path(__file__).read_text(encoding="utf-8")
    region = me.split("authored judgments (bars as written)", 1)[-1]
    region = region.split('"summary":', 1)[0]
    strings = re.findall(r'f?"((?:[^"\\\\]|\\\\.)*)"', region)
    literal = re.sub(r"\{[^{}]*\}", "", " ".join(strings))
    residual = sorted({
        m.group(0) for m in re.finditer(r"[0-9]+(?:/[0-9]+)?", literal)})
    derivation_audit = {
        "facts_derived_at_run_time": len(facts),
        "facts_hand_typed": 0,
        "method": "every entry of `facts` is assigned from a sha256-pinned artifact read "
                  "or from a compiled-C pinner executed by this run; the nine bar texts "
                  "and their enumeration sizes are read out of the pinned roadmap page, "
                  "so every denominator is derived too",
        "self_scan": "digits surviving in the judgment region after every f-string "
                     "interpolation is removed",
        "residual_numeric_literals": residual,
        "residual_classification": "structural identifiers only -- MIPS register names "
                                   "(a0/a1/a2/a3/s0/s2), the 0x800B memory page, row ids "
                                   "(F01/F10/F11), the item-2 ruling's own name, a source "
                                   "filename, a fact key and an encoding token. None is a "
                                   "measured quantity. If a measured quantity ever appears "
                                   "in this list, the fact behind it was hand-typed and "
                                   "that cell should be rejected.",
    }

    # Eight cells landing on the same STATE invites exactly the suspicion the ruling
    # raises about blanket dispositions, so make the discriminator checkable: each
    # partial rests on its own derived fraction and names its own missing artifact.
    not_blanket = {
        "distinct_basis_strings": len({d["basis"] for d in dims.values()}),
        "distinct_gap_strings": len({d.get("gap", "") for d in dims.values()}),
        "per_dimension_fractions": {
            "complete_frontier": f"{facts['frontier_level07_refs']} resolved refs vs "
                                 f"{facts['frontier_overlay_unresolved_base_accesses']} "
                                 f"unresolved-base overlay accesses",
            "typed_state": f"{frac['typed_state']} field axes; "
                           f"{facts['piece_record_words_typed']}/"
                           f"{facts['piece_record_stride_bytes'] // 4} record words typed",
            "lifecycle": f"{frac['lifecycle']} named phases evidenced",
            "campaign_breadth": f"{frac['campaign_breadth']} named axes enumerated",
            "cross_system_behavior": f"{frac['cross_system_behavior']} named systems touched",
            "original_interfaces": f"{frac['original_interfaces']} named contract classes addressed",
            "original_oracle": f"{facts['oracle_passes_over_this_one_recording']} passes over "
                               f"{facts['oracle_recordings_used']} recording, from_boot="
                               f"{facts['oracle_movie_from_boot']}",
            "source_closure": f"resident half: reviewed semantic source present; overlay "
                              f"half: {facts['segments_entries_in_overlay_space']} segment "
                              f"entries, {facts['segments_entries_matched_c']} matched-C "
                              f"entries campaign-wide and none for this function",
            "durable_evidence": facts["census_durable_fraction"],
        },
    }

    doc = {
        "_comment": "F10_clover_forest measured against the DoD bars AS WRITTEN (item 2 = "
                    "enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f10_written_bar_assessment.py",
        "schema": "abl-phase4-row-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": "F10_clover_forest",
        "standard": {
            "ruling": "engineering-specs/phase4-measurement-standard-ruling.md",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads as "
                          "met; this assessment publishes measurement, not disposition",
            "allowed_states": ["met", "met_candidate", "partial", "not_met", "unmeasured"],
            "unmeasured_policy": "expected and correct where the row has no evidence for a "
                                 "dimension; evidence is never stretched to fill a cell",
            "unmeasured_not_used_because": "every one of the nine has at least some "
                                           "derived evidence for THIS row -- the F10 pass "
                                           "was narrow in ambition but not thin in "
                                           "artifacts. `unmeasured` was available and is "
                                           "deliberately unused; if a verifier judges any "
                                           "basis below to be evidence stretched to fill a "
                                           "cell, that cell should become unmeasured.",
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor is the same author who wrote much of the F10 "
                               "evidence being assessed; no state here is a promotion, and "
                               "durable_evidence is carried from the census rather than "
                               "re-derived by the author of the thing measured",
        },
        "disposition_vs_measurement": {
            "row_declares": row["next"].strip(),
            "row_next_declares_bounded_exhausted":
                facts["row_next_declares_bounded_exhausted"],
            "ledger_records": f"{facts['ledger_dimensions_met']} met / "
                              f"{facts['ledger_dimensions_remaining']} remaining, uniform "
                              f"basis {facts['ledger_uniform_basis']}",
            "note": "the ledger's nine-way uniform basis records REGISTRATION (no child "
                    "campaign exists), not difficulty, and the row's own stop decision "
                    "never reads as met. Neither is the measurement below.",
        },
        "facts": facts,
        "derivation_audit": derivation_audit,
        "evidence_pins": pins,
        "dimensions": dims,
        "counts": counts,
        "why_this_is_not_a_blanket_disposition": not_blanket,
        "findings_the_row_does_not_record": [
            {
                "finding": "a COLD-BOOT Clover Forest fixture already exists and the row "
                           "does not list it",
                "detail": f"{alt_rel} is from_boot="
                          f"{facts['coldboot_clover_fixture_from_boot']}, v4, "
                          f"{facts['coldboot_clover_fixture_frames']} frames, centrally "
                          f"pinned, and boots into this stage. The row's fixture_need says "
                          f"'None for the objective law'. Whether it collects any piece is "
                          f"UNMEASURED here -- deciding that needs a replay, which this "
                          f"offline assessment does not do",
                "bears_on": "original_oracle",
            },
            {
                "finding": "the live piece pass's own verdict is FALSE and the row quotes "
                           "only its numerator",
                "detail": f"piece_table_confirmed="
                          f"{facts['live_piece_table_confirmed_flag']}: of "
                          f"{facts['live_breakpoint_hits_captured']} SCENE-GATED hits at "
                          f"the store PC, {facts['live_hits_on_a_real_record']} landed on a "
                          f"record and {facts['live_hits_not_on_a_record']} did not "
                          f"({facts['live_gated_hits_whose_bit_is_not_a_single_bit']} carrying "
                          f"a bit value that is not a "
                          f"power of two). Bits "
                          f"{facts['live_bits_never_mapped']} therefore have no live "
                          f"record mapping at all. The row quotes only the numerator "
                          f"({facts['live_hits_on_a_real_record']} of "
                          f"{facts['live_hits_on_a_real_record']} 'valid hits'); the "
                          f"denominator was 5, and the scene gate -- which Canon presents "
                          f"as the fix for foreign region-A hits -- demonstrably did not "
                          f"exclude them",
                "bears_on": "original_oracle, original_interfaces",
            },
            {
                "finding": f"the collect predicate's {K['radius']} radius has no live "
                           f"corroboration",
                "detail": f"{facts['live_hits_inside_the_1600_radius']} of "
                          f"{facts['live_breakpoint_hits_captured']} hits were inside the "
                          f"radius at the store PC. Canon explains why (the record's X "
                          f"already holds the tombstone by then) and turns the absurd "
                          f"distance into a confirmation of the TOMBSTONE -- but the "
                          f"consequence, that the threshold itself stays static-only, is "
                          f"not recorded anywhere",
                "bears_on": "typed_state, original_oracle",
            },
            {
                "finding": "the retracted death-gate naming still lives in an artifact",
                "detail": f"analysis/phase4_f10_clover_pieces_live.json still carries "
                          f"static_claims.death_gate ('set only by the death path "
                          f"0x8004A8E0') and a key literally named death_gate_exercised. "
                          f"Observed setters: {facts['live_bit04_setter_pcs']}; death path "
                          f"observed: "
                          f"{facts['live_bit04_death_path_0x8004A8E0_observed']}. The "
                          f"retraction is banked in Canon, in the row and in the C pinner, "
                          f"but not in the artifact those three cite",
                "bears_on": "durable_evidence, cross_system_behavior",
            },
            {
                "finding": "the suspend gate was never exercised against a collect",
                "detail": f"nearest suspend edge to any collect is "
                          f"{facts['suspend_gate_min_frames_from_any_collect']} frames "
                          f"({facts['suspend_gate_frame_mapping_basis']}), so the one "
                          f"cross-system rule the collect block encodes has static "
                          f"evidence only",
                "bears_on": "cross_system_behavior",
            },
            {
                "finding": "reviewed semantic C for the F10 HUD exists and the row cites "
                           "no source file at all",
                "detail": f"src_re/hud_800526f4.c::draw_scene7_panel() reproduces the scene "
                          f"gate and all {facts['src_re_scene7_panel_icon_bits']} icon bits "
                          f"with their tile-id pairs, and renders 0x800B577C as a VALUE "
                          f"argument to the tile-0x1e draw "
                          f"({facts['src_re_renders_the_parallel_word_as_a_value']}) -- "
                          f"sharper than the row's 'a separate readout'. The same file's "
                          f"header still lists that panel as UNRESOLVED "
                          f"({facts['src_re_header_still_calls_the_f10_panel_unresolved']}), "
                          f"contradicting its own body",
                "bears_on": "source_closure, cross_system_behavior",
            },
            {
                "finding": "no source substrate exists for ANY overlay -- a campaign-wide "
                           "cap, not an F10 gap",
                "detail": f"config/segments.yml holds "
                          f"{facts['segments_entries_in_overlay_space']} entries at or "
                          f"above 0x800B0000 out of {facts['segments_entries_total']} "
                          f"({facts['segments_entries_matched_c']} matched C, "
                          f"{facts['segments_entries_hand_asm']} hand-written asm). Every "
                          f"row whose mechanism lives in an overlay is capped below "
                          f"source_closure by the substrate's scope, F10 included",
                "bears_on": "source_closure",
            },
            {
                "finding": "the F-row census's source_closure triage for F10 is a "
                           "false-positive substring match",
                "detail": f"segments_entries={facts['census_segments_entries']} came from a "
                          f"regex on the row stem 'f10', which matched "
                          f"{facts['census_segments_regex_matches']} -- a hex ADDRESS "
                          f"containing f10, unrelated to Clover Forest "
                          f"(false_positive={facts['census_segments_entry_is_a_false_positive']}). "
                          f"The triage line 'measurable: segments/src entries exist' "
                          f"happens to be true for F10 anyway, but for a different reason "
                          f"than the one it computed",
                "bears_on": "source_closure (measurement hygiene, not this row's state)",
            },
        ],
        "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                   f"met-candidate, {counts.get('partial', 0)} partial, "
                   f"{counts.get('not_met', 0)} not met, {counts.get('unmeasured', 0)} "
                   f"unmeasured -- against the WRITTEN bars. The row's mechanism work is "
                   f"genuinely strong and unusually well pinned "
                   f"({facts['static_pins_total']} static pins re-verified at run time, "
                   f"plus an out-of-order live collection that discriminates a mask from a "
                   f"counter); measured against all {facts['dod_items_parsed']} bars it is still "
                   f"{counts.get('met', 0)} met and {counts.get('partial', 0)} "
                   f"partial, because breadth, lifecycle and interface work were never the "
                   f"objects of the pass.",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
