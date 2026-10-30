#!/usr/bin/env python3
"""Measure F05_riverbed_run and F07_city_entrance against the nine DoD bars AS WRITTEN.

Sibling of `tools/phase4_f01_written_bar_assessment.py` (the exemplar) and
`tools/phase4_f08_written_bar_assessment.py` (the rigor standard), under
`engineering-specs/phase4-measurement-standard-ruling.md`. The WRITTEN bars are:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

WHY THESE TWO ROWS TOGETHER, AND WHY SEPARATE SCORECARDS. They are the thinnest F
rows in the registry: both `external_lead`, both declaring
`missing: "Implementation unresolved."`, both declaring exactly two evidence
classes (`manual`, `secondary_lead`), and both citing exactly ONE analysis
artifact -- and it is not their own, it is the SHARED F08 scene-asset binding.
Measuring them in one pass makes the shared machinery cheap to reuse; it must not
make their conclusions shared. Every fact below is derived PER ROW and every
judgment is authored PER ROW. Nothing is cross-credited: where the two rows differ
the states differ, and they do.

A scorecard that is mostly `not_met` is the CORRECT outcome when that is the
truth. `unmeasured` is an allowed state and is used where a bar cannot be scored
from anything in the repository rather than being filled with something adjacent.

`secondary_lead`, which BOTH rows declare as one of their two evidence classes,
is defined in-repo as "non-authoritative trigger lead only" with authority bound
to hash-verified media and executable bytes. It can raise a claim to be tested; it
can never satisfy any of the nine bars. It is therefore counted as zero support
here, and the definition is derived from its artifact rather than asserted.

durable_evidence is NOT re-derived: it was MEASURED in
`analysis/phase4_f_row_measured_census.json` (2/2 declared fixtures intact for each
row) and is carried forward with its fraction, failing loudly if that measurement
moves.

TWO SYSTEMIC DEFECTS ARE CHECKED EXPLICITLY FOR EACH ROW:
  (a) OVERLAY MISATTRIBUTION -- every per-level overlay loads at the same base
      (region A, 0x800B39A0), so an address in that window names real content in
      almost every overlay image and `analysis/phase3_ownership_graph.json` stores
      no image field at all. Settled here from BYTES by
      `tools/phase4_f05_f07_stage_identity_pin.c` over all 21 candidate images x
      each row's own fixtures, before any overlay claim is made. The scan's inputs
      are re-derived from the pinned registries so the C run cannot drift away
      from the claims it supports.
  (b) SEMANTIC-REGISTRY COLLISION -- config/semantic_state.yaml keys overlay-local
      addresses GLOBALLY. Measured against each row's pinned overlay EXTENT, not
      against the shared region.

BOTH SOURCE REGISTRIES ARE READ before any source_closure claim: config/segments.yml
(resident) and config/overlays.yml + src/overlays/ +
analysis/overlay_decomp_progress.json (overlay track). A claim that overlay
byte-matching is impossible was banked and RETRACTED for checking only the first.
A third tree, `src_re/`, holds SEMANTIC reconstructions that are explicitly "not a
build input"; it is read, and it is counted as zero toward this bar, with the
disclaimer derived from the file rather than assumed.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a
fresh detached verifier. This tool never edits analysis/mechanics_baseline.yaml.

Usage: python3 tools/phase4_f05_f07_written_bar_assessment.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


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
        return yaml.safe_load(self.pin(rel).read_text(encoding="utf-8"))

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
        if key in self.facts:
            raise SystemExit(f"fact '{key}' recorded twice -- the two rows are "
                             "sharing a key, which is exactly the cross-crediting "
                             "this assessment forbids")
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
    drifting the C scan's declared base away from the overlay registry) were run by
    hand and each aborted with a non-zero exit and no output file. Those are
    one-off. These four are in-band and re-run on every generation, so a future
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
    try:
        probe2 = Evidence()
        probe2.pin("tools/phase4_f05_f07_written_bar_assessment.py")
        probe2.fact("dup", 1, "tools/phase4_f05_f07_written_bar_assessment.py")
        probe2.fact("dup", 2, "tools/phase4_f05_f07_written_bar_assessment.py")
    except SystemExit:
        fired.append("duplicate_fact_key_aborts")
    if len(fired) != 4:
        raise SystemExit("FAIL-LOUD MACHINERY IS BROKEN: only these guards fired: "
                         f"{fired}. Refusing to emit an assessment whose staleness "
                         "detection cannot be trusted.")
    return fired


# --------------------------------------------------------------------------- #
# per-row configuration. Everything here is a LOOKUP KEY, not a claim: each one
# is used to find a record in a pinned artifact, and the record then supplies the
# fact. The scene ids and overlay names below are NOT trusted -- they are checked
# against the C pin's decode of the campaign progression table and against the
# byte-level residency result, and a disagreement aborts.
# --------------------------------------------------------------------------- #
ROWS = [
    {
        "row_id": "F05_riverbed_run",
        "key": "f05",
        "stage_key": "stage05_riverbed_run",
        "movie_token": r"level05",
        "stage_name_token": r"riverbed",
        "pin_artifact": "analysis/phase4_f05_stage_identity_pin.json",
        "e10_fixtures": ["falling_spikes_l05", "pit_l05"],
        "hazard_word": "spike",
        "byte_matched_c": "src/overlays/LEVEL10_LEVEL/800b3bf0_init_overlay_state.c",
        "semantic_c": None,
        "gate_artifact": None,
    },
    {
        "row_id": "F07_city_entrance",
        "key": "f07",
        "stage_key": "stage07_city_entrance",
        "movie_token": r"level07",
        "stage_name_token": r"cityentrance|city_entrance",
        "pin_artifact": "analysis/phase4_f07_stage_identity_pin.json",
        "e10_fixtures": ["goo_l07", "pit_l07"],
        "hazard_word": "goo",
        "byte_matched_c": None,
        "semantic_c": "src_re/level04_grain_gate_update.c",
        "gate_artifact": "analysis/phase4_grain_gates.json",
    },
]

LIFECYCLE_BAR = ("cold boot / load / first use / repeated use / exhaustion / "
                 "retirement / reuse each evidenced")

CENSUS = "analysis/phase4_f_row_measured_census.json"
BASE = "analysis/mechanics_baseline.yaml"
DEBT = "analysis/phase4_closure_debt.json"
QUEUE = "analysis/phase4_movie_priority_queue.json"
OWN = "analysis/phase3_ownership_graph.json"
BIND = "analysis/phase4_f08_scene_binding.json"
OVLY = "config/overlays.yml"
SEG = "config/segments.yml"
OVLD = "analysis/overlay_decomp_progress.json"
FN = "analysis/functions.json"
SYMS = "analysis/overlay_symbols.json"
SEM = "config/semantic_state.yaml"
E02 = "analysis/phase4_e02_disc_region_code_census.json"
ORACLE = "analysis/phase2_completion_oracle.json"
AUDIT = "analysis/phase2_fixture_audit.json"
FIXSET = "analysis/phase0_2_external_fixture_set.json"
COV = "analysis/phase2_row_coverage.json"
ACT = "analysis/phase1_kind_actor_census.json"
C2 = "analysis/phase4_c2_level_type_authority.json"
E10 = "analysis/phase4_e10_hazards.json"
BREADTH = "analysis/phase4_f01_campaign_breadth.json"
SPIN = "analysis/phase4_spin_heading.json"
DEATH = "analysis/phase2_death_matrix.json"
STAGEB = "analysis/phase2_stage_baseline.json"
PINC = "tools/phase4_f05_f07_stage_identity_pin.c"
SELF = "tools/phase4_f05_f07_written_bar_assessment.py"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(
        ROOT / "analysis/phase4_f05_f07_written_bar_assessment.json"))
    args = ap.parse_args()

    E = Evidence()
    F = E.facts

    # ------------------------------------------------------------------ #
    # 0. prove the staleness detection works before trusting any number   #
    # ------------------------------------------------------------------ #
    E.pin(SELF)
    E.pin(PINC)
    E.fact("fail_loud_guards_fired", selftest_guards(), SELF)

    # ------------------------------------------------------------------ #
    # 1. SHARED inputs. These are shared MACHINERY, never shared verdicts. #
    # ------------------------------------------------------------------ #
    census = E.json(CENSUS)
    base = E.yaml(BASE)
    debt = E.json(DEBT)
    queue = E.json(QUEUE)
    own = E.json(OWN)
    bind = E.json(BIND)
    ovly = E.yaml(OVLY)
    seg = E.yaml(SEG)
    ovld = E.json(OVLD)
    fnj = E.json(FN)
    syms = E.json(SYMS)
    sem = E.yaml(SEM)
    e02 = E.json(E02)
    oracle = E.json(ORACLE)
    audit = E.json(AUDIT)
    fixset = E.json(FIXSET)
    cov = E.json(COV)
    act = E.json(ACT)
    c2 = E.json(C2)
    e10 = E.json(E10)
    breadth = E.json(BREADTH)
    spin = E.json(SPIN)
    death = E.json(DEATH)
    stageb = E.json(STAGEB)

    E.fact("census_baseline_sha256", req(census, "baseline_sha256", where=CENSUS), CENSUS)
    E.fact("baseline_sha256_matches_census",
           sha256_file(ROOT / BASE) == F["census_baseline_sha256"], [BASE, CENSUS])
    E.fact("f_rows_assessed_by_census", req(census, "rows_assessed", where=CENSUS), CENSUS)
    E.fact("f_rows_with_durable_evidence_met",
           req(census, "durable_evidence_met_fraction", where=CENSUS), CENSUS)

    # the definition that governs BOTH rows' second declared evidence class
    E.fact("secondary_lead_role", req(spin, "secondary_lead", "role", where=SPIN), SPIN)
    E.fact("secondary_lead_authority_rule",
           req(spin, "secondary_lead", "authority_rule", where=SPIN), SPIN)

    # the shared loader binding: the ONLY analysis artifact either row cites
    E.fact("shared_binding_status", req(bind, "status", where=BIND), BIND)
    E.fact("shared_binding_scope_limits", req(bind, "scope_limits", where=BIND), BIND)
    E.fact("shared_binding_rows_corrected",
           len(req(bind, "rows_corrected", where=BIND)), BIND)
    E.fact("shared_binding_scene_ids_mapped",
           len(req(bind, "scene_id_to_level_data_dir", where=BIND)), BIND)
    law_text = req(bind, "mechanism", "level_data_directory", where=BIND)
    law_pcs = sorted(set(re.findall(r"0x[0-9A-Fa-f]{8}", law_text)))
    if len(law_pcs) < 3:
        raise SystemExit("STALE CITATION: the shared binding's arithmetic law no longer "
                         "names the instruction addresses this assessment resolves")
    E.fact("shared_binding_arithmetic_law_pcs", law_pcs, BIND)
    bank_text = req(bind, "mechanism", "sound_bank", where=BIND)
    E.fact("shared_binding_sound_bank_pcs",
           sorted(set(re.findall(r"0x[0-9A-Fa-f]{8}", bank_text))), BIND)

    region_a = as_int(req(ovly, "region_a", where=OVLY))
    region_b = as_int(req(ovly, "region_b", where=OVLY))
    E.fact("overlay_registry_region_a", f"0x{region_a:08X}", OVLY)
    E.fact("overlay_registry_region_length", region_b - region_a, OVLY)
    E.fact("overlay_registry_total_entries", len(req(ovly, "overlays", where=OVLY)), OVLY)
    E.fact("overlay_track_total_code_functions",
           req(ovld, "overlay_code_functions", where=OVLD), OVLD)
    E.fact("overlay_track_matched_functions",
           req(ovld, "matched", "functions", where=OVLD), OVLD)
    E.fact("overlay_track_matched_pct", req(ovld, "matched", "pct_functions", where=OVLD),
           OVLD)
    E.fact("overlay_images_in_function_census", len(req(fnj, "overlays", where=FN)), FN)
    seg_units = [(as_int(req(u, "start", where=SEG)), as_int(req(u, "end", where=SEG)),
                  req(u, "source", where=SEG)) for u in req(seg, "attempted", where=SEG)]
    E.fact("resident_build_units", len(seg_units), SEG)
    E.fact("resident_build_toolchain", req(seg, "c_toolchain", "compiler", where=SEG), SEG)

    sem_entries = req(sem, "entries", where=SEM)

    def sem_addr(e):
        a = e.get("address")
        return as_int(a) if a is not None else None

    sem_addrs = {sem_addr(e) for e in sem_entries} - {None}
    E.fact("semantic_state_entries_total", len(sem_entries), SEM)
    E.fact("semantic_entries_inside_shared_region_a",
           sorted(f"0x{a:08X}" for a in sem_addrs if region_a <= a < region_b),
           [SEM, OVLY])
    E.fact("semantic_entries_inside_shared_region_a_ids",
           sorted(req(e, "id", where=SEM) for e in sem_entries
                  if sem_addr(e) is not None and region_a <= sem_addr(e) < region_b), SEM)
    tbl = next((e for e in sem_entries
                if sem_addr(e) == as_int("0x8001AD0C")), None)
    if tbl is None:
        raise SystemExit(f"STALE CITATION: {SEM} no longer registers the scene asset "
                         "table both rows cite as state")
    inv_ctx = req(tbl, "invariants", 0, "context", where=SEM)
    E.fact("shared_state_table_registry_id", req(tbl, "id", where=SEM), SEM)
    E.fact("shared_state_table_registry_confidence", req(tbl, "confidence", where=SEM), SEM)
    E.fact("shared_state_table_still_asserts_index_equals_id_minus_one",
           "row index = scene_id - 1; disc DIR" in inv_ctx
           and "CORRECTED" not in inv_ctx, SEM)
    E.fact("shared_state_table_invariant_records_its_own_correction",
           "CORRECTED" in inv_ctx, SEM)

    e02_levels = req(e02, "levels", where=E02)
    E.fact("e02_levels_censused", len(e02_levels), E02)
    E.fact("e02_authored_sectors_compared",
           req(e02, "agreement", "authored_sectors_compared", where=E02), E02)
    E.fact("e02_disagreements", len(req(e02, "agreement", "disagreements", where=E02)), E02)
    E.fact("e02_campaign_code_histogram",
           req(e02, "campaign_disc_histogram", where=E02), E02)
    E.fact("e02_progression_table_address",
           req(e02, "scene_universe", "campaign_progression_table", "address",
               where=E02), E02)
    E.fact("e02_progression_table_scenes",
           req(e02, "scene_universe", "campaign_progression_table", "scenes",
               where=E02), E02)
    codes_by_level = {k: sorted(int(c) for c in req(v, "code_histogram", where=E02)
                                if int(c) != 0)
                      for k, v in e02_levels.items()}
    E.fact("e02_levels_with_code_1", sorted(k for k, v in codes_by_level.items() if 1 in v),
           E02)
    E.fact("e02_levels_with_code_4", sorted(k for k, v in codes_by_level.items() if 4 in v),
           E02)
    E.fact("e02_levels_with_both_code_1_and_code_4",
           sorted(k for k, v in codes_by_level.items() if 1 in v and 4 in v), E02)
    E.fact("e02_levels_with_an_exit_code_2_or_3",
           sorted(k for k, v in codes_by_level.items() if 2 in v or 3 in v), E02)

    E.fact("e10_row", req(e10, "row", where=E10), E10)
    E.fact("e10_status", req(e10, "status", where=E10), E10)
    E.fact("e10_shared_damage_entry",
           req(e10, "shared_damage_mechanism", "entry", where=E10), E10)
    E.fact("e10_capsule_domain_hash_mismatches",
           req(e10, "capsule_validation", "domain_hash_mismatches", where=E10), E10)
    E.fact("e10_capsule_root_is_external",
           req(e10, "capsule_validation", "capsule_root", where=E10).startswith("/"), E10)
    E.fact("e10_capsule_root_exists_on_this_machine",
           Path(req(e10, "capsule_validation", "capsule_root", where=E10)).exists(), E10)
    E.fact("e10_still_open", req(e10, "scope", "still_open", where=E10), E10)
    E.fact("e10_closure_metrics", req(e10, "closure_metrics", where=E10), E10)

    E.fact("c2_taxonomy_coverage_demonstrated",
           req(c2, "result", "taxonomy_coverage_demonstrated", where=C2), C2)
    E.fact("c2_underivable_types", sorted(req(c2, "result", "underivable_types", where=C2)),
           C2)

    movies = req(audit, "movies", where=AUDIT)
    saves = req(audit, "saves", where=AUDIT)
    fixentries = req(fixset, "entries", where=FIXSET)
    ostages = req(oracle, "stages", where=ORACLE)

    # registered gate files, resolved by CONTENT rather than by naming convention
    test_dir = ROOT / "tests"
    if not test_dir.is_dir():
        raise SystemExit("STALE CITATION: tests/ is not a directory")
    test_bodies = {}
    for p in sorted(test_dir.glob("test_*.py")):
        test_bodies[f"tests/{p.name}"] = p.read_text(errors="ignore")
    if not test_bodies:
        raise SystemExit("STALE CITATION: tests/ contains no pytest files")
    E.fact("registered_test_files_total", len(test_bodies), SELF)

    scorecards: dict[str, dict] = {}
    per_row_counts: dict[str, dict] = {}

    # ================================================================== #
    #                        PER-ROW MEASUREMENT                          #
    # ================================================================== #
    for cfg in ROWS:
        RID, K = cfg["row_id"], cfg["key"]
        SK = cfg["stage_key"]
        PIN = cfg["pin_artifact"]

        def f(name, value, source):
            return E.fact(f"{K}_{name}", value, source)

        def g(name):
            return F[f"{K}_{name}"]

        # ---- 1. durable_evidence, carried forward ---------------------- #
        crow = req(census, "rows", RID, where=CENSUS)
        f("census_durable_state", req(crow, "durable_evidence", "state", where=CENSUS),
          CENSUS)
        f("census_durable_fraction",
          req(crow, "durable_evidence", "intact_pinned", where=CENSUS), CENSUS)
        f("census_durable_reason", req(crow, "durable_evidence", "reason", where=CENSUS),
          CENSUS)
        f("census_row_status", req(crow, "status", where=CENSUS), CENSUS)
        f("census_triage", req(crow, "measurability_triage", where=CENSUS), CENSUS)
        inv = req(crow, "evidence_inventory", where=CENSUS)
        f("census_declared_evidence_classes",
          req(inv, "declared_evidence_classes", where=CENSUS), CENSUS)
        f("census_derived_evidence_classes",
          req(inv, "derived_evidence_classes", where=CENSUS), CENSUS)
        f("census_analysis_artifacts", req(inv, "analysis_artifacts", where=CENSUS), CENSUS)
        f("census_vault_pages", req(inv, "vault_pages", where=CENSUS), CENSUS)
        f("census_source_files", req(inv, "source_files", where=CENSUS), CENSUS)
        f("census_segments_entries", req(inv, "segments_entries", where=CENSUS), CENSUS)
        f("census_overlay_build_entries", req(inv, "overlay_build_entries", where=CENSUS),
          CENSUS)
        f("census_overlay_matched_sources",
          req(inv, "overlay_matched_sources", where=CENSUS), CENSUS)
        f("census_overlay_name", req(inv, "overlay_name", where=CENSUS), CENSUS)
        f("census_scene_id", req(inv, "scene_id", where=CENSUS), CENSUS)
        f("census_stage_ordinal", req(inv, "stage_ordinal", where=CENSUS), CENSUS)
        f("census_has_runtime_trace_evidence",
          req(inv, "has_runtime_trace_evidence", where=CENSUS), CENSUS)
        f("census_has_static_code_evidence",
          req(inv, "has_static_code_evidence", where=CENSUS), CENSUS)
        fixtures = req(crow, "durable_evidence", "fixtures", where=CENSUS)
        external = [x["path"] for x in fixtures
                    if req(x, "kind", where=CENSUS) == "external_fixture"]
        f("row_external_fixtures", external, CENSUS)
        f("row_external_fixture_count", len(external), CENSUS)
        if g("census_durable_state") != "met":
            raise SystemExit(f"{RID}: carried-forward durable_evidence is no longer "
                             "'met' -- re-measure before reusing this assessment")
        f("row_external_fixtures_bytes_match_pin",
          sum(1 for p in external
              if p in fixentries and (ROOT / p).exists()
              and sha256_file(ROOT / p) == fixentries[p]["sha256"]), [FIXSET, CENSUS])
        f("row_external_fixture_consumers",
          sorted({c for p in external
                  for c in req(fixentries, p, "consumers", where=FIXSET)}), FIXSET)
        f("row_external_fixture_consumer_count", len(g("row_external_fixture_consumers")),
          FIXSET)

        # ---- 2. the baseline row (read-only) --------------------------- #
        rows = req(base, "rows", where=BASE)
        row = next((r for r in rows if r.get("id") == RID), None)
        if row is None:
            raise SystemExit(f"STALE CITATION: {BASE} no longer carries {RID}")
        f("row_name", req(row, "name", where=BASE), BASE)
        f("row_declared_stages_field", req(row, "stages", where=BASE), BASE)
        f("row_declared_status", req(row, "status", where=BASE), BASE)
        f("row_declared_evidence_classes", req(row, "evidence", where=BASE), BASE)
        f("row_declares_secondary_lead", "secondary_lead" in req(row, "evidence",
                                                                 where=BASE), BASE)
        f("row_binding_claims", len(req(row, "bindings", where=BASE)), BASE)
        f("row_records_prior_binding_falsified",
          any("FALSIFIED" in b for b in req(row, "bindings", where=BASE)), BASE)
        f("row_declared_missing", req(row, "missing", where=BASE), BASE)
        f("row_declared_fixture_have", req(row, "fixture_have", where=BASE), BASE)
        f("row_declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
        f("row_declared_next", req(row, "next", where=BASE), BASE)
        f("row_artifact_path_citations",
          sorted(set(re.findall(r"(?:analysis|tools|src|src_re|tests|config)/[\w./%-]+",
                                json.dumps(row)))), BASE)
        f("row_artifact_path_citation_count", len(g("row_artifact_path_citations")), BASE)

        # ---- 3. registry disposition, for contrast --------------------- #
        drow = next((r for r in req(debt, "rows", where=DEBT) if r.get("row_id") == RID),
                    None)
        if drow is None:
            raise SystemExit(f"STALE CITATION: {DEBT} no longer carries {RID}")
        f("registry_dimensions_met", req(drow, "counts", "met", where=DEBT), DEBT)
        f("registry_dimensions_remaining", req(drow, "counts", "remaining", where=DEBT),
          DEBT)
        f("registry_distinct_bases",
          sorted({d["basis"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
        f("registry_distinct_states",
          sorted({d["state"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
        f("registry_completion_state", req(drow, "completion_state", where=DEBT), DEBT)
        f("registry_campaign_id", req(drow, "campaign_id", where=DEBT), DEBT)
        f("registry_movie_count", req(drow, "movie_count", where=DEBT), DEBT)
        f("registry_capsule_count", req(drow, "capsule_count", where=DEBT), DEBT)
        f("registry_next_lane_reason", req(drow, "next_lane_reason", where=DEBT), DEBT)
        f("registry_family", req(drow, "family", where=DEBT), DEBT)

        qrow = next((r for r in req(queue, "rows", where=QUEUE) if r.get("row_id") == RID),
                    None)
        if qrow is None:
            raise SystemExit(f"STALE CITATION: {QUEUE} no longer carries {RID}")
        f("scheduler_eligible", req(qrow, "eligibility", "eligible", where=QUEUE), QUEUE)
        f("scheduler_ineligibility_reasons",
          req(qrow, "eligibility", "reasons", where=QUEUE), QUEUE)
        f("scheduler_sees_a_phase4_movie",
          req(qrow, "eligibility", "requirements", "case_sensitive_phase4_movie",
              where=QUEUE), QUEUE)
        f("scheduler_frontier_blocker_domains",
          req(qrow, "frontier_blocker_domains", where=QUEUE), QUEUE)
        f("scheduler_row_name", req(qrow, "name", where=QUEUE), QUEUE)
        f("scheduler_row_name_matches_baseline",
          req(qrow, "name", where=QUEUE) == g("row_name"), [QUEUE, BASE])
        f("scheduler_ownership_input_sha256",
          req(qrow, "static_ownership", "source_sha256", where=QUEUE), QUEUE)
        f("scheduler_ownership_input_is_current",
          g("scheduler_ownership_input_sha256") == sha256_file(ROOT / OWN), [QUEUE, OWN])
        f("scheduler_static_ownership_function_count",
          req(qrow, "static_ownership", "function_count", where=QUEUE), QUEUE)

        # ---- 4. ownership graph ---------------------------------------- #
        orow = req(own, "rows", RID, where=OWN)
        ofns = req(orow, "functions", where=OWN)
        f("ownership_function_citations", len(ofns), OWN)
        f("ownership_distinct_function_starts",
          sorted({x["function_start"] for x in ofns}), OWN)
        f("ownership_function_names", sorted({x.get("name") or "" for x in ofns}), OWN)
        f("ownership_overlay_space_functions",
          sum(1 for x in ofns if x["space"] != "resident"), OWN)
        f("ownership_functions_with_canon", sum(1 for x in ofns if x.get("canon")), OWN)
        ostate = req(orow, "state", where=OWN)
        f("ownership_state_addresses", [x["address"] for x in ostate], OWN)
        f("ownership_state_addresses_with_owner",
          sum(1 for x in ostate if x.get("semantic_ids")), OWN)
        f("ownership_row_name_matches_baseline",
          req(orow, "name", where=OWN) == g("row_name"), [OWN, BASE])
        f("ownership_graph_stores_an_image_field_for_region_a",
          any("image" in x for x in ostate) or any("image" in x for x in ofns), OWN)

        # ---- 5. NEW MEASUREMENT: stage identity pinned FROM BYTES ------- #
        pin = E.json(PIN)
        if req(pin, "row_id", where=PIN) != RID:
            raise SystemExit(f"{PIN} is not this row's scan")
        if as_int(req(pin, "declared_load_base", where=PIN)) != region_a:
            raise SystemExit(f"{RID}: the identity pin scanned a load base the overlay "
                             "registry does not declare")
        if req(pin, "region_length", where=PIN) != region_b - region_a:
            raise SystemExit(f"{RID}: the identity pin scanned a region length the "
                             "overlay registry does not declare")
        # the C scan must decode exactly the instructions the shared binding pins,
        # and must have READ (not decoded) exactly the two tables it names -- an
        # address quoted as a table must not silently become an instruction.
        pin_pcs = {d["pc"].lower() for d in req(pin, "decoded_instructions", where=PIN)}
        law_pcs_l = {p.lower() for p in F["shared_binding_arithmetic_law_pcs"]}
        missing_pcs = sorted(law_pcs_l - pin_pcs)
        if missing_pcs:
            raise SystemExit(f"{RID}: the identity pin did not decode the arithmetic-law "
                             f"instruction(s) the shared binding artifact pins: "
                             f"{missing_pcs}")
        bank_addrs = {p.lower() for p in F["shared_binding_sound_bank_pcs"]}
        pin_tables = {req(pin, "jump_table", "address", where=PIN).lower(),
                      req(pin, "sound_bank_string_table", "address", where=PIN).lower()}
        if not pin_tables <= bank_addrs:
            raise SystemExit(f"{RID}: the identity pin read tables the shared binding "
                             f"artifact does not name: {sorted(pin_tables - bank_addrs)}")
        if not (bank_addrs - pin_tables) <= pin_pcs:
            raise SystemExit(f"{RID}: the identity pin did not decode the sound-bank "
                             f"dispatch instruction(s) the shared binding names: "
                             f"{sorted((bank_addrs - pin_tables) - pin_pcs)}")
        f("identity_pin_inputs_match_registries", True, [PIN, OVLY, BIND])
        f("identity_pin_decoded_every_arithmetic_law_pc", sorted(law_pcs_l), [PIN, BIND])
        f("identity_pin_read_the_two_named_tables", sorted(pin_tables), [PIN, BIND])
        f("identity_pin_executable_sha256",
          req(pin, "executable", "sha256", where=PIN), PIN)
        f("identity_pin_progression_table_address",
          req(pin, "campaign_progression_table", "address", where=PIN), PIN)
        f("identity_pin_progression_table_scenes",
          req(pin, "campaign_progression_table", "scenes", where=PIN), PIN)
        f("identity_pin_scene_at_stage_ordinal",
          req(pin, "campaign_progression_table", "scene_at_this_stage_ordinal",
              where=PIN), PIN)
        f("identity_pin_ordinal_routes_to_declared_scene",
          req(pin, "campaign_progression_table", "matches_declared_scene", where=PIN), PIN)
        f("identity_pin_progression_table_agrees_with_e02",
          req(pin, "campaign_progression_table", "scenes", where=PIN)
          == F["e02_progression_table_scenes"], [PIN, E02])
        f("identity_pin_decoded_instructions",
          {d["pc"]: d["decoded"] for d in req(pin, "decoded_instructions", where=PIN)},
          PIN)
        f("identity_pin_sound_bank_prefix",
          req(pin, "sound_bank_string_table", "prefix_for_this_scene", where=PIN), PIN)
        f("identity_pin_sound_bank_index",
          req(pin, "sound_bank_string_table", "bank_index_for_this_scene", where=PIN), PIN)
        f("identity_pin_jump_table_entry_for_scene",
          req(pin, "jump_table", "entry_for_declared_scene", where=PIN), PIN)
        f("identity_pin_jump_table_distinct_entries",
          req(pin, "jump_table", "distinct_entries", where=PIN), PIN)
        prams = req(pin, "rams", where=PIN)
        f("identity_pin_fixtures_scanned", len(prams), PIN)
        f("identity_pin_fixture_scene_ids", [r["scene_id"] for r in prams], PIN)
        f("identity_pin_all_fixtures_are_this_scene",
          all(req(r, "scene_id_matches_declared", where=PIN) for r in prams), PIN)
        f("identity_pin_all_fixtures_slot_resolves",
          all(req(r, "slot_resolves_to_scene_id", where=PIN) for r in prams), PIN)
        f("identity_pin_fixture_slot_indexes",
          [r["scene_slot_index"] for r in prams], PIN)
        f("identity_pin_images_scanned", req(pin, "images_scanned", where=PIN), PIN)
        f("identity_pin_images_argmax_in_every_ram",
          req(pin, "images_argmax_in_every_ram", where=PIN), PIN)
        f("identity_pin_images_with_stable_declared_base",
          req(pin, "images_with_stable_declared_base", where=PIN), PIN)
        f("identity_pin_unique", req(pin, "unique_pin", where=PIN), PIN)
        f("identity_pin_result", req(pin, "result", where=PIN), PIN)
        f("identity_pin_file", req(pin, "unique_pin_file", where=PIN), PIN)
        f("identity_pin_sha1", req(pin, "unique_pin_sha1", where=PIN), PIN)
        f("identity_pin_sha256", req(pin, "unique_pin_sha256", where=PIN), PIN)
        f("identity_pin_size", req(pin, "unique_pin_size", where=PIN), PIN)
        f("identity_pin_extent", req(pin, "pinned_extent", where=PIN), PIN)
        f("identity_pin_nontrivial_pct",
          req(pin, "first_ram_pin_nontrivial_pct", where=PIN), PIN)
        f("identity_pin_runner_up", req(pin, "first_ram_runner_up", where=PIN), PIN)
        f("identity_pin_runner_up_pct",
          req(pin, "first_ram_runner_up_nontrivial_pct", where=PIN), PIN)
        if not g("identity_pin_unique"):
            raise SystemExit(f"{RID}: overlay residency is AMBIGUOUS; no overlay claim "
                             "may be made and this assessment must not be emitted as if "
                             "one could")
        f("identity_pin_agrees_with_census_overlay_name",
          Path(g("identity_pin_file")).stem == g("census_overlay_name"), [PIN, CENSUS])
        pimages = req(pin, "images", where=PIN)
        wanderers = sorted(im["path"] for im in pimages
                           if req(im, "per_ram", 0, "anchor_base_agreeing", where=PIN) >= 1
                           and not req(im, "stable_anchor_base_equals_declared",
                                       where=PIN))
        f("identity_pin_images_with_anchor_hits_but_no_stable_base", len(wanderers), PIN)
        f("identity_pin_images_with_anchor_hits_but_no_stable_base_paths", wanderers, PIN)
        diff = req(pin, "cross_fixture_diff", where=PIN)
        f("cross_fixture_region_a_differing_bytes",
          req(diff, "region_a_differing_bytes", where=PIN), PIN)
        f("cross_fixture_differing_inside_pinned_image",
          req(diff, "region_a_differing_inside_pinned_image", where=PIN), PIN)
        f("cross_fixture_differing_beyond_pinned_image",
          req(diff, "region_a_differing_beyond_pinned_image", where=PIN), PIN)
        f("cross_fixture_whole_ram_differing_words",
          req(diff, "whole_ram_differing_words", where=PIN), PIN)
        f("cross_fixture_whole_ram_words", req(diff, "whole_ram_words", where=PIN), PIN)
        nwords = req(pin, "named_words", where=PIN)
        f("named_overlay_words", [w["addr"] for w in nwords], PIN)
        f("named_overlay_words_count", req(pin, "named_words_count", where=PIN), PIN)
        f("named_overlay_words_inside_pinned_image",
          req(pin, "named_words_inside_pinned_image", where=PIN), PIN)
        f("named_overlay_words_zero_on_disc",
          req(pin, "named_words_zero_in_disc_image", where=PIN), PIN)
        f("named_overlay_words_varying_across_fixtures",
          req(pin, "named_words_varying_across_fixtures", where=PIN), PIN)
        f("named_overlay_word_values", {w["addr"]: w["values"] for w in nwords}, PIN)
        pclaims = req(pin, "claimed_ranges", where=PIN)
        f("claimed_ranges_checked", req(pin, "claimed_ranges_count", where=PIN), PIN)
        f("claimed_ranges_confirmed_byte_identical",
          req(pin, "claimed_ranges_confirmed_in_pinned_image", where=PIN), PIN)
        f("claimed_ranges_all_inside_pinned_extent",
          all(req(c, "inside_pinned_image_extent", where=PIN) for c in pclaims), PIN)
        f("claimed_ranges_not_byte_identical",
          sorted(c["name"] for c in pclaims
                 if not req(c, "ram_equals_pinned_disc_image_in_every_fixture",
                            where=PIN)), PIN)

        pin_lo = as_int(g("identity_pin_extent")[0])
        pin_hi = as_int(g("identity_pin_extent")[1])

        # the C scan's claimed ranges must be exactly the census's function
        # partition for THIS overlay (plus any extra artifact claims), or the two
        # have drifted apart and the numbers above stop meaning anything.
        ovl_name = g("census_overlay_name")
        census_fns = [x for x in req(fnj, "functions", where=FN)
                      if x.get("overlay") == ovl_name]
        if not census_fns:
            raise SystemExit(f"STALE CITATION: {FN} no longer censuses {ovl_name}")
        census_ranges = {(as_int(x["start"]), as_int(x["end"])) for x in census_fns}
        scanned_ranges = {(as_int(c["start"]), as_int(c["end"])) for c in pclaims}
        if not census_ranges <= scanned_ranges:
            raise SystemExit(
                f"{RID}: the identity pin no longer covers every censused function of "
                f"{ovl_name}: missing "
                f"{sorted(hex(a) for a, _ in census_ranges - scanned_ranges)}")
        f("overlay_functions_in_census", len(census_fns), FN)
        f("overlay_function_names_in_census",
          sorted(x.get("name") or f"0x{as_int(x['start']):08X}" for x in census_fns), FN)
        f("overlay_functions_named_in_census", sum(1 for x in census_fns if x.get("name")),
          FN)
        f("overlay_census_functions_all_inside_pinned_extent",
          all(pin_lo <= a and b <= pin_hi for a, b in census_ranges), [FN, PIN])
        ovl_syms = req(syms, "overlays", ovl_name, where=SYMS)
        f("overlay_symbol_entries", len(ovl_syms), SYMS)
        f("overlay_symbol_tiers", sorted({v["tier"] for v in ovl_syms.values()}), SYMS)
        f("overlay_symbols_proven",
          sorted(k for k, v in ovl_syms.items() if v["tier"] == "proven"), SYMS)
        f("overlay_symbols_resting_on_a_name_assumed_dynamic_tag",
          sorted(k for k, v in ovl_syms.items()
                 if any(str(x).startswith("dynamic:") for x in v.get("evidence", []))),
          SYMS)

        # ---- 6. defect (b): registry collision against THIS extent ------ #
        f("semantic_entries_inside_this_rows_overlay_extent",
          sorted(f"0x{a:08X}" for a in sem_addrs if pin_lo <= a < pin_hi), [SEM, PIN])
        f("row_state_addresses_registered_in_semantic_state",
          sum(1 for a in g("ownership_state_addresses") if as_int(a) in sem_addrs),
          [SEM, OWN])

        # ---- 7. source closure: BOTH registries, plus the src_re tree ---- #
        gov_resident = sorted({as_int(a) for a in F["shared_binding_arithmetic_law_pcs"]}
                              | {as_int(a) for a in F["shared_binding_sound_bank_pcs"]}
                              | {as_int(a) for a in g("ownership_state_addresses")}
                              | {as_int(x["function_start"]) for x
                                 in req(orow, "functions", where=OWN)})
        resolved, unresolved = {}, []
        for a in gov_resident:
            src = next((s for lo, hi, s in seg_units if lo <= a < hi), None)
            (resolved.setdefault(src, []).append(f"0x{a:08X}") if src
             else unresolved.append(f"0x{a:08X}"))
        f("governing_resident_addresses", len(gov_resident), [BIND, OWN])
        f("governing_resident_build_units", sorted(resolved), SEG)
        f("governing_resident_units_matching_c",
          len([s for s in resolved if s.startswith("src/")]), SEG)
        f("governing_resident_units_hand_asm",
          len([s for s in resolved if s.startswith("asm/")]), SEG)
        f("governing_resident_addresses_outside_any_build_unit", unresolved, SEG)
        ovl_entry = req(ovly, "overlays", where=OVLY).get(ovl_name)
        f("overlay_has_a_build_registry_entry", ovl_entry is not None, OVLY)
        f("overlay_code_functions_total",
          req(ovld, "per_overlay_totals", ovl_name, where=OVLD), OVLD)
        ovl_results = [r for r in req(ovld, "results", where=OVLD)
                       if r["overlay"] == ovl_name]
        f("overlay_matched_functions",
          sum(req(r, "matched_functions", where=OVLD) for r in ovl_results), OVLD)
        f("overlay_rebuild_validated",
          bool(ovl_results) and all(req(r, "validated", where=OVLD) for r in ovl_results),
          OVLD)
        f("overlay_rebuilt_sha1_equals_blob_sha1",
          bool(ovl_results) and all(req(r, "rebuilt_sha1", where=OVLD)
                                    == req(r, "sha1", where=OVLD) for r in ovl_results),
          OVLD)
        f("overlay_build_registry_sha1_equals_byte_pinned_image",
          bool(ovl_entry) and req(ovl_entry, "sha1", where=OVLY) == g("identity_pin_sha1"),
          [OVLY, PIN])
        matched_sources = sorted(req(a2, "source", where=OVLD)
                                 for r in ovl_results
                                 for a2 in req(r, "attempted", where=OVLD))
        f("overlay_matched_sources", matched_sources, OVLD)
        if cfg["byte_matched_c"]:
            if cfg["byte_matched_c"] not in matched_sources:
                raise SystemExit(f"{RID}: {cfg['byte_matched_c']} is no longer the "
                                 "overlay track's matched source for this overlay")
            csrc = E.text(cfg["byte_matched_c"])
            decl = sorted({s.lower() for s in re.findall(r"g_(800b[0-9a-fA-F]{4})", csrc)})
            f("byte_matched_c_source", cfg["byte_matched_c"], cfg["byte_matched_c"])
            f("byte_matched_c_declared_words", [f"0x{s}" for s in decl],
              cfg["byte_matched_c"])
            f("byte_matched_c_nonzero_initializers",
              sorted(int(m) for m in re.findall(r"=\s*(\d+);", csrc) if int(m)),
              cfg["byte_matched_c"])
            if {a.lower() for a in g("named_overlay_words")} != {f"0x{s}" for s in decl}:
                raise SystemExit(
                    f"{RID}: the identity pin read overlay words the byte-matched C no "
                    f"longer declares: scanned={sorted(g('named_overlay_words'))} "
                    f"declared={sorted('0x' + s for s in decl)}")
            f("named_words_match_the_byte_matched_c", True, [PIN, cfg["byte_matched_c"]])
        else:
            f("byte_matched_c_source", None, OVLD)
        if cfg["semantic_c"]:
            stext = E.text(cfg["semantic_c"])
            f("semantic_c_source", cfg["semantic_c"], cfg["semantic_c"])
            f("semantic_c_declares_itself_not_a_build_input",
              "not a build input" in stext, cfg["semantic_c"])
            f("semantic_c_is_in_either_build_registry",
              any(cfg["semantic_c"] == s for _, _, s in seg_units)
              or cfg["semantic_c"] in matched_sources, [SEG, OVLD])
        else:
            f("semantic_c_source", None, CENSUS)

        # ---- 8. the stage itself: hazards, exits, actors ---------------- #
        lvl = req(e02_levels, SK, where=E02)
        f("stage_collision_container", req(lvl, "container", where=E02), E02)
        f("stage_e02_scene", req(lvl, "scene", where=E02), E02)
        f("stage_e02_scene_agrees_with_the_byte_pin",
          req(lvl, "scene", where=E02) == g("identity_pin_scene_at_stage_ordinal"),
          [E02, PIN])
        f("stage_e02_save_is_a_row_fixture",
          req(lvl, "save", where=E02) in g("row_declared_fixture_have"), [E02, BASE])
        f("stage_authored_collision_sectors", req(lvl, "authored_sectors", where=E02), E02)
        f("stage_runtime_collision_sectors", req(lvl, "runtime_sectors", where=E02), E02)
        f("stage_region_code_histogram", req(lvl, "code_histogram", where=E02), E02)
        f("stage_nonzero_sectors",
          [(x["sector"], x["code"]) for x in req(lvl, "nonzero_sectors", where=E02)], E02)
        f("stage_disc_vs_runtime_mismatches",
          len(req(lvl, "disc_vs_runtime_mismatches", where=E02)), E02)
        f("stage_has_an_exit_region_code",
          any(c in (2, 3) for _, c in g("stage_nonzero_sectors")), E02)
        # the disc directory named by this stage's ORDINAL belongs to which stage?
        dir_token = f"LEVEL{int(g('census_stage_ordinal')):02d}/"
        owners = sorted(k for k, v in e02_levels.items()
                        if req(v, "container", where=E02).startswith(dir_token))
        f("disc_directory_named_by_this_stages_ordinal", dir_token, CENSUS)
        f("stages_owning_that_disc_directory", owners, E02)
        f("this_row_owns_the_disc_directory_named_by_its_ordinal", SK in owners, E02)

        arec = req(act, "levels", SK, where=ACT)
        arecs = req(arec, "actor_records", where=ACT)
        bound_ids = {int(k) for k in req(act, "actor_ids_with_canon_binding", where=ACT)}
        f("stage_actor_records", len(arecs), ACT)
        f("stage_actor_ids", sorted({x["id"] for x in arecs}), ACT)
        f("stage_actor_ids_with_canon_binding",
          sorted({x["id"] for x in arecs} & bound_ids), ACT)
        f("stage_actor_ids_without_canon_binding",
          sorted({x["id"] for x in arecs} - bound_ids), ACT)
        f("actor_census_canon_binding_set_size", len(bound_ids), ACT)
        f("stage_actor_census_uses_a_row_fixture",
          req(arec, "save", where=ACT) in g("row_declared_fixture_have"), [ACT, BASE])
        f("stage_actor_census_cited_by_the_row",
          "phase1_kind_actor_census" in json.dumps(row), [BASE, ACT])

        srow = req(stageb, "stages", SK, where=STAGEB)
        f("stage_baseline_role", req(srow, "role", where=STAGEB), STAGEB)
        f("stage_baseline_stable_fields", len(req(srow, "stable_fields", where=STAGEB)),
          STAGEB)
        f("stage_baseline_volatile_fields",
          len(req(srow, "volatile_fields", where=STAGEB)), STAGEB)
        f("stage_baseline_uses_a_row_fixture",
          req(srow, "save", where=STAGEB) in g("row_declared_fixture_have"),
          [STAGEB, BASE])
        drow2 = req(death, "matrix", SK, where=DEATH)
        f("stage_death_observed", req(drow2, "death_observed", where=DEATH), DEATH)
        f("stage_death_respawn", req(drow2, "respawn", where=DEATH), DEATH)
        f("stage_death_laws",
          {k: req(drow2, k, where=DEATH) for k in
           ("law_lives_minus_1", "law_respawn_hp_4", "law_same_scene")}, DEATH)
        f("stage_death_records_tried", req(drow2, "records_tried", where=DEATH), DEATH)

        # ---- 9. the campaign completion oracle (natural, from boot) ----- #
        st = req(ostages, SK, where=ORACLE)
        f("oracle_movie", req(st, "movie", where=ORACLE), ORACLE)
        f("oracle_frames", req(st, "frames", where=ORACLE), ORACLE)
        f("oracle_target_scene", req(st, "target_scene", where=ORACLE), ORACLE)
        f("oracle_replay_accepted", req(st, "pristine_replay_accepted", where=ORACLE),
          ORACLE)
        f("oracle_entered_stage_frame", req(st, "entered_stage_frame", where=ORACLE),
          ORACLE)
        f("oracle_stage_exited", req(st, "stage_exited_by_movie_end", where=ORACLE), ORACLE)
        f("oracle_snapshot_fields",
          sorted(req(st, "last_in_stage", "snapshot", where=ORACLE)), ORACLE)
        f("oracle_last_in_stage_snapshot",
          req(st, "last_in_stage", "snapshot", where=ORACLE), ORACLE)
        f("oracle_scene_timeline_segments", len(req(st, "scene_timeline", where=ORACLE)),
          ORACLE)
        f("oracle_corroborates_the_byte_pinned_scene",
          req(st, "target_scene", where=ORACLE) == g("identity_pin_scene_at_stage_ordinal"),
          [ORACLE, PIN])
        f("oracle_cited_by_the_row", "phase2_completion_oracle" in json.dumps(row),
          [BASE, ORACLE])
        f("oracle_movie_is_centrally_pinned",
          req(st, "movie", where=ORACLE) in fixentries, [ORACLE, FIXSET])
        # the movie corpus's numbering is STAGE numbering -- proved, not assumed:
        # the oracle binds a LEVELnn-named movie to a target scene that is this
        # row's byte-pinned scene, while the disc directory of the same name is a
        # different stage entirely.
        f("movie_corpus_uses_stage_numbering_proof",
          {"oracle_movie": req(st, "movie", where=ORACLE),
           "target_scene": req(st, "target_scene", where=ORACLE),
           "byte_pinned_scene": g("identity_pin_scene_at_stage_ordinal"),
           "disc_dir_of_the_same_name_belongs_to": owners},
          [ORACLE, PIN, E02])

        # ---- 10. the movie corpus for this stage ------------------------ #
        tok = re.compile(cfg["movie_token"], re.I)
        name_tok = re.compile(cfg["stage_name_token"], re.I)
        token_mov = sorted(k for k in movies if tok.search(k))
        attributed = sorted({k for k in token_mov if name_tok.search(k)}
                            | {g("oracle_movie")}
                            | {k for k in token_mov if "/E10/" in k or "/E09/" in k})
        f("stage_movies_token_matched", len(token_mov), AUDIT)
        f("stage_movies_token_matched_paths", token_mov, AUDIT)
        f("stage_movies_attributed", len(attributed), [AUDIT, ORACLE])
        f("stage_movies_attributed_paths", attributed, [AUDIT, ORACLE])
        f("stage_movies_attribution_unverified",
          sorted(set(token_mov) - set(attributed)), [AUDIT, ORACLE])
        f("stage_movie_frames",
          {k: req(movies, k, "frames", where=AUDIT) for k in attributed}, AUDIT)
        f("stage_movies_under_phase4",
          sorted(k for k in attributed if k.startswith("movies/Phase4/")), AUDIT)
        f("stage_movies_under_phase4_interpreter",
          sorted(k for k in attributed if k.startswith("movies/Phase4/Interpreter/")),
          AUDIT)
        f("stage_movies_centrally_pinned",
          sum(1 for k in attributed if k in fixentries), FIXSET)
        f("stage_movies_bytes_match_pin",
          sum(1 for k in attributed
              if k in fixentries and (ROOT / k).exists()
              and sha256_file(ROOT / k) == fixentries[k]["sha256"]), FIXSET)
        f("stage_movies_declared_by_the_row",
          sorted(set(attributed) & set(g("row_declared_fixture_have"))), [AUDIT, BASE])
        f("stage_saves_pinned",
          len([k for k in saves if tok.search(k) or name_tok.search(k)]), AUDIT)
        crow3 = req(cov, "rows", RID, where=COV)
        f("row_coverage_status", req(crow3, "status", where=COV), COV)
        f("row_coverage_unaudited_fixtures", len(req(crow3, "unaudited_fixtures",
                                                     where=COV)), COV)
        f("row_coverage_non_pristine_fixtures",
          len(req(crow3, "non_pristine_fixtures", where=COV)), COV)

        # The F01 breadth corpus replayed this stage's operator runs at 60 Hz with
        # write watches. Two things are measured here: what it saw in this stage,
        # and -- because it reports writer PCs only as a UNION over levels -- how
        # many of those PCs land inside THIS row's byte-pinned overlay extent
        # without any image attribution. That is systemic defect (a) appearing
        # inside an artifact other rows already rely on.
        treq = req(breadth, "f01_transition_request_0x800823A0", where=BREADTH)
        per_level = req(treq, "per_level", where=BREADTH)
        bsess = sorted(k for k in per_level if tok.search(k) or name_tok.search(k))
        if not bsess:
            raise SystemExit(f"{RID}: {BREADTH} no longer replays this stage")
        f("f01_breadth_sessions_for_this_stage", bsess, BREADTH)
        f("f01_breadth_transition_values_seen_in_this_stage",
          {k: per_level[k] for k in bsess}, BREADTH)
        f("f01_breadth_transition_values_observed_campaign_wide",
          req(treq, "values_observed", where=BREADTH), BREADTH)
        all_writer_pcs = sorted({p for v in req(treq, "by_value", where=BREADTH).values()
                                 for p in req(v, "writer_pcs", where=BREADTH)})
        f("f01_breadth_transition_writer_pcs", all_writer_pcs, BREADTH)
        f("f01_breadth_writer_pcs_in_region_a",
          sorted(p for p in all_writer_pcs if region_a <= as_int(p) < region_b),
          [BREADTH, OVLY])
        f("f01_breadth_writer_pcs_inside_this_rows_pinned_extent",
          sorted(p for p in all_writer_pcs if pin_lo <= as_int(p) < pin_hi),
          [BREADTH, PIN])
        f("f01_breadth_reports_writer_pcs_per_level", False, BREADTH)

        # ---- 11. hazard evidence recorded on this stage by E10 ---------- #
        e10fx = [x for x in req(e10, "fixtures", where=E10)
                 if x["name"] in cfg["e10_fixtures"]]
        if len(e10fx) != len(cfg["e10_fixtures"]):
            raise SystemExit(f"{RID}: {E10} no longer carries this stage's hazard "
                             f"fixtures {cfg['e10_fixtures']}")
        f("e10_fixtures_for_this_stage", [x["name"] for x in e10fx], E10)
        f("e10_events_for_this_stage", {x["name"]: x["event"] for x in e10fx}, E10)
        f("e10_producer_classes_for_this_stage",
          {x["name"]: x["producer_class"] for x in e10fx}, E10)
        f("e10_damage_callers_for_this_stage", {x["name"]: x["caller"] for x in e10fx},
          E10)
        f("e10_results_for_this_stage", {x["name"]: x["result"] for x in e10fx}, E10)
        rev_mov = {v["sha256"]: k for k, v in movies.items()}
        rev_sav = {v["sha256"]: k for k, v in saves.items()}
        f("e10_cited_movie_hashes_present_in_todays_corpus",
          {x["name"]: rev_mov.get(x["movie_sha256"]) for x in e10fx}, [E10, AUDIT])
        f("e10_cited_start_state_hashes_present_in_todays_corpus",
          {x["name"]: rev_sav.get(x["state_sha256"]) for x in e10fx}, [E10, AUDIT])
        f("e10_hazard_evidence_cited_by_the_row",
          "e10" in json.dumps(row).lower(), [BASE, E10])

        # ---- 12. row-specific: the grain-gate campaign (F07 only) ------- #
        if cfg["gate_artifact"]:
            gg = E.json(cfg["gate_artifact"])
            GA = cfg["gate_artifact"]
            f("gate_campaign_state", req(gg, "campaign_state", where=GA), GA)
            f("gate_overlay_path",
              req(gg, "static_census", "city_overlay", "path", where=GA), GA)
            f("gate_overlay_sha256",
              req(gg, "static_census", "city_overlay", "sha256", where=GA), GA)
            f("gate_overlay_sha256_equals_byte_pinned_image",
              req(gg, "static_census", "city_overlay", "sha256", where=GA)
              == g("identity_pin_sha256"), [GA, PIN])
            f("gate_function_range",
              [req(gg, "static_census", "city_function", "start", where=GA),
               req(gg, "static_census", "city_function", "end_exclusive", where=GA)], GA)
            f("gate_function_pinned_words",
              {k: v["address"] for k, v in
               req(gg, "static_census", "city_function", "words", where=GA).items()}, GA)
            f("gate_function_pinned_word_count",
              len(req(gg, "static_census", "city_function", "words", where=GA)), GA)
            f("gate_law", req(gg, "static_census", "law", where=GA), GA)
            nat = [r for r in req(gg, "live", "natural_replays", where=GA)
                   if tok.search(r["fixture"]["path"])]
            f("gate_natural_replays_for_this_stage", len(nat), GA)
            f("gate_natural_replay_before_states",
              [r["before"]["city_gate_states"] for r in nat], GA)
            f("gate_natural_replay_after_states",
              [r["after"]["city_gate_states"] for r in nat], GA)
            f("gate_natural_replay_grain", [r["before"]["grain"] for r in nat], GA)
            f("gate_natural_replay_opens_a_gate",
              any(r["before"]["city_gate_states"] != r["after"]["city_gate_states"]
                  and 0 in r["after"]["city_gate_states"] for r in nat), GA)
            ctl = req(gg, "live", "city_threshold_controls", where=GA)
            f("gate_success_controls", len(ctl), GA)
            f("gate_success_requires_injection",
              all("mutation" in c for c in ctl), GA)
            f("gate_success_injection_addresses",
              sorted({c["mutation"]["address"] for c in ctl}), GA)
            f("gate_state_excluded_from_card_serialization",
              req(gg, "static_census", "card_serialization",
                  "excluded_overlay_state", where=GA), GA)
            f("gate_bounded_residuals", req(gg, "bounded_residuals", where=GA), GA)
            f("gate_campaign_cited_by_the_row",
              "grain_gates" in json.dumps(row), [BASE, GA])
            f("gate_addresses_inside_this_rows_pinned_extent",
              all(pin_lo <= as_int(req(w, "address", where=GA)) < pin_hi
                  for w in req(gg, "static_census", "city_function", "words",
                               where=GA).values()), [GA, PIN])
            f("gate_function_range_inside_this_rows_pinned_extent",
              pin_lo <= as_int(req(gg, "static_census", "city_function", "start",
                                   where=GA))
              and as_int(req(gg, "static_census", "city_function", "end_exclusive",
                             where=GA)) <= pin_hi, [GA, PIN])
        else:
            # measure the ABSENCE, so silence is not read as coverage
            gate_like = sorted(p.name for p in (ROOT / "analysis").glob("*.json")
                               if SK.split("_", 1)[1] in p.name.lower()
                               or RID.lower() in p.name.lower())
            f("row_named_analysis_artifacts", gate_like, CENSUS)
            f("row_named_analysis_artifact_count", len(gate_like), CENSUS)

        # ---- 13. registered gates that actually cover this stage --------- #
        needles = [SK, RID, g("identity_pin_file"), ovl_name]
        if cfg["gate_artifact"]:
            needles.append(cfg["gate_artifact"])
        gate_files = sorted(k for k, body in test_bodies.items()
                            if any(n in body for n in needles))
        for gf in gate_files:
            E.pin(gf)
        f("registered_gate_files_touching_this_stage", gate_files,
          gate_files or [CENSUS])
        f("registered_gate_files_naming_the_row_id",
          sorted(k for k, body in test_bodies.items() if RID in body),
          gate_files or [CENSUS])
        f("registered_gate_files_naming_the_pinned_overlay",
          sorted(k for k, body in test_bodies.items() if ovl_name in body),
          gate_files or [CENSUS])

        # ---- 14. c2 pre-outcome type authority --------------------------- #
        f("c2_row_types", [t["type"] for t in req(c2, "mapping", RID, "types", where=C2)],
          C2)
        f("c2_rows_sharing_this_type",
          sorted(set(sum((req(c2, "types_with_at_least_one_level", t, where=C2)
                          for t in g("c2_row_types")), []))), C2)
        f("c2_frozen_name_matches_this_row",
          req(c2, "mapping", RID, "frozen_name", where=C2) == g("row_name"), [C2, BASE])
        f("c2_session_name", req(c2, "mapping", RID, "session", where=C2), C2)

        # =============================================================== #
        #                 AUTHORED JUDGMENTS -- PER ROW                    #
        # =============================================================== #
        subject = ("the maze and the spike hazards that name the row, and whatever "
                   "completes the stage") if K == "f05" else \
                  ("the circus objective that names the row, plus the city enemies "
                   "and the grain-drop expiry the row asks about")
        exits = [x for x in g("stage_nonzero_sectors") if x[1] in (2, 3)]
        if K == "f05":
            never = (
                f"no artifact anywhere states what COMPLETES this stage. Its exit "
                f"SECTOR is known and gated by a registered pytest file "
                f"({exits}, sector/code pairs from the disc census), but nothing says "
                f"what -- if anything -- must happen before standing on it. There is no "
                f"maze analysis for scene "
                f"{g('identity_pin_scene_at_stage_ordinal')} of any kind; no spike ACTOR "
                f"is identified anywhere in the {g('stage_actor_records')}-record roster "
                f"({len(g('stage_actor_ids_without_canon_binding'))} of "
                f"{len(g('stage_actor_ids'))} ids here are outside the actor census's own "
                f"canon-binding set, which names only "
                f"{g('actor_census_canon_binding_set_size')} ids campaign-wide); and "
                f"no objective counter, flag or trigger has ever been looked for")
        else:
            never = (
                f"no artifact anywhere connects a circus member, performer or marker to a "
                f"counter, trigger or actor id in scene "
                f"{g('identity_pin_scene_at_stage_ordinal')}. The grain GATES are solved "
                f"and a completion HANDLER is located inside the byte-pinned overlay, but "
                f"what the player must DO to reach it is unstated -- and this stage "
                f"authors no exit region code at all "
                f"(has_exit_code={g('stage_has_an_exit_region_code')}), so its exit is "
                f"overlay-owned and unproven. The row's declared 'enemy grain drops may "
                f"expire' has zero coverage anywhere. "
                f"{len(g('stage_actor_ids_without_canon_binding'))} of "
                f"{len(g('stage_actor_ids'))} actor ids in this stage sit outside the "
                f"actor census's own canon-binding set (which names "
                f"{g('actor_census_canon_binding_set_size')} ids campaign-wide), so the "
                f"'city-enemy census' the row asks for exists only as an unlabelled id "
                f"histogram")

        gate_note = (f"{len(g('registered_gate_files_touching_this_stage'))} registered "
                     f"pytest file(s) touch this stage "
                     f"({g('registered_gate_files_touching_this_stage')}), "
                     f"{len(g('registered_gate_files_naming_the_row_id'))} name the ROW")

        dims: dict[str, dict] = {}

        dims["durable_evidence"] = {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {g('census_durable_fraction')} in "
                     f"{CENSUS} -- {g('census_durable_reason')}. This assessment fails "
                     f"loudly if that measurement moves off 'met'. Re-confirmed "
                     f"independently here: {g('row_external_fixtures_bytes_match_pin')} of "
                     f"{g('row_external_fixture_count')} declared external fixtures still "
                     f"byte-match their central pin, and they are load-bearing far beyond "
                     f"this row ({g('row_external_fixture_consumer_count')} registered "
                     f"consumers). Coverage audit is clean: "
                     f"{g('row_coverage_status')}, {g('row_coverage_unaudited_fixtures')} "
                     f"unaudited and {g('row_coverage_non_pristine_fixtures')} "
                     f"non-pristine. NEW here, regenerability now exists where it did "
                     f"not: {PINC} rebuilds this row's identity from the same fixtures "
                     f"with no emulator, and {gate_note}",
            "gap": f"the carried measurement covers FIXTURE INTACTNESS of the two saves "
                   f"the row happens to declare. It says nothing about coverage, and the "
                   f"declared set is a small fraction of what exists: "
                   f"{g('stage_movies_attributed')} movies for this stage are pinned and "
                   f"byte-matching ({g('stage_movies_bytes_match_pin')} of "
                   f"{g('stage_movies_centrally_pinned')} verified here), of which the "
                   f"row declares {g('stage_movies_declared_by_the_row')}. Until today "
                   f"this row had produced zero artifacts of its own: the census credits "
                   f"it {len(g('census_analysis_artifacts'))} analysis artifact "
                   f"({g('census_analysis_artifacts')}), which is a SHARED one, "
                   f"{len(g('census_vault_pages'))} vault pages and "
                   f"{len(g('census_source_files'))} source files",
        }

        # ---------------- original_oracle ------------------------------- #
        if K == "f05":
            oracle_state = "partial"
            oracle_basis = (
                f"the stage's IDENTITY is now asserted against the original game with "
                f"zero injection and no emulator: both declared fixtures read scene id "
                f"{g('identity_pin_fixture_scene_ids')} straight out of their .sav "
                f"containers, their scene-slot index "
                f"{g('identity_pin_fixture_slot_indexes')} resolves through the campaign "
                f"progression table at {g('identity_pin_progression_table_address')} back "
                f"to the same id (all fixtures: "
                f"{g('identity_pin_all_fixtures_slot_resolves')}), and the resident "
                f"overlay is uniquely {g('identity_pin_file')} at "
                f"{g('identity_pin_nontrivial_pct')}% non-trivial agreement against "
                f"{g('identity_pin_runner_up_pct')}% for the runner-up "
                f"({g('identity_pin_runner_up')}) over "
                f"{g('identity_pin_images_scanned')} candidate images. Natural BEHAVIOUR "
                f"of this stage is asserted from a cold boot by an artifact the row does "
                f"not cite ({g('oracle_cited_by_the_row')}): {g('oracle_movie')}, "
                f"{g('oracle_frames')} frames, target scene {g('oracle_target_scene')} "
                f"(corroborates the byte pin: "
                f"{g('oracle_corroborates_the_byte_pinned_scene')}), entered at frame "
                f"{g('oracle_entered_stage_frame')}, exited by end "
                f"({g('oracle_stage_exited')}), accepted "
                f"({g('oracle_replay_accepted')}). "
                f"{len(g('e10_fixtures_for_this_stage'))} hazard fixtures in this stage "
                f"are asserted on natural capsule replays by {F['e10_row']}: "
                f"{g('e10_events_for_this_stage')} with callers "
                f"{g('e10_damage_callers_for_this_stage')}")
            oracle_gap = (
                f"none of that is an oracle for this row's OBJECTIVE, and none of it is "
                f"this row's. The identity result is an IDENTITY claim; the completion "
                f"oracle asserts entry and exit and never an objective event; the hazard "
                f"assertions belong to {F['e10_row']} (status "
                f"'{F['e10_status']}'), the row does not cite them "
                f"({g('e10_hazard_evidence_cited_by_the_row')}), and their capsules are "
                f"external with the cited movie hash no longer resolving in today's "
                f"corpus ({g('e10_cited_movie_hashes_present_in_todays_corpus')}) even "
                f"though the cited start states do "
                f"({g('e10_cited_start_state_hashes_present_in_todays_corpus')}). "
                f"{never}. The census triage says "
                f"'{g('census_triage')['original_oracle']}', and measured against the "
                f"row's own artifacts that is exactly right")
        else:
            oracle_state = "partial"
            oracle_basis = (
                f"identity first, with zero injection and no emulator: both declared "
                f"fixtures read scene id {g('identity_pin_fixture_scene_ids')} out of "
                f"their .sav containers, slot "
                f"{g('identity_pin_fixture_slot_indexes')} resolves through the "
                f"progression table back to the same id, and the resident overlay is "
                f"uniquely {g('identity_pin_file')} "
                f"({g('identity_pin_nontrivial_pct')}% vs "
                f"{g('identity_pin_runner_up_pct')}%). Natural stage behaviour from a "
                f"cold boot exists and is uncited by the row "
                f"({g('oracle_cited_by_the_row')}): {g('oracle_movie')}, "
                f"{g('oracle_frames')} frames, scene {g('oracle_target_scene')}, entered "
                f"{g('oracle_entered_stage_frame')}, exited by end "
                f"({g('oracle_stage_exited')}). Uniquely among these two rows there is "
                f"also a MECHANISM asserted inside this stage on natural replays: the "
                f"grain-gate campaign ({g('gate_campaign_state')}) recorded "
                f"{g('gate_natural_replays_for_this_stage')} natural replays in scene 4 "
                f"at grain {g('gate_natural_replay_grain')} with gate states "
                f"{g('gate_natural_replay_before_states')} -> "
                f"{g('gate_natural_replay_after_states')}, and this assessment confirms "
                f"by bytes that its function lives in THIS row's pinned image "
                f"(its declared overlay sha256 equals the byte-pinned image's: "
                f"{g('gate_overlay_sha256_equals_byte_pinned_image')}; all "
                f"{g('gate_function_pinned_word_count')} pinned instruction words fall "
                f"inside the pinned extent: "
                f"{g('gate_addresses_inside_this_rows_pinned_extent')}). The row's own "
                f"two fixtures supply the endpoints of that mechanism's state array: "
                f"{g('named_overlay_word_values')}")
            oracle_gap = (
                f"the natural arm proves DENIAL only. Every recorded natural replay ends "
                f"with the gate still closed "
                f"(opens_a_gate={g('gate_natural_replay_opens_a_gate')}); the "
                f"{g('gate_success_controls')} successful openings are all produced by "
                f"INJECTION into {g('gate_success_injection_addresses')} "
                f"(requires_injection={g('gate_success_requires_injection')}), which is "
                f"precisely what this bar excludes. And gates are not the objective: "
                f"{never}. The hazard assertions for this stage belong to "
                f"{F['e10_row']} and are uncited by the row "
                f"({g('e10_hazard_evidence_cited_by_the_row')}); the gate campaign is "
                f"uncited too ({g('gate_campaign_cited_by_the_row')}). No assertion "
                f"anywhere is keyed to {subject}")

        dims["original_oracle"] = {
            "state": oracle_state,
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": oracle_basis,
            "gap": oracle_gap,
        }

        # ---------------- complete_frontier ----------------------------- #
        if K == "f05":
            cf_state = "not_met"
            cf_basis = (
                f"what IS enumerated is the LOADER's, and it is another row's: the shared "
                f"binding closes the id->directory map over all "
                f"{F['shared_binding_scene_ids_mapped']} ids and this assessment "
                f"re-decodes its arithmetic from the pristine image "
                f"({g('identity_pin_decoded_instructions')}), with the dispatcher's jump "
                f"table read out in full ({g('identity_pin_jump_table_distinct_entries')} "
                f"distinct entries; this scene's entry "
                f"{g('identity_pin_jump_table_entry_for_scene')}). NEW and genuinely on "
                f"this row's frontier: the pinned overlay's whole code partition is now "
                f"enumerated AND proved to be this file -- "
                f"{g('overlay_functions_in_census')} censused functions, all inside the "
                f"pinned extent ({g('overlay_census_functions_all_inside_pinned_extent')}"
                f"), {g('claimed_ranges_confirmed_byte_identical')} of "
                f"{g('claimed_ranges_checked')} ranges byte-identical between RAM and the "
                f"pinned disc image in every fixture "
                f"({g('overlay_function_names_in_census')})")
            cf_gap = (
                f"that is a CANDIDATE SET, not a frontier, and the bar asks for the "
                f"relevant one. Nothing enumerates callers, callees, callbacks or "
                f"indirect tables for anything this row is named for. The ownership graph "
                f"resolves the row to {len(g('ownership_distinct_function_starts'))} "
                f"distinct function ({g('ownership_distinct_function_starts')}) -- the "
                f"shared loader dispatcher, identical to the sibling row's entry, with "
                f"{g('ownership_overlay_space_functions')} overlay-space functions and "
                f"{g('ownership_state_addresses_with_owner')} of "
                f"{len(g('ownership_state_addresses'))} state addresses owned. Of the "
                f"{g('overlay_symbol_entries')} symbols in the pinned overlay only "
                f"{len(g('overlay_symbols_proven'))} is tier 'proven' "
                f"({g('overlay_symbols_proven')}); the rest are name-inferred, and "
                f"{len(g('overlay_symbols_resting_on_a_name_assumed_dynamic_tag'))} rest "
                f"on a 'dynamic:<overlay>' tag that the shared load base cannot justify. "
                f"No residual is explicitly bounded anywhere: the row's whole statement "
                f"of what is unresolved is '{g('row_declared_missing')}'")
        else:
            cf_state = "partial"
            cf_basis = (
                f"for ONE mechanism in this stage the frontier is enumerated and closed, "
                f"and this assessment proves it belongs to this row's image rather than "
                f"to an address in a shared window: the grain-gate function "
                f"{g('gate_function_range')} with "
                f"{g('gate_function_pinned_word_count')} instruction words pinned by "
                f"address and opcode, its 3-entry state array, its threshold law "
                f"({g('gate_law')['city_thresholds']}), denial sfx "
                f"{g('gate_law')['denial_sfx']} and cooldown rule -- all inside the "
                f"byte-pinned extent {g('identity_pin_extent')} of "
                f"{g('identity_pin_file')}, whose sha256 the gate artifact independently "
                f"declares ({g('gate_overlay_sha256_equals_byte_pinned_image')}). The "
                f"whole overlay code partition is enumerated too: "
                f"{g('overlay_functions_in_census')} functions "
                f"({g('overlay_function_names_in_census')}), all inside the extent, "
                f"{g('claimed_ranges_confirmed_byte_identical')} of "
                f"{g('claimed_ranges_checked')} checked ranges byte-identical between RAM "
                f"and disc in both fixtures. The loader frontier is closed over all "
                f"{F['shared_binding_scene_ids_mapped']} ids and re-decoded here "
                f"({g('identity_pin_decoded_instructions')})")
            cf_gap = (
                f"the enumerated frontier is the GATE's and the LOADER's, not the "
                f"OBJECTIVE's. {never}. `level04_complete_handler` is inside the pinned "
                f"extent and byte-confirmed, but nothing enumerates what SETS the "
                f"condition it runs on -- no callers, no callbacks, no indirect table is "
                f"enumerated for the objective, and the ownership graph still resolves "
                f"this row to {len(g('ownership_distinct_function_starts'))} distinct "
                f"function ({g('ownership_distinct_function_starts')}), the shared loader "
                f"dispatcher, with {g('ownership_overlay_space_functions')} overlay-space "
                f"functions. Of {g('overlay_symbol_entries')} overlay symbols, "
                f"{len(g('overlay_symbols_proven'))} are tier 'proven' and "
                f"{len(g('overlay_symbols_resting_on_a_name_assumed_dynamic_tag'))} rest "
                f"on a 'dynamic:<overlay>' tag the shared load base cannot justify -- "
                f"including the completion handler, and including "
                f"'level_audio_handler', which the gate campaign shows is the grain-gate "
                f"function. The row's own statement of the residual is "
                f"'{g('row_declared_missing')}' -- not an enumeration and not a bound")

        dims["complete_frontier"] = {
            "state": cf_state,
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": cf_basis,
            "gap": cf_gap,
        }

        # ---------------- typed_state ----------------------------------- #
        if K == "f05":
            ts_state = "not_met"
            ts_basis = (
                f"the only typed thing in this row is the loader's scene id, which is "
                f"registered with a declared range and is shared with every other stage "
                f"row. NEW here and genuinely this row's: "
                f"{g('named_overlay_words_count')} overlay-local words are declared by "
                f"the one byte-matched C function in the pinned image "
                f"({g('byte_matched_c_source')}, initializers "
                f"{g('byte_matched_c_nonzero_initializers')}), all "
                f"{g('named_overlay_words_inside_pinned_image')} inside the pinned "
                f"extent and all {g('named_overlay_words_zero_on_disc')} zero on disc, "
                f"so they are runtime state living inside the image. Measured across the "
                f"row's own two fixtures: {g('named_overlay_word_values')}")
            ts_gap = (
                f"that is an ENUMERATION of four words, not a typing of any of them. "
                f"{g('named_overlay_words_varying_across_fixtures')} of "
                f"{g('named_overlay_words_count')} vary and their value domain is "
                f"unbounded -- {g('identity_pin_fixtures_scanned')} samples cannot "
                f"separate a counter from a timer, and "
                f"the initializer the byte-matched C writes "
                f"({g('byte_matched_c_nonzero_initializers')}) appears in NEITHER "
                f"fixture, which is itself unexplained. Nothing else is typed: "
                f"{g('row_state_addresses_registered_in_semantic_state')} of "
                f"{len(g('ownership_state_addresses'))} cited state addresses appear in "
                f"config/semantic_state.yaml's {F['semantic_state_entries_total']} "
                f"entries, and no record type, no field and no invariant is registered "
                f"for anything in this stage's overlay")
        else:
            ts_state = "partial"
            ts_basis = (
                f"one state array in this stage is fully typed with an exhaustive domain, "
                f"by the grain-gate campaign and confirmed here to be inside this row's "
                f"image: {g('gate_law')['city_gate_count']} x s32 at the addresses "
                f"{g('named_overlay_words')[1:]}, closed sentinel "
                f"{g('gate_law')['city_closed']}, open countdown start "
                f"{g('gate_law')['city_open_countdown_start']}, terminal 0, thresholds "
                f"{g('gate_law')['city_thresholds']} -- plus the denial countdown at "
                f"{g('named_overlay_words')[0]} with rule "
                f"'{g('gate_law')['denial_cooldown_rule']}'. This assessment adds the "
                f"lifecycle endpoints from the row's OWN fixtures, which no artifact had "
                f"read: {g('named_overlay_word_values')} -- all-closed in the mid-stage "
                f"save and all-terminal in the ending save, with all "
                f"{g('named_overlay_words_zero_on_disc')} words zero on disc. The array "
                f"is also proved NOT card-serialized "
                f"({g('gate_state_excluded_from_card_serialization')})")
            ts_gap = (
                f"one typed array is not the row's state. Nothing types anything to do "
                f"with {subject}: no objective counter, no performer/circus state, no "
                f"goo or enemy state field is registered or bounded anywhere. "
                f"{g('row_state_addresses_registered_in_semantic_state')} of "
                f"{len(g('ownership_state_addresses'))} cited state addresses are in "
                f"config/semantic_state.yaml, and "
                f"{len(g('semantic_entries_inside_this_rows_overlay_extent'))} of its "
                f"{F['semantic_state_entries_total']} entries fall inside this row's "
                f"pinned extent -- the typed gate array is registered in the E09 "
                f"artifact, not in the shared registry other rows read. The cross-fixture "
                f"diff bounds where the rest could be: "
                f"{g('cross_fixture_differing_inside_pinned_image')} bytes differ inside "
                f"the pinned image and {g('cross_fixture_whole_ram_differing_words')} of "
                f"{g('cross_fixture_whole_ram_words')} RAM words differ overall -- a "
                f"bound, not a typing")

        dims["typed_state"] = {
            "state": ts_state,
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": ts_basis,
            "gap": ts_gap,
        }

        # ---------------- lifecycle -------------------------------------- #
        if K == "f05":
            lc_state = "partial"
            lc_basis = (
                f"three phases are evidenced, all for the stage CONTAINER and all by "
                f"artifacts this row does not cite. LOAD: the overlay's arrival at the "
                f"shared base is proved by bytes in both fixtures, and its "
                f"INITIALIZATION is proved from byte-matched source "
                f"({g('named_overlay_words_count')} words, "
                f"{g('named_overlay_words_zero_on_disc')} zero on disc). COLD BOOT / "
                f"ENTRY / EXIT: the completion oracle enters scene "
                f"{g('oracle_target_scene')} at frame "
                f"{g('oracle_entered_stage_frame')} and exits by movie end. DEATH AND "
                f"RESPAWN in this stage is separately observed "
                f"({g('stage_death_observed')}, respawn {g('stage_death_respawn')}, laws "
                f"{g('stage_death_laws')})")
            lc_gap = (
                f"3 of the bar's {len(LIFECYCLE_BAR.split('/'))} phases, and zero "
                f"phases of anything this row is named for. First use, repeated use, "
                f"exhaustion, retirement and reuse of the "
                f"spike hazard or of any objective mechanism have no evidence of any "
                f"kind, because no mechanism has been identified that could have a "
                f"lifecycle. The {g('identity_pin_fixtures_scanned')} fixtures are "
                f"independent snapshots, not a "
                f"progression, and no per-phase claim map is registered for this row the "
                f"way F01 has one. Scored on the same footing as the F08 sibling, whose "
                f"lifecycle was judged partial on load + cold-boot entry/exit alone")
        else:
            lc_state = "partial"
            lc_basis = (
                f"for the grain-gate mechanism the lifecycle is unusually well covered "
                f"and this assessment closes one more phase of it from the row's own "
                f"fixtures. LOAD + INIT: all {g('named_overlay_words_count')} tracked "
                f"words are zero on disc and the image is byte-resident in both fixtures. "
                f"FIRST USE and REPEATED USE (denial arm): "
                f"{g('gate_natural_replays_for_this_stage')} natural replays at grain "
                f"{g('gate_natural_replay_grain')}. TERMINAL STATE: measured here for the "
                f"first time -- the row's mid-stage save holds "
                f"{g('named_overlay_word_values')[g('named_overlay_words')[1]]} and its "
                f"ending save holds the terminal value, so the row's own two fixtures "
                f"bracket the array from all-closed to all-open. RETIREMENT/PERSISTENCE: "
                f"the array is proved excluded from card serialization "
                f"({g('gate_state_excluded_from_card_serialization')}). DEATH/RESPAWN in "
                f"this stage is observed ({g('stage_death_observed')}, "
                f"{g('stage_death_laws')})")
            lc_gap = (
                f"every one of those phases belongs to the GATE, which is a progression "
                f"gate and not the row's objective; the transition from closed to open is "
                f"still only evidenced under injection. For {subject} no phase is "
                f"evidenced at all. No per-phase claim map is registered for this row, "
                f"and the exhaustion/reuse phases are not defined for a mechanism nobody "
                f"has identified")

        dims["lifecycle"] = {
            "state": lc_state,
            "written_bar": LIFECYCLE_BAR,
            "basis": lc_basis,
            "gap": lc_gap,
        }

        # ---------------- cross_system_behavior --------------------------- #
        dims["cross_system_behavior"] = {
            "state": "not_met",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"no artifact belonging to this row exercises any combination; the "
                     f"census records runtime trace evidence "
                     f"{g('census_has_runtime_trace_evidence')} and static code evidence "
                     f"{g('census_has_static_code_evidence')} for this row, the registry "
                     f"records {g('registry_capsule_count')} capsules and "
                     f"{g('registry_movie_count')} movies, and the triage says "
                     f"'{g('census_triage')['cross_system_behavior']}'. What exists is "
                     f"other rows' single-axis work in this stage: hazard-vs-health "
                     f"({g('e10_events_for_this_stage')}) and death-vs-respawn "
                     f"({g('stage_death_laws')})"
                     + (f", and grain-vs-gate "
                        f"({g('gate_law')['city_thresholds']} against the resident grain "
                        f"byte)" if cfg["gate_artifact"] else ""),
            "gap": f"the material for a first crossing is sitting unused and pinned: "
                   f"{g('stage_actor_records')} actor records over "
                   f"{len(g('stage_actor_ids'))} distinct ids from this row's own fixture "
                   f"({g('stage_actor_census_uses_a_row_fixture')}, cited by the row: "
                   f"{g('stage_actor_census_cited_by_the_row')}), "
                   f"{g('stage_movies_attributed')} pinned routes including "
                   f"{len(g('stage_movies_under_phase4_interpreter'))} under "
                   f"movies/Phase4/Interpreter/, and a completion snapshot already "
                   f"carrying {len(g('oracle_snapshot_fields'))} cross-system fields "
                   f"({g('oracle_snapshot_fields')}). This dimension is not blocked by a "
                   f"missing fixture; it is unattempted",
        }

        # ---------------- original_interfaces ----------------------------- #
        if K == "f05":
            oi_state = "not_met"
            oi_basis = (
                f"the only documented interface is the shared loader's, pinned to the "
                f"instruction and re-decoded here from the pristine image "
                f"({g('identity_pin_decoded_instructions')}), with this scene's sound-bank "
                f"prefix resolved to '{g('identity_pin_sound_bank_prefix')}' at bank index "
                f"{g('identity_pin_sound_bank_index')}. The row does record its own "
                f"falsification ({g('row_records_prior_binding_falsified')}), which is the "
                f"self-correcting behaviour the bar wants")
            oi_gap = (
                f"no interface of this row's own subject is documented, and the unknown is "
                f"not enumerated with a named obstruction -- it is one sentence: "
                f"'{g('row_declared_missing')}'. That is the shape the bar explicitly "
                f"rejects. Measured support: the row cites "
                f"{g('row_artifact_path_citation_count')} artifact path(s) "
                f"({g('row_artifact_path_citations')}); its declared evidence classes are "
                f"{g('row_declared_evidence_classes')}, one of which is `secondary_lead`, "
                f"defined in-repo as '{F['secondary_lead_role']}' and therefore worth zero "
                f"toward any bar; and the census derives "
                f"{g('census_derived_evidence_classes')} from the row's artifacts. Of the "
                f"pinned overlay's {g('overlay_functions_in_census')} functions, "
                f"{g('overlay_functions_named_in_census')} carry a name and only "
                f"{len(g('overlay_symbols_proven'))} is 'proven'; none has a documented ABI")
        else:
            oi_state = "partial"
            oi_basis = (
                f"two interfaces are documented to the instruction. The shared loader's, "
                f"re-decoded here ({g('identity_pin_decoded_instructions')}, sound bank "
                f"'{g('identity_pin_sound_bank_prefix')}' at index "
                f"{g('identity_pin_sound_bank_index')}); and, inside this row's own "
                f"byte-pinned overlay, the grain-gate interface -- "
                f"{g('gate_function_pinned_word_count')} named instruction words "
                f"({sorted(g('gate_function_pinned_words')) }), the grain input, the "
                f"proximity helper, the SFX helpers and the paired object channels. A "
                f"readable semantic reconstruction exists at {g('semantic_c_source')}. The "
                f"row records its own falsification "
                f"({g('row_records_prior_binding_falsified')})")
            oi_gap = (
                f"the row's own unknown is not enumerated with a named obstruction; it is "
                f"'{g('row_declared_missing')}'. None of the documented interface is "
                f"documented BY this row: it cites "
                f"{g('row_artifact_path_citation_count')} artifact path(s) "
                f"({g('row_artifact_path_citations')}) and does not cite the gate campaign "
                f"({g('gate_campaign_cited_by_the_row')}). Its declared classes are "
                f"{g('row_declared_evidence_classes')}, one being `secondary_lead` "
                f"('{F['secondary_lead_role']}'), worth zero here. Of the pinned overlay's "
                f"{g('overlay_functions_in_census')} functions "
                f"{g('overlay_functions_named_in_census')} carry a name, "
                f"{len(g('overlay_symbols_proven'))} are 'proven', and the one that "
                f"matters most is misnamed: the census and the symbol table call "
                f"0x800b3d84 'level_audio_handler' while the gate campaign shows it is the "
                f"grain-gate update")

        dims["original_interfaces"] = {
            "state": oi_state,
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": oi_basis,
            "gap": oi_gap,
        }

        # ---------------- source_closure ---------------------------------- #
        if K == "f05":
            sc_state = "not_met"
            sc_basis = (
                f"measured against BOTH registries. RESIDENT (config/segments.yml, "
                f"{F['resident_build_units']} units, toolchain "
                f"{F['resident_build_toolchain']}): this row's "
                f"{g('governing_resident_addresses')} distinct governing resident "
                f"addresses resolve to {len(g('governing_resident_build_units'))} build "
                f"unit(s) -- {g('governing_resident_units_matching_c')} matching C and "
                f"{g('governing_resident_units_hand_asm')} hand-written byte-exact ASM "
                f"({g('governing_resident_build_units')}), with "
                f"{len(g('governing_resident_addresses_outside_any_build_unit'))} data "
                f"addresses in no unit. OVERLAY (config/overlays.yml + src/overlays/ + "
                f"{OVLD}, {F['overlay_track_matched_functions']}/"
                f"{F['overlay_track_total_code_functions']} matched campaign-wide = "
                f"{F['overlay_track_matched_pct']}%): this row's overlay HAS a build entry "
                f"({g('overlay_has_a_build_registry_entry')}) -- "
                f"{g('overlay_matched_functions')} of "
                f"{g('overlay_code_functions_total')} code functions matched from "
                f"{g('overlay_matched_sources')}, rebuild validated "
                f"({g('overlay_rebuild_validated')}) with rebuilt sha1 equal to the blob's "
                f"({g('overlay_rebuilt_sha1_equals_blob_sha1')}), and that sha1 is the "
                f"sha1 of the image this assessment byte-pinned as resident "
                f"({g('overlay_build_registry_sha1_equals_byte_pinned_image')}). So "
                f"overlay byte-matching is DEMONSTRATED for this row's overlay, not "
                f"impossible")
            sc_gap = (
                f"no governing function of this row's SUBJECT is byte-matched C, because "
                f"no governing function of its subject has been identified. The one "
                f"matched overlay function is a 4-store initializer; the resident "
                f"dispatcher that owns every pinned loader instruction is hand ASM. "
                f"{g('overlay_code_functions_total') - g('overlay_matched_functions')} of "
                f"{g('overlay_code_functions_total')} code functions in the pinned image "
                f"have no C, including level_object_spawn_handler, the only plausible "
                f"objective-adjacent function in it. Note the direction of the census's "
                f"own triage -- '{g('census_triage')['source_closure']}' -- which "
                f"measures REGISTRATION, and would read as support if the word "
                f"'governing' in the bar were dropped. Scored not_met on the same footing "
                f"as the F08 sibling, which has the identical shape (one matched "
                f"4-store overlay initializer, validated rebuild) and was judged not_met "
                f"for exactly this reason. The difference from F07 is in the GAP, not the "
                f"state: here the path is demonstrated open, there it is untouched")
        else:
            sc_state = "not_met"
            sc_basis = (
                f"measured against BOTH registries, and a third tree. RESIDENT "
                f"(config/segments.yml, {F['resident_build_units']} units): this row's "
                f"{g('governing_resident_addresses')} distinct governing resident "
                f"addresses resolve to {len(g('governing_resident_build_units'))} build "
                f"unit(s) -- {g('governing_resident_units_matching_c')} matching C, "
                f"{g('governing_resident_units_hand_asm')} hand-written byte-exact ASM "
                f"({g('governing_resident_build_units')}). OVERLAY (config/overlays.yml + "
                f"src/overlays/ + {OVLD}): this row's overlay has NO build entry at all "
                f"({g('overlay_has_a_build_registry_entry')}), "
                f"{g('overlay_matched_functions')} of "
                f"{g('overlay_code_functions_total')} code functions matched -- and "
                f"{g('overlay_code_functions_total')} is the largest per-level function "
                f"count in the campaign. THIRD TREE: {g('semantic_c_source')} reads like "
                f"C for the gate function, but it declares itself not a build input "
                f"({g('semantic_c_declares_itself_not_a_build_input')}) and appears in "
                f"neither registry ({g('semantic_c_is_in_either_build_registry')}), so it "
                f"is documentation and counts zero here")
            sc_gap = (
                f"zero byte-matched C for this row, in either registry. The path is open "
                f"rather than blocked, and that is measurable: sibling per-level overlays "
                f"DO have validated entries with rebuilt sha1 equal to the blob, so the "
                f"only thing missing for this image is the work. Note the census triage "
                f"agrees for the right reason: "
                f"'{g('census_triage')['source_closure']}'")

        dims["source_closure"] = {
            "state": sc_state,
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": sc_basis,
            "gap": sc_gap,
        }

        # ---------------- campaign_breadth -------------------------------- #
        dims["campaign_breadth"] = {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage, "
                           "variant, lifecycle and exceptional path -- which requires "
                           "the applicable set itself to be enumerated",
            "basis": f"this row has produced no conclusion of its own to generalize. The "
                     f"one denominator that IS closed for it is the scene universe: the "
                     f"campaign progression table decoded here lists "
                     f"{len(g('identity_pin_progression_table_scenes'))} reachable "
                     f"scenes and independently agrees with the disc census "
                     f"({g('identity_pin_progression_table_agrees_with_e02')}), which "
                     f"located all {F['e02_levels_censused']} levels over "
                     f"{F['e02_authored_sectors_compared']} authored sectors with "
                     f"{F['e02_disagreements']} disagreements. A pre-outcome type "
                     f"authority places this row as {g('c2_row_types')} together with "
                     f"{g('c2_rows_sharing_this_type')}",
            "gap": f"within the stage there is no denominator at all: of "
                   f"{g('stage_movies_attributed')} pinned routes this row's artifacts "
                   f"replay zero, and its evidence is two static snapshots. Campaign-wide "
                   f"the applicability universe is not enumerated -- the type authority "
                   f"itself reports taxonomy_coverage_demonstrated="
                   f"{F['c2_taxonomy_coverage_demonstrated']} because "
                   f"{sorted(F['c2_underivable_types'])} have no textual authority. No "
                   f"variant, retry, death or exceptional-path axis is enumerated for "
                   f"this stage. This dimension fails the WRITTEN bar, not only a strict "
                   f"reading of it",
        }

        counts: dict[str, int] = {}
        for d in dims.values():
            counts[d["state"]] = counts.get(d["state"], 0) + 1
        per_row_counts[RID] = counts

        scorecards[RID] = {
            "row_id": RID,
            "row_name": g("row_name"),
            "stage_ordinal": g("census_stage_ordinal"),
            "scene_id_byte_pinned": g("identity_pin_scene_at_stage_ordinal"),
            "overlay_byte_pinned": g("identity_pin_file"),
            "registry_status": g("row_declared_status"),
            "carried_forward": {
                "dimension": "durable_evidence",
                "from": CENSUS,
                "state": g("census_durable_state"),
                "fraction": g("census_durable_fraction"),
                "note": "measured there against pinned bytes; re-deriving it here would "
                        "be a second opinion on a settled measurement, not evidence",
            },
            "systemic_defect_checks": {
                "a_overlay_misattribution": {
                    "applies_to_this_row": True,
                    "why": f"every per-level overlay loads at "
                           f"{F['overlay_registry_region_a']}, so an address in that "
                           f"window names real content in most of the "
                           f"{F['overlay_images_in_function_census']} censused images, "
                           f"and {OWN} stores no image field for this row "
                           f"(has_image_field="
                           f"{g('ownership_graph_stores_an_image_field_for_region_a')})",
                    "settled_by": PINC,
                    "verdict": f"{g('identity_pin_result')} -- {g('identity_pin_file')} "
                               f"({g('identity_pin_nontrivial_pct')}% non-trivial "
                               f"agreement vs {g('identity_pin_runner_up_pct')}% for "
                               f"{g('identity_pin_runner_up')}) across "
                               f"{g('identity_pin_images_scanned')} images x "
                               f"{g('identity_pin_fixtures_scanned')} fixtures; agrees "
                               f"with the census's overlay name "
                               f"({g('identity_pin_agrees_with_census_overlay_name')})",
                    "how_close_it_was": f"{g('identity_pin_images_with_anchor_hits_but_no_stable_base')} "
                                        f"other images produce anchor hits at a WANDERING "
                                        f"base "
                                        f"({g('identity_pin_images_with_anchor_hits_but_no_stable_base_paths')}); "
                                        f"base stability plus the >=2-anchor rule are "
                                        f"what separate them",
                    "was_the_row_already_wrong": False,
                    "what_it_licenses": f"every overlay-local statement in this scorecard "
                                        f"is scoped to the extent "
                                        f"{g('identity_pin_extent')} of a file whose "
                                        f"bytes were compared, not to an address",
                },
                "b_semantic_registry_collision": {
                    "applies_to_this_row": True,
                    "va_collision_hit": bool(
                        g("semantic_entries_inside_this_rows_overlay_extent")),
                    "measured": f"{len(F['semantic_entries_inside_shared_region_a'])} "
                                f"semantic_state entries fall inside the SHARED region A "
                                f"({F['semantic_entries_inside_shared_region_a']}, ids "
                                f"{F['semantic_entries_inside_shared_region_a_ids']}), "
                                f"and "
                                f"{len(g('semantic_entries_inside_this_rows_overlay_extent'))} "
                                f"fall inside THIS row's pinned extent "
                                f"{g('identity_pin_extent')}. The pinned EXTENT, not the "
                                f"shared region, is what keeps the collision out",
                    "related_finding": f"the shared table entry both rows cite as state "
                                       f"({F['shared_state_table_registry_id']}, "
                                       f"confidence "
                                       f"'{F['shared_state_table_registry_confidence']}') "
                                       f"records its own correction "
                                       f"({F['shared_state_table_invariant_records_its_own_correction']}) "
                                       f"and no longer asserts the falsified "
                                       f"index law "
                                       f"({F['shared_state_table_still_asserts_index_equals_id_minus_one']})",
                },
            },
            "registry_disposition_for_contrast": {
                "source": DEBT,
                "campaign_id": g("registry_campaign_id"),
                "completion_state": g("registry_completion_state"),
                "dimensions_met": g("registry_dimensions_met"),
                "dimensions_remaining": g("registry_dimensions_remaining"),
                "distinct_basis_strings": g("registry_distinct_bases"),
                "distinct_states": g("registry_distinct_states"),
                "note": f"the registry carries ONE blanket basis across all nine "
                        f"dimensions and scores the row 0/9. That is a disposition, not a "
                        f"measurement -- and it records movie_count "
                        f"{g('registry_movie_count')} and capsule_count "
                        f"{g('registry_capsule_count')} for a stage with "
                        f"{g('stage_movies_attributed')} pinned, byte-matching movies",
            },
            "dimensions": dims,
            "counts": counts,
            "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                       f"met-candidate, {counts.get('partial', 0)} partial, "
                       f"{counts.get('not_met', 0)} not met, "
                       f"{counts.get('unmeasured', 0)} unmeasured -- against the WRITTEN "
                       f"bars.",
            "never_investigated": never,
        }

    # ------------------------------------------------------------------ #
    # cross-row guard: the two scorecards must not have become identical  #
    # ------------------------------------------------------------------ #
    a, b = [scorecards[r["row_id"]] for r in ROWS]
    same = [k for k in a["dimensions"]
            if a["dimensions"][k]["basis"] == b["dimensions"][k]["basis"]]
    if same:
        raise SystemExit("CROSS-CREDITING GUARD: these dimensions carry an identical "
                         f"basis string for both rows: {same}. Separate rows require "
                         "separately measured bases.")
    E.fact("cross_row_identical_basis_strings", len(same), SELF)
    E.fact("cross_row_state_vectors",
           {r["row_id"]: {k: v["state"] for k, v in
                          scorecards[r["row_id"]]["dimensions"].items()} for r in ROWS},
           SELF)
    E.fact("cross_row_dimensions_scored_differently",
           sorted(k for k in a["dimensions"]
                  if a["dimensions"][k]["state"] != b["dimensions"][k]["state"]), SELF)

    doc = {
        "_comment": "F05_riverbed_run and F07_city_entrance measured, SEPARATELY, "
                    "against the nine DoD dimensions AS WRITTEN (item 2 = enumerated; "
                    "residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored per row; every fact derived from a pinned artifact at run "
                    "time. No cross-crediting: a guard aborts if any dimension carries "
                    "the same basis for both rows. Regenerate: "
                    "tools/phase4_f05_f07_written_bar_assessment.py",
        "schema": "abl-phase4-f05-f07-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_ids": [r["row_id"] for r in ROWS],
        "standard": {
            "ruling": "engineering-specs/phase4-measurement-standard-ruling.md",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads as "
                          "met; this assessment publishes measurement, not disposition",
            "allowed_states": ["met", "met_candidate", "partial", "not_met", "unmeasured"],
            "crediting_rule_applied": {
                "rule": "evidence is credited to a row when it is ABOUT that row's stage "
                        "or subject -- measured on this stage's scene id, this stage's "
                        "byte-pinned overlay image, or this stage's fixtures/movies -- "
                        "regardless of which row authored it, and the scorecard then says "
                        "plainly that the row does not cite it. Evidence that is "
                        "campaign-wide INFRASTRUCTURE, identical for every stage row, is "
                        "credited to neither row.",
                "worked_example": "the scene->asset loader binding is the only analysis "
                                  "artifact either row cites, and it lifts NEITHER row's "
                                  "original_interfaces: the same four instruction PCs and "
                                  "five state addresses appear verbatim in both rows' "
                                  "ownership entries and in a dozen others. The grain-gate "
                                  "campaign DOES lift F07, because its overlay sha256 "
                                  "equals the image byte-pinned in F07's own fixtures.",
                "why_it_matters": "without one stated rule, 'uncited but relevant' and "
                                  "'shared and therefore free' collapse into each other, "
                                  "which is how a thin row acquires a partial it has not "
                                  "earned.",
            },
            "secondary_lead_counts_for_nothing": {
                "role": F["secondary_lead_role"],
                "authority_rule": F["secondary_lead_authority_rule"],
                "applied": "both rows declare it as one of their two evidence classes; "
                           "it is counted as zero support in every dimension below",
            },
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "edits_mechanics_baseline": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor did not author either row's underlying "
                               "evidence, but did author this assessment and the one NEW "
                               "measurement in it "
                               "(tools/phase4_f05_f07_stage_identity_pin.c and its two "
                               "artifacts) -- so on stage identity, overlay residency, "
                               "the claimed-range confirmations and the cross-fixture "
                               "diff the tool, the claim and the judgment share an "
                               "author. Every state is a submission to a fresh detached "
                               "verifier, not a promotion; `partial` and `not_met` are as "
                               "challengeable as `met`",
        },
        "fail_loud_contract": {
            "guards": F["fail_loud_guards_fired"],
            "in_band": "re-proved on every generation before any artifact is read; if a "
                       "guard stops firing the run aborts instead of emitting numbers "
                       "whose staleness detection cannot be trusted",
            "structural_aborts": [
                "the identity pin's declared base / region length must equal what "
                "config/overlays.yml declares",
                "the identity pin must decode every instruction PC the shared binding "
                "artifact pins",
                "the identity pin's claimed ranges must cover every censused function of "
                "the pinned overlay",
                "the identity pin's named words must be exactly those declared by the "
                "byte-matched C, where such C exists",
                "overlay residency must be UNIQUE or no overlay claim is emitted at all",
                "a fact key recorded twice aborts (cross-row key collision)",
                "any dimension whose basis string is identical for both rows aborts",
            ],
            "out_of_band_probes_run_2026-08-11": [
                "moved analysis/phase4_f07_stage_identity_pin.json aside -> abort, "
                "exit 1, no output file",
                "renamed unique_pin_file inside the F05 identity pin -> abort, exit 1, "
                "no output file",
                "drifted one named word away from the byte-matched C source -> abort "
                "naming both sets, exit 1, no output file",
            ],
            "note": "the out-of-band list records actions taken by the assessor; the "
                    "in-band guards above are re-measured every run",
        },
        "fact_provenance": {
            "facts_total": len(F),
            "facts_derived_from_pinned_artifacts": len(E.provenance),
            "facts_hand_typed": len(F) - len(E.provenance),
            "rule": "facts are recorded through fact(key, value, source); a value cannot "
                    "be stored without naming a pinned artifact, every lookup is strict, "
                    "and a duplicate key aborts, so a renamed key, a removed artifact or "
                    "a cross-row collision aborts the run instead of silently defaulting",
            "by_fact": E.provenance,
        },
        "facts": F,
        "evidence_pins": E.pins,
        "scorecards": scorecards,
        "counts_by_row": per_row_counts,
        "summary": "; ".join(
            f"{r['row_id']}: {scorecards[r['row_id']]['summary']}" for r in ROWS),
        "notable": [
            "BOTH ROWS' IDENTITY IS NOW PROVED FROM BYTES, AND BOTH WERE RIGHT. The "
            f"progression table at {F['f05_identity_pin_progression_table_address']} "
            f"decodes to {F['f05_identity_pin_progression_table_scenes']}: ordinal 5 -> "
            f"scene {F['f05_identity_pin_scene_at_stage_ordinal']}, ordinal 7 -> scene "
            f"{F['f07_identity_pin_scene_at_stage_ordinal']}. Every declared fixture "
            f"reads its row's scene id out of the .sav container "
            f"(F05 {F['f05_identity_pin_fixture_scene_ids']}, "
            f"F07 {F['f07_identity_pin_fixture_scene_ids']}), and the resident overlay is "
            f"unique in each case ({F['f05_identity_pin_file']} at "
            f"{F['f05_identity_pin_nontrivial_pct']}%, {F['f07_identity_pin_file']} at "
            f"{F['f07_identity_pin_nontrivial_pct']}%) out of "
            f"{F['f05_identity_pin_images_scanned']} candidates. Before this, the only "
            "support for either binding was a shared artifact neither row had "
            "independently checked.",

            "THE TWO ROWS LOOK IDENTICAL IN EVERY REGISTRY AND ARE NOT REMOTELY "
            f"EQUIVALENT. Both are scored 0/9 with one blanket basis, both have "
            f"movie_count {F['f05_registry_movie_count']}, both are ineligible for the "
            f"movie scheduler with reason {F['f05_scheduler_ineligibility_reasons']}, and "
            f"the ownership graph resolves BOTH to the same single resident function "
            f"{F['f05_ownership_distinct_function_starts']}. Measured, F07 has a "
            f"completed campaign inside its own byte-pinned overlay (grain gates: "
            f"{F['f07_gate_function_pinned_word_count']} pinned instruction words, a "
            f"typed 3-entry state array, {F['f07_gate_natural_replays_for_this_stage']} "
            f"natural replays, a registered pytest gate) while F05 has "
            f"{F['f05_overlay_matched_functions']} matched overlay function and no "
            f"mechanism of any kind. Their scorecards differ on "
            f"{F['cross_row_dimensions_scored_differently']}.",

            "THE BLOCKER EACH ROW RECORDS IS NOT A MISSING FIXTURE. F05 asks for "
            f"'{F['f05_row_declared_fixture_need']}' while "
            f"{F['f05_stage_movies_attributed']} movies for its stage are pinned and "
            f"byte-matching, including a from-boot completion replay "
            f"({F['f05_oracle_movie']}, {F['f05_oracle_frames']} frames) and a falling-"
            f"spikes hazard capture. F07 asks for "
            f"'{F['f07_row_declared_fixture_need']}' while "
            f"{F['f07_stage_movies_attributed']} of its stage's movies are pinned, "
            f"including a goo capture and three gate replays. Each row declares "
            f"{F['f05_stage_movies_declared_by_the_row']} / "
            f"{F['f07_stage_movies_declared_by_the_row']} of them, and the scheduler "
            f"consequently reports sees_a_phase4_movie="
            f"{F['f05_scheduler_sees_a_phase4_movie']} for both. Under-declaration in "
            "the row is propagating into the scheduler and blocking the exact work the "
            "row asks for.",

            "WHAT F07 ACTUALLY HAS, STATED PRECISELY SO IT IS NOT OVERSOLD. The "
            f"grain-gate campaign is '{F['f07_gate_campaign_state']}' and its overlay "
            f"sha256 equals the image byte-pinned here "
            f"({F['f07_gate_overlay_sha256_equals_byte_pinned_image']}), so its "
            "overlay-local addresses are this row's for a reason stronger than a name. "
            f"But its natural arm proves DENIAL only "
            f"(opens_a_gate={F['f07_gate_natural_replay_opens_a_gate']}); all "
            f"{F['f07_gate_success_controls']} successful openings are produced by "
            f"injection into {F['f07_gate_success_injection_addresses']}. A grain gate is "
            "also a progression gate, not the circus objective the row is named for.",

            "NEW, SMALL, AND THIS ROW'S OWN: F07'S TWO FIXTURES BRACKET THE GATE ARRAY. "
            f"Read from the .sav containers, {F['f07_named_overlay_word_values']} -- the "
            "mid-stage save holds all three gates at the closed sentinel and the ending "
            "save holds all three at the terminal value, with every word zero on disc. No "
            "artifact had read the row's own fixtures for this. It is a lifecycle "
            "endpoint pair, not an objective.",

            "F05'S FOUR OVERLAY WORDS ARE A CLEAN OPEN QUESTION. The one byte-matched C "
            f"function in {F['f05_identity_pin_file']} declares "
            f"{F['f05_named_overlay_words_count']} words and writes initializer(s) "
            f"{F['f05_byte_matched_c_nonzero_initializers']}; measured across the row's "
            f"own fixtures they read {F['f05_named_overlay_word_values']}, with "
            f"{F['f05_named_overlay_words_varying_across_fixtures']} varying and the "
            "initializer value appearing in neither. Two samples cannot type them. That "
            "is the row's first named, testable state candidate and it is UNRESOLVED.",

            "THE HAZARD CONTEXT IS CONFIRMED AND IT CLOSES NOTHING. Scene "
            f"{F['f05_identity_pin_scene_at_stage_ordinal']} authors "
            f"{F['f05_stage_region_code_histogram']} over "
            f"{F['f05_stage_authored_collision_sectors']} sectors and scene "
            f"{F['f07_identity_pin_scene_at_stage_ordinal']} authors "
            f"{F['f07_stage_region_code_histogram']} over "
            f"{F['f07_stage_authored_collision_sectors']}; F07's stage is the only level "
            f"in the campaign carrying both families "
            f"({F['e02_levels_with_both_code_1_and_code_4']}), and F05's stage is one of "
            f"{len(F['e02_levels_with_an_exit_code_2_or_3'])} carrying an exit code while "
            "F07's carries none at all. That is EXIT and HAZARD evidence, owned by E02, "
            "and it says nothing about either objective -- F07's stage has no exit sector "
            "at all, so its exit is overlay-owned and unproven.",

            "UNMEASURED HERE, named so silence is not read as absence: whether any of the "
            f"{F['f05_overlay_functions_in_census']} functions in F05's pinned overlay or "
            f"the {F['f07_overlay_functions_in_census']} in F07's implements the stage "
            "objective (no artifact walks them); whether the pinned routes would supply "
            "lifecycle or crossing coverage (that needs replays); and whether F07's "
            "`level04_complete_handler` is reached by an objective condition or by "
            "something else entirely (its 'dynamic:' evidence tag is name-assumed, which "
            "the shared load base cannot justify).",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    for rid in [r["row_id"] for r in ROWS]:
        sc = scorecards[rid]
        print(f"[written-bar] {rid}: {sc['summary']}")
        for name, d in sc["dimensions"].items():
            print(f"    {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} "
          f"derived / {doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
