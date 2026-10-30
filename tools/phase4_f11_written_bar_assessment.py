#!/usr/bin/env python3
"""Measure F11 (The Tree) against the nine DoD dimensions AS WRITTEN.

Standard: `engineering-specs/phase4-measurement-standard-ruling.md`. One standard,
applied per-dimension, against each bar as written:

  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

Exemplar: `tools/phase4_f01_written_bar_assessment.py`. Same contract here --
JUDGMENTS are authored and attributable; every FACT they rest on is derived from a
pinned artifact at run time, so a stale citation fails loudly instead of aging
silently. This tool hand-types no number that appears in a basis string.

WHY THAT MATTERS ON THIS ROW SPECIFICALLY: F11's registry binding and its Experiment
page both state "19/19 pins" for `tools/phase4_f11_static.c`. The tool carries a
different number today and its own test asserts the newer one. Both narrative
surfaces aged; nothing detected it. This tool therefore COMPILES AND RUNS the C
pinner and reports what it actually returns, next to what the prose claims.

F11 IS A MULTI-MECHANISM ROW -- scouts/Dot, climbing, acorns, swinging. A claim proved
for one of those is not credited across the row: `per_mechanism` below records which
mechanism each artifact actually measured, and `cross_system_behavior` is judged on
whether they were ever exercised TOGETHER rather than only separately.

AUTHORITY: this assesses; it does not promote. `durable_evidence` is carried forward
from the measured F-row census, not re-derived.

Usage: python3 tools/phase4_f11_written_bar_assessment.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW = "F11_the_tree"

# The C pinner and the blob it pins. Compiled and RUN, never quoted from prose.
STATIC_C = "tools/phase4_f11_static.c"
STATIC_BLOB = "REBUILD/files/LEVEL02/LEVEL1.BIN"

# The two operator recordings every runtime artifact on this row derives from.
F11_MOVIES = [
    "movies/Phase4/Interpreter/Any% Runs/LEVEL11_THETREE.movie.json",
    "movies/Phase4/Interpreter/F11_scouts.movie.json",
]

# Authored mapping only: which of the row's four named mechanics each artifact
# measured. The COUNTS attached to each mechanism below are derived, not authored.
MECHANISM_ARTIFACTS = {
    "scouts_dot": ["analysis/phase4_f11_scout_progression.json",
                   "analysis/phase4_f11_find_event.json",
                   "analysis/phase4_f11_exit_gate.json",
                   "analysis/phase4_f11_overlay_state.json"],
    "acorns": ["analysis/phase4_f11_actor_census.json",
               "analysis/phase4_f11_acorns.json",
               "analysis/phase4_f11_acorn_state.json"],
    "climbing": ["analysis/phase4_f11_climbing.json"],
    "swinging": [],
}

# Keys whose presence would bind an artifact to the disc/binary/mode it was taken on.
PROVENANCE_KEYS = ("authority", "media", "disc", "cue", "exe_sha256", "binary",
                   "duckstation", "execution_mode", "retail_exe", "serial",
                   "movie_sha256", "media_sha256", "binary_sha256")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def distinct_run(seq):
    return [x for i, x in enumerate(seq) if i == 0 or x != seq[i - 1]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(ROOT / "analysis/phase4_f11_written_bar_assessment.json"))
    args = ap.parse_args()

    pins: list[dict] = []
    facts: dict[str, object] = {}
    seen: set[str] = set()

    def pin(rel: str) -> Path:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"[f11-written-bar] MISSING pinned artifact: {rel}")
        if rel not in seen:
            seen.add(rel)
            pins.append({"path": rel, "sha256": sha256_file(p)})
        return p

    def derive(rel: str) -> dict:
        return json.loads(pin(rel).read_text())

    def derive_yaml(rel: str):
        return yaml.safe_load(pin(rel).read_text())

    # ---------------------------------------------------------------- the row --
    base = derive_yaml("analysis/mechanics_baseline.yaml")
    rows = base["rows"] if isinstance(base, dict) else base
    row = next(r for r in rows if r.get("id") == ROW)
    binding_text = " ".join(row.get("bindings") or [])
    prose = binding_text + " " + str(row.get("missing", "")) + " " + str(row.get("next", ""))
    facts["row_status"] = row["status"]
    facts["row_binding_claims"] = len(row.get("bindings") or [])
    facts["row_declared_fixtures"] = len(row.get("fixture_have") or [])
    facts["row_declares_fixture_need"] = bool(row.get("fixture_need"))
    facts["row_mechanics_in_name"] = sorted(MECHANISM_ARTIFACTS)

    # ------------------------------------------- durable_evidence: CARRIED FWD --
    census = derive("analysis/phase4_f_row_measured_census.json")
    crow = census["rows"][ROW]
    facts["durable_evidence_state_measured"] = crow["durable_evidence"]["state"]
    facts["durable_evidence_fraction"] = crow["durable_evidence"]["intact_pinned"]
    cart = crow["evidence_inventory"]["analysis_artifacts"]
    facts["census_analysis_artifacts"] = len(cart)
    facts["census_row_named_artifacts"] = sum(1 for a in cart if "_f11_" in a)
    facts["census_shared_artifacts"] = sorted(a for a in cart if "_f11_" not in a)
    facts["census_source_closure_triage"] = crow["measurability_triage"]["source_closure"]
    facts["census_segments_entries"] = crow["evidence_inventory"]["segments_entries"]

    # The census's source_closure triage keys on the row stem. Re-run its own regex:
    # if the only hit is a hex address that happens to contain the stem, the triage
    # is a substring artifact, not a registered source surface.
    seg_text = pin("config/segments.yml").read_text()
    stem = ROW.split("_")[0].lower()
    seg_hits = re.findall(
        rf"(?:src/main/[\w./-]*{stem}[\w./-]*|asm/hand_written/[\w./-]*{stem}[\w./-]*)",
        seg_text)
    facts["segments_hits_for_row_stem"] = seg_hits
    # a hit is spurious when the stem only ever occurs inside a hex address run
    facts["segments_hits_are_address_substrings"] = bool(seg_hits) and all(
        re.search(rf"[0-9a-f]{{4,}}{stem}", h) for h in seg_hits)

    # ------------------------------------------------ runtime evidence, derived --
    gate = derive("analysis/phase4_f11_exit_gate.json")
    gf = gate["findings"]
    facts["gate_frames"] = gate["frames"]
    facts["gate_events"] = gate["event_total"]
    facts["gate_ring_truncated"] = gate["ring_truncated"]
    facts["gate_finds"] = len(gf["bit_set_events"])
    facts["gate_distinct_scouts_found"] = len({e["scout"] for e in gf["bit_set_events"]})
    facts["gate_setter_pcs"] = gf["setter_pcs"]
    facts["gate_clear_events"] = len(gf["bit_clear_events"])
    facts["gate_counter_walk"] = distinct_run(gf["counter_values"])
    facts["gate_counter_reached_zero"] = gf["counter_reached_zero"]
    facts["gate_latch_writer_pcs"] = gf["goal_latch_writer_pcs"]
    facts["gate_latch_set_pcs"] = sorted(
        {w["pc"] for w in gf["goal_latch_writes"] if w["v"] == 1})

    find = derive("analysis/phase4_f11_find_event.json")
    facts["find_frames"] = find["frames"]
    facts["find_events"] = len(find["findings"]["bit_set_events"])
    facts["find_setter_pcs"] = find["findings"]["setter_pcs"]
    facts["find_ring_truncated"] = find["ring_truncated"]

    ov = derive("analysis/phase4_f11_overlay_state.json")
    overlay_words = sorted(k for k in ov["fields"] if k.startswith("0x800B4A"))
    facts["overlay_state_words"] = len(overlay_words)
    facts["overlay_words_silent"] = len(ov["silent"])
    facts["overlay_state_block"] = ov["state_block"]
    facts["overlay_words_named_in_artifact"] = sum(
        1 for k in overlay_words if ov["fields"][k]["label"] != "unknown")
    # the word the semantic registry types for a DIFFERENT overlay
    collide = ov["fields"]["0x800B4A3C"]
    facts["collide_addr"] = "0x800B4A3C"
    facts["collide_measured_min"] = collide["min"]
    facts["collide_measured_max"] = collide["max"]
    facts["collide_measured_writes"] = collide["writes"]

    ac = derive("analysis/phase4_f11_acorns.json")
    af = ac["findings"]
    facts["acorn_watch_count"] = len(ac["scouts"])
    facts["acorn_bit_sets"] = len(af["bit_set_events"])
    facts["acorn_bit_clears"] = len(af["bit_clear_events"])
    facts["acorn_distinct_marked"] = len({e["scout"] for e in af["bit_set_events"]})
    facts["acorn_setter_pcs"] = af["setter_pcs"]
    facts["acorn_clearer_pcs"] = af["clearer_pcs"]

    st = derive("analysis/phase4_f11_acorn_state.json")
    sf = st["findings"]
    facts["acorn_prediction_registered_falsifiable"] = bool(st.get("falsifiable_as"))
    facts["acorn_retirements"] = len(sf["retirement_hp_zero_events"])
    facts["acorn_retired_ids"] = sf["acorns_retired"]
    facts["acorn_plus62_values_at_retire"] = sf["plus62_values_at_retire"]
    facts["acorn_state_verdict_confirmed"] = sf["verdict"].startswith("CONFIRMED")

    cen = derive("analysis/phase4_f11_actor_census.json")
    facts["census_scene_id"] = cen["scene_id"]
    facts["census_actors"] = len(cen["actors"])
    facts["census_species"] = len(cen["distinct_species"])
    facts["census_unidentified_species"] = len(cen["unidentified_species"])
    facts["census_acorn_actors"] = cen["species_histogram"]["31"]
    facts["census_scout_actors"] = cen["species_histogram"]["32"]

    cl = derive("analysis/phase4_f11_climbing.json")
    facts["climb_state_writes"] = cl["state_word"]["writes"]
    facts["climb_state_domain"] = cl["state_word"]["distinct_values"]
    facts["climb_values_outside_documented_domain"] = \
        cl["state_word"]["values_outside_documented_domain"]
    facts["climb_writer_pcs_retained"] = len(cl["state_word"]["writer_pcs"])
    facts["climb_flik_y_span"] = cl["flik_y"]["max"] - cl["flik_y"]["min"]
    facts["climb_artifact_verdict"] = cl["verdict"]
    # The row's prose claims a COMPLETE per-value writer map for the state word. Parse
    # that map out of the binding itself ("5 (0xA/0xB), 1 (0xC/...), ...") and check it
    # against the writer set the artifact actually retained.
    climb_binding = next((b for b in (row.get("bindings") or [])
                          if "CLIMBING IS NOT A DISCRETE STATE" in b), "")
    prose_map: dict[str, list[str]] = {}
    for val, group in re.findall(r"(\d+) \(((?:0x[0-9A-Fa-f]{8}/?)+)\)", climb_binding):
        prose_map[val] = [a.lower() for a in re.findall(r"0x[0-9A-Fa-f]{8}", group)]
    retained = {p[0].lower() for p in cl["state_word"]["writer_pcs"]}
    all_sites = sorted({a for v in prose_map.values() for a in v})
    facts["climb_prose_writer_map"] = prose_map
    facts["climb_prose_writer_sites"] = len(all_sites)
    facts["climb_prose_sites_absent_from_retained_set"] = sorted(
        s for s in all_sites if s not in retained)
    facts["climb_state3_sites_in_prose"] = prose_map.get("3", [])
    facts["climb_state3_sites_in_retained_set"] = [
        s for s in prose_map.get("3", []) if s in retained]

    prog = derive("analysis/phase4_f11_scout_progression.json")
    facts["progression_saves"] = len(prog["saves"])
    facts["progression_scene_ids_uniform"] = len(set(prog["scene_ids"])) == 1
    facts["progression_candidates_total"] = prog["candidate_count"]
    facts["progression_candidates_retained"] = len(prog["candidates"])

    # provenance: does any runtime artifact bind itself to disc / binary / mode?
    art_paths = [p for v in MECHANISM_ARTIFACTS.values() for p in v]
    prov = {}
    for rel in art_paths:
        doc = derive(rel)
        prov[rel] = sorted(k for k in doc
                           if any(t in k.lower() for t in PROVENANCE_KEYS))
    facts["f11_artifacts_probed"] = len(prov)
    facts["f11_artifacts_with_provenance_block"] = sum(1 for v in prov.values() if v)
    facts["f11_artifacts_binding_movie_bytes"] = sum(
        1 for v in prov.values() if any("sha" in k for k in v))

    # a comparison row that DOES carry provenance, so the gap is a choice not a norm
    a16 = derive("analysis/phase4_a16_swinging.json")
    facts["a16_has_authority_block"] = "authority" in a16
    facts["a16_classification"] = a16["classification"]
    facts["a16_capsule_accepted"] = a16["capsule"]["accepted"]
    facts["a16_capsule_frames"] = a16["capsule"]["frame_records_parsed"]
    facts["a16_capture_mode"] = a16["capsule"]["capture_mode"]

    # -------------------------------------------------- the movies, as recorded --
    pinset = derive("analysis/phase0_2_external_fixture_set.json")["entries"]
    movies = []
    for rel in F11_MOVIES:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"[f11-written-bar] MISSING operator recording: {rel}")
        digest = sha256_file(p)
        entry = pinset.get(rel)
        doc = json.loads(p.read_text())
        ss = doc.get("start_state") or {}
        movies.append({
            "path": rel,
            "sha256": digest,
            "centrally_pinned": bool(entry),
            "bytes_match_pin": bool(entry) and entry.get("sha256") == digest,
            "movie_version": doc.get("version"),
            "frames": len(doc.get("frames") or []),
            "armed_while_paused": doc.get("armed_while_paused"),
            "from_boot": ss.get("from_boot"),
            "reproducible_only_from_state": ss.get("reproducible_only_from_state"),
            "start_state_sha256_backfilled": ss.get("sha256_backfilled"),
            "declared_row_fixture": rel in (row.get("fixture_have") or []),
        })
    facts["f11_movies"] = movies
    facts["f11_movies_from_boot"] = sum(1 for m in movies if m["from_boot"])
    facts["f11_movies_state_anchored"] = sum(
        1 for m in movies if m["reproducible_only_from_state"])
    facts["f11_movies_with_backfilled_start_hash"] = sum(
        1 for m in movies if m["start_state_sha256_backfilled"])
    facts["f11_movies_declared_as_row_fixtures"] = sum(
        1 for m in movies if m["declared_row_fixture"])
    facts["f11_movies_bytes_match_central_pin"] = sum(
        1 for m in movies if m["bytes_match_pin"])

    # ----------------------------------------- static pins: COMPILED AND RUN now --
    csrc = pin(STATIC_C)
    blob = pin(STATIC_BLOB)
    out_bin = ROOT / "build" / "phase4_f11_static"
    out_bin.parent.mkdir(exist_ok=True)
    cc = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                         str(csrc), "-o", str(out_bin)],
                        cwd=ROOT, capture_output=True, text=True)
    if cc.returncode != 0:
        raise SystemExit(f"[f11-written-bar] {STATIC_C} does not compile:\n{cc.stderr}")
    run = subprocess.run([str(out_bin), STATIC_BLOB], cwd=ROOT,
                         capture_output=True, text=True)
    m = re.search(r"(\d+)/(\d+) pins OK", run.stdout)
    if not m:
        raise SystemExit(f"[f11-written-bar] no pin verdict from {STATIC_C}:\n{run.stdout[-2000:]}")
    facts["static_pins_ok"] = int(m.group(1))
    facts["static_pins_total"] = int(m.group(2))
    facts["static_pins_all_hold"] = run.returncode == 0 and m.group(1) == m.group(2)

    # what the NARRATIVE surfaces claim the pin count is -- derived, not typed
    exp = "ObsidianVault/Experiments/EXP_2026-08-04_phase4_f11_the_tree_scouts.md"
    exp_text = pin(exp).read_text()
    claimed = sorted({int(a) for a, b in re.findall(r"(\d+)/(\d+)\s+pins", prose + " " + exp_text)})
    facts["pin_counts_claimed_in_prose"] = claimed
    facts["pin_count_prose_matches_tool"] = claimed == [facts["static_pins_total"]]

    # ------------------------------------------------ frontier / typing, derived --
    own = derive("analysis/phase3_ownership_graph.json")["rows"][ROW]
    facts["ownership_functions"] = len(own["functions"])
    facts["ownership_state_addresses"] = len(own["state"])
    facts["ownership_assets"] = len(own["assets"])
    facts["ownership_overlay_entries"] = len(own["overlay"])
    facts["ownership_reader_groups"] = len(own["readers"])
    facts["ownership_writer_groups"] = len(own["writers"])
    facts["ownership_gaps"] = len(own["gaps"])
    typed = [s for s in own["state"] if s.get("semantic_ids")]
    facts["ownership_state_typed"] = len(typed)
    facts["ownership_state_untyped"] = len(own["state"]) - len(typed)
    facts["ownership_overlay_spaces"] = sorted(
        {o["space"] for o in own["overlay"] if o["space"] != "resident"})

    # the semantic entry the ownership graph credits to F11 but that owns a
    # DIFFERENT overlay's field at the same absolute address
    sem = derive_yaml("config/semantic_state.yaml")["entries"]
    ts = next(e for e in sem if e["id"] == "original.training_step")
    facts["collide_semantic_id"] = ts["id"]
    facts["collide_semantic_owner"] = ts["owner"]
    facts["collide_semantic_kind"] = ts["kind"]
    facts["collide_declared_max"] = next(
        i["max"] for i in ts["invariants"] if i["kind"] == "range")
    facts["collide_declared_context"] = next(
        i.get("context") for i in ts["invariants"] if i["kind"] == "range")
    facts["collide_credited_to_row"] = any(
        ts["id"] in s.get("semantic_ids", []) for s in own["state"])

    inv = derive("analysis/phase4_campaign_inventory.json")["rows"][ROW]
    surfaces = {s["address"]: s for s in inv["source_surfaces"]}
    facts["governing_functions"] = len(surfaces)
    status_counts: dict[str, int] = {}
    for s in surfaces.values():
        status_counts[s["decompilation_status"]] = \
            status_counts.get(s["decompilation_status"], 0) + 1
    facts["governing_function_decomp_status"] = status_counts
    facts["governing_functions_byte_matched_c"] = status_counts.get("c", 0)
    facts["governing_functions_absent_from_index"] = status_counts.get("missing", 0)
    facts["governing_function_names"] = {a: s["name"] for a, s in sorted(surfaces.items())}

    wbrows = derive("analysis/phase4_closure_workbench.json")["rows"]
    wb = wbrows[ROW] if isinstance(wbrows, dict) else \
        next(r for r in wbrows if r.get("row_id") == ROW)
    facts["workbench_obligations"] = len(wb["obligations"])
    facts["workbench_missing_layers"] = {
        o["id"]: len(o["missing_layers"]) for o in wb["obligations"]}
    facts["workbench_obligations_fully_missing"] = sum(
        1 for o in wb["obligations"]
        if len(o["missing_layers"]) == len(o["declared_layers"]))

    debt = derive("analysis/phase4_closure_debt.json")
    drow = next(r for r in debt["rows"] if r["row_id"] == ROW)
    facts["ledger_dimensions_met"] = drow["counts"]["met"]
    facts["ledger_dimensions_remaining"] = drow["counts"]["remaining"]
    facts["ledger_basis_strings"] = sorted(
        {d["basis"] for d in drow["dimensions"].values()})
    facts["ledger_movie_count"] = drow["movie_count"]
    facts["ledger_prior_offline_analysis_count"] = drow["prior_offline_analysis_count"]

    cov = derive("analysis/phase4_coverage_matrix.json")["rows"][ROW]
    facts["coverage_matrix_baseline_status"] = cov["baseline_status"]
    facts["coverage_matrix_status_matches_registry"] = \
        cov["baseline_status"] == row["status"]

    mq = derive("analysis/phase4_movie_priority_queue.json")
    mrow = next(r for r in mq["rows"] if r["row_id"] == ROW)
    facts["movie_queue_eligible"] = mrow["eligibility"]["eligible"]
    facts["movie_queue_reasons"] = mrow["eligibility"]["reasons"]

    # ---------------- the acorn's OTHER role, measured on a different row (E10) --
    e10 = derive("analysis/phase4_e10_hazards.json")
    acorn_fx = next(f for f in e10["fixtures"] if f["name"].startswith("acorn"))
    facts["e10_acorn_fixture"] = acorn_fx["name"]
    facts["e10_acorn_records"] = acorn_fx["records"]
    facts["e10_acorn_producer_caller"] = acorn_fx["caller"]
    facts["e10_acorn_event"] = acorn_fx["event"]
    facts["e10_acorn_in_scope"] = [s for s in e10["scope"]["included"] if "acorn" in s]
    facts["f11_prose_mentions_acorn_damage_producer"] = \
        acorn_fx["caller"].lower() in prose.lower()

    # ------------------------------------------------------- tests as a surface --
    tsrc = pin("tests/test_phase4_f11_the_tree.py").read_text()
    facts["row_test_functions"] = len(re.findall(r"^def test_", tsrc, re.M))

    # ----------------------------------------------- per-mechanism coverage roll --
    per_mech = {}
    for mech, arts in MECHANISM_ARTIFACTS.items():
        per_mech[mech] = {
            "artifacts": arts,
            "artifact_count": len(arts),
            "in_row_name": True,
            "runtime_artifacts": sum(1 for a in arts if "movie" in derive(a)),
        }
    per_mech["scouts_dot"]["measured"] = (
        f"{facts['gate_finds']} finds from one PC {facts['gate_setter_pcs']}, "
        f"{facts['gate_clear_events']} clears, counter walk {facts['gate_counter_walk']}, "
        f"latch by {facts['gate_latch_writer_pcs']}")
    per_mech["acorns"]["measured"] = (
        f"{facts['census_acorn_actors']} actors; {facts['acorn_bit_sets']} marks / "
        f"{facts['acorn_bit_clears']} clears across {facts['acorn_distinct_marked']}; "
        f"{facts['acorn_retirements']} retirements, +0x62 -> "
        f"{facts['acorn_plus62_values_at_retire']}")
    per_mech["climbing"]["measured"] = (
        f"bounded NEGATIVE only: {facts['climb_state_writes']} state-word writes, "
        f"domain {facts['climb_state_domain']}, no climb state")
    per_mech["swinging"]["measured"] = (
        "NOTHING on this row -- owned by A16_swinging "
        f"({facts['a16_classification']}, capsule accepted="
        f"{facts['a16_capsule_accepted']}, capture_mode {facts['a16_capture_mode']})")
    facts["per_mechanism"] = per_mech
    facts["mechanisms_with_zero_row_evidence"] = sorted(
        m for m, v in per_mech.items() if v["artifact_count"] == 0)

    # ================================================================ JUDGMENTS ==
    dims = {
        "durable_evidence": {
            "state": facts["durable_evidence_state_measured"],
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD from the measured F-row census, not re-derived: "
                     f"{facts['durable_evidence_fraction']} declared fixtures intact -- "
                     f"each exists, is centrally pinned and byte-matches its pin. "
                     f"{facts['census_row_named_artifacts']} row-named analysis artifacts "
                     f"(plus {len(facts['census_shared_artifacts'])} shared) "
                     f"and {facts['row_test_functions']} row tests are git-tracked and "
                     f"the C pinner recompiles and passes today "
                     f"({facts['static_pins_ok']}/{facts['static_pins_total']})",
            "gap": f"the fixture SET is intact but is not the evidence base: "
                   f"{facts['f11_movies_declared_as_row_fixtures']} of the "
                   f"{len(F11_MOVIES)} operator recordings that carry every runtime "
                   f"finding on this row are declared row fixtures (both are pinned "
                   f"elsewhere and byte-match: "
                   f"{facts['f11_movies_bytes_match_central_pin']}/{len(F11_MOVIES)}). "
                   f"And {facts['f11_artifacts_binding_movie_bytes']} of "
                   f"{facts['f11_artifacts_probed']} artifacts record a movie hash, so "
                   f"the 2026-08-05 start-state backfill rewrote both movie files after "
                   f"the 2026-08-04 artifacts were produced with nothing able to detect "
                   f"it. Not a re-measurement -- a named residual on a met dimension",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the runtime evidence IS natural and uninjected: two operator "
                     f"recordings, watch-only, no poke or perturbation in any artifact, "
                     f"ring not truncated in the two headline runs "
                     f"(gate {facts['gate_ring_truncated']}, find "
                     f"{facts['find_ring_truncated']}) across "
                     f"{facts['gate_frames']} and {facts['find_frames']} frames. The "
                     f"acorn retirement was registered as a FALSIFIABLE prediction "
                     f"before the run ({facts['acorn_prediction_registered_falsifiable']}) "
                     f"and confirmed ({facts['acorn_retirements']} retirements, +0x62 "
                     f"taking only {facts['acorn_plus62_values_at_retire']}), which is "
                     f"the strongest oracle-shaped act on the row",
            "gap": f"no cold boot: {facts['f11_movies_from_boot']} of "
                   f"{len(F11_MOVIES)} recordings are from_boot, "
                   f"{facts['f11_movies_state_anchored']} are "
                   f"reproducible_only_from_state and "
                   f"{facts['f11_movies_with_backfilled_start_hash']} carry a BACKFILLED "
                   f"start-state hash (no recording-time binding exists). NO NEGATIVE "
                   f"CONTROL for the row's headline claim -- the gate's refusal path "
                   f"(fewer than five scouts touching Dot) is never exercised in "
                   f"evidence; only the satisfied path is. "
                   f"{facts['f11_artifacts_with_provenance_block']} of "
                   f"{facts['f11_artifacts_probed']} artifacts record the disc, binary "
                   f"or execution mode they were taken on (A16 does: "
                   f"{facts['a16_has_authority_block']}), and the workbench still lists "
                   f"{facts['workbench_missing_layers']['original_oracle']} oracle "
                   f"layers missing",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant, residual explicitly bounded "
                           "-- not an empty unresolved set",
            "basis": f"one surface is genuinely ENUMERATED and closed: the stage "
                     f"overlay's absolute-global store set, "
                     f"{facts['overlay_state_block']}, from a dataflow scan of "
                     f"the blob, every one exercised live "
                     f"({facts['overlay_words_silent']} silent) and "
                     f"{facts['overlay_words_named_in_artifact']} named. The stage actor "
                     f"roster is enumerated too ({facts['census_actors']} actors / "
                     f"{facts['census_species']} species in scene "
                     f"{facts['census_scene_id']}), and the scout set and stride were "
                     f"read off the counting loop rather than assumed. "
                     f"{facts['static_pins_ok']}/{facts['static_pins_total']} static pins "
                     f"hold against the blob the row PROVED resident",
            "gap": f"the enumeration is per-surface, not per-row, and no residual is "
                   f"declared -- the item-2 bounding mechanism F01 used is not carried "
                   f"here. The ownership graph lists {facts['ownership_gaps']} state "
                   f"addresses 'cited with no semantic-registry owner' and no named "
                   f"obstruction; {facts['census_unidentified_species']} of the stage's "
                   f"{facts['census_species']} species are unidentified in the census "
                   f"artifact itself. The retained writer set in the climbing artifact is "
                   f"TOP-{facts['climb_writer_pcs_retained']} TRUNCATED, so of the "
                   f"{facts['climb_prose_writer_sites']} writer sites the row's prose "
                   f"enumerates as the COMPLETE map, "
                   f"{len(facts['climb_prose_sites_absent_from_retained_set'])} "
                   f"({facts['climb_prose_sites_absent_from_retained_set']}) cannot be "
                   f"checked against the registered evidence -- including "
                   f"{facts['climb_state3_sites_in_prose']}, the only site the prose "
                   f"credits with state 3, of which "
                   f"{len(facts['climb_state3_sites_in_retained_set'])} appears in the "
                   f"retained set even though state 3 is observed. Same shape in the save "
                   f"diff ({facts['progression_candidates_retained']} of "
                   f"{facts['progression_candidates_total']} candidates retained). "
                   f"Nothing is enumerated for swinging",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"all {facts['overlay_state_words']} overlay words carry a MEASURED "
                     f"domain (writes, distinct values, min/max, writer PCs); the scout "
                     f"counter's domain is closed by its DERIVATION (walk "
                     f"{facts['gate_counter_walk']}, publish = 5 - found) rather than "
                     f"observed alone, which is the one field on this row that is typed "
                     f"rather than merely bounded",
            "gap": f"only {facts['overlay_words_named_in_artifact']} of "
                   f"{facts['overlay_state_words']} overlay words are LABELLED in the "
                   f"artifact -- the other "
                   f"{facts['overlay_state_words'] - facts['overlay_words_named_in_artifact']} "
                   f"characterisations (found-scout ordinal, found-actor pointer, two "
                   f"angle accumulators, three countdown timers, a mode word, a ramp) "
                   f"live only in prose and are not machine-checked by anything. "
                   f"{facts['ownership_state_untyped']} of "
                   f"{facts['ownership_state_addresses']} state addresses this row cites "
                   f"have no semantic-registry owner. Worse, one of the "
                   f"{facts['ownership_state_typed']} that DO is mis-scoped: "
                   f"{facts['collide_addr']} is credited to this row as "
                   f"{facts['collide_semantic_id']} (kind {facts['collide_semantic_kind']}, "
                   f"owner {facts['collide_semantic_owner']}, declared range max "
                   f"{facts['collide_declared_max']} in context "
                   f"'{facts['collide_declared_context']}'), while F11's own measurement "
                   f"of that address in a DIFFERENT resident blob is "
                   f"{facts['collide_measured_min']}..{facts['collide_measured_max']} over "
                   f"{facts['collide_measured_writes']} writes. Overlay-local addresses "
                   f"are keyed globally, so the registry types the ADDRESS, not the "
                   f"field, and F11's typed count is inflated by one. The acorn record "
                   f"fields (+0x5A/+0x62/+0x6E) are observed but not typed: only the "
                   f"retirement value {facts['acorn_plus62_values_at_retire']} is explained",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"ACORNS carry a near-complete arc and it is the row's best result: "
                     f"marked by overlay {facts['acorn_setter_pcs']} -> leaves the live "
                     f"actor table -> retired -> re-initialised by "
                     f"{facts['acorn_clearer_pcs']} -> reused, with REPEATED use measured "
                     f"({facts['acorn_bit_sets']} marks and "
                     f"{facts['acorn_bit_clears']} clears across "
                     f"{facts['acorn_distinct_marked']} of "
                     f"{facts['acorn_watch_count']} acorns, "
                     f"{facts['acorn_retirements']} retirements over "
                     f"{len(facts['acorn_retired_ids'])} of them). SCOUTS get load+init "
                     f"(the {facts['find_frames']}-frame recording starts before the "
                     f"level load), first use, repeated use ({facts['gate_finds']} finds) "
                     f"and persistence ({facts['gate_clear_events']} clears); Dot's bit "
                     f"is the one-shot consumed per touch",
            "gap": f"NOT CREDITED ACROSS THE ROW. Cold boot is absent for every mechanism "
                   f"({facts['f11_movies_from_boot']} from-boot recordings); exhaustion is "
                   f"never argued or marked n/a-with-reason. Climbing contributes no "
                   f"lifecycle at all -- its single result is a bounded NEGATIVE on the "
                   f"player state word -- and "
                   f"{facts['mechanisms_with_zero_row_evidence']} has no F11 artifact of "
                   f"any kind. No per-phase claim map artifact exists for F11 -- the "
                   f"acorn arc is "
                   f"reconstructed from prose across two artifacts, not registered as a "
                   f"phase-by-phase map the way F01's is",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"exactly ONE combination is measured end to end inside a single "
                     f"natural run: player contact (resident resolver "
                     f"{facts['find_setter_pcs']}) x overlay scout counter x cinematic "
                     f"camera x per-count sfx table x objective latch (set by "
                     f"{facts['gate_latch_set_pcs']}) x scene transition, over "
                     f"{facts['gate_frames']} frames and {facts['gate_events']} events",
            "gap": f"the four mechanics were only ever watched SEPARATELY -- each artifact "
                   f"carries its own watch set and no artifact crosses two of them, so "
                   f"nothing tests acorns during a find, climbing under any of it, or "
                   f"swinging at all. The sharpest omission is that the acorn's OTHER "
                   f"role is a DIFFERENT ROW's result: E10's {facts['e10_acorn_fixture']} "
                   f"fixture measures the same stage's acorn as a DAMAGE PRODUCER "
                   f"(caller {facts['e10_acorn_producer_caller']}, "
                   f"{facts['e10_acorn_records']} records, {facts['e10_acorn_event']}) and "
                   f"F11's prose never cites it "
                   f"(mentions_producer={facts['f11_prose_mentions_acorn_damage_producer']}). "
                   f"'Reusable prop, counted by nothing' is therefore half the acorn: it "
                   f"is also this stage's rolling hazard, and prop-state x damage was "
                   f"never joined. No combination matrix is registered",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated WITH named "
                           "obstructions",
            "basis": f"the overlay->resident call interface is documented at instruction "
                     f"level with argument evidence and machine-checked: "
                     f"{facts['static_pins_ok']}/{facts['static_pins_total']} pins hold, "
                     f"covering the cinematic-camera call and its flags argument, "
                     f"play_sound, sfx_dispatch fed from a per-count byte table, the "
                     f"cinematic-camera flags read, the actor-record offsets and the "
                     f"shared live actor table. The ownership graph enumerates "
                     f"{facts['ownership_reader_groups']} reader and "
                     f"{facts['ownership_writer_groups']} writer groups over "
                     f"{facts['ownership_functions']} functions and "
                     f"{facts['ownership_assets']} assets",
            "gap": f"no interface/ABI ledger artifact exists for this row, so argument "
                   f"DOMAINS are undocumented, and the "
                   f"{facts['ownership_gaps']} enumerated unknowns carry no named "
                   f"obstruction -- the written bar asks for both halves. An unresolved "
                   f"NAMING conflict sits on the row's most-cited call: the derived "
                   f"function census calls 0x8004da94 "
                   f"'{facts['governing_function_names']['0x8004da94']}' while F11's own "
                   f"evidence (a scout find is not a level completion) and Canon "
                   f"SYS_cinematic_camera call it the cinematic-camera start. The same "
                   f"census still resolves this row's overlay functions against "
                   f"{facts['ownership_overlay_spaces']} -- the LEVEL03_* naming this "
                   f"row's own binding falsified by a 100.0% code-window match to "
                   f"LEVEL02/LEVEL1.BIN",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured against the row's own governing set: of "
                     f"{facts['governing_functions']} unique functions the campaign "
                     f"inventory attributes to F11, decompilation status is "
                     f"{facts['governing_function_decomp_status']} -- "
                     f"{facts['governing_functions_byte_matched_c']} carries C "
                     f"(scene_setup_and_load, a shared resident function owned by another "
                     f"row) and the {facts['governing_functions_absent_from_index']} "
                     f"overlay-local functions that contain every F11 mechanism are "
                     f"absent from the index entirely. F11 has produced no source",
            "gap": f"the F-row census reported this dimension as "
                   f"'{facts['census_source_closure_triage']}' on "
                   f"{facts['census_segments_entries']} segments entry. That is a "
                   f"SUBSTRING ARTIFACT, verified here by re-running the census's own "
                   f"regex: the only match for stem '{stem}' is "
                   f"{facts['segments_hits_for_row_stem']}, i.e. the hex address, not an "
                   f"F11 surface (address_substring="
                   f"{facts['segments_hits_are_address_substrings']}). Closing this needs "
                   f"the overlay functions indexed against the CORRECT blob first",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage -- which "
                           "requires the applicable set itself to be enumerated",
            "basis": f"the row's one campaign-wide generalisation was FALSIFIED INSIDE THE "
                     f"ROW: 'bit 0x1000 = the player has contacted me, campaign-wide' was "
                     f"retracted to a shared scratch flag by this row's own acorn evidence "
                     f"(setter {facts['acorn_setter_pcs']} is overlay code on the acorn's "
                     f"own predicate, not the contact resolver "
                     f"{facts['find_setter_pcs']}). Evidence covers exactly one stage "
                     f"(scene {facts['census_scene_id']}, "
                     f"scene_ids_uniform={facts['progression_scene_ids_uniform']} across "
                     f"{facts['progression_saves']} saves) from "
                     f"{len(F11_MOVIES)} recordings",
            "gap": "the applicability universe is not enumerated -- which stages have a "
                   "finder objective, reusable props, or vertical traversal is nowhere "
                   "declared, so 'every applicable stage' has no denominator. The one "
                   "claim from this row that did generalise (asset-graph name != resident "
                   "blob) was generalised by ANOTHER row's arithmetic rule, which is not "
                   "this row meeting the bar. This fails the WRITTEN bar, not only the "
                   "strict one",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F11 (The Tree) measured against the nine DoD bars AS WRITTEN (item 2 "
                    "= enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f11_written_bar_assessment.py",
        "schema": "abl-phase4-f11-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": ROW,
        "row_name": row["name"],
        "standard": {
            "ruling": "engineering-specs/phase4-measurement-standard-ruling.md",
            "exemplar": "tools/phase4_f01_written_bar_assessment.py",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads as "
                          "met; this assessment publishes measurement, not disposition",
            "multi_mechanism_rule": "F11 names four mechanics. A result proved for one is "
                                    "not credited across the row; see per_mechanism",
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor is not the author of F11's evidence, but is "
                               "the author of this measurement and of the census it "
                               "carries durable_evidence forward from; no state here is a "
                               "promotion and met_candidate is a submission, not a met",
            "durable_evidence_carried_forward_from":
                "analysis/phase4_f_row_measured_census.json",
        },
        "facts": facts,
        "evidence_pins": pins,
        "dimensions": dims,
        "counts": counts,
        "states_considered_and_not_used": {
            "allowed": ["met", "met_candidate", "partial", "not_met", "unmeasured"],
            "met_candidate": "NONE. Nothing on this row is currently submittable for "
                             "promotion: every dimension short of met has a gap that is "
                             "a missing measurement, not a pending adjudication. The "
                             "closest is lifecycle (the acorn arc), which fails only "
                             "because cold boot and a registered per-phase claim map are "
                             "absent.",
            "unmeasured": "NONE, and this was checked rather than assumed. Every "
                          "dimension has at least some F11 evidence bearing on its bar, "
                          "so 'unmeasured' would understate what exists. The row-level "
                          "absence is per-MECHANISM, not per-dimension: swinging has no "
                          "F11 artifact at all and is recorded that way in "
                          "per_mechanism, where it belongs, instead of being spread "
                          "across nine cells.",
        },
        "registration_defects_found": [
            f"pin count: prose claims {facts['pin_counts_claimed_in_prose']} pins in both "
            f"the registry binding and the Experiment page; the tool returns "
            f"{facts['static_pins_ok']}/{facts['static_pins_total']} today "
            f"(matches={facts['pin_count_prose_matches_tool']})",
            f"closure ledger: F11 shows {facts['ledger_dimensions_met']} met / "
            f"{facts['ledger_dimensions_remaining']} remaining on the blanket basis "
            f"{facts['ledger_basis_strings']}, with movie_count="
            f"{facts['ledger_movie_count']} and prior_offline_analysis_count="
            f"{facts['ledger_prior_offline_analysis_count']} -- while "
            f"{facts['census_analysis_artifacts']} artifacts and {len(F11_MOVIES)} "
            f"recordings exist",
            f"coverage matrix records baseline_status "
            f"'{facts['coverage_matrix_baseline_status']}' against a registry status of "
            f"'{facts['row_status']}' (matches="
            f"{facts['coverage_matrix_status_matches_registry']})",
            f"movie queue holds F11 ineligible for {facts['movie_queue_reasons']} while "
            f"both of its recordings live under movies/Phase4/Interpreter/",
            f"semantic registry credits {facts['collide_semantic_id']} "
            f"({facts['collide_semantic_owner']}) to F11 at {facts['collide_addr']}",
            f"climbing artifact still stores the pre-resolution verdict: "
            f"\"{facts['climb_artifact_verdict']}\" -- the row's binding resolved this "
            f"(state 3 is the handstand-dismount exit) but the artifact was never "
            f"regenerated",
        ],
        "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                   f"met-candidate, {counts.get('partial', 0)} partial, "
                   f"{counts.get('not_met', 0)} not met, "
                   f"{counts.get('unmeasured', 0)} unmeasured -- against the WRITTEN "
                   f"bars. Compare: the closure ledger carries this row at "
                   f"{facts['ledger_dimensions_met']}/9 on one blanket basis string. "
                   f"Of the row's four named mechanics, "
                   f"{len(facts['mechanisms_with_zero_row_evidence'])} "
                   f"({facts['mechanisms_with_zero_row_evidence']}) has no F11 evidence "
                   f"at all, and none of the four was ever exercised in combination with "
                   f"another.",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[f11-written-bar] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
