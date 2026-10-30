#!/usr/bin/env python3
"""Measure F08_city_square's nine DoD dimensions against the bars AS WRITTEN.

Sibling of `tools/phase4_f01_written_bar_assessment.py` (the exemplar) and
`tools/phase4_f09_written_bar_assessment.py` (the rigor standard), under
`engineering-specs/phase4-measurement-standard-ruling.md`. The WRITTEN bars are:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

WHY F08 IS AN INTERESTING SHAPE. F09 was a stage row whose subjects were driven
by OTHER rows. F08 is the opposite: it is a stage row that solved a CAMPAIGN-WIDE
infrastructure problem (the scene->asset binding, which it corrected for twelve
rows on 2026-08-05) and has not started on its own subject at all -- how
performers are found via markers. So this assessment separates, per dimension,
what F08 proved about the loader from what F08 must prove about its objective.

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
`analysis/phase4_f_row_measured_census.json` (5/5 declared fixtures intact) and
is carried forward with its fraction, failing loudly if that measurement moves.

TWO SYSTEMIC DEFECTS ARE CHECKED EXPLICITLY, because two other rows were hit by
them today:
  (a) OVERLAY MISATTRIBUTION -- every per-level overlay loads at the same base
      (region A), so an address in that window names real content in almost every
      overlay image and an address-only census picks the wrong file. F08 is the
      row that DISCOVERED this class, but its own answer was recorded as prose
      percentages with no tool behind them. `tools/phase4_f08_overlay_residency_pin.c`
      (compiled C owns the byte decoding) re-decides it from bytes across every
      image and every fixture, and this tool re-derives what that scan was given
      from the pinned registries so the two cannot drift apart.
  (b) SEMANTIC-REGISTRY COLLISION -- config/semantic_state.yaml keys
      overlay-local addresses GLOBALLY. Measured here against F08's pinned
      overlay EXTENT, not against the shared region.

BOTH SOURCE REGISTRIES ARE READ before any source_closure claim: config/segments.yml
(resident) and config/overlays.yml + src/overlays/ + analysis/overlay_decomp_progress.json
(overlay track). A claim that overlay byte-matching is impossible was banked and
retracted for checking only the first.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a
fresh detached verifier. This tool never edits analysis/mechanics_baseline.yaml.

Usage: python3 tools/phase4_f08_written_bar_assessment.py [--out PATH] [--no-gates]
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
ROW_ID = "F08_city_square"


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
    drifting the residency pin away from the C source it is checked against) were
    run by hand and each aborted with a non-zero exit and no output file. Those are
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
                    default=str(ROOT / "analysis/phase4_f08_written_bar_assessment.json"))
    ap.add_argument("--no-gates", action="store_true",
                    help="skip executing this row's registered pytest gates")
    args = ap.parse_args()

    E = Evidence()
    F = E.facts

    # ------------------------------------------------------------------ #
    # 0. prove the staleness detection works before trusting any number   #
    # ------------------------------------------------------------------ #
    SELF = "tools/phase4_f08_written_bar_assessment.py"
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
    E.fact("census_source_files_credited", len(req(inv, "source_files", where=CENSUS)), CENSUS)
    E.fact("census_segments_entries", req(inv, "segments_entries", where=CENSUS), CENSUS)
    E.fact("census_overlay_build_entries", req(inv, "overlay_build_entries", where=CENSUS),
           CENSUS)
    E.fact("census_overlay_name", req(inv, "overlay_name", where=CENSUS), CENSUS)
    E.fact("census_scene_id", req(inv, "scene_id", where=CENSUS), CENSUS)
    E.fact("census_stage_ordinal", req(inv, "stage_ordinal", where=CENSUS), CENSUS)
    E.fact("census_has_runtime_trace_evidence",
           req(inv, "has_runtime_trace_evidence", where=CENSUS), CENSUS)
    E.fact("census_overlay_track_totals", req(inv, "overlay_track_totals", where=CENSUS),
           CENSUS)

    fixtures = req(crow, "durable_evidence", "fixtures", where=CENSUS)
    external = [f["path"] for f in fixtures
                if req(f, "kind", where=CENSUS) == "external_fixture"]
    in_repo = [f["path"] for f in fixtures
               if req(f, "kind", where=CENSUS) == "in_repo_artifact"]
    E.fact("row_external_fixtures", external, CENSUS)
    E.fact("row_external_fixture_count", len(external), CENSUS)
    E.fact("row_in_repo_artifact_count", len(in_repo), CENSUS)
    if F["census_durable_state"] != "met":
        raise SystemExit("carried-forward durable_evidence is no longer 'met' -- "
                         "re-measure before reusing this assessment")

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
    E.fact("row_declared_fixtures", len(req(row, "fixture_have", where=BASE)), BASE)
    E.fact("row_declared_fixture_paths", req(row, "fixture_have", where=BASE), BASE)
    E.fact("row_declared_missing", req(row, "missing", where=BASE), BASE)
    E.fact("row_declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
    E.fact("row_declared_evidence_classes", req(row, "evidence", where=BASE), BASE)
    E.fact("row_declared_next", req(row, "next", where=BASE), BASE)
    E.fact("row_declared_status", req(row, "status", where=BASE), BASE)
    E.fact("row_records_prior_binding_falsified",
           any("FALSIFIED" in b for b in req(row, "bindings", where=BASE)), BASE)
    E.fact("row_artifact_path_citations",
           len(set(re.findall(r"(?:analysis|tools|src|src_re|tests|config)/[\w./%-]+",
                              json.dumps(row)))), BASE)
    # The row F08's correction is a SIBLING of: the other city stage, same type.
    f07 = next((r for r in rows if r.get("id") == "F07_city_entrance"), None)
    if f07 is None:
        raise SystemExit(f"STALE CITATION: {BASE} no longer carries F07_city_entrance")
    E.fact("sibling_city_row_status", req(f07, "status", where=BASE), BASE)

    # ------------------------------------------------------------------ #
    # 4. the row's own evidence artifact: the corrected scene binding     #
    # ------------------------------------------------------------------ #
    BIND = "analysis/phase4_f08_scene_binding.json"
    bind = E.json(BIND)
    E.fact("binding_status", req(bind, "status", where=BIND), BIND)
    E.fact("binding_scene_id", req(bind, "f08_corrected_binding", "scene_id", where=BIND), BIND)
    E.fact("binding_level_data_dir",
           req(bind, "f08_corrected_binding", "level_data_dir", where=BIND), BIND)
    E.fact("binding_variant", req(bind, "f08_corrected_binding", "variant", where=BIND), BIND)
    E.fact("binding_overlay_resident",
           req(bind, "f08_corrected_binding", "overlay_resident", where=BIND), BIND)
    E.fact("binding_was_claimed", req(bind, "f08_corrected_binding", "was_claimed", where=BIND),
           BIND)
    E.fact("binding_residency_confirmations",
           len(req(bind, "residency_confirmation", where=BIND)), BIND)
    E.fact("binding_residency_all_matched",
           all(req(c, "match", where=BIND) for c in req(bind, "residency_confirmation",
                                                        where=BIND)), BIND)
    E.fact("binding_residency_distinct_scenes",
           len({req(c, "scene", where=BIND) for c in req(bind, "residency_confirmation",
                                                         where=BIND)}), BIND)
    E.fact("binding_rows_corrected", len(req(bind, "rows_corrected", where=BIND)), BIND)
    E.fact("binding_rows_with_wrong_binding",
           len(req(bind, "rows_with_wrong_scene_asset_binding", where=BIND)), BIND)
    wrong_ids = {req(r, "row", where=BIND)
                 for r in req(bind, "rows_with_wrong_scene_asset_binding", where=BIND)}
    E.fact("binding_rows_corrected_but_not_listed_wrong",
           sorted(set(req(bind, "rows_corrected", where=BIND)) - wrong_ids), BIND)
    E.fact("binding_scene_ids_mapped", len(req(bind, "scene_id_to_level_data_dir", where=BIND)),
           BIND)
    E.fact("binding_sound_bank_ids_mapped",
           len(req(bind, "scene_id_to_sound_bank_index", where=BIND)), BIND)
    E.fact("binding_scope_limits", req(bind, "scope_limits", where=BIND), BIND)
    E.fact("binding_scope_limit_count", len(req(bind, "scope_limits", where=BIND)), BIND)
    E.fact("binding_false_positive_note", req(bind, "false_positive_note", where=BIND), BIND)
    E.fact("binding_declares_tools", req(bind, "tools", where=BIND), BIND)
    E.fact("binding_residency_method_is_offline",
           req(bind, "residency_method", where=BIND).startswith("offline"), BIND)
    E.fact("binding_string_dir_diverges_for",
           req(bind, "string_dir_vs_arithmetic_dir", "diverge_for_ids", where=BIND), BIND)

    # the arithmetic law's three pinned instruction addresses, read from the artifact
    law_text = req(bind, "mechanism", "level_data_directory", where=BIND)
    law_pcs = sorted(set(re.findall(r"0x[0-9A-Fa-f]{8}", law_text)))
    if len(law_pcs) < 3:
        raise SystemExit("STALE CITATION: the binding artifact's arithmetic law no longer "
                         "names the instruction addresses this assessment resolves")
    E.fact("arithmetic_law_instruction_pcs", law_pcs, BIND)
    bank_text = req(bind, "mechanism", "sound_bank", where=BIND)
    E.fact("sound_bank_mechanism_pcs", sorted(set(re.findall(r"0x[0-9A-Fa-f]{8}", bank_text))),
           BIND)

    # ------------------------------------------------------------------ #
    # 5. NEW MEASUREMENT: which overlay FILE is resident, decided by      #
    #    BYTES across every image and every fixture (defect (a)).         #
    #    The scan's inputs are re-derived here from the pinned registries #
    #    so the C run cannot drift away from the claims it supports.      #
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
    E.fact("overlay_registry_entry_base", f'0x{as_int(req(ovl_entry, "base", where=OVLY)):08X}',
           OVLY)
    E.fact("overlay_registry_attempted_units", len(req(ovl_entry, "attempted", where=OVLY)),
           OVLY)
    E.fact("overlay_registry_total_overlays", len(req(ovly, "overlays", where=OVLY)), OVLY)

    INITC = req(ovl_entry, "attempted", 0, "source", where=OVLY)
    init_src = E.text(INITC)
    word_syms = sorted({s.lower() for s in re.findall(r"g_(800b[0-9a-fA-F]{4})", init_src)})
    if not word_syms:
        raise SystemExit(f"STALE CITATION: {INITC} no longer declares overlay-local "
                         "globals; the named-word scan has nothing to be checked against")
    E.fact("byte_matched_c_source", INITC, INITC)
    E.fact("byte_matched_c_declared_words", [f"0x{s.upper()}" for s in word_syms], INITC)
    E.fact("byte_matched_c_declared_word_count", len(word_syms), INITC)
    init_literals = [int(m) for m in re.findall(r"=\s*(\d+);", init_src)]
    E.fact("byte_matched_c_nonzero_initializers", sorted(v for v in init_literals if v), INITC)

    PIN = "analysis/phase4_f08_overlay_residency_pin.json"
    pin = E.json(PIN)
    PINSRC = "tools/phase4_f08_overlay_residency_pin.c"
    E.pin(PINSRC)
    if as_int(req(pin, "declared_load_base", where=PIN)) != region_a:
        raise SystemExit("the residency pin scanned a load base the overlay registry does "
                         "not declare")
    if req(pin, "region_length", where=PIN) != region_b - region_a:
        raise SystemExit("the residency pin scanned a region length the overlay registry "
                         "does not declare")
    scanned_words = {req(w, "addr", where=PIN).lower() for w in req(pin, "named_words",
                                                                    where=PIN)}
    if scanned_words != {f"0x{s}" for s in word_syms}:
        raise SystemExit("the residency pin read words the byte-matched C source no longer "
                         f"declares: scanned={sorted(scanned_words)} "
                         f"declared={sorted('0x' + s for s in word_syms)}")
    E.fact("residency_pin_inputs_match_registries", True, [PIN, OVLY, INITC])
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

    pimages = req(pin, "images", where=PIN)
    falsified_file = next((im for im in pimages if "LEVEL10_LEVEL.BIN" in im["path"]), None)
    if falsified_file is None:
        raise SystemExit(f"STALE CITATION: {PIN} no longer scans the image the row's prior "
                         "binding named (LEVEL10_LEVEL.BIN)")
    E.fact("falsified_claim_image_nontrivial_pct",
           req(falsified_file, "per_ram", 0, "nontrivial_pct", where=PIN), PIN)
    E.fact("falsified_claim_image_anchor_agreement",
           req(falsified_file, "per_ram", 0, "anchor_base_agreeing", where=PIN), PIN)
    E.fact("falsified_claim_image_stable_base",
           req(falsified_file, "stable_anchor_base_equals_declared", where=PIN), PIN)
    wanderers = sorted(im["path"] for im in pimages
                       if req(im, "per_ram", 0, "anchor_base_agreeing", where=PIN) >= 1
                       and not req(im, "stable_anchor_base_equals_declared", where=PIN))
    E.fact("images_with_anchor_hits_but_no_stable_declared_base", len(wanderers), PIN)
    E.fact("images_with_anchor_hits_but_no_stable_declared_base_paths", wanderers, PIN)
    at_declared = sorted(im["path"] for im in pimages
                         if req(im, "per_ram", 0, "anchor_base", where=PIN)
                         == req(pin, "declared_load_base", where=PIN))
    E.fact("images_whose_best_anchor_base_is_the_declared_base", len(at_declared), PIN)
    E.fact("images_whose_best_anchor_base_is_the_declared_base_paths", at_declared, PIN)

    diff = req(pin, "cross_fixture_diff", where=PIN)
    E.fact("region_a_bytes", req(diff, "region_a_bytes", where=PIN), PIN)
    E.fact("region_a_differing_bytes", req(diff, "region_a_differing_bytes", where=PIN), PIN)
    E.fact("region_a_differing_inside_pinned_image",
           req(diff, "region_a_differing_inside_pinned_image", where=PIN), PIN)
    E.fact("region_a_differing_beyond_pinned_image",
           req(diff, "region_a_differing_beyond_pinned_image", where=PIN), PIN)
    E.fact("whole_ram_words", req(diff, "whole_ram_words", where=PIN), PIN)
    E.fact("whole_ram_differing_words", req(diff, "whole_ram_differing_words", where=PIN), PIN)
    chains = req(pin, "subset_chain_search", where=PIN)
    E.fact("u32_subset_chains", req(chains, "u32_subset_chains", where=PIN), PIN)
    E.fact("u32_strict_one_bit_per_step_chains",
           req(chains, "u32_strict_one_bit_per_step_chains", where=PIN), PIN)
    E.fact("u16_subset_chains", req(chains, "u16_subset_chains", where=PIN), PIN)
    E.fact("u16_strict_one_bit_per_step_chains",
           req(chains, "u16_strict_one_bit_per_step_chains", where=PIN), PIN)
    E.fact("named_words_count", req(pin, "named_words_count", where=PIN), PIN)
    E.fact("named_words_inside_pinned_image", req(pin, "named_words_inside_pinned_image",
                                                  where=PIN), PIN)
    E.fact("named_words_zero_in_disc_image",
           req(pin, "named_words_zero_in_disc_image", where=PIN), PIN)
    E.fact("named_words_varying_across_fixtures",
           req(pin, "named_words_varying_across_fixtures", where=PIN), PIN)
    varying = [w for w in req(pin, "named_words", where=PIN)
               if req(w, "varies_across_fixtures", where=PIN)]
    E.fact("varying_overlay_word_addresses", [w["addr"] for w in varying], PIN)
    E.fact("varying_overlay_word_values", [w["values"] for w in varying], PIN)

    # ------------------------------------------------------------------ #
    # 6. how ambiguous IS an address in that window? ask the census.      #
    # ------------------------------------------------------------------ #
    OVLD = "analysis/overlay_decomp_progress.json"
    ovld = E.json(OVLD)
    E.fact("overlay_track_total_code_functions",
           req(ovld, "overlay_code_functions", where=OVLD), OVLD)
    E.fact("overlay_track_matched_functions", req(ovld, "matched", "functions", where=OVLD),
           OVLD)
    E.fact("overlay_track_matched_pct", req(ovld, "matched", "pct_functions", where=OVLD), OVLD)
    E.fact("pinned_overlay_code_functions",
           req(ovld, "per_overlay_totals", ovl_name, where=OVLD), OVLD)
    ovl_results = [r for r in req(ovld, "results", where=OVLD) if r["overlay"] == ovl_name]
    if not ovl_results:
        raise SystemExit(f"STALE CITATION: {OVLD} no longer carries a result for {ovl_name}")
    E.fact("pinned_overlay_matched_functions",
           sum(req(r, "matched_functions", where=OVLD) for r in ovl_results), OVLD)
    E.fact("pinned_overlay_rebuild_validated",
           all(req(r, "validated", where=OVLD) for r in ovl_results), OVLD)
    E.fact("pinned_overlay_rebuilt_sha1_matches",
           all(req(r, "rebuilt_sha1", where=OVLD) == req(r, "sha1", where=OVLD)
               for r in ovl_results), OVLD)
    attempted = [(as_int(req(a, "start", where=OVLD)), req(a, "source", where=OVLD))
                 for r in ovl_results for a in req(r, "attempted", where=OVLD)]
    E.fact("pinned_overlay_matched_sources", sorted(s for _, s in attempted), OVLD)
    init_pc = attempted[0][0]
    E.fact("pinned_overlay_matched_entry", f"0x{init_pc:08X}", OVLD)

    FN = "analysis/functions.json"
    fnj = E.json(FN)
    fns = req(fnj, "functions", where=FN)
    E.fact("overlay_images_in_function_census", len(req(fnj, "overlays", where=FN)), FN)
    covering = {f["overlay"] for f in fns
                if f.get("space") == "overlay"
                and as_int(f["start"]) <= init_pc < as_int(f["end"])}
    E.fact("overlay_images_covering_the_matched_entry_pc", len(covering), [FN, OVLD])
    pinned_fns = [f for f in fns if f.get("overlay") == ovl_name]
    E.fact("pinned_overlay_functions_in_census", len(pinned_fns), FN)
    E.fact("pinned_overlay_function_names",
           sorted(f.get("name") or f"0x{as_int(f['start']):08X}" for f in pinned_fns), FN)
    E.fact("pinned_overlay_functions_named", sum(1 for f in pinned_fns if f.get("name")), FN)

    # ------------------------------------------------------------------ #
    # 7. the semantic registries: who OWNS this row's code and state?     #
    # ------------------------------------------------------------------ #
    OWN = "analysis/phase3_ownership_graph.json"
    own = E.json(OWN)
    orow = req(own, "rows", ROW_ID, where=OWN)
    ofns = req(orow, "functions", where=OWN)
    E.fact("ownership_functions", len(ofns), OWN)
    E.fact("ownership_functions_with_canon", sum(1 for f in ofns if f.get("canon")), OWN)
    E.fact("ownership_distinct_function_starts",
           len({f["function_start"] for f in ofns}), OWN)
    E.fact("ownership_overlay_functions",
           sum(1 for f in ofns if f["space"] != "resident"), OWN)
    E.fact("ownership_overlay_spaces_named",
           sorted({f["space"] for f in ofns if f["space"] != "resident"}), OWN)
    ostate = req(orow, "state", where=OWN)
    E.fact("ownership_state_addresses", len(ostate), OWN)
    E.fact("ownership_state_address_list", [s["address"] for s in ostate], OWN)
    E.fact("ownership_state_addresses_with_owner",
           sum(1 for s in ostate if s.get("semantic_ids")), OWN)
    E.fact("ownership_gaps", len(req(orow, "gaps", where=OWN)), OWN)
    E.fact("ownership_gap_items", req(orow, "gaps", where=OWN), OWN)
    E.fact("ownership_reader_bounding_claim",
           req(orow, "readers", 0, "evidence", where=OWN), OWN)
    E.fact("ownership_reader_status", req(orow, "readers", 0, "status", where=OWN), OWN)

    # Is that bounding claim TRUE? It names two artifacts; check both for the two
    # table addresses it is bounding. A bounding claim that cites an artifact which
    # does not carry the address is not a bound.
    JRT = "analysis/phase3_jr_tables.json"
    jrt = E.json(JRT)
    DMAP = "analysis/phase3_dispatch_map.json"
    dmap = E.json(DMAP)
    jr_text, dmap_text = json.dumps(jrt).lower(), json.dumps(dmap).lower()
    table_addrs = [s["address"] for s in ostate if s["address"].lower().startswith("0x8001")]
    E.fact("row_table_state_addresses", table_addrs, OWN)
    E.fact("row_table_addresses_present_in_jr_tables",
           sum(1 for a in table_addrs if a.lower() in jr_text), [JRT, OWN])
    E.fact("row_table_addresses_present_in_dispatch_map",
           sum(1 for a in table_addrs if a.lower() in dmap_text), [DMAP, OWN])
    jr_site = next((k for k, v in req(jrt, "decoded", where=JRT).items()
                    if any(a.lower() == str(req(v, "table", where=JRT)).lower()
                           for a in table_addrs)), None)
    if jr_site is None:
        raise SystemExit(f"STALE CITATION: {JRT} no longer decodes this row's dispatch table")
    jr_entry = req(jrt, "decoded", jr_site, where=JRT)
    E.fact("dispatch_table_decoded_site", jr_site, JRT)
    E.fact("dispatch_table_entries", req(jr_entry, "entries", where=JRT), JRT)
    E.fact("dispatch_table_distinct_targets", req(jr_entry, "distinct_targets", where=JRT), JRT)
    E.fact("dispatch_table_named_targets", req(jr_entry, "named_targets", where=JRT), JRT)
    E.fact("dispatch_table_owner_function", req(jr_entry, "function", where=JRT), JRT)
    E.fact("jr_tables_total_sites", req(jrt, "jr_sites", where=JRT), JRT)
    E.fact("jr_tables_decoded_sites", req(jrt, "decoded_sites", where=JRT), JRT)

    SEM = "config/semantic_state.yaml"
    sem = E.yaml(SEM)
    sem_entries = req(sem, "entries", where=SEM)

    def sem_addr(e):
        a = e.get("address")
        return as_int(a) if isinstance(a, (int, str)) and a is not None else None

    sem_addrs = {sem_addr(e) for e in sem_entries} - {None}
    E.fact("semantic_state_entries_total", len(sem_entries), SEM)
    row_state = [as_int(s["address"]) for s in ostate]
    E.fact("row_state_addresses_registered",
           sum(1 for a in row_state if a in sem_addrs), [SEM, OWN])
    pin_lo, pin_hi = region_a, region_a + int(F["residency_pin_size"])
    E.fact("pinned_overlay_extent",
           [f"0x{pin_lo:08X}", f"0x{pin_hi:08X}"], [OVLY, PIN])
    E.fact("semantic_entries_inside_shared_region_a",
           sorted(f"0x{a:08X}" for a in sem_addrs if region_a <= a < region_b), [SEM, OVLY])
    E.fact("semantic_entries_inside_this_rows_overlay_extent",
           sorted(f"0x{a:08X}" for a in sem_addrs if pin_lo <= a < pin_hi), [SEM, OVLY, PIN])
    collide = [e for e in sem_entries
               if sem_addr(e) is not None and region_a <= sem_addr(e) < region_b]
    E.fact("semantic_entries_inside_shared_region_a_ids",
           sorted(req(e, "id", where=SEM) for e in collide), SEM)

    # the registered invariant for this row's own table: is it still the falsified law?
    tbl_entry = next((e for e in sem_entries
                      if sem_addr(e) is not None
                      and f"0x{sem_addr(e):08x}" in [a.lower() for a in table_addrs]), None)
    if tbl_entry is None:
        raise SystemExit(f"STALE CITATION: {SEM} no longer registers this row's asset table")
    inv_ctx = req(tbl_entry, "invariants", 0, "context", where=SEM)
    E.fact("registered_table_entry_id", req(tbl_entry, "id", where=SEM), SEM)
    E.fact("registered_table_confidence", req(tbl_entry, "confidence", where=SEM), SEM)
    E.fact("registered_table_invariant_context", inv_ctx, SEM)
    E.fact("registered_table_invariant_still_asserts_index_equals_id_minus_one",
           "row index = scene_id - 1" in inv_ctx, SEM)
    E.fact("registered_table_evidence", req(tbl_entry, "evidence", where=SEM), SEM)

    SITES = "config/confirmed_sites.yaml"
    sites = E.yaml(SITES)
    site_entries = req(sites, "entries", where=SITES)
    gov_static = {as_int(a) for a in F["arithmetic_law_instruction_pcs"]} | \
                 {as_int(a) for a in F["sound_bank_mechanism_pcs"]}
    E.fact("confirmed_sites_total", len(site_entries), SITES)
    E.fact("row_governing_pcs_registered_as_confirmed_sites",
           sum(1 for a in gov_static
               if any(as_int(s["address"]) == a for s in site_entries)), [SITES, BIND])

    RECS = "config/record_types.yaml"
    recs = E.yaml(RECS)
    E.fact("record_types_registered", len(req(recs, "records", where=RECS)), RECS)
    E.fact("record_types_covering_this_rows_overlay",
           sum(1 for r in req(recs, "records", where=RECS)
               if pin_lo <= as_int(req(r, "base", where=RECS)) < pin_hi), [RECS, PIN])

    # ------------------------------------------------------------------ #
    # 8. Canon currency: did the correction reach the pages others read?  #
    # ------------------------------------------------------------------ #
    SYS = "ObsidianVault/Canon/Systems/SYS_scene_asset_load_graph.md"
    sysdoc = E.text(SYS)
    E.fact("canon_page_sections", len(re.findall(r"^#{2,3} ", sysdoc, re.M)), SYS)
    E.fact("canon_page_still_asserts_index_equals_id_minus_one",
           bool(re.search(r"row index = \*\*scene_id . 1\*\*", sysdoc)), SYS)
    canon_rows = re.findall(
        r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*`[^`]+`\s*\|\s*([A-Z0-9_]+)\s*\|", sysdoc, re.M)
    if not canon_rows:
        raise SystemExit(f"STALE CITATION: {SYS} no longer carries a campaign map table")
    truth_dirs = req(bind, "scene_id_to_level_data_dir", where=BIND)
    disagree = [sid for sid, _asset, ovl in canon_rows
                if not req(truth_dirs, sid, where=BIND).startswith(ovl + "/")]
    E.fact("canon_campaign_map_rows", len(canon_rows), SYS)
    E.fact("canon_campaign_map_rows_disagreeing_with_the_corrected_law", len(disagree),
           [SYS, BIND])
    E.fact("canon_campaign_map_disagreeing_scene_ids", disagree, [SYS, BIND])
    canon_f08 = next((r for r in canon_rows if int(r[0]) == F["binding_scene_id"]), None)
    if canon_f08 is None:
        raise SystemExit(f"STALE CITATION: {SYS} no longer has a row for this row's scene")
    E.fact("canon_row_for_this_scene_asset", canon_f08[1], SYS)
    E.fact("canon_row_for_this_scene_overlay", canon_f08[2], SYS)
    E.fact("canon_row_for_this_scene_still_names_the_falsified_overlay",
           canon_f08[2] not in F["binding_level_data_dir"], [SYS, BIND])

    GRAPH3 = "analysis/phase3_scene_asset_graph.json"
    g3 = E.json(GRAPH3)
    E.fact("phase3_law_is_the_corrected_one",
           "CORRECTED 2026-08-01" in req(g3, "law", where=GRAPH3), GRAPH3)
    E.fact("phase3_law_says_prior_rule_wrong_for",
           bool(re.search(r"wrong for 11 of 15", req(g3, "law", where=GRAPH3))), GRAPH3)

    EXP = "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f08_scene_asset_binding.md"
    expdoc = E.text(EXP)
    E.fact("experiment_status_frontmatter",
           re.search(r"^status:\s*(\S+)", expdoc, re.M).group(1), EXP)
    E.fact("experiment_declares_still_open",
           bool(re.search(r"^## Still open", expdoc, re.M)), EXP)
    E.fact("experiment_records_its_own_first_version_was_wrong",
           "CORRECTION TO THIS NOTE'S FIRST VERSION" in expdoc, EXP)

    # ------------------------------------------------------------------ #
    # 9. source closure -- BOTH registries, resident and overlay          #
    # ------------------------------------------------------------------ #
    SEG = "config/segments.yml"
    seg = E.yaml(SEG)
    units = [(as_int(req(e, "start", where=SEG)), as_int(req(e, "end", where=SEG)),
              req(e, "source", where=SEG)) for e in req(seg, "attempted", where=SEG)]
    E.fact("resident_build_units", len(units), SEG)
    E.fact("resident_build_toolchain", req(seg, "c_toolchain", "compiler", where=SEG), SEG)

    governing: dict[str, int] = {}
    for i, pc in enumerate(F["arithmetic_law_instruction_pcs"]):
        governing[f"arith_law_{i}"] = as_int(pc)
    for i, pc in enumerate(F["sound_bank_mechanism_pcs"]):
        governing[f"sound_bank_{i}"] = as_int(pc)
    for s in ostate:
        governing[f"state_{s['address']}"] = as_int(s["address"])
    governing["dispatch_jr_site"] = as_int(F["dispatch_table_decoded_site"])
    for t in req(jr_entry, "targets", where=JRT):
        governing[f"dispatch_target_{t['index']}"] = as_int(req(t, "target", where=JRT))
    governing["overlay_init"] = init_pc
    for f in pinned_fns:
        governing[f"overlay_fn_{f['start']}"] = as_int(f["start"])

    # count DISTINCT addresses: several roles legitimately name the same address
    # (the overlay's init entry is both a build unit and a census function), and
    # counting roles would inflate every number below.
    gov_addrs = set(governing.values())
    resident = {a for a in gov_addrs if not (pin_lo <= a < pin_hi)}
    overlay = {a for a in gov_addrs if pin_lo <= a < pin_hi}
    resolved: dict[str, list[str]] = {}
    unresolved: list[int] = []
    for a in sorted(resident):
        src = next((s for lo, hi, s in units if lo <= a < hi), None)
        (resolved.setdefault(src, []).append(f"0x{a:08X}") if src else unresolved.append(a))
    matched_starts = {s for s, _ in attempted}
    E.fact("governing_roles", len(governing), [BIND, OWN, JRT, FN, OVLD])
    E.fact("governing_addresses", len(gov_addrs), [BIND, OWN, JRT, FN, OVLD])
    E.fact("governing_addresses_resident", len(resident), [BIND, OWN, JRT, PIN])
    E.fact("governing_addresses_in_this_rows_overlay", len(overlay), [FN, OVLD, PIN])
    E.fact("governing_resident_build_units", len(resolved), SEG)
    E.fact("governing_resident_units_matching_c",
           len([s for s in resolved if s.startswith("src/")]), SEG)
    E.fact("governing_resident_units_hand_asm",
           len([s for s in resolved if s.startswith("asm/")]), SEG)
    E.fact("governing_resident_unit_names", sorted(resolved), SEG)
    E.fact("governing_resident_addresses_outside_any_build_unit", len(unresolved), SEG)
    E.fact("governing_overlay_addresses_with_matched_c",
           len(overlay & matched_starts), [OVLD, FN])

    # ------------------------------------------------------------------ #
    # 10. fixtures, oracles and the scheduler that reads them             #
    # ------------------------------------------------------------------ #
    AUDIT = "analysis/phase2_fixture_audit.json"
    audit = E.json(AUDIT)
    movies = req(audit, "movies", where=AUDIT)
    # WARNING -- TWO TOKEN TRAPS here, both of the kind that produced the very error
    # this row exists to correct. (1) "LEVEL08" is the movie corpus's STAGE number,
    # but as a DISC DIRECTORY it belongs to a different scene entirely; the census
    # below proves which. (2) "B08" is a ROW id (a power-slot row) whose movies also
    # carry an "08", and matching it would credit this stage with recordings that are
    # not its own. So attribute a movie only when the stage NAME appears in it, or
    # when the campaign completion oracle itself binds it to this stage.
    stage_token = re.compile(r"level08", re.I)
    stage_name = re.compile(r"citysquare|city_square", re.I)
    token_mov = sorted(k for k in movies if stage_token.search(k))

    ORACLE = "analysis/phase2_completion_oracle.json"
    oracle = E.json(ORACLE)
    ostages = req(oracle, "stages", where=ORACLE)
    st8_key = next((k for k in ostages if "08" in k), None)
    if st8_key is None:
        raise SystemExit(f"STALE CITATION: {ORACLE} no longer carries a stage-08 entry")
    st8 = ostages[st8_key]
    E.fact("completion_oracle_stage_key", st8_key, ORACLE)

    # Resolve the token trap by measurement rather than by naming convention:
    # the oracle binds this STAGE key to a movie whose path carries the LEVEL08
    # token while its target scene is this row's scene, and the disc-side census
    # shows a DIFFERENT stage owns the LEVEL08/ disc directory.
    oracle_movie = req(st8, "movie", where=ORACLE)
    stage_mov = sorted({k for k in token_mov if stage_name.search(k)} | {oracle_movie})
    unverified = sorted(set(token_mov) - set(stage_mov))
    E.fact("stage8_movies_token_matched", len(token_mov), AUDIT)
    E.fact("stage8_movies_attributed", len(stage_mov), [AUDIT, ORACLE])
    E.fact("stage8_movies_attributed_paths", stage_mov, [AUDIT, ORACLE])
    E.fact("stage8_movies_token_matched_attribution_unverified", unverified,
           [AUDIT, ORACLE])
    E.fact("stage8_movies_pinned", len(stage_mov), [AUDIT, ORACLE])
    E.fact("stage8_movie_frames",
           {k: req(movies, k, "frames", where=AUDIT) for k in stage_mov}, AUDIT)
    E.fact("stage8_movie_format_versions",
           {k: req(movies, k, "format_version", where=AUDIT) for k in stage_mov}, AUDIT)
    E.fact("stage8_movies_under_phase4_interpreter",
           sorted(k for k in stage_mov if k.startswith("movies/Phase4/Interpreter/")), AUDIT)
    saves = req(audit, "saves", where=AUDIT)
    E.fact("stage8_saves_pinned",
           len([k for k in saves if stage_token.search(k) or stage_name.search(k)]), AUDIT)
    E.fact("row_declared_fixtures_are_all_saves",
           all(p.endswith(".sav") for p in F["row_declared_fixture_paths"]), BASE)
    E.fact("stage8_movies_declared_by_the_row",
           sum(1 for k in stage_mov if k in F["row_declared_fixture_paths"]), [AUDIT, BASE])

    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    fixset = E.json(FIXSET)
    entries = req(fixset, "entries", where=FIXSET)
    E.fact("stage8_movies_centrally_pinned",
           sum(1 for k in stage_mov if k in entries), FIXSET)
    E.fact("stage8_movies_bytes_match_pin",
           sum(1 for k in stage_mov
               if k in entries and (ROOT / k).exists()
               and sha256_file(ROOT / k) == entries[k]["sha256"]), FIXSET)
    E.fact("row_external_fixtures_bytes_match_pin",
           sum(1 for p in external
               if p in entries and (ROOT / p).exists()
               and sha256_file(ROOT / p) == entries[p]["sha256"]), [FIXSET, CENSUS])
    E.fact("row_external_fixture_consumers",
           sorted({c for p in external for c in req(entries, p, "consumers", where=FIXSET)}),
           FIXSET)
    E.fact("row_external_fixture_consumer_count",
           len(F["row_external_fixture_consumers"]), FIXSET)

    E.fact("completion_oracle_movie", oracle_movie, ORACLE)
    E.fact("completion_oracle_frames", req(st8, "frames", where=ORACLE), ORACLE)
    E.fact("completion_oracle_target_scene", req(st8, "target_scene", where=ORACLE), ORACLE)
    E.fact("completion_oracle_replay_accepted",
           req(st8, "pristine_replay_accepted", where=ORACLE), ORACLE)
    E.fact("completion_oracle_entered_stage_frame",
           req(st8, "entered_stage_frame", where=ORACLE), ORACLE)
    E.fact("completion_oracle_stage_exited",
           req(st8, "stage_exited_by_movie_end", where=ORACLE), ORACLE)
    E.fact("completion_oracle_last_in_stage_snapshot_fields",
           sorted(req(st8, "last_in_stage", "snapshot", where=ORACLE)), ORACLE)
    E.fact("completion_oracle_corroborates_the_scene_id",
           F["completion_oracle_target_scene"] == F["binding_scene_id"], [ORACLE, BIND])
    E.fact("completion_oracle_cited_by_the_row",
           "phase2_completion_oracle" in json.dumps(row), [BASE, ORACLE])

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
    E.fact("scheduler_ownership_input_sha256",
           req(qrow, "static_ownership", "source_sha256", where=QUEUE), QUEUE)
    E.fact("scheduler_ownership_input_is_current",
           F["scheduler_ownership_input_sha256"] == sha256_file(ROOT / OWN), [QUEUE, OWN])

    # ------------------------------------------------------------------ #
    # 11. the stage itself: collision environment, actors, type taxonomy  #
    # ------------------------------------------------------------------ #
    E02 = "analysis/phase4_e02_disc_region_code_census.json"
    e02 = E.json(E02)
    levels = req(e02, "levels", where=E02)
    s8 = next((v for k, v in levels.items() if "08" in k), None)
    if s8 is None:
        raise SystemExit(f"STALE CITATION: {E02} no longer carries a stage-08 level")
    E.fact("stage8_collision_container", req(s8, "container", where=E02), E02)
    E.fact("stage8_collision_scene", req(s8, "scene", where=E02), E02)
    E.fact("stage8_authored_collision_sectors", req(s8, "authored_sectors", where=E02), E02)
    E.fact("stage8_runtime_collision_sectors", req(s8, "runtime_sectors", where=E02), E02)
    E.fact("stage8_region_code_histogram", req(s8, "code_histogram", where=E02), E02)
    E.fact("stage8_has_no_nonzero_region_codes",
           list(req(s8, "code_histogram", where=E02)) == ["0"], E02)
    E.fact("e02_levels_censused", len(levels), E02)
    E.fact("e02_disc_runtime_disagreements",
           len(req(e02, "agreement", "disagreements", where=E02)), E02)
    E.fact("e02_authored_sectors_compared",
           req(e02, "agreement", "authored_sectors_compared", where=E02), E02)
    E.fact("e02_corroborates_the_scene_id",
           req(s8, "scene", where=E02) == F["binding_scene_id"], [E02, BIND])
    nonzero_levels = sum(1 for v in levels.values()
                         if list(req(v, "code_histogram", where=E02)) != ["0"])
    E.fact("e02_levels_with_any_nonzero_region_code", nonzero_levels, E02)

    # The movie-corpus token trap, settled from the disc side: the stage ORDINAL
    # names a disc directory that belongs to a different stage entirely.
    dir_token = f"LEVEL{int(F['census_stage_ordinal']):02d}/"
    owners = sorted(k for k, v in levels.items()
                    if req(v, "container", where=E02).startswith(dir_token))
    E.fact("disc_directory_named_by_this_stages_ordinal", dir_token, CENSUS)
    E.fact("stages_owning_that_disc_directory", owners, E02)
    E.fact("this_row_owns_the_disc_directory_named_by_its_ordinal",
           F["completion_oracle_stage_key"] in owners, [E02, ORACLE])

    ACT = "analysis/phase1_kind_actor_census.json"
    act = E.json(ACT)
    alevels = req(act, "levels", where=ACT)
    a8 = next((v for k, v in alevels.items() if "08" in k), None)
    if a8 is None:
        raise SystemExit(f"STALE CITATION: {ACT} no longer carries a stage-08 level")
    arecs = req(a8, "actor_records", where=ACT)
    E.fact("stage8_actor_census_save", req(a8, "save", where=ACT), ACT)
    E.fact("stage8_actor_records", len(arecs), ACT)
    E.fact("stage8_actor_ids", sorted({r["id"] for r in arecs}), ACT)
    E.fact("stage8_actor_id_count", len({r["id"] for r in arecs}), ACT)
    bound_ids = {int(k) for k in req(act, "actor_ids_with_canon_binding", where=ACT)}
    E.fact("stage8_actor_ids_with_canon_binding",
           len({r["id"] for r in arecs} & bound_ids), ACT)
    E.fact("stage8_actor_census_uses_a_row_fixture",
           req(a8, "save", where=ACT) in F["row_declared_fixture_paths"], [ACT, BASE])
    E.fact("stage8_actor_census_cited_by_the_row",
           "phase1_kind_actor_census" in json.dumps(row), [BASE, ACT])

    C2 = "analysis/phase4_c2_level_type_authority.json"
    c2 = E.json(C2)
    E.fact("c2_row_types",
           [t["type"] for t in req(c2, "mapping", ROW_ID, "types", where=C2)], C2)
    E.fact("c2_rows_sharing_this_type",
           sorted(set(sum((req(c2, "types_with_at_least_one_level", t, where=C2)
                           for t in F["c2_row_types"]), []))), C2)
    E.fact("c2_taxonomy_coverage_demonstrated",
           req(c2, "result", "taxonomy_coverage_demonstrated", where=C2), C2)
    E.fact("c2_underivable_types", sorted(req(c2, "result", "underivable_types", where=C2)), C2)
    E.fact("c2_frozen_name_matches_this_row",
           req(c2, "mapping", ROW_ID, "frozen_name", where=C2) == req(row, "name", where=BASE),
           [C2, BASE])

    # ------------------------------------------------------------------ #
    # 12. the row's registered executable gate                            #
    # ------------------------------------------------------------------ #
    test_dir = ROOT / "tests"
    if not test_dir.is_dir():
        raise SystemExit("STALE CITATION: tests/ is not a directory")
    row_artifacts = [BIND, PIN]
    gate_files = []
    for p in sorted(test_dir.glob("test_*.py")):
        body = p.read_text(errors="ignore")
        if any(a in body for a in row_artifacts) or "phase4_f08" in body:
            rel = f"tests/{p.name}"
            E.pin(rel)
            gate_files.append(rel)
    if not gate_files:
        raise SystemExit("no registered gate covers any of this row's artifacts -- "
                         "the gate set this assessment measures has disappeared")
    E.fact("registered_gate_files", len(gate_files), gate_files)
    E.fact("registered_gate_file_names", gate_files, gate_files)

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
        total_tests = F["registered_gate_tests_passed"] + F["registered_gate_tests_failed"]
        gate_note = (f"{F['registered_gate_tests_passed']}/{total_tests} tests in this row's "
                     f"{F['registered_gate_files']} registered gate file(s) pass on today's "
                     f"tree")
    else:
        gate_note = (f"this row's {F['registered_gate_files']} registered gate file(s) were "
                     f"NOT executed for this run (--no-gates), so their health is unmeasured")

    subject_note = (
        f"the row's SUBJECT -- how performers are found via markers -- is untouched: the "
        f"row's own declared missing item is '{F['row_declared_missing']}' and the census "
        f"triage records '{F['census_triage']['original_oracle']}'")

    dims = {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"{CENSUS} -- {F['census_durable_reason']}. This assessment fails loudly "
                     f"if that measurement moves off 'met'. Independently re-confirmed here: "
                     f"all {F['row_external_fixtures_bytes_match_pin']} of "
                     f"{F['row_external_fixture_count']} declared external fixtures still "
                     f"byte-match their central pin, and they are load-bearing far beyond this "
                     f"row ({F['row_external_fixture_consumer_count']} registered consumers). "
                     f"Regenerability is real here too: the row's single analysis artifact is "
                     f"produced by a self-verifying compiled-C tool that a registered gate "
                     f"builds and runs ({gate_note}), and the new residency pin added by this "
                     f"assessment is regenerable from the same fixtures with no emulator",
            "gap": f"the carried measurement covers FIXTURE INTACTNESS. Two things it does not "
                   f"cover, both measured here. (1) The declared set is incomplete: "
                   f"{F['stage8_movies_pinned']} pinned stage-8 movies exist "
                   f"({F['stage8_movies_bytes_match_pin']} byte-matching their pin) and the "
                   f"row declares {F['stage8_movies_declared_by_the_row']} of them "
                   f"(fixture_have is all saves: "
                   f"{F['row_declared_fixtures_are_all_saves']}). (2) The prose numbers this "
                   f"row's conclusions rest on had no generator until now -- the 99.14%/5.53% "
                   f"residency figures and the '4 bytes of 7,656' diff existed only as text",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"what IS asserted is asserted with zero injection. The corrected binding "
                     f"is proved against {F['binding_residency_confirmations']} natural "
                     f"pristine save states spanning "
                     f"{F['binding_residency_distinct_scenes']} distinct scenes "
                     f"(all matched: {F['binding_residency_all_matched']}), read OFFLINE out of "
                     f"the .sav containers with no emulator and no poke "
                     f"(offline method: {F['binding_residency_method_is_offline']}); this "
                     f"assessment re-derives it from bytes across all "
                     f"{F['residency_pin_images_scanned']} overlay images x "
                     f"{F['residency_pin_rams_scanned']} fixtures. Independent natural "
                     f"corroboration of the same scene id comes from two directions the row "
                     f"never cites: the disc-vs-runtime collision census "
                     f"(corroborates={F['e02_corroborates_the_scene_id']}, "
                     f"{F['e02_disc_runtime_disagreements']} disagreements over "
                     f"{F['e02_authored_sectors_compared']} sectors) and the campaign "
                     f"completion oracle, which is a from-boot natural replay of this stage "
                     f"({F['completion_oracle_movie']}, {F['completion_oracle_frames']} frames, "
                     f"pristine_replay_accepted={F['completion_oracle_replay_accepted']}, "
                     f"entered at frame {F['completion_oracle_entered_stage_frame']}, exited by "
                     f"end={F['completion_oracle_stage_exited']})",
            "gap": f"none of that is an oracle for this row's BEHAVIOUR. The binding is an "
                   f"IDENTITY claim, not a behavioural one, and {subject_note}. The one "
                   f"artifact that does assert stage-8 behaviour from a cold boot is the "
                   f"completion oracle, and the row does not cite it "
                   f"(cited={F['completion_oracle_cited_by_the_row']}); it asserts entry and "
                   f"exit, never a performer-found event. No assertion in this row is keyed to "
                   f"the objective at all",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"for the LOADER the frontier is enumerated and exhaustive, not sampled: "
                     f"the dispatcher's indirect table is fully decoded "
                     f"({F['dispatch_table_entries']} entries, "
                     f"{F['dispatch_table_distinct_targets']} distinct targets, "
                     f"{F['dispatch_table_named_targets']} named, at site "
                     f"{F['dispatch_table_decoded_site']} in "
                     f"{F['dispatch_table_owner_function']}), the id->directory map is closed "
                     f"over all {F['binding_scene_ids_mapped']} ids and the id->sound-bank map "
                     f"over all {F['binding_sound_bank_ids_mapped']}, the two are proved "
                     f"PERMUTED, the divergence is localized to ids "
                     f"{F['binding_string_dir_diverges_for']}, and the blast radius is "
                     f"enumerated: {F['binding_rows_with_wrong_binding']} rows named as "
                     f"carrying the wrong binding and {F['binding_rows_corrected']} listed as "
                     f"corrected (the extra entries being "
                     f"{F['binding_rows_corrected_but_not_listed_wrong']}). NEW HERE: the "
                     f"overlay was named "
                     f"by ADDRESS and by an unreproducible percentage; "
                     f"{PINSRC} settles it from bytes -- of "
                     f"{F['residency_pin_images_scanned']} images exactly "
                     f"{F['residency_pin_images_with_stable_declared_base']} is the argmax in "
                     f"every fixture AND has a stable declared base "
                     f"({F['residency_pin_file']}, {F['residency_pin_nontrivial_pct']}% vs "
                     f"{F['residency_pin_runner_up_pct']}% for the runner-up "
                     f"{F['residency_pin_runner_up']}; {F['residency_pin_result']}). The row's "
                     f"headline negative is now enumerated instead of asserted: across the five "
                     f"fixtures {F['whole_ram_differing_words']} of {F['whole_ram_words']} RAM "
                     f"words differ, {F['u32_subset_chains']} u32 / {F['u16_subset_chains']} "
                     f"u16 of them order into a bitwise subset chain, and "
                     f"{F['u32_strict_one_bit_per_step_chains']} are the strict "
                     f"one-bit-per-step shape a five-performer cumulative mask would take",
            "gap": f"the enumerated frontier is the LOADER's, not the OBJECTIVE's. Nothing "
                   f"enumerates the marker mechanism's callers, callees or callbacks -- the "
                   f"row names no governing function for it, and the ownership graph resolves "
                   f"this row to {F['ownership_distinct_function_starts']} distinct function(s) "
                   f"({F['ownership_functions']} cited addresses), all in the loader. "
                   f"{F['ownership_gaps']} of {F['ownership_state_addresses']} cited state "
                   f"addresses have no semantic-registry owner "
                   f"({F['ownership_gap_items']}). What this assessment adds is a CANDIDATE "
                   f"SET, and a candidate set is not a frontier: "
                   f"{F['pinned_overlay_functions_in_census']} functions in the pinned overlay "
                   f"(including a level_completion_handler), "
                   f"{F['named_words_count']} overlay-local state words declared by the "
                   f"byte-matched C of which {F['named_words_varying_across_fixtures']} varies "
                   f"across the performer fixtures, and "
                   f"{F['stage8_actor_records']} actor records / "
                   f"{F['stage8_actor_id_count']} distinct ids already censused from this row's "
                   f"own fixture ({F['stage8_actor_census_uses_a_row_fixture']}) and never "
                   f"cited by it ({F['stage8_actor_census_cited_by_the_row']})",
        },
        "campaign_breadth": {
            "state": "partial",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"F08's one conclusion generalizes with a CLOSED denominator, which is "
                     f"rare for an F row: the dispatcher bounds its own universe at "
                     f"{F['dispatch_table_entries']} scene ids and the correction is measured "
                     f"across all of them, corroborated at "
                     f"{F['binding_residency_distinct_scenes']} independent scenes and against "
                     f"the disc-side collision census for all {F['e02_levels_censused']} levels "
                     f"({F['e02_disc_runtime_disagreements']} disagreements). It then "
                     f"generalized in the strongest possible sense -- it changed "
                     f"{F['binding_rows_corrected']} other rows. A pre-outcome type authority "
                     f"also exists and places this row as {F['c2_row_types']} together with "
                     f"{F['c2_rows_sharing_this_type']}",
            "gap": f"within the stage there is no denominator at all. Of "
                   f"{F['stage8_movies_pinned']} pinned stage-8 routes the row's artifacts "
                   f"replay zero (its evidence is five static snapshots), and the five fixtures "
                   f"are explicitly not a progression. The type authority itself reports "
                   f"taxonomy_coverage_demonstrated="
                   f"{F['c2_taxonomy_coverage_demonstrated']} because "
                   f"{F['c2_underivable_types']} have no textual authority, so the eight-type "
                   f"bar is undemonstrated campaign-wide. No variant, retry, death or "
                   f"exceptional-path axis is enumerated for this stage",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"the loader's state is typed with exhaustive domains: the scene id is a "
                     f"registered u32 field with a declared range, and both of its derived "
                     f"domains are closed functions of it over the full id set "
                     f"({F['binding_scene_ids_mapped']} directories, "
                     f"{F['binding_sound_bank_ids_mapped']} bank indices), with the "
                     f"variant-selecting bit pinned to an instruction. NEW HERE, the overlay's "
                     f"own state block is now typed from a BYTE-MATCHED source rather than "
                     f"inferred: the C at {F['pinned_overlay_matched_entry']} declares "
                     f"{F['byte_matched_c_declared_word_count']} overlay-local words, all "
                     f"{F['named_words_inside_pinned_image']} inside the pinned image extent, "
                     f"all {F['named_words_zero_in_disc_image']} zero in the disc image (so "
                     f"they are runtime state living inside the image, not static data), with "
                     f"initializers {F['byte_matched_c_nonzero_initializers']} and everything "
                     f"else zeroed. Exactly "
                     f"{F['named_words_varying_across_fixtures']} of them varies across the "
                     f"five performer fixtures: {F['varying_overlay_word_addresses']} with "
                     f"values {F['varying_overlay_word_values']}",
            "gap": f"the registry that exists is WRONG for this row, which is worse than empty. "
                   f"config/semantic_state.yaml holds {F['semantic_state_entries_total']} "
                   f"entries; {F['row_state_addresses_registered']} of this row's "
                   f"{F['ownership_state_addresses']} cited state addresses appear, and the one "
                   f"that does ({F['registered_table_entry_id']}, confidence "
                   f"'{F['registered_table_confidence']}') still carries the FALSIFIED "
                   f"invariant 'row index = scene_id - 1' "
                   f"(still_asserts="
                   f"{F['registered_table_invariant_still_asserts_index_equals_id_minus_one']})"
                   f" -- the exact law this row refuted on 2026-08-05 and Phase 3 refuted on "
                   f"2026-08-01. Nothing types the varying overlay word: its value domain is "
                   f"unbounded, five samples do not distinguish an objective counter from a "
                   f"free-running timer (the values straddle the initializer in both "
                   f"directions), and "
                   f"{F['record_types_covering_this_rows_overlay']} record types cover this "
                   f"overlay",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"LOAD is the best-evidenced phase in this row and is now evidenced twice "
                     f"over: the overlay's arrival at the shared base is proved by bytes in all "
                     f"{F['residency_pin_rams_scanned']} fixtures, and its INITIALIZATION is "
                     f"proved from byte-matched source -- "
                     f"{F['byte_matched_c_declared_word_count']} state words zeroed or set at "
                     f"overlay init, all of them zero on disc. Cold boot, stage entry and stage "
                     f"exit are evidenced for the stage container by the completion oracle "
                     f"(entered {F['completion_oracle_entered_stage_frame']}, exited by "
                     f"end={F['completion_oracle_stage_exited']}, "
                     f"accepted={F['completion_oracle_replay_accepted']})",
            "gap": f"zero phases of the OBJECTIVE are evidenced, and the phases that are "
                   f"evidenced belong to the stage container and come from an artifact the row "
                   f"does not cite. First use, repeated use, exhaustion, retirement and reuse "
                   f"of the performer mechanism have no evidence of any kind; the five "
                   f"fixtures are five independent mid-stage snapshots, not a progression, "
                   f"which the row states and this assessment confirms "
                   f"({F['u32_strict_one_bit_per_step_chains']} strict cumulative chains "
                   f"anywhere in RAM). No per-phase claim map is registered for this row the "
                   f"way F01 has one",
        },
        "cross_system_behavior": {
            "state": "not_met",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"nothing. No artifact belonging to this row exercises any combination: "
                     f"its evidence is static image reads plus offline save parsing "
                     f"(runtime trace evidence present: "
                     f"{F['census_has_runtime_trace_evidence']}), and the census triage says "
                     f"'{F['census_triage']['cross_system_behavior']}'",
            "gap": f"the material for a first crossing is sitting unused: the stage's actor "
                   f"pool is censused at {F['stage8_actor_records']} records over "
                   f"{F['stage8_actor_id_count']} distinct ids "
                   f"({F['stage8_actor_ids_with_canon_binding']} of those ids have a Canon "
                   f"role), the completion oracle's stage snapshot already carries "
                   f"{len(F['completion_oracle_last_in_stage_snapshot_fields'])} cross-system "
                   f"fields, and {F['stage8_movies_pinned']} routes are pinned. This dimension "
                   f"is not blocked by a missing fixture; it is unattempted",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the loader interface is documented to the instruction and, unusually, "
                     f"documented as TWO interfaces that must not be conflated: the level-data "
                     f"path is arithmetic, pinned at instructions "
                     f"{F['arithmetic_law_instruction_pcs']}, and the sound-bank path is a "
                     f"permuted jump table whose bounds test, table base and string base are "
                     f"pinned at {F['sound_bank_mechanism_pcs']} and whose dispatch is fully "
                     f"decoded. The unknown is "
                     f"enumerated with a named obstruction rather than left blank: "
                     f"'{F['row_declared_missing']}', with the named next step "
                     f"'{F['row_declared_next']}'. The row also records its own falsification "
                     f"({F['row_records_prior_binding_falsified']}) and the experiment note "
                     f"records that its own first version was wrong "
                     f"({F['experiment_records_its_own_first_version_was_wrong']}) -- the "
                     f"interface documentation is self-correcting in the way the bar wants",
            "gap": f"the documentation did not reach the surfaces other rows read, which is "
                   f"measurable and severe. The Canon system page still asserts the falsified "
                   f"law (still_asserts="
                   f"{F['canon_page_still_asserts_index_equals_id_minus_one']}) and "
                   f"{F['canon_campaign_map_rows_disagreeing_with_the_corrected_law']} of its "
                   f"{F['canon_campaign_map_rows']} campaign-map rows name an overlay directory "
                   f"the corrected law contradicts -- including this row's own scene, still "
                   f"printed as '{F['canon_row_for_this_scene_asset']}' / "
                   f"'{F['canon_row_for_this_scene_overlay']}'. "
                   f"{F['row_governing_pcs_registered_as_confirmed_sites']} of the row's "
                   f"governing instruction PCs are registered as confirmed sites out of "
                   f"{F['confirmed_sites_total']} entries. The ownership graph's bounding claim "
                   f"for the readers is itself unbacked: it names two artifacts, and this row's "
                   f"table addresses appear in "
                   f"{F['row_table_addresses_present_in_jr_tables']} and "
                   f"{F['row_table_addresses_present_in_dispatch_map']} of them respectively "
                   f"(of {len(F['row_table_state_addresses'])} addresses). The overlay side has "
                   f"no documented ABI at all: {F['pinned_overlay_functions_in_census']} "
                   f"functions, {F['ownership_functions_with_canon']} Canon page(s) across the "
                   f"whole row",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured against BOTH registries, not one. RESIDENT (config/segments.yml, "
                     f"{F['resident_build_units']} units, toolchain "
                     f"{F['resident_build_toolchain']}): the "
                     f"{F['governing_addresses_resident']} distinct resident governing "
                     f"addresses derived "
                     f"from this row's own artifacts resolve to "
                     f"{F['governing_resident_build_units']} build unit(s) -- "
                     f"{F['governing_resident_units_matching_c']} matching C and "
                     f"{F['governing_resident_units_hand_asm']} hand-written byte-exact ASM "
                     f"({F['governing_resident_unit_names']}), with "
                     f"{F['governing_resident_addresses_outside_any_build_unit']} outside any "
                     f"unit (the two ASCII/pointer tables are data, in no unit). OVERLAY "
                     f"(config/overlays.yml + src/overlays/ + "
                     f"analysis/overlay_decomp_progress.json, "
                     f"{F['overlay_track_matched_functions']}/"
                     f"{F['overlay_track_total_code_functions']} matched campaign-wide = "
                     f"{F['overlay_track_matched_pct']}%): this row's overlay HAS a build entry "
                     f"-- {F['pinned_overlay_matched_functions']} of "
                     f"{F['pinned_overlay_code_functions']} code functions matched from "
                     f"{F['pinned_overlay_matched_sources']}, rebuild validated "
                     f"({F['pinned_overlay_rebuild_validated']}) with rebuilt sha1 equal to the "
                     f"blob's ({F['pinned_overlay_rebuilt_sha1_matches']}), and that sha1 is "
                     f"the sha1 of the image this assessment byte-pinned as resident "
                     f"({F['residency_pin_agrees_with_overlay_registry_sha1']}). So overlay "
                     f"byte-matching is DEMONSTRATED for this row's overlay, not impossible",
            "gap": f"no governing function of this row is byte-matched C. The resident "
                   f"dispatcher that owns every pinned instruction is hand ASM, and of the "
                   f"{F['governing_addresses_in_this_rows_overlay']} distinct governing "
                   f"addresses inside the overlay only "
                   f"{F['governing_overlay_addresses_with_matched_c']} has "
                   f"matched C -- the state initializer, which is real and directly on the "
                   f"frontier but is not the objective logic. The functions that would carry "
                   f"the marker mechanism (notably the completion handler among the "
                   f"{F['pinned_overlay_functions_in_census']} census functions) have no C. "
                   f"Note the direction of the census's own triage: it reports "
                   f"'{F['census_triage']['source_closure']}', which measures REGISTRATION; "
                   f"measured against the row's real governing addresses the count of C units "
                   f"is {F['governing_resident_units_matching_c']}",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F08_city_square measured against the nine DoD dimensions AS WRITTEN "
                    "(item 2 = enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f08_written_bar_assessment.py",
        "schema": "abl-phase4-f08-written-bar-assessment/1",
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
            "author_conflict": "the assessor did not author F08's underlying evidence, but "
                               "did author this assessment, the F-row census whose "
                               "durable_evidence result it carries forward, and the one NEW "
                               "measurement in it (tools/phase4_f08_overlay_residency_pin.c) "
                               "-- so on the overlay-residency question and the cross-fixture "
                               "diff the tool, the claim and the judgment share an author. "
                               "Every state below is a submission to a fresh detached "
                               "verifier, not a promotion; `partial` and `not_met` are as "
                               "challengeable as `met`",
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
            "_comment": "two defects confirmed on other rows today, checked explicitly here "
                        "so silence is not read as absence",
            "a_overlay_misattribution": {
                "applies_to_this_row": True,
                "why": f"the row's binding is a claim about which FILE occupies the shared "
                       f"overlay base {F['overlay_registry_region_a']}, and an address in that "
                       f"window is ambiguous across "
                       f"{F['overlay_images_covering_the_matched_entry_pc']} of the "
                       f"{F['overlay_images_in_function_census']} censused overlay images",
                "was_the_row_already_wrong": False,
                "how_settled": f"{PINSRC}: of {F['residency_pin_images_scanned']} images x "
                               f"{F['residency_pin_rams_scanned']} fixtures, "
                               f"{F['residency_pin_images_with_stable_declared_base']} image is "
                               f"the argmax of non-trivial agreement in every fixture AND has "
                               f">=2 anchors agreeing on the declared base",
                "verdict": f"{F['residency_pin_result']} -- {F['residency_pin_file']} "
                           f"({F['residency_pin_nontrivial_pct']}% vs "
                           f"{F['residency_pin_runner_up_pct']}% runner-up), sha1 agreeing with "
                           f"the overlay build registry "
                           f"({F['residency_pin_agrees_with_overlay_registry_sha1']}). The "
                           f"row's 2026-08-05 correction is CONFIRMED by an independent method",
                "how_close_it_was": f"{F['images_whose_best_anchor_base_is_the_declared_base']} "
                                    f"images have their best anchor hit at the declared base "
                                    f"({F['images_whose_best_anchor_base_is_the_declared_base_paths']}) "
                                    f"and {F['images_with_anchor_hits_but_no_stable_declared_base']} "
                                    f"images produce anchor hits at a WANDERING base -- base "
                                    f"stability and the >=2-anchor rule are what separate them, "
                                    f"exactly as the row's own false-positive note warned",
            },
            "b_semantic_registry_collision": {
                "applies_to_this_row": True,
                "va_collision_hit": False,
                "measured": f"{len(F['semantic_entries_inside_shared_region_a'])} "
                            f"semantic_state entries fall inside the SHARED region A "
                            f"({F['semantic_entries_inside_shared_region_a']}, ids "
                            f"{F['semantic_entries_inside_shared_region_a_ids']}), but "
                            f"{len(F['semantic_entries_inside_this_rows_overlay_extent'])} fall "
                            f"inside THIS row's pinned overlay extent "
                            f"{F['pinned_overlay_extent']}. The pinned EXTENT, not the shared "
                            f"region, is what keeps the collision out",
                "different_defect_found": f"the registry entry this row DOES own "
                                          f"({F['registered_table_entry_id']} at "
                                          f"{F['row_table_state_addresses']}) still carries the "
                                          f"invariant 'row index = scene_id - 1' at confidence "
                                          f"'{F['registered_table_confidence']}' -- the law "
                                          f"this row falsified. Same failure mode as a VA "
                                          f"collision (a registry asserting the wrong thing "
                                          f"about a real address), different mechanism",
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
                    "scores the row 0/9. That is a disposition, not a measurement -- and it "
                    f"records movie_count {F['registry_movie_count']} for a stage with "
                    f"{F['stage8_movies_pinned']} pinned movies",
        },
        "fail_loud_contract": {
            "guards": F["fail_loud_guards_fired"],
            "in_band": "re-proved on every generation before any artifact is read; if a "
                       "guard stops firing the run aborts instead of emitting numbers whose "
                       "staleness detection cannot be trusted",
            "out_of_band_probes_run_2026-08-11": [
                "moved analysis/phase4_f08_scene_binding.json aside -> abort, exit 1, no "
                "output file",
                "renamed unique_pin_file inside the residency pin -> abort, exit 1, no "
                "output file",
                "drifted one named_words address away from the byte-matched C source -> "
                "abort naming both sets, exit 1, no output file",
            ],
            "note": "the out-of-band list records actions taken by the assessor; the "
                    "in-band guards above are re-measured every run",
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
                   f"unmeasured -- against the WRITTEN bars. F08 is a stage row that solved "
                   f"an INFRASTRUCTURE problem for the whole campaign and has not started its "
                   f"own: the loader binding is enumerated, exhaustive over a closed "
                   f"denominator, gated, and now byte-pinned, while the stage objective the "
                   f"row is named for has no oracle, no lifecycle, no crossing and no C.",
        "notable": [
            f"THE ROW'S CORRECTION NEVER REACHED THE PAGES OTHER ROWS READ. Measured: the "
            f"Canon system page still states the falsified law "
            f"(still_asserts={F['canon_page_still_asserts_index_equals_id_minus_one']}) and "
            f"{F['canon_campaign_map_rows_disagreeing_with_the_corrected_law']} of its "
            f"{F['canon_campaign_map_rows']} campaign-map rows name an overlay directory the "
            f"corrected law contradicts (scene ids "
            f"{F['canon_campaign_map_disagreeing_scene_ids']}); this row's own scene is still "
            f"printed there as '{F['canon_row_for_this_scene_asset']}' / "
            f"'{F['canon_row_for_this_scene_overlay']}'. config/semantic_state.yaml likewise "
            f"still registers 'row index = scene_id - 1' at confidence "
            f"'{F['registered_table_confidence']}'. The correction landed in the analysis "
            f"artifact, the experiment note, the baseline row and a pytest gate -- and in "
            f"none of the two places a reader would consult. The two ids that AGREE "
            f"(1 and 15) are the same two coincidences that let the error survive review "
            f"twice.",
            f"THE ROW'S HEADLINE NEGATIVE WAS PROSE, AND IT OVERSTATES BY 2x. 'Region A "
            f"differs in only 4 bytes of 7,656' is right about region A "
            f"({F['region_a_differing_bytes']} of {F['region_a_bytes']}) but region A is "
            f"sized for the largest overlay: only "
            f"{F['region_a_differing_inside_pinned_image']} of those bytes are inside this "
            f"row's {F['residency_pin_size']}-byte overlay, and the other "
            f"{F['region_a_differing_beyond_pinned_image']} are stale bytes belonging to no "
            f"resident image. Corrected, the overlay-local signal is a SINGLE word: "
            f"{F['varying_overlay_word_addresses']} with values "
            f"{F['varying_overlay_word_values']} across the five performer fixtures, zero on "
            f"disc, initialized to {F['byte_matched_c_nonzero_initializers']} by the one "
            f"byte-matched C function in this overlay. That is the row's first named, "
            f"testable objective-state candidate -- and it is UNRESOLVED: five samples "
            f"straddling the initializer are equally consistent with a free-running timer.",
            f"THE ROW'S OTHER NEGATIVE IS CONFIRMED IN ITS STRONG FORM AND CORRECTED IN ITS "
            f"LITERAL ONE. 'No subset-chain mask found in resident RAM': measured over all "
            f"{F['whole_ram_words']} words of the five fixtures, "
            f"{F['u32_subset_chains']} u32 and {F['u16_subset_chains']} u16 words DO order "
            f"into a bitwise subset chain -- but {F['u32_strict_one_bit_per_step_chains']} "
            f"u32 and {F['u16_strict_one_bit_per_step_chains']} u16 are the strict "
            f"one-bit-per-step shape a five-performer cumulative mask must take. The "
            f"conclusion stands; the search space it rests on is now enumerated instead of "
            f"asserted, and {F['whole_ram_differing_words']} differing words is the real "
            f"bound on where the objective state can be.",
            f"THE BLOCKER THE ROW RECORDS IS NOT A MISSING FIXTURE. The row asks for "
            f"'{F['row_declared_fixture_need']}' and its next action is a live Interpreter "
            f"trace, while {F['stage8_movies_attributed']} stage-8 movies are already pinned "
            f"and byte-matching ({F['stage8_movie_frames']}), "
            f"{len(F['stage8_movies_under_phase4_interpreter'])} of them under "
            f"movies/Phase4/Interpreter/. The row declares "
            f"{F['stage8_movies_declared_by_the_row']} of them, and the movie scheduler "
            f"consequently marks this row ineligible with reason "
            f"{F['scheduler_ineligibility_reasons']} "
            f"(sees_a_phase4_movie={F['scheduler_sees_a_phase4_movie']}). The scheduler is "
            f"also running on a stale ownership snapshot "
            f"(input_is_current={F['scheduler_ownership_input_is_current']}; it records "
            f"{F['scheduler_static_ownership_function_count']} owned functions where the "
            f"graph now has {F['ownership_functions']}). Under-declaration in the row is "
            f"propagating into the scheduler and blocking the exact work the row asks for.",
            f"AN UNCITED CAMPAIGN ORACLE ALREADY COVERS THIS STAGE FROM A COLD BOOT. "
            f"{F['completion_oracle_movie']} ({F['completion_oracle_frames']} frames) enters "
            f"scene {F['completion_oracle_target_scene']} at frame "
            f"{F['completion_oracle_entered_stage_frame']} and exits by movie end, "
            f"pristine_replay_accepted={F['completion_oracle_replay_accepted']} -- and it "
            f"independently corroborates the corrected scene id "
            f"({F['completion_oracle_corroborates_the_scene_id']}). The row does not cite it "
            f"({F['completion_oracle_cited_by_the_row']}). Likewise "
            f"{ACT} censuses {F['stage8_actor_records']} actor records over "
            f"{F['stage8_actor_id_count']} ids from this row's own fixture, uncited "
            f"({F['stage8_actor_census_cited_by_the_row']}).",
            f"THIS STAGE AUTHORS NO REGION CODES AT ALL. Its collision container "
            f"{F['stage8_collision_container']} has histogram "
            f"{F['stage8_region_code_histogram']} over "
            f"{F['stage8_authored_collision_sectors']} authored sectors "
            f"(no_nonzero_codes={F['stage8_has_no_nonzero_region_codes']}), against "
            f"{F['e02_levels_with_any_nonzero_region_code']} of "
            f"{F['e02_levels_censused']} levels that do author them. Whatever ends this "
            f"stage, it is not the region-code exit mechanism F01 proved -- so the objective "
            f"and the exit are the same open question, and the exit path is not inherited "
            f"from any closed row.",
            f"THE SAME TOKEN TRAP THAT CREATED THIS ROW'S ERROR IS STILL LIVE IN THE FIXTURE "
            f"CORPUS, and this assessment walked into it once before catching it. "
            f"'{F['disc_directory_named_by_this_stages_ordinal']}' -- the disc directory named "
            f"by this stage's ordinal -- belongs to {F['stages_owning_that_disc_directory']}, "
            f"not to this row (owns_it={F['this_row_owns_the_disc_directory_named_by_its_ordinal']}); "
            f"the movie corpus uses STAGE numbering, proved by the oracle binding "
            f"{F['completion_oracle_stage_key']} to a LEVEL08-named movie whose target scene is "
            f"{F['completion_oracle_target_scene']}. Separately, 'B08' is a ROW id whose movies "
            f"also carry an 08. Matching the bare token yields "
            f"{F['stage8_movies_token_matched']} movies; only "
            f"{F['stage8_movies_attributed']} are attributable to this stage by name or by the "
            f"oracle, leaving {F['stage8_movies_token_matched_attribution_unverified']} "
            f"token-matched with attribution unverified. Any future F08 work that selects "
            f"fixtures by the ordinal token will pick up another stage's recordings.",
            f"UNMEASURED HERE, and named so a verifier does not read silence as absence: "
            f"whether {F['varying_overlay_word_addresses']} is the objective counter (that "
            f"needs a live watch during a performer-found event, not a re-read); whether any "
            f"of the {F['pinned_overlay_functions_in_census']} pinned-overlay functions "
            f"implements marker detection (no artifact walks them); and whether the "
            f"{F['stage8_movies_pinned']} pinned routes would supply lifecycle or crossing "
            f"coverage (that needs a replay).",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar F08] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} derived / "
          f"{doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
