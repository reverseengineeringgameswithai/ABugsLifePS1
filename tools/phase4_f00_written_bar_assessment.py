#!/usr/bin/env python3
"""Measure F00_training's nine DoD dimensions against the bars AS WRITTEN.

Sibling of `tools/phase4_f01_written_bar_assessment.py` (the exemplar) and
`tools/phase4_f08_written_bar_assessment.py` (the rigor standard), under
`engineering-specs/phase4-measurement-standard-ruling.md`. The WRITTEN bars are:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

WHY F00 IS AN UNUSUAL SHAPE. It is the F row with the MOST documentation (17 vault
pages, more than any other) and the LEAST registered campaign machinery (closure
debt 0/9 by one blanket basis, movie_count 0, no gate naming the row). It is also
the only F row the census credits with `source_files` -- and that credit is the
first thing this assessment tests, because `src_re/` is RE PROSE, not a build
registry: it appears in neither config/segments.yml nor config/overlays.yml, and
`src_re/training_tutorial_progression.c` says of itself "This is RE pseudocode. It
is not compiled into the mod." Its real byte-matched C is somewhere else entirely.

So this assessment separates, per dimension, what is DOCUMENTED about Training from
what is MEASURED about it, and it adds two new measurements of its own so the
separation is not itself an opinion.

Design (identical to the exemplar):
  * every FACT is read from a cited artifact at run time and the artifact is
    sha256-pinned, so a stale citation fails LOUDLY instead of aging silently.
    `fact()` cannot record a value without naming the artifact it came from, and
    `req()` raises on a missing key rather than substituting a default;
  * every JUDGMENT is authored and attributable, and carries `written_bar` /
    `basis` / `gap`;
  * `unmeasured` is an allowed and expected state. Evidence is not stretched to
    fill a cell.

durable_evidence is NOT re-derived here: it was MEASURED in
`analysis/phase4_f_row_measured_census.json` (2/2 declared fixtures intact) and is
carried forward with its fraction, failing loudly if that measurement moves.

TWO SYSTEMIC DEFECTS ARE CHECKED EXPLICITLY:
  (a) OVERLAY MISATTRIBUTION -- every per-level overlay loads at the same base
      (region A, 0x800B39A0), so an address in that window names real content in
      most images and an address-only census picks the wrong file.
      `tools/phase4_f08_overlay_residency_pin.c` is reused UNCHANGED (its output
      keeps that tool's F08 branding strings, which this assessment records rather
      than edits) to decide from bytes, across every image and both pinned Training
      fixtures, which file is resident.
  (b) SEMANTIC-REGISTRY COLLISION -- config/semantic_state.yaml keys overlay-local
      addresses GLOBALLY with no image field, and this row's registered address has
      already been attributed to three rows. `tools/phase4_f00_state_owner_probe.c`
      (compiled C owns instruction decoding) re-decides readers, writers and
      cross-image ambiguity from bytes.

BOTH SOURCE REGISTRIES ARE READ before any source_closure claim: config/segments.yml
(resident) and config/overlays.yml + src/overlays/ + analysis/overlay_decomp_progress.json
(overlay track). A claim that overlay byte-matching is impossible was banked and
retracted for checking only the first.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a fresh
detached verifier. This tool never edits analysis/mechanics_baseline.yaml.

Usage: python3 tools/phase4_f00_written_bar_assessment.py [--out PATH] [--no-gates]
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
ROW_ID = "F00_training"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class Evidence:
    """Loads + pins artifacts, and records which artifact every fact came from."""

    def __init__(self) -> None:
        self.pins: list[dict] = []
        self._seen: set[str] = set()
        self.facts: dict[str, object] = {}
        self.provenance: dict[str, object] = {}

    def pin(self, rel: str) -> Path:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"STALE CITATION: {rel} does not exist")
        if rel not in self._seen:
            self._seen.add(rel)
            self.pins.append({"path": rel, "sha256": sha256_file(p)})
        return p

    def json(self, rel: str) -> dict:
        return json.loads(self.pin(rel).read_text())

    def yaml(self, rel: str) -> dict:
        return yaml.safe_load(self.pin(rel).read_text())

    def text(self, rel: str) -> str:
        return self.pin(rel).read_text(errors="ignore")

    def fact(self, key: str, value, source):
        """Record a fact. Impossible to record one without naming its artifact(s)."""
        srcs = [source] if isinstance(source, str) else list(source)
        if not srcs:
            raise SystemExit(f"fact '{key}' names no artifact")
        for s in srcs:
            if s not in self._seen:
                raise SystemExit(f"fact '{key}' cites unpinned artifact {s}")
        self.facts[key] = value
        self.provenance[key] = srcs[0] if len(srcs) == 1 else srcs
        return value


def req(doc, *path, where: str = ""):
    """Strict lookup: a missing key is a stale citation, not a default."""
    cur = doc
    for k in path:
        try:
            cur = cur[k]
        except (KeyError, IndexError, TypeError):
            raise SystemExit(
                f"STALE CITATION: {where or 'artifact'} no longer has "
                f"{'.'.join(str(x) for x in path)} (failed at {k!r})")
    return cur


def as_int(v) -> int:
    return v if isinstance(v, int) else int(str(v), 16)


def selftest_guards() -> list[str]:
    """Prove the fail-loud machinery still fails, every run.

    Out-of-band probes (moving a pinned artifact aside, renaming a key inside one,
    drifting a derived input away from the C scan it is checked against) are run by
    hand and each must abort with a non-zero exit and no output file. Those are
    one-off. These three are in-band and re-run on every generation, so a future
    refactor that turns a guard into a silent default is caught here rather than
    discovered later in a stale number.
    """
    fired = []
    probe = Evidence()
    try:
        probe.pin("analysis/__this_artifact_does_not_exist__.json")
    except SystemExit:
        fired.append("missing_artifact_aborts")
    try:
        req({"a": {"b": 1}}, "a", "renamed_key", where="synthetic")
    except SystemExit:
        fired.append("renamed_key_aborts")
    try:
        probe.fact("x", 1, "analysis/never_pinned.json")
    except SystemExit:
        fired.append("fact_without_a_pinned_source_aborts")
    if len(fired) != 3:
        raise SystemExit("FAIL-LOUD MACHINERY IS BROKEN: only these guards fired: "
                         f"{fired}. Refusing to emit an assessment whose staleness "
                         "detection cannot be trusted.")
    return fired


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(ROOT / "analysis/phase4_f00_written_bar_assessment.json"))
    ap.add_argument("--no-gates", action="store_true",
                    help="skip executing this row's registered pytest gates")
    args = ap.parse_args()

    E = Evidence()
    F = E.facts

    # ------------------------------------------------------------------ #
    # 0. prove the staleness detection works before trusting any number   #
    # ------------------------------------------------------------------ #
    SELF = "tools/phase4_f00_written_bar_assessment.py"
    E.pin(SELF)
    E.fact("fail_loud_guards_fired", selftest_guards(), SELF)

    # ------------------------------------------------------------------ #
    # 1. durable_evidence -- CARRIED FORWARD from the measured census.    #
    # ------------------------------------------------------------------ #
    CENSUS = "analysis/phase4_f_row_measured_census.json"
    census = E.json(CENSUS)
    crow = req(census, "rows", ROW_ID, where=CENSUS)
    E.fact("census_durable_state", req(crow, "durable_evidence", "state", where=CENSUS), CENSUS)
    E.fact("census_durable_fraction",
           req(crow, "durable_evidence", "intact_pinned", where=CENSUS), CENSUS)
    E.fact("census_durable_reason",
           req(crow, "durable_evidence", "reason", where=CENSUS), CENSUS)
    E.fact("census_row_status", req(crow, "status", where=CENSUS), CENSUS)
    E.fact("census_baseline_sha256", req(census, "baseline_sha256", where=CENSUS), CENSUS)
    E.fact("census_triage", req(crow, "measurability_triage", where=CENSUS), CENSUS)
    inv = req(crow, "evidence_inventory", where=CENSUS)
    E.fact("census_analysis_artifacts_credited",
           len(req(inv, "analysis_artifacts", where=CENSUS)), CENSUS)
    E.fact("census_analysis_artifacts", req(inv, "analysis_artifacts", where=CENSUS), CENSUS)
    E.fact("census_vault_pages_credited", len(req(inv, "vault_pages", where=CENSUS)), CENSUS)
    E.fact("census_source_files", req(inv, "source_files", where=CENSUS), CENSUS)
    E.fact("census_segments_entries", req(inv, "segments_entries", where=CENSUS), CENSUS)
    E.fact("census_overlay_build_entries", req(inv, "overlay_build_entries", where=CENSUS),
           CENSUS)
    E.fact("census_overlay_matched_sources",
           req(inv, "overlay_matched_sources", where=CENSUS), CENSUS)
    E.fact("census_overlay_name", req(inv, "overlay_name", where=CENSUS), CENSUS)
    E.fact("census_scene_id", req(inv, "scene_id", where=CENSUS), CENSUS)
    E.fact("census_stage_ordinal", req(inv, "stage_ordinal", where=CENSUS), CENSUS)
    E.fact("census_has_static_code_evidence",
           req(inv, "has_static_code_evidence", where=CENSUS), CENSUS)
    E.fact("census_has_runtime_trace_evidence",
           req(inv, "has_runtime_trace_evidence", where=CENSUS), CENSUS)
    E.fact("census_overlay_track_totals", req(inv, "overlay_track_totals", where=CENSUS),
           CENSUS)

    fixtures = req(crow, "durable_evidence", "fixtures", where=CENSUS)
    external = [f["path"] for f in fixtures
                if req(f, "kind", where=CENSUS) == "external_fixture"]
    E.fact("row_external_fixtures", external, CENSUS)
    E.fact("row_external_fixture_count", len(external), CENSUS)
    if F["census_durable_state"] != "met":
        raise SystemExit("carried-forward durable_evidence is no longer 'met' -- "
                         "re-measure before reusing this assessment")

    # Is this row really the only F row with a source credit, and what KIND is it?
    all_rows = req(census, "rows", where=CENSUS)
    E.fact("f_rows_censused", len(all_rows), CENSUS)
    E.fact("f_rows_with_any_source_files",
           sorted(r for r, v in all_rows.items()
                  if req(v, "evidence_inventory", "source_files", where=CENSUS)), CENSUS)
    E.fact("f_rows_with_any_segments_entries",
           sorted(r for r, v in all_rows.items()
                  if req(v, "evidence_inventory", "segments_entries", where=CENSUS)), CENSUS)
    E.fact("f_rows_with_an_overlay_build_entry",
           sorted(r for r, v in all_rows.items()
                  if req(v, "evidence_inventory", "overlay_build_entries", where=CENSUS)),
           CENSUS)
    E.fact("f_rows_with_more_vault_pages_than_this_one",
           sorted(r for r, v in all_rows.items()
                  if len(req(v, "evidence_inventory", "vault_pages", where=CENSUS))
                  > F["census_vault_pages_credited"]), CENSUS)

    # ------------------------------------------------------------------ #
    # 2. the registry's own disposition for this row                      #
    # ------------------------------------------------------------------ #
    DEBT = "analysis/phase4_closure_debt.json"
    debt = E.json(DEBT)
    drow = next((r for r in req(debt, "rows", where=DEBT) if r.get("row_id") == ROW_ID), None)
    if drow is None:
        raise SystemExit(f"STALE CITATION: {DEBT} no longer carries {ROW_ID}")
    E.fact("registry_dimensions_met", req(drow, "counts", "met", where=DEBT), DEBT)
    E.fact("registry_dimensions_remaining", req(drow, "counts", "remaining", where=DEBT), DEBT)
    E.fact("registry_distinct_bases",
           sorted({d["basis"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
    E.fact("registry_distinct_states",
           sorted({d["state"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
    E.fact("registry_completion_state", req(drow, "completion_state", where=DEBT), DEBT)
    E.fact("registry_campaign_id", req(drow, "campaign_id", where=DEBT), DEBT)
    E.fact("registry_movie_count", req(drow, "movie_count", where=DEBT), DEBT)
    E.fact("registry_capsule_count", req(drow, "capsule_count", where=DEBT), DEBT)
    E.fact("registry_prior_offline_analysis_count",
           req(drow, "prior_offline_analysis_count", where=DEBT), DEBT)
    E.fact("registry_next_lane_reason", req(drow, "next_lane_reason", where=DEBT), DEBT)

    # ------------------------------------------------------------------ #
    # 3. the baseline row itself (read-only; this tool never edits it)    #
    # ------------------------------------------------------------------ #
    BASE = "analysis/mechanics_baseline.yaml"
    base = E.yaml(BASE)
    rows = req(base, "rows", where=BASE)
    row = next((r for r in rows if r.get("id") == ROW_ID), None)
    if row is None:
        raise SystemExit(f"STALE CITATION: {BASE} no longer carries {ROW_ID}")
    E.fact("baseline_sha256_matches_census",
           sha256_file(ROOT / BASE) == F["census_baseline_sha256"], [BASE, CENSUS])
    E.fact("row_binding_claims", len(req(row, "bindings", where=BASE)), BASE)
    E.fact("row_bindings", req(row, "bindings", where=BASE), BASE)
    E.fact("row_declared_fixture_paths", req(row, "fixture_have", where=BASE), BASE)
    E.fact("row_declared_missing", req(row, "missing", where=BASE), BASE)
    E.fact("row_declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
    E.fact("row_declared_evidence_classes", req(row, "evidence", where=BASE), BASE)
    E.fact("row_declared_next", req(row, "next", where=BASE), BASE)
    E.fact("row_declared_status", req(row, "status", where=BASE), BASE)
    E.fact("row_declared_stages", str(req(row, "stages", where=BASE)), BASE)
    E.fact("row_artifact_path_citations",
           sorted(set(re.findall(r"(?:analysis|tools|src|src_re|tests|config)/[\w./%-]+",
                                 json.dumps(row)))), BASE)
    E.fact("row_artifact_path_citation_count", len(F["row_artifact_path_citations"]), BASE)
    E.fact("dod_dimension_prose", req(base, "dimensions", where=BASE), BASE)

    # ------------------------------------------------------------------ #
    # 4. THE MAPPING: stage ordinal -> scene -> overlay, and the LEVEL00  #
    #    negative. Training is the one stage whose folk name (LEVEL00) is #
    #    a different disc directory from the one it actually loads.       #
    # ------------------------------------------------------------------ #
    GRAPH3 = "analysis/phase3_scene_asset_graph.json"
    g3 = E.json(GRAPH3)
    numbering = req(g3, "operator_level_numbering", where=GRAPH3)
    m = re.search(r"(0x[0-9A-Fa-f]{8}) maps the player-facing level ordinal", numbering)
    if not m:
        raise SystemExit(f"STALE CITATION: {GRAPH3} no longer names the progression table "
                         "address in operator_level_numbering")
    E.fact("progression_table_address", m.group(1), GRAPH3)
    tbl = re.search(r"\[([-\d,\s]+)\]", numbering)
    if not tbl:
        raise SystemExit(f"STALE CITATION: {GRAPH3} no longer prints the progression table")
    progression = [int(x) for x in tbl.group(1).split(",")]
    E.fact("progression_table", progression, GRAPH3)
    E.fact("training_ordinal", 0, GRAPH3)
    E.fact("scene_from_progression_table", progression[0], GRAPH3)
    E.fact("scene_matches_the_census_binding",
           progression[0] == F["census_scene_id"], [GRAPH3, CENSUS])
    scene_key = f"scene_{progression[0]:02d}"
    sc = req(g3, "scenes", scene_key, where=GRAPH3)
    E.fact("scene_disc_dir", req(sc, "disc_dir", where=GRAPH3), GRAPH3)
    E.fact("scene_level_data", req(sc, "level_data", where=GRAPH3), GRAPH3)
    E.fact("scene_vab_dir", req(sc, "vab_dir", where=GRAPH3), GRAPH3)
    E.fact("scene_vab_dir_matches_disc_dir",
           req(sc, "vab_dir_matches_disc_dir", where=GRAPH3), GRAPH3)
    E.fact("scene_phase2_stage_labels", req(sc, "phase2_stage_labels", where=GRAPH3), GRAPH3)
    E.fact("phase3_law_is_the_corrected_one",
           "CORRECTED 2026-08-01" in req(g3, "law", where=GRAPH3), GRAPH3)

    BIND = "analysis/phase4_f08_scene_binding.json"
    bindj = E.json(BIND)
    E.fact("law_directory_for_this_scene",
           req(bindj, "scene_id_to_level_data_dir", str(progression[0]), where=BIND), BIND)
    E.fact("law_string_dir_diverges_for_ids",
           req(bindj, "string_dir_vs_arithmetic_dir", "diverge_for_ids", where=BIND), BIND)
    E.fact("this_scene_is_a_string_dir_divergence",
           progression[0] in [int(x) for x in str(F["law_string_dir_diverges_for_ids"])
                              .split(",")], BIND)
    E.fact("prior_prose_residency_claim",
           req(bindj, "string_dir_vs_arithmetic_dir", "proof", where=BIND), BIND)
    E.fact("prior_prose_residency_claim_names_the_same_two_saves",
           all(s in req(bindj, "string_dir_vs_arithmetic_dir", "proof", where=BIND)
               for s in ["training_all_stuff_collected_ending.sav",
                         "phase3_pristine_training_gameplay_i5.sav"]), BIND)
    E.fact("law_arithmetic_mechanism",
           req(bindj, "mechanism", "level_data_directory", where=BIND), BIND)
    E.fact("law_arithmetic_instruction_pcs",
           sorted(set(re.findall(r"0x[0-9A-Fa-f]{8}",
                                 req(bindj, "mechanism", "level_data_directory",
                                     where=BIND)))), BIND)

    E08 = "analysis/phase4_e08_object_census.json"
    e08 = E.json(E08)
    lv = req(e08, "levels", where=E08)
    dat_dir = F["scene_disc_dir"].upper()
    dat_name = req(F["scene_level_data"], "dat", where=GRAPH3)
    this_dat = f"{dat_dir}/{dat_name}"
    if this_dat not in lv:
        raise SystemExit(f"STALE CITATION: {E08} no longer censuses {this_dat}")
    E.fact("this_stage_level_dat", this_dat, [E08, GRAPH3])
    E.fact("this_stage_type3f_entries", req(lv, this_dat, "type3f_entries", where=E08), E08)
    E.fact("this_stage_type3f_kind_histogram",
           req(lv, this_dat, "type3f_kind_histogram", where=E08), E08)
    folk = "LEVEL00/LEVEL.DAT"
    if folk not in lv:
        raise SystemExit(f"STALE CITATION: {E08} no longer censuses {folk}")
    E.fact("folk_named_level00_dat_type3f_entries",
           req(lv, folk, "type3f_entries", where=E08), E08)
    E.fact("folk_named_level00_dat_type3f_tables",
           req(lv, folk, "type3f_tables", where=E08), E08)

    BOARD = "tools/training_board_edit.py"
    board = E.text(BOARD)
    tf = re.search(r'^TARGET_FILE\s*=\s*"([^"]+)"', board, re.M)
    if not tf:
        raise SystemExit(f"STALE CITATION: {BOARD} no longer declares TARGET_FILE")
    E.fact("board_editor_target_file", tf.group(1), BOARD)
    E.fact("board_editor_target_agrees_with_the_law",
           tf.group(1).split("/")[0].lower() == F["scene_disc_dir"].lower(),
           [BOARD, GRAPH3])
    E.fact("board_editor_still_carries_stale_level01_prose",
           bool(re.search(r"LEVEL01", board)), BOARD)

    # ------------------------------------------------------------------ #
    # 5. NEW MEASUREMENT A -- defect (a): which overlay FILE is resident, #
    #    decided by BYTES over every image and both pinned fixtures.      #
    # ------------------------------------------------------------------ #
    OVLY = "config/overlays.yml"
    ovly = E.yaml(OVLY)
    region_a = as_int(req(ovly, "region_a", where=OVLY))
    region_b = as_int(req(ovly, "region_b", where=OVLY))
    ovl_name = F["census_overlay_name"]
    ovl_entry = req(ovly, "overlays", ovl_name, where=OVLY)
    E.fact("overlay_registry_region_a", f"0x{region_a:08X}", OVLY)
    E.fact("overlay_registry_region_length", region_b - region_a, OVLY)
    E.fact("overlay_registry_entry_blob", req(ovl_entry, "blob", where=OVLY), OVLY)
    E.fact("overlay_registry_entry_sha1", req(ovl_entry, "sha1", where=OVLY), OVLY)
    E.fact("overlay_registry_total_overlays", len(req(ovly, "overlays", where=OVLY)), OVLY)

    # the RE source is the ONLY artifact that names this overlay's state words.
    RESRC = "src_re/training_tutorial_progression.c"
    resrc = E.text(RESRC)
    E.fact("re_source_declares_itself_pseudocode",
           "This is RE pseudocode. It is not compiled" in resrc, RESRC)
    E.fact("re_source_evidence_disc_is_a_mod_build", "ABL_ALLMODS" in resrc, RESRC)

    def redef(name: str) -> int:
        mm = re.search(rf"#define\s+{name}\s+.*?(0x800B[0-9A-Fa-f]{{4}})", resrc)
        if not mm:
            raise SystemExit(f"STALE CITATION: {RESRC} no longer defines {name}")
        return int(mm.group(1), 16)

    n_state = int(re.search(r"for \(int i = 0; i < (\d+); i\+\+\)\s*\n\s*G_TRAIN_STEP_STATE",
                            resrc).group(1))
    n_2b = int(re.search(r"kind2b_count < (\d+)", resrc).group(1))
    n_2c = int(re.search(r"kind2c_count < (\d+)", resrc).group(1))
    A_STEP, A_WAIT = redef("G_TRAIN_STEP"), redef("G_TRAIN_WAIT")
    A_ALT, A_AUDIO = redef("G_TRAIN_ALT_AUDIO"), redef("G_TRAIN_AUDIO_IDS")
    A_STATE, A_PREV = redef("G_TRAIN_STEP_STATE"), redef("G_PREV_A6580")
    A_2B, A_2C = redef("G_KIND2B_PTR"), redef("G_KIND2C_PTR")
    words = ([A_STEP, A_WAIT, A_ALT, A_AUDIO, A_PREV]
             + [A_STATE + 4 * i for i in range(n_state)]
             + [A_2B + 4 * i for i in range(n_2b)]
             + [A_2C + 4 * i for i in range(n_2c)])
    E.fact("re_declared_step_field", f"0x{A_STEP:08X}", RESRC)
    E.fact("re_declared_step_state_array", [f"0x{A_STATE:08X}", n_state], RESRC)
    E.fact("re_declared_cached_pickup_pointers", [n_2b, n_2c], RESRC)
    E.fact("re_declared_word_count", len(words), RESRC)
    jt = sorted(re.findall(r"step\s+(\d+)\s*->\s*(0x[0-9A-Fa-f]{8})", resrc),
                key=lambda t: int(t[0]))
    if not jt:
        raise SystemExit(f"STALE CITATION: {RESRC} no longer prints its jump table")
    E.fact("re_declared_jump_table_targets", [a for _, a in jt], RESRC)
    E.fact("re_declared_jump_table_arms", len(jt), RESRC)
    decoded_arms = sorted({int(x) for x in re.findall(r"^\s*case (\d+):", resrc, re.M)})
    if not decoded_arms:
        raise SystemExit(f"STALE CITATION: {RESRC} no longer decodes any step arm")
    E.fact("re_decoded_arm_indices", decoded_arms, RESRC)
    E.fact("re_arms_left_in_prose", len(jt) - len(decoded_arms), RESRC)

    PIN = "analysis/phase4_f00_overlay_residency_pin.json"
    pin = E.json(PIN)
    PINSRC = "tools/phase4_f08_overlay_residency_pin.c"
    E.pin(PINSRC)
    E.fact("residency_pin_generator", req(pin, "generated_by", where=PIN), PIN)
    E.fact("residency_pin_generator_is_reused_unchanged",
           req(pin, "generated_by", where=PIN) == PINSRC, [PIN, PINSRC])
    if as_int(req(pin, "declared_load_base", where=PIN)) != region_a:
        raise SystemExit("the residency pin scanned a load base the overlay registry does "
                         "not declare")
    if req(pin, "region_length", where=PIN) != region_b - region_a:
        raise SystemExit("the residency pin scanned a region length the overlay registry "
                         "does not declare")
    scanned = {as_int(w["addr"]) for w in req(pin, "named_words", where=PIN)}
    if scanned != set(words):
        raise SystemExit("the residency pin read words the RE source no longer declares: "
                         f"scanned={sorted(hex(x) for x in scanned)} "
                         f"declared={sorted(hex(x) for x in words)}")
    E.fact("residency_pin_inputs_match_registries", True, [PIN, OVLY, RESRC])
    E.fact("residency_pin_images_scanned", req(pin, "images_scanned", where=PIN), PIN)
    E.fact("residency_pin_rams_scanned", req(pin, "rams_scanned", where=PIN), PIN)
    E.fact("residency_pin_ram_labels",
           [req(r, "label", where=PIN) for r in req(pin, "rams", where=PIN)], PIN)
    E.fact("residency_pin_images_argmax_in_every_ram",
           req(pin, "images_argmax_in_every_ram", where=PIN), PIN)
    E.fact("residency_pin_images_with_stable_declared_base",
           req(pin, "images_with_stable_declared_base", where=PIN), PIN)
    E.fact("residency_pin_unique", req(pin, "unique_pin", where=PIN), PIN)
    E.fact("residency_pin_file", req(pin, "unique_pin_file", where=PIN), PIN)
    E.fact("residency_pin_sha1", req(pin, "unique_pin_sha1", where=PIN), PIN)
    E.fact("residency_pin_size", req(pin, "unique_pin_size", where=PIN), PIN)
    E.fact("residency_pin_result", req(pin, "result", where=PIN), PIN)
    E.fact("residency_pin_nontrivial_pct", req(pin, "first_ram_pin_nontrivial_pct", where=PIN),
           PIN)
    E.fact("residency_pin_runner_up", req(pin, "first_ram_runner_up", where=PIN), PIN)
    E.fact("residency_pin_runner_up_pct",
           req(pin, "first_ram_runner_up_nontrivial_pct", where=PIN), PIN)
    E.fact("residency_pin_agrees_with_overlay_registry_sha1",
           F["residency_pin_sha1"] == F["overlay_registry_entry_sha1"], [PIN, OVLY])
    E.fact("residency_pin_agrees_with_row_binding",
           Path(F["residency_pin_file"]).stem == ovl_name, [PIN, CENSUS])
    pin_lo, pin_hi = region_a, region_a + int(F["residency_pin_size"])
    E.fact("pinned_overlay_extent", [f"0x{pin_lo:08X}", f"0x{pin_hi:08X}"], [OVLY, PIN])

    nw = req(pin, "named_words", where=PIN)
    E.fact("named_words_count", req(pin, "named_words_count", where=PIN), PIN)
    E.fact("named_words_inside_pinned_image",
           req(pin, "named_words_inside_pinned_image", where=PIN), PIN)
    E.fact("named_words_zero_in_disc_image",
           req(pin, "named_words_zero_in_disc_image", where=PIN), PIN)
    E.fact("named_words_varying_across_fixtures",
           req(pin, "named_words_varying_across_fixtures", where=PIN), PIN)
    by_addr = {as_int(w["addr"]): w for w in nw}
    E.fact("step_field_values_across_fixtures",
           req(by_addr, A_STEP, "values", where=PIN), PIN)
    E.fact("step_field_is_zero_on_disc",
           req(by_addr, A_STEP, "disc_image_u32", where=PIN) == 0, PIN)
    E.fact("step_state_array_values",
           [req(by_addr, A_STATE + 4 * i, "values", where=PIN) for i in range(n_state)], PIN)
    E.fact("step_state_slots_nonzero_per_fixture",
           [sum(1 for i in range(n_state)
                if req(by_addr, A_STATE + 4 * i, "values", where=PIN)[k])
            for k in range(F["residency_pin_rams_scanned"])], PIN)
    E.fact("cached_pickup_pointer_values",
           [req(by_addr, a, "values", where=PIN)[0]
            for a in [A_2B + 4 * i for i in range(n_2b)]
            + [A_2C + 4 * i for i in range(n_2c)]], PIN)
    ptrs = F["cached_pickup_pointer_values"]
    E.fact("cached_pickup_pointer_stride",
           sorted({ptrs[i + 1] - ptrs[i] for i in range(len(ptrs) - 1)}), PIN)
    E.fact("cached_pickup_pointer_count_matches_disc_type3f_kinds",
           [n_2b, n_2c] == [req(F["this_stage_type3f_kind_histogram"], "0x2b", where=E08),
                            req(F["this_stage_type3f_kind_histogram"], "0x2c", where=E08)],
           [PIN, E08, RESRC])
    E.fact("audio_id_table_is_static_on_disc",
           req(by_addr, A_AUDIO, "disc_image_u32", where=PIN) != 0, PIN)

    diff = req(pin, "cross_fixture_diff", where=PIN)
    E.fact("region_a_bytes", req(diff, "region_a_bytes", where=PIN), PIN)
    E.fact("region_a_differing_bytes", req(diff, "region_a_differing_bytes", where=PIN), PIN)
    E.fact("region_a_differing_inside_pinned_image",
           req(diff, "region_a_differing_inside_pinned_image", where=PIN), PIN)
    E.fact("region_a_differing_beyond_pinned_image",
           req(diff, "region_a_differing_beyond_pinned_image", where=PIN), PIN)
    E.fact("whole_ram_words", req(diff, "whole_ram_words", where=PIN), PIN)
    E.fact("whole_ram_differing_words", req(diff, "whole_ram_differing_words", where=PIN), PIN)

    # the two RAM images came from pinned save states, not from a live emulator
    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    fixset = E.json(FIXSET)
    entries = req(fixset, "entries", where=FIXSET)
    all_training_saves = sorted(k for k in entries
                                if k.endswith(".sav") and re.search(r"training", k, re.I))
    save_names = sorted(k for k in all_training_saves
                        if req(entries, k, "media_class", where=FIXSET) == "pristine")
    E.fact("training_saves_centrally_pinned", all_training_saves, FIXSET)
    E.fact("training_saves_pristine", save_names, FIXSET)
    E.fact("training_saves_non_pristine",
           sorted(set(all_training_saves) - set(save_names)), FIXSET)
    E.fact("training_saves_bytes_match_pin",
           sum(1 for q in all_training_saves
               if (ROOT / q).exists() and sha256_file(ROOT / q) == entries[q]["sha256"]),
           FIXSET)
    # the two RAM images the residency pin scanned are named by their save stems
    pin_rams = [req(r, "label", where=PIN) for r in req(pin, "rams", where=PIN)]
    matched_rams = sorted(q for q in save_names
                          if any(lab.split("_")[-1] in q or q.startswith(lab.split("_")[0])
                                 for lab in pin_rams))
    E.fact("residency_pin_rams_are_pinned_pristine_training_saves",
           len(pin_rams) == F["residency_pin_rams_scanned"] and bool(matched_rams), [PIN, FIXSET])
    E.fact("pristine_training_saves_the_row_declares",
           sorted(q for q in save_names if q in F["row_declared_fixture_paths"]),
           [FIXSET, BASE])
    E.fact("row_external_fixtures_bytes_match_pin",
           sum(1 for p in external
               if p in entries and (ROOT / p).exists()
               and sha256_file(ROOT / p) == entries[p]["sha256"]), [FIXSET, CENSUS])
    E.fact("row_external_fixture_consumers",
           sorted({c for p in external for c in req(entries, p, "consumers", where=FIXSET)}),
           FIXSET)

    # ------------------------------------------------------------------ #
    # 6. NEW MEASUREMENT B -- defect (b): who reads and writes the        #
    #    registered address, decided by compiled-C instruction decoding.  #
    # ------------------------------------------------------------------ #
    SEM = "config/semantic_state.yaml"
    sem = E.yaml(SEM)
    sem_entries = req(sem, "entries", where=SEM)
    E.fact("semantic_state_entries_total", len(sem_entries), SEM)

    def sem_addr(e):
        a = e.get("address")
        return as_int(a) if isinstance(a, (int, str)) and a is not None else None

    ent = next((e for e in sem_entries if sem_addr(e) == A_STEP), None)
    if ent is None:
        raise SystemExit(f"STALE CITATION: {SEM} no longer registers an entry at "
                         f"0x{A_STEP:08X}")
    E.fact("registered_entry_id", req(ent, "id", where=SEM), SEM)
    E.fact("registered_entry_kind", req(ent, "kind", where=SEM), SEM)
    E.fact("registered_entry_width", req(ent, "width", where=SEM), SEM)
    E.fact("registered_entry_owner", req(ent, "owner", where=SEM), SEM)
    E.fact("registered_entry_confidence", req(ent, "confidence", where=SEM), SEM)
    E.fact("registered_entry_evidence", req(ent, "evidence", where=SEM), SEM)
    invr = req(ent, "invariants", 0, where=SEM)
    E.fact("registered_entry_range",
           [req(invr, "min", where=SEM), req(invr, "max", where=SEM)], SEM)
    E.fact("registered_entry_range_context", req(invr, "context", where=SEM), SEM)
    E.fact("registered_entry_declared_writers",
           [f"0x{as_int(w['address']):08X}" for w in req(ent, "writers", where=SEM)], SEM)
    E.fact("registered_entry_declared_writer_names",
           [w.get("name") for w in req(ent, "writers", where=SEM)], SEM)
    E.fact("registered_entry_has_no_image_field", "image" not in ent, SEM)
    E.fact("semantic_entries_inside_shared_region_a",
           sorted(f"0x{sem_addr(e):08X}" for e in sem_entries
                  if sem_addr(e) is not None and region_a <= sem_addr(e) < region_b), SEM)
    E.fact("semantic_entries_inside_this_rows_overlay_extent",
           sorted(f"0x{sem_addr(e):08X}" for e in sem_entries
                  if sem_addr(e) is not None and pin_lo <= sem_addr(e) < pin_hi),
           [SEM, PIN])

    XREF = "analysis/phase3_xrefs.json"
    xref = E.json(XREF)
    xe = req(xref, "entries", F["registered_entry_id"], where=XREF)
    E.fact("xrefs_gp", req(xref, "gp", where=XREF), XREF)
    E.fact("xrefs_declared_readers",
           [req(r, "pc", where=XREF) for r in req(xe, "readers", where=XREF)], XREF)
    E.fact("xrefs_declared_reader_functions",
           sorted({req(r, "function", where=XREF) for r in req(xe, "readers", where=XREF)}),
           XREF)
    E.fact("xrefs_declared_writer_count", req(xe, "writer_count", where=XREF), XREF)
    ows = req(xref, "declared_writers_in_overlay_space", where=XREF)
    myow = next((o for o in ows if req(o, "entry", where=XREF) == F["registered_entry_id"]),
                None)
    if myow is None:
        raise SystemExit(f"STALE CITATION: {XREF} no longer records this entry's declared "
                         "writer as unverifiable overlay-space")
    E.fact("xrefs_admits_it_cannot_see_the_declared_writer",
           req(myow, "why", where=XREF), XREF)

    PROBE = "analysis/phase4_f00_state_owner_probe.json"
    probe = E.json(PROBE)
    PROBESRC = "tools/phase4_f00_state_owner_probe.c"
    E.pin(PROBESRC)
    if as_int(req(probe, "gp", where=PROBE)) != as_int(F["xrefs_gp"]):
        raise SystemExit("the state-owner probe used a $gp the xref census does not declare")
    if as_int(req(probe, "overlay_load_base", where=PROBE)) != region_a:
        raise SystemExit("the state-owner probe used a load base the registry does not "
                         "declare")
    if req(probe, "pinned_image", where=PROBE) != F["residency_pin_file"]:
        raise SystemExit("the state-owner probe pinned a different image than the residency "
                         "pin decided")
    probe_readers = [req(r, "pc", where=PROBE)
                     for r in req(probe, "claimed_resident_readers", where=PROBE)]
    if sorted(x.lower() for x in probe_readers) != sorted(
            x.lower() for x in F["xrefs_declared_readers"]):
        raise SystemExit("the probe decoded reader PCs the xref census no longer declares")
    probe_writers = [req(w, "pc", where=PROBE)
                     for w in req(probe, "claimed_overlay_writers", where=PROBE)]
    if sorted(x.lower() for x in probe_writers) != sorted(
            x.lower() for x in F["registered_entry_declared_writers"]):
        raise SystemExit("the probe decoded writer PCs the semantic registry no longer "
                         "declares")
    if [x.upper() for x in req(probe, "claimed_sequence", "words", where=PROBE)] != \
            [x.upper() for x in F["re_declared_jump_table_targets"]]:
        raise SystemExit("the probe searched for a jump table the RE source no longer prints")
    # the decode list is the RE source's overlay-space literals that are neither state
    # words nor jump-table arms, i.e. the code entries it names. Re-derived, never re-typed.
    re_overlay_literals = {int(x, 16) for x in re.findall(r"0x800[Bb][0-9A-Fa-f]{4}", resrc)} \
        | {int(x, 16) for x in re.findall(r"_(800[Bb][0-9A-Fa-f]{4})\(", resrc)}
    re_code_entries = sorted(re_overlay_literals - set(words)
                             - {int(a, 16) for a in F["re_declared_jump_table_targets"]})
    if sorted(as_int(d["address"]) for d in req(probe, "decoded", where=PROBE)) \
            != re_code_entries:
        raise SystemExit("the probe decoded a different set of RE-named overlay entries than "
                         "the RE source now names")
    E.fact("re_named_overlay_code_entries", [f"0x{a:08X}" for a in re_code_entries], RESRC)
    E.fact("re_named_overlay_code_entries_all_inside_the_pinned_image",
           all(req(d, "in_pinned_image", where=PROBE)
               for d in req(probe, "decoded", where=PROBE)), PROBE)
    E.fact("re_named_overlay_code_entry_words",
           {req(d, "address", where=PROBE): req(d, "word", where=PROBE)
            for d in req(probe, "decoded", where=PROBE)}, PROBE)
    E.fact("probe_inputs_match_the_registries_they_check", True,
           [PROBE, XREF, SEM, RESRC, PIN])
    E.fact("probe_exe_sha256", req(probe, "exe", "sha256", where=PROBE), PROBE)
    E.fact("probe_reference_recovery", req(probe, "reference_recovery", where=PROBE), PROBE)

    tgt = next((t for t in req(probe, "targets", where=PROBE)
                if as_int(req(t, "address", where=PROBE)) == A_STEP), None)
    if tgt is None:
        raise SystemExit(f"STALE CITATION: {PROBE} no longer scans 0x{A_STEP:08X}")
    E.fact("probe_resident_reference_count",
           req(tgt, "resident_reference_count", where=PROBE), PROBE)
    E.fact("probe_images_whose_extent_covers_the_address",
           req(tgt, "images_whose_extent_covers_the_address", where=PROBE), PROBE)
    E.fact("probe_images_referencing_the_address",
           req(tgt, "images_referencing_the_address", where=PROBE), PROBE)
    E.fact("probe_pinned_image_reference_count",
           req(tgt, "pinned_image_reference_count", where=PROBE), PROBE)
    E.fact("probe_pinned_image_store_count",
           req(tgt, "pinned_image_store_count", where=PROBE), PROBE)
    E.fact("probe_pinned_image_load_count",
           req(tgt, "pinned_image_load_count", where=PROBE), PROBE)
    other = sorted((req(im, "path", where=PROBE), req(im, "reference_count", where=PROBE),
                    sum(1 for s in req(im, "sites", where=PROBE) if s["store"]))
                   for im in req(tgt, "images", where=PROBE)
                   if req(im, "reference_count", where=PROBE)
                   and req(im, "path", where=PROBE) != F["residency_pin_file"])
    E.fact("other_images_referencing_the_same_address", other, PROBE)
    pinned_img = next(im for im in req(tgt, "images", where=PROBE)
                      if req(im, "path", where=PROBE) == F["residency_pin_file"])
    E.fact("measured_store_pcs_in_the_pinned_image",
           [req(s, "pc", where=PROBE) for s in req(pinned_img, "sites", where=PROBE)
            if s["store"]], PROBE)
    E.fact("declared_writer_count_vs_measured_store_count",
           [len(F["registered_entry_declared_writers"]),
            len(F["measured_store_pcs_in_the_pinned_image"])], [SEM, PROBE])
    E.fact("declared_writer_is_among_the_measured_stores",
           any(a.lower() in [s.lower() for s in F["measured_store_pcs_in_the_pinned_image"]]
               for a in F["registered_entry_declared_writers"]), [SEM, PROBE])
    dw = req(probe, "claimed_overlay_writers", 0, where=PROBE)
    dwp = next(p for p in req(dw, "per_image", where=PROBE)
               if req(p, "image", where=PROBE) == F["residency_pin_file"])
    E.fact("declared_writer_word_in_the_pinned_image", req(dwp, "insn", where=PROBE), PROBE)
    E.fact("declared_writer_decodes_as_a_memory_op",
           req(dwp, "op", where=PROBE) is not None, PROBE)
    E.fact("declared_writer_is_a_store_in_any_image",
           any(req(p, "is_store", where=PROBE) for p in req(dw, "per_image", where=PROBE)),
           PROBE)

    rdrs = req(probe, "claimed_resident_readers", where=PROBE)
    E.fact("resident_readers_confirmed_from_bytes",
           sum(1 for r in rdrs if req(r, "matches_a_target", where=PROBE)), PROBE)
    E.fact("resident_reader_ops",
           sorted({req(r, "op", where=PROBE) for r in rdrs}), PROBE)
    E.fact("resident_reader_insn_words",
           sorted({req(r, "insn", where=PROBE) for r in rdrs}), PROBE)
    E.fact("resident_reader_resolution",
           sorted({req(r, "resolution", where=PROBE) for r in rdrs}), PROBE)

    seqhits = req(probe, "claimed_sequence", "found_in", where=PROBE)
    if not seqhits:
        raise SystemExit(f"STALE CITATION: {PROBE} no longer finds the RE-declared jump "
                         "table in any image; the frontier claim below has no basis")
    E.fact("jump_table_images_containing_it", len(seqhits), PROBE)
    E.fact("jump_table_address", req(seqhits, 0, "address", where=PROBE), PROBE)
    E.fact("jump_table_image", req(seqhits, 0, "image", where=PROBE), PROBE)
    E.fact("jump_table_all_arms_inside_that_image",
           req(seqhits, 0, "all_words_inside_this_image", where=PROBE), PROBE)
    E.fact("jump_table_is_in_the_pinned_image",
           req(seqhits, 0, "image", where=PROBE) == F["residency_pin_file"], PROBE)

    # Every arm of that table re-reads the field the table is indexed by. Measured,
    # not assumed: pair each arm with the first load of the field at or after it.
    loads = sorted(as_int(s["pc"]) for s in req(pinned_img, "sites", where=PROBE)
                   if not s["store"])
    arms = [as_int(a) for a in F["re_declared_jump_table_targets"]]
    pairs = {}
    for a in arms:
        nxt = [l for l in loads if 0 <= l - a <= 64]
        if nxt:
            pairs[f"0x{a:08X}"] = nxt[0] - a
    E.fact("jump_table_arms_that_reload_the_field", len(pairs), PROBE)
    E.fact("jump_table_arm_reload_offsets", sorted(set(pairs.values())), PROBE)
    E.fact("jump_table_arm_count_equals_declared_range_span",
           len(arms) == F["registered_entry_range"][1] - F["registered_entry_range"][0] + 1,
           [PROBE, SEM])

    FN = "analysis/functions.json"
    fnj = E.json(FN)
    fns = req(fnj, "functions", where=FN)
    E.fact("overlay_images_in_function_census", len(req(fnj, "overlays", where=FN)), FN)
    mine = [f for f in fns if f.get("overlay") == ovl_name]
    if not mine:
        raise SystemExit(f"STALE CITATION: {FN} no longer censuses {ovl_name}")
    E.fact("census_entries_in_the_pinned_overlay", len(mine), FN)
    E.fact("census_code_functions_in_the_pinned_overlay",
           sum(1 for f in mine if f["range_type"] == "code"), FN)
    E.fact("census_data_records_in_the_pinned_overlay",
           sum(1 for f in mine if f["range_type"] == "data"), FN)
    E.fact("census_function_names_in_the_pinned_overlay",
           sorted(f["name"] for f in mine if f["name"]), FN)
    E.fact("overlay_summary_function_count",
           req(fnj, "overlays", ovl_name, "functions", where=FN), FN)
    E.fact("overlay_resident_callees",
           req(fnj, "overlays", ovl_name, "resident_callees", where=FN), FN)
    jt_rec = next((f for f in mine
                   if as_int(f["start"]) == as_int(F["jump_table_address"])), None)
    if jt_rec is None:
        raise SystemExit(f"STALE CITATION: {FN} no longer carries a record starting at the "
                         "jump-table address the probe located")
    E.fact("function_census_classifies_the_jump_table_range",
           req(jt_rec, "range_type", where=FN), FN)
    E.fact("function_census_jump_table_range_size", req(jt_rec, "size", where=FN), FN)
    E.fact("jump_table_size_matches_arm_count",
           req(jt_rec, "size", where=FN) == 4 * len(arms), [FN, PROBE])
    state_rec = next((f for f in mine
                      if as_int(f["start"]) <= A_STEP < as_int(f["end"])), None)
    if state_rec is None:
        raise SystemExit(f"STALE CITATION: {FN} no longer covers the registered address")
    E.fact("function_census_classifies_the_state_block",
           req(state_rec, "range_type", where=FN), FN)
    E.fact("function_census_state_block_extent",
           [state_rec["start"], state_rec["end"]], FN)
    store_owner = {}
    for st in F["measured_store_pcs_in_the_pinned_image"]:
        owner = next((f["name"] for f in mine
                      if as_int(f["start"]) <= as_int(st) < as_int(f["end"])), None)
        if owner is None:
            raise SystemExit(f"STALE CITATION: {FN} covers no function containing the "
                             f"measured store {st}")
        store_owner[st] = owner
    E.fact("function_owning_each_measured_store", store_owner, [FN, PROBE])
    E.fact("function_owning_the_measured_stores", sorted(set(store_owner.values())),
           [FN, PROBE])
    E.fact("initializing_store_owner", store_owner[min(store_owner, key=as_int)],
           [FN, PROBE])
    E.fact("advancing_store_owner", store_owner[max(store_owner, key=as_int)], [FN, PROBE])

    OWN = "analysis/phase3_ownership_graph.json"
    own = E.json(OWN)
    orow = req(own, "rows", ROW_ID, where=OWN)
    E.fact("ownership_functions", len(req(orow, "functions", where=OWN)), OWN)
    E.fact("ownership_overlay_entries", len(req(orow, "overlay", where=OWN)), OWN)
    E.fact("ownership_state_addresses",
           [s["address"] for s in req(orow, "state", where=OWN)], OWN)
    E.fact("ownership_writers", len(req(orow, "writers", where=OWN)), OWN)
    E.fact("ownership_gaps", len(req(orow, "gaps", where=OWN)), OWN)
    E.fact("ownership_frontier_blockers",
           sorted(req(orow, "frontier_blockers", where=OWN)), OWN)
    E.fact("ownership_frontier_blocker_texts",
           {k: v["missing_link"] for k, v in req(orow, "frontier_blockers", where=OWN).items()},
           OWN)
    sharers = sorted({rid for rid, r in req(own, "rows", where=OWN).items()
                      for rd in (r.get("readers") or [])
                      if rd.get("state_id") == F["registered_entry_id"]})
    E.fact("rows_the_ownership_graph_attributes_this_state_to", sharers, OWN)
    E.fact("rows_sharing_this_state_count", len(sharers), OWN)

    # Which overlay does the OTHER row that stores to this address load? Derive it
    # from that row's own stage ordinal through the same progression law, so the
    # collision is explained rather than merely observed.
    collision = {}
    for rid in sharers:
        if rid == ROW_ID:
            continue
        orow2 = next((r for r in rows if r.get("id") == rid), None)
        if orow2 is None:
            continue
        st = str(req(orow2, "stages", where=BASE)).strip()
        if st.isdigit() and 0 <= int(st) < len(progression):
            s2 = progression[int(st)]
            collision[rid] = (f"LEVEL{(s2 if s2 <= 10 else s2 - 10):02d}_"
                              f"{'LEVEL' if s2 <= 10 else 'LEVEL1'}")
        else:
            collision[rid] = f"not stage-scoped (stages={st!r})"
    E.fact("collision_rows_resolved_to_their_own_overlay", collision, [OWN, BASE, GRAPH3])
    E.fact("collision_explained_by_the_other_images_that_reference_the_address",
           sorted({Path(p).stem for p, _, st in other if st}) ==
           sorted({v for v in collision.values() if not v.startswith("not ")}),
           [PROBE, OWN, BASE])

    # ------------------------------------------------------------------ #
    # 7. source closure -- BOTH registries, resident and overlay          #
    # ------------------------------------------------------------------ #
    SEG = "config/segments.yml"
    seg = E.yaml(SEG)
    units = [(as_int(req(e, "start", where=SEG)), as_int(req(e, "end", where=SEG)),
              req(e, "source", where=SEG)) for e in req(seg, "attempted", where=SEG)]
    E.fact("resident_build_units", len(units), SEG)
    E.fact("resident_build_toolchain", req(seg, "c_toolchain", "compiler", where=SEG), SEG)
    E.fact("resident_registry_contains_any_src_re_unit",
           any(s.startswith("src_re/") for _, _, s in units), SEG)
    E.fact("overlay_registry_contains_any_src_re_unit",
           any(a["source"].startswith("src_re/")
               for v in req(ovly, "overlays", where=OVLY).values()
               for a in (v.get("attempted") or [])), OVLY)
    E.fact("census_credited_source_files_are_in_neither_build_registry",
           all(s.startswith("src_re/") for s in F["census_source_files"])
           and not F["resident_registry_contains_any_src_re_unit"]
           and not F["overlay_registry_contains_any_src_re_unit"],
           [CENSUS, SEG, OVLY])

    OVLD = "analysis/overlay_decomp_progress.json"
    ovld = E.json(OVLD)
    E.fact("overlay_track_total_code_functions",
           req(ovld, "overlay_code_functions", where=OVLD), OVLD)
    E.fact("overlay_track_matched_functions", req(ovld, "matched", "functions", where=OVLD),
           OVLD)
    E.fact("overlay_track_matched_pct", req(ovld, "matched", "pct_functions", where=OVLD), OVLD)
    E.fact("pinned_overlay_code_functions",
           req(ovld, "per_overlay_totals", ovl_name, where=OVLD), OVLD)
    res = [r for r in req(ovld, "results", where=OVLD) if r["overlay"] == ovl_name]
    if not res:
        raise SystemExit(f"STALE CITATION: {OVLD} no longer carries a result for {ovl_name}")
    E.fact("pinned_overlay_matched_functions",
           sum(req(r, "matched_functions", where=OVLD) for r in res), OVLD)
    E.fact("pinned_overlay_rebuild_validated",
           all(req(r, "validated", where=OVLD) for r in res), OVLD)
    E.fact("pinned_overlay_rebuilt_sha1_matches_the_blob",
           all(req(r, "rebuilt_sha1", where=OVLD) == req(r, "sha1", where=OVLD)
               for r in res), OVLD)
    attempted = [(as_int(req(a, "start", where=OVLD)), req(a, "source", where=OVLD))
                 for r in res for a in req(r, "attempted", where=OVLD)]
    E.fact("pinned_overlay_matched_sources", sorted(s for _, s in attempted), OVLD)
    E.fact("pinned_overlay_matched_entry", f"0x{attempted[0][0]:08X}", OVLD)

    MC = attempted[0][1]
    mc = E.text(MC)
    lits = sorted({int(x) for x in re.findall(r"value < (\d+)", mc)})
    if not lits:
        raise SystemExit(f"STALE CITATION: {MC} no longer carries the bound literals this "
                         "assessment reports as byte-matched")
    E.fact("byte_matched_c_bound_literals", lits, MC)
    E.fact("byte_matched_c_outer_guard_literal", max(lits), MC)
    E.fact("byte_matched_c_guard_literal_equals_registered_max",
           max(lits) == F["registered_entry_range"][1], [MC, SEM])
    E.fact("byte_matched_c_guard_is_exclusive_so_it_excludes_the_terminal_step",
           bool(re.search(rf"value < {max(lits)}\b", mc)), MC)
    E.fact("byte_matched_c_callee", sorted(set(re.findall(r"sub_(800b[0-9a-f]{4})", mc))), MC)
    caller = [as_int(s["pc"]) for s in req(pinned_img, "sites", where=PROBE)
              if not s["store"] and attempted[0][0] - 8 <= as_int(s["pc"]) < attempted[0][0]]
    E.fact("byte_matched_c_is_fed_the_registered_field",
           [f"0x{c:08X}" for c in caller], PROBE)

    # WHICH other row documents the callback? The one citing both this row's field and
    # the callee the byte-matched C jumps to -- derived, not asserted.
    addr_tok = f"0x{A_STEP:08X}"
    E.fact("other_baseline_rows_citing_this_address",
           sorted(r["id"] for r in rows
                  if r.get("id") != ROW_ID and addr_tok.lower() in json.dumps(r).lower()),
           BASE)
    callee_tok = F["byte_matched_c_callee"]
    if not callee_tok:
        raise SystemExit(f"STALE CITATION: {MC} no longer names an overlay callee")
    E.fact("another_row_documents_the_overlay_callback_that_reads_it",
           sorted(r["id"] for r in rows
                  if r.get("id") != ROW_ID
                  and addr_tok.lower() in json.dumps(r).lower()
                  and any(t in json.dumps(r).lower() for t in callee_tok)), BASE)

    # governing addresses, split by space, resolved against BOTH registries
    governing: dict[str, int] = {}
    for i, pc in enumerate(F["xrefs_declared_readers"]):
        governing[f"resident_reader_{i}"] = as_int(pc)
    for i, pc in enumerate(F["measured_store_pcs_in_the_pinned_image"]):
        governing[f"overlay_store_{i}"] = as_int(pc)
    for f0 in mine:
        if f0["range_type"] == "code":
            governing[f"overlay_fn_{f0['start']}"] = as_int(f0["start"])
    for i, a in enumerate(arms):
        governing[f"jump_arm_{i}"] = a
    governing["state_field"] = A_STEP
    governing["jump_table"] = as_int(F["jump_table_address"])
    gov = set(governing.values())
    resident = {a for a in gov if not (pin_lo <= a < pin_hi)}
    overlay = {a for a in gov if pin_lo <= a < pin_hi}
    resolved: dict[str, list[str]] = {}
    unresolved: list[int] = []
    for a in sorted(resident):
        src = next((s for lo, hi, s in units if lo <= a < hi), None)
        (resolved.setdefault(src, []).append(f"0x{a:08X}") if src else unresolved.append(a))
    matched_ranges = [(as_int(req(a, "start", where=OVLY)), as_int(req(a, "end", where=OVLY)))
                      for a in req(ovl_entry, "attempted", where=OVLY)]
    E.fact("byte_matched_c_bytes", sum(hi - lo for lo, hi in matched_ranges), OVLY)
    E.fact("governing_roles", len(governing), [XREF, PROBE, FN, SEM])
    E.fact("governing_addresses", len(gov), [XREF, PROBE, FN, SEM])
    E.fact("governing_addresses_resident", len(resident), [XREF, PIN])
    E.fact("governing_addresses_in_this_rows_overlay", len(overlay), [FN, PROBE, PIN])
    E.fact("governing_resident_build_units", sorted(x for x in resolved if x), SEG)
    E.fact("governing_resident_units_matching_c",
           len([s for s in resolved if s and s.startswith("src/")]), SEG)
    E.fact("governing_resident_units_hand_asm",
           len([s for s in resolved if s and s.startswith("asm/")]), SEG)
    E.fact("governing_resident_addresses_outside_any_build_unit", len(unresolved), SEG)
    E.fact("governing_overlay_addresses_with_matched_c",
           len([a for a in overlay if any(lo <= a < hi for lo, hi in matched_ranges)]),
           [OVLY, OVLD])

    # ------------------------------------------------------------------ #
    # 8. fixtures, oracles, and the scheduler that reads them             #
    # ------------------------------------------------------------------ #
    AUDIT = "analysis/phase2_fixture_audit.json"
    audit = E.json(AUDIT)
    movies = req(audit, "movies", where=AUDIT)
    ORACLE = "analysis/phase2_completion_oracle.json"
    oracle = E.json(ORACLE)
    stage_key = req(sc, "phase2_stage_labels", 0, where=GRAPH3)
    ost = req(oracle, "stages", stage_key, where=ORACLE)
    E.fact("completion_oracle_stage_key", stage_key, [ORACLE, GRAPH3])
    E.fact("completion_oracle_movie", req(ost, "movie", where=ORACLE), ORACLE)
    E.fact("completion_oracle_frames", req(ost, "frames", where=ORACLE), ORACLE)
    E.fact("completion_oracle_target_scene", req(ost, "target_scene", where=ORACLE), ORACLE)
    E.fact("completion_oracle_replay_accepted",
           req(ost, "pristine_replay_accepted", where=ORACLE), ORACLE)
    E.fact("completion_oracle_entered_stage_frame",
           req(ost, "entered_stage_frame", where=ORACLE), ORACLE)
    E.fact("completion_oracle_stage_exited",
           req(ost, "stage_exited_by_movie_end", where=ORACLE), ORACLE)
    E.fact("completion_oracle_snapshot_fields",
           sorted(req(ost, "last_in_stage", "snapshot", where=ORACLE)), ORACLE)
    E.fact("completion_oracle_corroborates_the_scene_id",
           req(ost, "target_scene", where=ORACLE) == progression[0], [ORACLE, GRAPH3])
    E.fact("completion_oracle_cited_by_the_row",
           "phase2_completion_oracle" in json.dumps(row), [BASE, ORACLE])

    stage_mov = sorted(k for k in movies
                       if re.search(r"training", k, re.I) or re.search(r"level00", k, re.I))
    E.fact("stage_movies_pinned", len(stage_mov), AUDIT)
    E.fact("stage_movies_pinned_paths", stage_mov, AUDIT)
    E.fact("stage_movie_frames",
           {k: req(movies, k, "frames", where=AUDIT) for k in stage_mov}, AUDIT)
    E.fact("stage_movies_under_phase4_interpreter",
           sorted(k for k in stage_mov if k.startswith("movies/Phase4/Interpreter/")), AUDIT)
    E.fact("stage_movie_format_versions",
           sorted({req(movies, k, "format_version", where=AUDIT) for k in stage_mov}), AUDIT)
    E.fact("stage_movies_declared_by_the_row",
           sorted(k for k in stage_mov if k in F["row_declared_fixture_paths"]),
           [AUDIT, BASE])
    E.fact("stage_movies_centrally_pinned",
           sum(1 for k in stage_mov if k in entries), [AUDIT, FIXSET])

    ANCH = "analysis/phase3_training_anchor_fixture.json"
    anch = E.json(ANCH)
    E.fact("anchor_fixture_classification", req(anch, "classification", where=ANCH), ANCH)
    E.fact("anchor_fixture_observed_scene", req(anch, "observed_scene", where=ANCH), ANCH)
    E.fact("anchor_fixture_reproducible",
           req(anch, "playback_generation", "reproducible", where=ANCH), ANCH)
    E.fact("anchor_fixture_reproduction_verified",
           req(anch, "playback_generation", "reproduction_verified", where=ANCH), ANCH)
    E.fact("anchor_fixture_target_frame",
           req(anch, "playback_generation", "target_movie_frame", where=ANCH), ANCH)
    E.fact("anchor_fixture_movie", req(anch, "movie", "path", where=ANCH), ANCH)
    E.fact("anchor_fixture_from_boot", req(anch, "movie", "from_boot", where=ANCH), ANCH)
    E.fact("anchor_fixture_is_the_pin_ram_source",
           req(anch, "output", where=ANCH) in save_names, [ANCH, FIXSET])

    COV = "analysis/phase2_row_coverage.json"
    cov = E.json(COV)
    crow2 = req(cov, "rows", ROW_ID, where=COV)
    E.fact("row_coverage_status", req(crow2, "status", where=COV), COV)
    E.fact("row_coverage_unaudited_fixtures", len(req(crow2, "unaudited_fixtures", where=COV)),
           COV)
    E.fact("row_coverage_non_pristine_fixtures",
           len(req(crow2, "non_pristine_fixtures", where=COV)), COV)

    QUEUE = "analysis/phase4_movie_priority_queue.json"
    queue = E.json(QUEUE)
    qrow = next((r for r in req(queue, "rows", where=QUEUE) if r.get("row_id") == ROW_ID), None)
    if qrow is None:
        raise SystemExit(f"STALE CITATION: {QUEUE} no longer carries {ROW_ID}")
    E.fact("scheduler_eligible", req(qrow, "eligibility", "eligible", where=QUEUE), QUEUE)
    E.fact("scheduler_ineligibility_reasons",
           req(qrow, "eligibility", "reasons", where=QUEUE), QUEUE)
    E.fact("scheduler_sees_a_phase4_movie",
           req(qrow, "eligibility", "requirements", "case_sensitive_phase4_movie",
               where=QUEUE), QUEUE)
    E.fact("scheduler_frontier_blocker_domains",
           req(qrow, "frontier_blocker_domains", where=QUEUE), QUEUE)
    E.fact("scheduler_static_ownership_function_count",
           req(qrow, "static_ownership", "function_count", where=QUEUE), QUEUE)
    E.fact("scheduler_ownership_input_is_current",
           req(qrow, "static_ownership", "source_sha256", where=QUEUE)
           == sha256_file(ROOT / OWN), [QUEUE, OWN])

    WIN = "analysis/phase2_action_windows.json"
    win = E.json(WIN)
    wm = req(win, "movies", F["completion_oracle_movie"], where=WIN)
    E.fact("action_windows_stage_label", req(wm, "stage", where=WIN), WIN)
    E.fact("action_window_recognizers", len(req(wm, "events", where=WIN)), WIN)
    E.fact("action_windows_in_stage_total",
           sum(req(e, "in_stage_count", where=WIN)
               for e in req(wm, "events", where=WIN).values()), WIN)
    E.fact("action_window_recognizers_with_zero_in_stage",
           sorted(k for k, e in req(wm, "events", where=WIN).items()
                  if not req(e, "in_stage_count", where=WIN)), WIN)
    E.fact("action_windows_cited_by_the_row",
           "phase2_action_windows" in json.dumps(row), [BASE, WIN])

    # ------------------------------------------------------------------ #
    # 9. the stage itself: exit mechanism, actors, type taxonomy          #
    # ------------------------------------------------------------------ #
    E02 = "analysis/phase4_e02_disc_region_code_census.json"
    e02 = E.json(E02)
    lvl = req(e02, "levels", stage_key, where=E02)
    E.fact("stage_collision_container", req(lvl, "container", where=E02), E02)
    E.fact("stage_collision_scene", req(lvl, "scene", where=E02), E02)
    E.fact("stage_authored_collision_sectors", req(lvl, "authored_sectors", where=E02), E02)
    E.fact("stage_runtime_collision_sectors", req(lvl, "runtime_sectors", where=E02), E02)
    E.fact("stage_region_code_histogram", req(lvl, "code_histogram", where=E02), E02)
    E.fact("stage_nonzero_region_sectors", req(lvl, "nonzero_sectors", where=E02), E02)
    E.fact("stage_disc_vs_runtime_mismatches",
           len(req(lvl, "disc_vs_runtime_mismatches", where=E02)), E02)
    E.fact("e02_corroborates_the_scene_id",
           req(lvl, "scene", where=E02) == progression[0], [E02, GRAPH3])
    E.fact("e02_container_agrees_with_the_law",
           req(lvl, "container", where=E02).split("/")[0].lower()
           == F["scene_disc_dir"].lower(), [E02, GRAPH3])
    E.fact("e02_authored_sectors_compared",
           req(e02, "agreement", "authored_sectors_compared", where=E02), E02)
    E.fact("e02_disagreements", len(req(e02, "agreement", "disagreements", where=E02)), E02)

    ACT = "analysis/phase1_kind_actor_census.json"
    act = E.json(ACT)
    alv = req(act, "levels", stage_key, where=ACT)
    arecs = req(alv, "actor_records", where=ACT)
    E.fact("stage_actor_census_save", req(alv, "save", where=ACT), ACT)
    E.fact("stage_actor_records", len(arecs), ACT)
    E.fact("stage_actor_ids", sorted({r["id"] for r in arecs}), ACT)
    bound = {int(k) for k in req(act, "actor_ids_with_canon_binding", where=ACT)}
    E.fact("stage_actor_ids_with_canon_binding",
           sorted({r["id"] for r in arecs} & bound), ACT)
    E.fact("stage_actor_census_uses_the_pin_ram_source",
           req(alv, "save", where=ACT) in save_names, [ACT, FIXSET])
    E.fact("stage_actor_census_cited_by_the_row",
           "phase1_kind_actor_census" in json.dumps(row), [BASE, ACT])

    C2 = "analysis/phase4_c2_level_type_authority.json"
    c2 = E.json(C2)
    E.fact("c2_row_types",
           [t["type"] for t in req(c2, "mapping", ROW_ID, "types", where=C2)], C2)
    E.fact("c2_row_type_rules",
           [t["rule"] for t in req(c2, "mapping", ROW_ID, "types", where=C2)], C2)
    E.fact("c2_taxonomy_coverage_demonstrated",
           req(c2, "result", "taxonomy_coverage_demonstrated", where=C2), C2)
    E.fact("c2_underivable_types", sorted(req(c2, "result", "underivable_types", where=C2)), C2)
    E.fact("c2_frozen_name_matches_this_row",
           req(c2, "mapping", ROW_ID, "frozen_name", where=C2) == req(row, "name", where=BASE),
           [C2, BASE])

    # ------------------------------------------------------------------ #
    # 10. the documentation surface -- 17 pages, but what KIND of pages?  #
    # ------------------------------------------------------------------ #
    pages = req(inv, "vault_pages", where=CENSUS)
    classes: dict[str, int] = {}
    statuses: dict[str, str] = {}
    source_states: dict[str, str] = {}
    allmods, md_pages, stubs = [], [], []
    for rel in pages:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"STALE CITATION: credited vault page {rel} does not exist")
        cls = rel.split("ObsidianVault/")[1].split("/")[0]
        classes[cls] = classes.get(cls, 0) + 1
        if not rel.endswith(".md"):
            continue
        md_pages.append(rel)
        txt = E.text(rel)
        ms = re.search(r"^status:\s*(\S+)", txt, re.M)
        statuses[rel] = ms.group(1) if ms else None
        mss = re.search(r"^source_state:\s*(\S+)", txt, re.M)
        source_states[rel] = mss.group(1) if mss else None
        if "ALLMODS" in txt:
            allmods.append(rel)
        if "landing page" in txt:
            stubs.append(rel)
    E.fact("vault_pages_total", len(pages), CENSUS)
    E.fact("vault_pages_by_class", classes, CENSUS)
    E.fact("vault_pages_markdown", len(md_pages), CENSUS)
    E.fact("vault_pages_under_mods_dir", classes.get("Mods", 0), CENSUS)
    E.fact("vault_page_statuses", statuses, md_pages)
    E.fact("vault_pages_without_a_status", sorted(k for k, v in statuses.items() if not v),
           md_pages)
    E.fact("vault_pages_declaring_source_state_original_game",
           sorted(k for k, v in source_states.items() if v == "original_game"), md_pages)
    E.fact("vault_pages_that_are_landing_stubs", sorted(stubs), md_pages)
    E.fact("vault_pages_mentioning_an_allmods_build", sorted(allmods), md_pages)
    E.fact("non_mod_vault_pages_mentioning_an_allmods_build",
           sorted(x for x in allmods if "/Mods/" not in x), md_pages)

    # ------------------------------------------------------------------ #
    # 11. the row's registered executable gate                            #
    # ------------------------------------------------------------------ #
    test_dir = ROOT / "tests"
    if not test_dir.is_dir():
        raise SystemExit("STALE CITATION: tests/ is not a directory")
    tokens = [ROW_ID, F["registered_entry_id"].split(".")[-1], f'"{stage_key}"',
              PIN, PROBE] + [Path(p).name for p in F["row_declared_fixture_paths"]] \
        + F["census_analysis_artifacts"]
    gate_files, gate_tokens = [], {}
    for p in sorted(test_dir.glob("test_*.py")):
        body = p.read_text(errors="ignore")
        hit = [t for t in tokens if t in body]
        if hit:
            rel = f"tests/{p.name}"
            E.pin(rel)
            gate_files.append(rel)
            gate_tokens[rel] = hit
    if not gate_files:
        raise SystemExit("no registered gate mentions this row, its state id, its stage key "
                         "or any of its artifacts -- the gate set this assessment measures "
                         "has disappeared")
    E.fact("registered_gate_files", len(gate_files), gate_files)
    E.fact("registered_gate_file_names", gate_files, gate_files)
    E.fact("registered_gate_match_tokens", gate_tokens, gate_files)
    E.fact("gate_files_naming_the_row_id",
           sorted(f for f, t in gate_tokens.items() if ROW_ID in t), gate_files)
    E.fact("gate_files_covering_the_new_measurements",
           sorted(f for f, t in gate_tokens.items() if PIN in t or PROBE in t), gate_files)

    if args.no_gates:
        E.fact("registered_gates_executed", False, gate_files)
    else:
        runp = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "--color=no",
             "-p", "no:cacheprovider", *gate_files],
            cwd=str(ROOT), capture_output=True, text=True)
        out = re.sub(r"\x1b\[[0-9;]*m", "", runp.stdout)
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        passed = re.search(r"(\d+) passed", tail)
        failed = re.search(r"(\d+) failed", tail)
        if not passed and not failed:
            raise SystemExit(f"could not read a pytest summary from the gate run: {tail!r}")
        E.fact("registered_gates_executed", True, gate_files)
        E.fact("registered_gate_tests_passed", int(passed.group(1)) if passed else 0,
               gate_files)
        E.fact("registered_gate_tests_failed", int(failed.group(1)) if failed else 0,
               gate_files)
        names = sorted({ln.split()[1].split("::")[0]
                        for ln in out.splitlines() if ln.startswith("FAILED ")})
        if F["registered_gate_tests_failed"] and not names:
            raise SystemExit("the gate run reported failures but no FAILED lines could be "
                             "attributed to a file -- the summary parse is wrong")
        E.fact("registered_gate_files_with_a_failure", names, gate_files)

    # ------------------------------------------------------------------ #
    # AUTHORED JUDGMENTS against the WRITTEN bars                         #
    # ------------------------------------------------------------------ #
    if F["registered_gates_executed"]:
        total = F["registered_gate_tests_passed"] + F["registered_gate_tests_failed"]
        gate_note = (f"{F['registered_gate_tests_passed']}/{total} tests in the "
                     f"{F['registered_gate_files']} gate file(s) that touch this row pass on "
                     f"today's tree")
    else:
        gate_note = (f"this row's {F['registered_gate_files']} gate file(s) were NOT executed "
                     f"for this run (--no-gates), so their health is unmeasured")

    dims = {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"{CENSUS} -- {F['census_durable_reason']}. This assessment fails loudly "
                     f"if that measurement moves off 'met'. Independently re-confirmed here: "
                     f"{F['row_external_fixtures_bytes_match_pin']} of "
                     f"{F['row_external_fixture_count']} declared external fixtures still "
                     f"byte-match their central pin. Regenerability is unusually strong for "
                     f"this row and was not part of the carried measurement: the strict "
                     f"anchor save is not merely preserved, it is REPRODUCIBLE -- "
                     f"{ANCH} records a from-boot replay of "
                     f"{F['anchor_fixture_movie']} to frame "
                     f"{F['anchor_fixture_target_frame']} regenerating the pinned bytes "
                     f"(reproduction_verified={F['anchor_fixture_reproduction_verified']}, "
                     f"classification '{F['anchor_fixture_classification']}'), and that same "
                     f"save is one of the {F['residency_pin_rams_scanned']} RAM images both "
                     f"new measurements in this assessment run on. Both new artifacts are "
                     f"regenerable offline with no emulator ({gate_note})",
            "gap": f"the carried measurement covers FIXTURE INTACTNESS of a two-item declared "
                   f"set. Measured here, the declared set is a small fraction of what exists: "
                   f"{F['stage_movies_pinned']} Training-stage movies are centrally pinned "
                   f"({F['stage_movies_centrally_pinned']} of them byte-checkable) and the "
                   f"row declares {len(F['stage_movies_declared_by_the_row'])}; "
                   f"{len(F['training_saves_pristine'])} pristine Training save states are "
                   f"pinned (plus {len(F['training_saves_non_pristine'])} non-pristine) and "
                   f"the row declares "
                   f"{len(F['pristine_training_saves_the_row_declares'])}. Neither NEW artifact this "
                   f"assessment adds is covered by any gate "
                   f"({len(F['gate_files_covering_the_new_measurements'])} gate files), and "
                   f"no gate file anywhere names the row id "
                   f"({len(F['gate_files_naming_the_row_id'])})",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the natural-execution material for this stage is the best-provisioned "
                     f"of any F row assessed so far, and none of it involves injection. A "
                     f"from-boot campaign replay covers the whole stage "
                     f"({F['completion_oracle_movie']}, {F['completion_oracle_frames']} "
                     f"frames, pristine_replay_accepted="
                     f"{F['completion_oracle_replay_accepted']}, entered at frame "
                     f"{F['completion_oracle_entered_stage_frame']}, exited by end="
                     f"{F['completion_oracle_stage_exited']}) and independently corroborates "
                     f"the scene id ({F['completion_oracle_corroborates_the_scene_id']}). "
                     f"Both save states this assessment measures are pristine-class and one "
                     f"is provably regenerable from a from-boot movie. NEW HERE, the row's "
                     f"central claim is now asserted against ORIGINAL bytes for the first "
                     f"time: the RE source every downstream page derives from was taken on a "
                     f"MOD build (evidence disc is ABL_ALLMODS: "
                     f"{F['re_source_evidence_disc_is_a_mod_build']}; it also declares itself "
                     f"pseudocode: {F['re_source_declares_itself_pseudocode']}), "
                     f"and its model is re-established here against the pristine image -- the "
                     f"step field's value is {F['step_field_values_across_fixtures']} in the "
                     f"two natural fixtures, its per-step state array shows "
                     f"{F['step_state_slots_nonzero_per_fixture']} of "
                     f"{F['re_declared_step_state_array'][1]} slots written, and the "
                     f"{len(F['cached_pickup_pointer_values'])} cached pickup pointers are "
                     f"contiguous at stride {F['cached_pickup_pointer_stride']}, matching the "
                     f"disc-side type-0x3f kind histogram "
                     f"({F['cached_pickup_pointer_count_matches_disc_type3f_kinds']})",
            "gap": f"none of that is an ORACLE. Nothing asserts, at a named frame of a named "
                   f"movie, that a lesson gate advanced -- which is exactly what the row asks "
                   f"for ('{F['row_declared_missing']}'). The two fixtures are two static "
                   f"snapshots, not a progression, and they sample "
                   f"2 of {F['re_declared_jump_table_arms']} steps. The campaign oracle "
                   f"asserts entry and exit only, and the row does not cite it "
                   f"({F['completion_oracle_cited_by_the_row']}); "
                   f"{F['action_windows_in_stage_total']} in-stage input windows are already "
                   f"recognized for that same movie and are likewise uncited "
                   f"({F['action_windows_cited_by_the_row']}). No gate asserts any Training "
                   f"behaviour keyed to the objective",
        },
        "complete_frontier": {
            "state": "met_candidate",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"the relevant frontier for this row's mechanic is a single indirect "
                     f"dispatch table, and it is now ENUMERATED from bytes rather than "
                     f"asserted in prose. {PROBESRC} finds the RE-declared "
                     f"{F['re_declared_jump_table_arms']}-arm table verbatim in exactly "
                     f"{F['jump_table_images_containing_it']} of "
                     f"{F['residency_pin_images_scanned']} overlay images, at "
                     f"{F['jump_table_address']} in {F['jump_table_image']}, with every arm "
                     f"inside that image ({F['jump_table_all_arms_inside_that_image']}) -- "
                     f"and the independent function census classifies exactly that range as "
                     f"'{F['function_census_classifies_the_jump_table_range']}' of "
                     f"{F['function_census_jump_table_range_size']} bytes, which is "
                     f"4 x the arm count ({F['jump_table_size_matches_arm_count']}). The "
                     f"table is bound to the state field by measurement, not by reading: "
                     f"{F['jump_table_arms_that_reload_the_field']} of "
                     f"{F['re_declared_jump_table_arms']} arms reload the field at a uniform "
                     f"offset of {F['jump_table_arm_reload_offsets']} bytes. The reference "
                     f"census around the field is exhaustive over both spaces: "
                     f"{F['probe_resident_reference_count']} resident references (both "
                     f"confirmed by decode below) and "
                     f"{F['probe_pinned_image_reference_count']} in the pinned overlay "
                     f"({F['probe_pinned_image_store_count']} stores, "
                     f"{F['probe_pinned_image_load_count']} loads), against the "
                     f"{F['census_code_functions_in_the_pinned_overlay']} code functions and "
                     f"{F['census_data_records_in_the_pinned_overlay']} data records the "
                     f"function census gives this overlay, plus its "
                     f"{len(F['overlay_resident_callees'])} enumerated resident callees. The "
                     f"residual is explicitly bounded rather than absent: the ownership "
                     f"graph's three frontier blockers "
                     f"({F['ownership_frontier_blockers']}) are each retired by a named "
                     f"measurement here",
            "gap": f"two bounded residuals, both named. (1) The enumeration is of the STEP "
                   f"MACHINE, not of the lesson CONDITIONS: what each arm waits for is "
                   f"decoded for {len(F['re_decoded_arm_indices'])} arms "
                   f"({F['re_decoded_arm_indices']}) in the "
                   f"RE source and left in prose for the rest, and the RE source is prose "
                   f"about a mod build. (2) The pinned overlay's callers are enumerated only "
                   f"inward: {F['ownership_functions']} functions are registered to this row "
                   f"in the ownership graph, and no artifact walks the "
                   f"{F['census_code_functions_in_the_pinned_overlay']} overlay functions to "
                   f"say which resident caller drives the tick. Item 2 names four things and "
                   f"CALLERS is one of them, so a verifier may reasonably reduce this to "
                   f"partial; what is offered against that is that callees ARE enumerated "
                   f"({len(F['overlay_resident_callees'])} resident callees for the image), "
                   f"the callback is byte-matched, the indirect table is exhaustive and "
                   f"unique across images, and the caller residual is bounded to resident "
                   f"code entering this image. A verifier must decide whether that, with the "
                   f"lesson conditions declared open, meets written item 2",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"this row is deliberately stage-unique -- Training is the only stage "
                     f"with a tutorial step machine, so 'generalizes across stages' has no "
                     f"content for its central mechanic, and the type authority places it as "
                     f"{F['c2_row_types']} with rule {F['c2_row_type_rules']}. What DOES "
                     f"generalize is measured: the scene/asset binding this row depends on is "
                     f"the campaign-wide arithmetic law "
                     f"(phase3_law_is_the_corrected_one={F['phase3_law_is_the_corrected_one']}), "
                     f"and Training is one of the ids where the string directory and the "
                     f"arithmetic directory DIVERGE "
                     f"({F['this_scene_is_a_string_dir_divergence']}, diverging ids "
                     f"{F['law_string_dir_diverges_for_ids']}), so this stage is the law's "
                     f"hardest case and it holds",
            "gap": f"there is no denominator inside the stage either. Of "
                   f"{F['stage_movies_pinned']} pinned Training routes "
                   f"({len(F['stage_movies_under_phase4_interpreter'])} of them under "
                   f"movies/Phase4/Interpreter/, i.e. traceable), the row's evidence replays "
                   f"none and declares "
                   f"{len(F['stage_movies_declared_by_the_row'])}. The step machine has "
                   f"{F['re_declared_jump_table_arms']} arms and the fixtures sample 2 of "
                   f"them. The type authority itself reports taxonomy_coverage_demonstrated="
                   f"{F['c2_taxonomy_coverage_demonstrated']} because "
                   f"{F['c2_underivable_types']} have no textual authority. No variant, "
                   f"retry, death or exceptional-path axis is enumerated for this stage, and "
                   f"the applicability universe the written bar needs does not exist",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"this row's one registered field is now typed and DOMAIN-BOUNDED by "
                     f"three independent measurements rather than by declaration. (i) "
                     f"STRUCTURAL: the field indexes a table with exactly "
                     f"{F['re_declared_jump_table_arms']} arms, byte-located and "
                     f"size-confirmed by the function census, so the domain is bounded by the "
                     f"table -- and the arm count equals the span of the registry's declared "
                     f"range ({F['jump_table_arm_count_equals_declared_range_span']}). (ii) "
                     f"SOURCE: the one byte-matched C function in this overlay guards on "
                     f"{F['byte_matched_c_bound_literals']}, and its outer guard literal "
                     f"{F['byte_matched_c_outer_guard_literal']} IS the registered maximum "
                     f"({F['byte_matched_c_guard_literal_equals_registered_max']}), used "
                     f"exclusively "
                     f"({F['byte_matched_c_guard_is_exclusive_so_it_excludes_the_terminal_step']}) "
                     f"so the callback runs for steps below it and is silent on the terminal "
                     f"step -- exactly the shape a 0..max domain with a looping last arm "
                     f"takes. (iii) "
                     f"OBSERVED: the field reads {F['step_field_values_across_fixtures']} "
                     f"across the two pristine fixtures, both inside the declared range "
                     f"{F['registered_entry_range']}, and it is zero in the disc image "
                     f"({F['step_field_is_zero_on_disc']}) so it is runtime state living "
                     f"inside the overlay image. The surrounding block is typed too: "
                     f"{F['named_words_count']} RE-declared words, all "
                     f"{F['named_words_inside_pinned_image']} inside the pinned image, "
                     f"{F['named_words_zero_in_disc_image']} zero on disc with the one "
                     f"exception being the static audio-id table "
                     f"({F['audio_id_table_is_static_on_disc']}), and the per-step state "
                     f"array is populated exactly as a progression predicts "
                     f"({F['step_state_slots_nonzero_per_fixture']} slots written in the two "
                     f"fixtures)",
            "gap": f"the REGISTRY is wrong in ways that matter more than the field being "
                   f"right. Its declared writer {F['registered_entry_declared_writers']} "
                   f"named '{F['registered_entry_declared_writer_names']}' is not a store in "
                   f"ANY of the {F['residency_pin_images_scanned']} images "
                   f"(is_store_anywhere={F['declared_writer_is_a_store_in_any_image']}; in "
                   f"the pinned image the word is "
                   f"{F['declared_writer_word_in_the_pinned_image']}, which does not decode "
                   f"as a memory operation), while the real stores are "
                   f"{F['function_owning_each_measured_store']} -- so the declared/measured "
                   f"writer counts are {F['declared_writer_count_vs_measured_store_count']} "
                   f"and the declared one is not among them "
                   f"({F['declared_writer_is_among_the_measured_stores']}). Only "
                   f"{len(F['semantic_entries_inside_this_rows_overlay_extent'])} semantic "
                   f"entry covers this overlay's whole extent, none of the other "
                   f"{F['named_words_count'] - 1} state words is registered at all, and "
                   f"{F['re_arms_left_in_prose']} of the "
                   f"{F['re_declared_jump_table_arms']} steps have no decoded advance "
                   f"condition, so the per-step state array's value domain is unbounded",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"COLD BOOT and LOAD are evidenced twice over and from opposite "
                     f"directions. The overlay's arrival at the shared base is proved by "
                     f"bytes in both fixtures ({F['residency_pin_result']}, "
                     f"{F['residency_pin_nontrivial_pct']}% vs "
                     f"{F['residency_pin_runner_up_pct']}% for the runner-up), and its "
                     f"INITIALIZATION is proved from an instruction: of the "
                     f"{len(F['measured_store_pcs_in_the_pinned_image'])} measured stores the "
                     f"lower one sits in {F['initializing_store_owner']} and the advancing "
                     f"one in {F['advancing_store_owner']}. Cold boot to stage entry "
                     f"and stage exit are evidenced by the campaign oracle (entered "
                     f"{F['completion_oracle_entered_stage_frame']}, exited by end="
                     f"{F['completion_oracle_stage_exited']}), and the strict anchor is a "
                     f"from-boot regeneration ({F['anchor_fixture_reproducible']}). "
                     f"REPEATED USE is the phase this row is best placed on of any F row: the "
                     f"per-step state array shows "
                     f"{F['step_state_slots_nonzero_per_fixture']} slots written between the "
                     f"two fixtures, i.e. the mechanism demonstrably ran many times",
            "gap": f"FIRST USE, EXHAUSTION, RETIREMENT and REUSE have no evidence. The two "
                   f"fixtures are endpoints, not a trace: nothing observes a single advance "
                   f"happening, which is what the row's own next action asks for "
                   f"('{F['row_declared_next']}'). The terminal step's behaviour "
                   f"(exhaustion) is asserted in RE prose from a mod build and never "
                   f"measured; nothing evidences the overlay being torn down or the block "
                   f"being reused by the next scene. No per-phase claim map is registered for "
                   f"this row the way F01 has one",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"one native crossing is real and byte-evidenced, and it is not one the "
                     f"row claims: the tutorial step field is read by RESIDENT code. Both "
                     f"resident reader PCs the xref census declares "
                     f"({F['xrefs_declared_readers']}, in "
                     f"{F['xrefs_declared_reader_functions']}) decode as "
                     f"{F['resident_reader_ops']} resolving to the registered address "
                     f"({F['resident_readers_confirmed_from_bytes']}/"
                     f"{len(F['xrefs_declared_readers'])} confirmed, "
                     f"{F['resident_reader_resolution']}), so the overlay-local tutorial state "
                     f"crosses into the resident gameplay state machine. A second crossing is "
                     f"documented by another baseline row and lands in this overlay "
                     f"({F['another_row_documents_the_overlay_callback_that_reads_it']}; rows "
                     f"citing the address at all: "
                     f"{F['other_baseline_rows_citing_this_address']}): the one byte-matched C "
                     f"function here is that callback, fed the same field "
                     f"({F['byte_matched_c_is_fed_the_registered_field']}) and dispatching on "
                     f"it to {F['byte_matched_c_callee']}. Stage-level crossings exist in uncited artifacts: the campaign "
                     f"oracle's stage snapshot carries "
                     f"{len(F['completion_oracle_snapshot_fields'])} cross-system fields and "
                     f"{F['action_windows_in_stage_total']} in-stage input events are "
                     f"recognized on that movie",
            "gap": f"the resident crossing is SCENE-GATED and the gate is not measured here: "
                   f"the same two instructions read whatever image is resident at "
                   f"{F['overlay_registry_region_a']}, and "
                   f"{F['probe_images_referencing_the_address']} images write that word, so "
                   f"what those reads mean outside Training is unestablished. Beyond that, no "
                   f"COMBINATION is exercised anywhere. Nothing tests the tutorial "
                   f"advancing while the player takes damage, dies, pauses, or is carrying; "
                   f"the recognizer set on this stage's own movie already reports "
                   f"{len(F['action_window_recognizers_with_zero_in_stage'])} of "
                   f"{F['action_window_recognizers']} recognizers at zero in-stage "
                   f"({F['action_window_recognizers_with_zero_in_stage']}), so several native "
                   f"axes are not even present in the one route that is analysed. The "
                   f"stage's actor pool is censused at {F['stage_actor_records']} records over "
                   f"ids {F['stage_actor_ids']} with "
                   f"{len(F['stage_actor_ids_with_canon_binding'])} of those ids carrying a "
                   f"Canon role, from this row's own pinned save "
                   f"({F['stage_actor_census_uses_the_pin_ram_source']}) and uncited by it "
                   f"({F['stage_actor_census_cited_by_the_row']}) -- so even the instructor "
                   f"NPC the row is named for is not bound to an actor id",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the load-side interface is documented to the instruction and this "
                     f"stage is its hardest case: dir = scene<=10 ? scene : scene-10 pinned at "
                     f"{F['law_arithmetic_instruction_pcs']}, giving "
                     f"{F['law_directory_for_this_scene']} for scene "
                     f"{F['scene_from_progression_table']}, which the ordinal table at "
                     f"{F['progression_table_address']} reaches from ordinal "
                     f"{F['training_ordinal']}. Four independent artifacts agree and none is "
                     f"downstream of another: the byte-level residency pin "
                     f"({F['residency_pin_file']}, sha1 matching the overlay build registry: "
                     f"{F['residency_pin_agrees_with_overlay_registry_sha1']}), the disc-side "
                     f"collision census ({F['stage_collision_container']}, "
                     f"corroborates={F['e02_corroborates_the_scene_id']}), the completion "
                     f"oracle's observed scene "
                     f"({F['completion_oracle_corroborates_the_scene_id']}), and the board "
                     f"editor's resolved target ({F['board_editor_target_file']}, "
                     f"agrees={F['board_editor_target_agrees_with_the_law']}). The folk name "
                     f"is refuted on the disc side too: "
                     f"{folk} holds "
                     f"{F['folk_named_level00_dat_type3f_entries']} type-0x3f entries in "
                     f"{F['folk_named_level00_dat_type3f_tables']} tables, while "
                     f"{F['this_stage_level_dat']} holds "
                     f"{F['this_stage_type3f_entries']}. The unknown is enumerated with a "
                     f"named obstruction rather than left blank: "
                     f"'{F['row_declared_missing']}'",
            "gap": f"the interface documentation that other readers consult is stale or "
                   f"mod-facing, and that is measurable. Of {F['vault_pages_total']} credited "
                   f"vault pages, {F['vault_pages_under_mods_dir']} live under Mods/ "
                   f"(distribution {F['vault_pages_by_class']}), "
                   f"{len(F['vault_pages_that_are_landing_stubs'])} of the Canon pages are "
                   f"landing stubs that carry no claim of their own, only "
                   f"{len(F['vault_pages_declaring_source_state_original_game'])} declares "
                   f"source_state original_game, and "
                   f"{len(F['non_mod_vault_pages_mentioning_an_allmods_build'])} of the "
                   f"non-Mods pages cite an ALLMODS build "
                   f"({F['non_mod_vault_pages_mentioning_an_allmods_build']}) as does the RE "
                   f"source itself ({F['re_source_evidence_disc_is_a_mod_build']}). "
                   f"{BOARD} still carries stale LEVEL01 prose alongside its resolved LEVEL07 "
                   f"target ({F['board_editor_still_carries_stale_level01_prose']}). On the "
                   f"registry side: the shared overlay region holds "
                   f"{len(F['semantic_entries_inside_shared_region_a'])} semantic entry "
                   f"({F['semantic_entries_inside_shared_region_a']}), and it carries no image "
                   f"field ({F['registered_entry_has_no_image_field']}), the xref "
                   f"census itself records that it cannot see the declared writer "
                   f"('{F['xrefs_admits_it_cannot_see_the_declared_writer']}'), and the "
                   f"function census, the overlay summary and the movie scheduler report "
                   f"{F['census_entries_in_the_pinned_overlay']}, "
                   f"{F['overlay_summary_function_count']} and "
                   f"{F['scheduler_static_ownership_function_count']} functions for the same "
                   f"overlay",
        },
        "source_closure": {
            "state": "partial",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured against BOTH registries, and the first result is a "
                     f"CORRECTION. The census credits this row with "
                     f"{len(F['census_source_files'])} source files "
                     f"({F['census_source_files']}) and it is the only F row so credited "
                     f"({F['f_rows_with_any_source_files']}) -- but those are RE PROSE, not "
                     f"byte-matched C: they appear in neither build registry "
                     f"({F['census_credited_source_files_are_in_neither_build_registry']}), "
                     f"and the file says so itself "
                     f"({F['re_source_declares_itself_pseudocode']}). RESIDENT "
                     f"(config/segments.yml, {F['resident_build_units']} units, toolchain "
                     f"{F['resident_build_toolchain']}): this row has "
                     f"{F['census_segments_entries']} entries, as does every F row "
                     f"({F['f_rows_with_any_segments_entries']}), and its "
                     f"{F['governing_addresses_resident']} resident governing addresses land "
                     f"in {len(F['governing_resident_build_units'])} build unit(s) with "
                     f"{F['governing_resident_addresses_outside_any_build_unit']} outside any "
                     f"unit. OVERLAY (config/overlays.yml + src/overlays/ + "
                     f"{OVLD}, {F['overlay_track_matched_functions']}/"
                     f"{F['overlay_track_total_code_functions']} = "
                     f"{F['overlay_track_matched_pct']}% campaign-wide): this row's overlay "
                     f"HAS a build entry -- {F['pinned_overlay_matched_functions']} of "
                     f"{F['pinned_overlay_code_functions']} code functions matched from "
                     f"{F['pinned_overlay_matched_sources']}, rebuild validated "
                     f"({F['pinned_overlay_rebuild_validated']}) with rebuilt sha1 equal to "
                     f"the blob's ({F['pinned_overlay_rebuilt_sha1_matches_the_blob']}), and "
                     f"that sha1 is the sha1 of the image this assessment byte-pinned as "
                     f"resident ({F['residency_pin_agrees_with_overlay_registry_sha1']}). "
                     f"Unlike the sibling rows, that one matched function is ON this row's "
                     f"frontier rather than beside it: it is fed the row's registered field "
                     f"({F['byte_matched_c_is_fed_the_registered_field']}) and its outer "
                     f"guard literal is the registered domain maximum "
                     f"({F['byte_matched_c_guard_literal_equals_registered_max']}). So overlay "
                     f"byte-matching is DEMONSTRATED for this row's overlay, not impossible",
            "gap": f"one governing function of {F['governing_addresses_in_this_rows_overlay']} "
                   f"overlay governing addresses has matched C "
                   f"({F['governing_overlay_addresses_with_matched_c']}), and it is a "
                   f"{F['byte_matched_c_bytes']}-byte dispatch "
                   f"wrapper. The function that actually runs the tutorial -- the one "
                   f"containing the advancing store -- is "
                   f"{F['advancing_store_owner']} and has no C, nor do the "
                   f"other {F['census_code_functions_in_the_pinned_overlay'] - 1} code "
                   f"functions in the image. On the resident side the two confirmed readers "
                   f"resolve to {F['governing_resident_units_matching_c']} matching-C unit(s) "
                   f"and {F['governing_resident_units_hand_asm']} hand-ASM unit(s). Note the "
                   f"direction of the census's own triage: it reports "
                   f"'{F['census_triage']['source_closure']}', which measures REGISTRATION -- "
                   f"and here the registration that produced it was the src_re credit, which "
                   f"is not source closure at all",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F00_training measured against the nine DoD dimensions AS WRITTEN "
                    "(item 2 = enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f00_written_bar_assessment.py",
        "schema": "abl-phase4-f00-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": ROW_ID,
        "row_name": req(row, "name", where=BASE),
        "standard": {
            "ruling": "engineering-specs/phase4-measurement-standard-ruling.md",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads as "
                          "met; this assessment publishes measurement, not disposition",
            "allowed_states": ["met", "met_candidate", "partial", "not_met", "unmeasured"],
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "edits_mechanics_baseline": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor did not author F00's underlying evidence, but "
                               "did author this assessment, the F-row census whose "
                               "durable_evidence result it carries forward, and both NEW "
                               "measurements in it (the residency pin run and "
                               "tools/phase4_f00_state_owner_probe.c) -- so on overlay "
                               "residency, the writer correction and the jump-table "
                               "enumeration the tool, the claim and the judgment share an "
                               "author. Every state below is a submission to a fresh "
                               "detached verifier, not a promotion; `partial` and `not_met` "
                               "are as challengeable as `met_candidate`",
        },
        "carried_forward": {
            "dimension": "durable_evidence",
            "from": CENSUS,
            "state": F["census_durable_state"],
            "fraction": F["census_durable_fraction"],
            "note": "measured there against pinned bytes; re-deriving it here would be a "
                    "second opinion on a settled measurement, not evidence",
        },
        "systemic_defect_checks": {
            "_comment": "two defects confirmed on other rows, checked explicitly here so "
                        "silence is not read as absence",
            "a_overlay_misattribution": {
                "applies_to_this_row": True,
                "why": f"the row's whole binding is a claim about an address in the shared "
                       f"overlay window {F['overlay_registry_region_a']}, and "
                       f"{F['probe_images_whose_extent_covers_the_address']} of "
                       f"{F['residency_pin_images_scanned']} overlay images extend far enough "
                       f"to contain that address",
                "was_the_row_already_wrong": False,
                "how_settled": f"{PINSRC} (reused unchanged: "
                               f"{F['residency_pin_generator_is_reused_unchanged']}; its "
                               f"output therefore keeps that tool's F08-branded strings) over "
                               f"{F['residency_pin_images_scanned']} images x "
                               f"{F['residency_pin_rams_scanned']} pristine Training fixtures",
                "verdict": f"{F['residency_pin_result']} -- {F['residency_pin_file']} "
                           f"({F['residency_pin_nontrivial_pct']}% vs "
                           f"{F['residency_pin_runner_up_pct']}% for the runner-up "
                           f"{F['residency_pin_runner_up']}), sha1 agreeing with the overlay "
                           f"build registry "
                           f"({F['residency_pin_agrees_with_overlay_registry_sha1']}) and with "
                           f"the row's declared overlay "
                           f"({F['residency_pin_agrees_with_row_binding']}). The row's "
                           f"scene-17 binding is CONFIRMED by an independent method",
                "how_much_ambiguity_was_really_there":
                    f"{F['probe_images_referencing_the_address']} images actually REFERENCE "
                    f"the address in code, not one: besides the pinned image "
                    f"({F['probe_pinned_image_reference_count']} references, "
                    f"{F['probe_pinned_image_store_count']} stores) the others are "
                    f"{F['other_images_referencing_the_same_address']} (path, references, "
                    f"stores). An address-only census had a real chance of picking wrong",
            },
            "b_semantic_registry_collision": {
                "applies_to_this_row": True,
                "va_collision_hit": True,
                "measured": f"the ownership graph attributes this one state id to "
                            f"{F['rows_sharing_this_state_count']} rows "
                            f"({F['rows_the_ownership_graph_attributes_this_state_to']}), and "
                            f"the registry entry carries no image field "
                            f"({F['registered_entry_has_no_image_field']}). Resolving each "
                            f"sharing row through the same ordinal->scene->overlay law gives "
                            f"{F['collision_rows_resolved_to_their_own_overlay']}, and those "
                            f"overlays are exactly the other images the byte scan finds "
                            f"storing to the same address "
                            f"({F['collision_explained_by_the_other_images_that_reference_the_address']}). "
                            f"The collision is therefore not a bookkeeping slip: the same VA "
                            f"is genuinely different, written state in different overlays",
                "is_the_entry_correct_for_THIS_row":
                    f"YES for identity and domain, NO for provenance. Correct: the address is "
                    f"inside the byte-pinned image extent {F['pinned_overlay_extent']}, it is "
                    f"zero on disc and runtime-written, its observed values "
                    f"{F['step_field_values_across_fixtures']} lie inside the declared range "
                    f"{F['registered_entry_range']}, the arm count of the table it indexes "
                    f"equals that range's span "
                    f"({F['jump_table_arm_count_equals_declared_range_span']}), and the one "
                    f"byte-matched C function in the image guards on that same maximum "
                    f"({F['byte_matched_c_guard_literal_equals_registered_max']}). Wrong: the "
                    f"declared writer {F['registered_entry_declared_writers']} is not a store "
                    f"in any image ({F['declared_writer_is_a_store_in_any_image']}), the real "
                    f"stores are {F['measured_store_pcs_in_the_pinned_image']}, and the entry "
                    f"names no image so it cannot be right for the other overlay that also "
                    f"writes there",
            },
        },
        "registry_disposition_for_contrast": {
            "source": DEBT,
            "campaign_id": F["registry_campaign_id"],
            "completion_state": F["registry_completion_state"],
            "dimensions_met": F["registry_dimensions_met"],
            "dimensions_remaining": F["registry_dimensions_remaining"],
            "distinct_basis_strings": F["registry_distinct_bases"],
            "distinct_states": F["registry_distinct_states"],
            "note": "the registry carries ONE blanket basis across all nine dimensions and "
                    f"scores the row 0/9, recording movie_count "
                    f"{F['registry_movie_count']} and prior_offline_analysis_count "
                    f"{F['registry_prior_offline_analysis_count']} for a stage with "
                    f"{F['stage_movies_pinned']} pinned movies and "
                    f"{F['census_analysis_artifacts_credited']} credited analysis artifacts. "
                    "That is a disposition, not a measurement",
        },
        "fail_loud_contract": {
            "guards": F["fail_loud_guards_fired"],
            "in_band": "re-proved on every generation before any artifact is read; if a "
                       "guard stops firing the run aborts instead of emitting numbers whose "
                       "staleness detection cannot be trusted",
            "cross_tool_guards": [
                "the residency pin's load base and region length must equal what "
                "config/overlays.yml declares",
                "the residency pin's word set must equal the set derived from the RE "
                "source's own #defines and loop bounds",
                "the state-owner probe's $gp, load base and pinned image must equal what "
                "analysis/phase3_xrefs.json, config/overlays.yml and the residency pin say",
                "the probe's reader PCs must equal analysis/phase3_xrefs.json's, its writer "
                "PCs must equal config/semantic_state.yaml's, and its searched sequence must "
                "equal the RE source's printed jump table",
                "every credited vault page must exist",
            ],
            "out_of_band_probes": "each was run by hand against this exact tool; every one "
                                  "must abort with a non-zero exit and leave NO output file",
            "out_of_band_probes_run_2026-08-11": [
                "moved analysis/phase4_f00_state_owner_probe.json aside -> exit 1, no output "
                "file, 'STALE CITATION: ... does not exist'",
                "renamed unique_pin_file inside the residency pin -> exit 1, no output file, "
                "'STALE CITATION: ... no longer has unique_pin_file'",
                "dropped one named word from the residency pin so its word set no longer "
                "equals the RE source's -> exit 1, no output file, both sets printed",
                "rewrote the state-owner probe's pinned_image to another overlay -> exit 1, "
                "no output file, 'the state-owner probe pinned a different image than the "
                "residency pin decided'",
                "moved a credited vault page aside -> exit 1, no output file, 'STALE "
                "CITATION: credited vault page ... does not exist'",
            ],
            "regenerability_checked": "both new artifacts were regenerated from their "
                                      "compiled-C generators after the probes and compared "
                                      "byte-for-byte with the committed copies",
        },
        "fact_provenance": {
            "facts_total": len(F),
            "facts_derived_from_pinned_artifacts": len(E.provenance),
            "facts_hand_typed": len(F) - len(E.provenance),
            "rule": "facts are recorded through fact(key, value, source); a value cannot be "
                    "stored without naming a pinned artifact, and every lookup is strict, so "
                    "a renamed or removed key aborts the run instead of silently defaulting",
            "by_fact": E.provenance,
        },
        "facts": F,
        "evidence_pins": E.pins,
        "dimensions": dims,
        "counts": counts,
        "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                   f"met-candidate, {counts.get('partial', 0)} partial, "
                   f"{counts.get('not_met', 0)} not met, {counts.get('unmeasured', 0)} "
                   f"unmeasured -- against the WRITTEN bars. F00 is the most DOCUMENTED and "
                   f"least REGISTERED F row: 17 vault pages and a 0/9 blanket disposition. "
                   f"Measured, its mechanic turns out to be the best-bounded of any F row "
                   f"assessed -- an enumerated 14-arm dispatch table, a domain bound agreed "
                   f"by structure, byte-matched C and observation -- while the objective "
                   f"oracle the row asks for still does not exist.",
        "notable": [
            f"THE ROW'S SOURCE CREDIT IS NOT SOURCE CLOSURE. This is the only F row the "
            f"census credits with source files ({F['f_rows_with_any_source_files']}), and the "
            f"credit is for {F['census_source_files']} -- RE prose that appears in NEITHER "
            f"build registry ({F['census_credited_source_files_are_in_neither_build_registry']}) "
            f"and that says of itself it is not compiled "
            f"({F['re_source_declares_itself_pseudocode']}). It is also derived from a MOD "
            f"build ({F['re_source_evidence_disc_is_a_mod_build']}), as is the archived Canon "
            f"provenance note. The row's REAL byte-matched C is one overlay function "
            f"({F['pinned_overlay_matched_sources']}), and it is better than the credit "
            f"suggested: it is fed this row's registered field "
            f"({F['byte_matched_c_is_fed_the_registered_field']}) and its outer guard literal "
            f"{F['byte_matched_c_outer_guard_literal']} is the registered domain maximum.",

            f"THE REGISTERED WRITER IS NOT A WRITER. config/semantic_state.yaml declares "
            f"{F['registered_entry_declared_writers']} "
            f"('{F['registered_entry_declared_writer_names']}') as the writer of "
            f"{F['re_declared_step_field']} at confidence "
            f"'{F['registered_entry_confidence']}'. Decoded from bytes, that word is "
            f"{F['declared_writer_word_in_the_pinned_image']} and it is not a store in ANY of "
            f"the {F['residency_pin_images_scanned']} images "
            f"(is_store_in_any_image={F['declared_writer_is_a_store_in_any_image']}). The "
            f"actual stores are {F['function_owning_each_measured_store']} -- the "
            f"initializing one in {F['initializing_store_owner']} and the advancing one in "
            f"{F['advancing_store_owner']}. "
            f"analysis/phase3_xrefs.json already flagged that it could not check this "
            f"('{F['xrefs_admits_it_cannot_see_the_declared_writer']}') and the check was "
            f"never done; it is done here.",

            f"THE SAME ADDRESS IS REAL STATE IN TWO DIFFERENT OVERLAYS, AND THAT EXPLAINS THE "
            f"THREE-ROW COLLISION. {F['probe_images_referencing_the_address']} of "
            f"{F['residency_pin_images_scanned']} images reference "
            f"{F['re_declared_step_field']} in code; besides this row's "
            f"({F['probe_pinned_image_reference_count']} references, "
            f"{F['probe_pinned_image_store_count']} stores) the others are "
            f"{F['other_images_referencing_the_same_address']}. The ownership graph attributes "
            f"the entry to {F['rows_the_ownership_graph_attributes_this_state_to']}, and "
            f"resolving each of those rows through the ordinal->scene->overlay law lands on "
            f"exactly those images ({F['collision_rows_resolved_to_their_own_overlay']}, "
            f"consistent={F['collision_explained_by_the_other_images_that_reference_the_address']}). "
            f"A registry that keys overlay VAs globally cannot be right for both rows; adding "
            f"an image field is the fix, and this row's entry is the correct one for "
            f"{F['residency_pin_file']}.",

            f"THE DISPATCH TABLE IS WHERE ITEM 2 IS ACTUALLY MET. The "
            f"{F['re_declared_jump_table_arms']}-arm table exists verbatim at "
            f"{F['jump_table_address']} in exactly "
            f"{F['jump_table_images_containing_it']} of "
            f"{F['residency_pin_images_scanned']} images; the function census independently "
            f"classifies that range as "
            f"'{F['function_census_classifies_the_jump_table_range']}' of "
            f"{F['function_census_jump_table_range_size']} bytes "
            f"({F['jump_table_size_matches_arm_count']} = 4 x arms); and "
            f"{F['jump_table_arms_that_reload_the_field']}/"
            f"{F['re_declared_jump_table_arms']} arms reload the indexing field at a uniform "
            f"offset of {F['jump_table_arm_reload_offsets']} bytes. Three independent "
            f"structures agreeing is what makes this an enumeration rather than a reading of "
            f"the RE prose it came from.",

            f"THE 17 VAULT PAGES ARE MOSTLY NOT ABOUT THE ORIGINAL GAME. Distribution "
            f"{F['vault_pages_by_class']}; {F['vault_pages_under_mods_dir']} are MOD pages; "
            f"{len(F['vault_pages_that_are_landing_stubs'])} of the Canon pages are landing "
            f"stubs carrying no claim of their own "
            f"({F['vault_pages_that_are_landing_stubs']}); exactly "
            f"{len(F['vault_pages_declaring_source_state_original_game'])} page declares "
            f"source_state original_game "
            f"({F['vault_pages_declaring_source_state_original_game']}); and "
            f"{len(F['non_mod_vault_pages_mentioning_an_allmods_build'])} of the non-Mods "
            f"pages cite an ALLMODS build "
            f"({F['non_mod_vault_pages_mentioning_an_allmods_build']}), as does the RE source "
            f"the row's central model comes from. Page count is the wrong proxy for this row's evidence, "
            f"which is why the census's own inventory is reported here by KIND.",

            f"THE STAGE'S EXIT IS THE REGION-CODE MECHANISM, ALREADY CLOSED BY ANOTHER ROW. "
            f"{F['stage_collision_container']} authors "
            f"{F['stage_authored_collision_sectors']} collision sectors with histogram "
            f"{F['stage_region_code_histogram']}: a single non-zero sector, "
            f"{F['stage_nonzero_region_sectors']}, with zero disc-vs-runtime mismatches "
            f"({F['stage_disc_vs_runtime_mismatches']}) across a census of "
            f"{F['e02_authored_sectors_compared']} sectors and "
            f"{F['e02_disagreements']} disagreements. So unlike F08, this stage's exit path is "
            f"inherited from a closed row and only the tutorial progression is open.",

            f"THE BLOCKER THE ROW RECORDS IS NOT A MISSING FIXTURE. The row asks for "
            f"'{F['row_declared_fixture_need']}' while {F['stage_movies_pinned']} Training "
            f"movies are pinned ({len(F['stage_movies_under_phase4_interpreter'])} under "
            f"movies/Phase4/Interpreter/, i.e. traceable, format versions "
            f"{F['stage_movie_format_versions']}) and "
            f"{len(F['training_saves_pristine'])} pristine Training saves exist "
            f"({F['training_saves_pristine']}). The row declares "
            f"{len(F['stage_movies_declared_by_the_row'])} of the movies and none of the "
            f"saves, so the scheduler marks it ineligible with reason "
            f"{F['scheduler_ineligibility_reasons']} "
            f"(sees_a_phase4_movie={F['scheduler_sees_a_phase4_movie']}) and reports "
            f"{F['scheduler_static_ownership_function_count']} owned function(s). "
            f"Under-declaration in the row is blocking the exact work the row asks for.",

            f"UNMEASURED HERE, and named so a verifier does not read silence as absence: what "
            f"each of the {F['re_declared_jump_table_arms']} steps waits for (the RE source "
            f"decodes {len(F['re_decoded_arm_indices'])} arms and leaves "
            f"{F['re_arms_left_in_prose']} in prose, and it is prose about a mod build); "
            f"whether a single advance can be observed happening (that needs a replay of one "
            f"of the {len(F['stage_movies_under_phase4_interpreter'])} traceable routes, not "
            f"a re-read); which actor id among {F['stage_actor_ids']} is the instructor NPC; "
            f"and whether the per-step state array's values have bounded domains.",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar F00] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} derived / "
          f"{doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
