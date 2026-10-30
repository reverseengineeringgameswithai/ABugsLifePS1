#!/usr/bin/env python3
"""Measure F02_tunnels' nine DoD dimensions against the bars AS WRITTEN.

Second test case for the uniform standard ruled in
`engineering-specs/phase4-measurement-standard-ruling.md`; the first was
`tools/phase4_f01_written_bar_assessment.py`, whose design this copies. The WRITTEN
bars are:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT "the
    unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

Why F02 next: it is the opposite shape to F01. F01 is a row whose single subject was
driven hard; F02 is a row with TWO named subjects ("gates + falling debris") of which
one half is closed to a reviewed structural negative and the other half -- the stage-2
objective/completion condition -- is the row's own declared `missing`. Measuring it
shows what the written bars say about a genuinely half-answered row, and the honest
answer is mostly `partial`.

Design (identical to the F01 exemplar):
  * every FACT is read from a cited artifact at run time and the artifact is
    sha256-pinned, so a stale citation fails LOUDLY instead of aging silently. `fact()`
    cannot record a value without naming the artifact it came from, and `req()` raises
    on a missing key rather than substituting a default;
  * every JUDGMENT is authored and attributable, and carries `written_bar` / `basis` /
    `gap`;
  * `unmeasured` is an allowed and expected state. Evidence is not stretched to fill a
    cell.

durable_evidence is NOT re-derived here: it was MEASURED in
`analysis/phase4_f_row_measured_census.json` (4/4 declared fixtures intact) and is
carried forward with its fraction, failing loudly if that measurement ever moves.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a fresh
detached verifier.

Usage: python3 tools/phase4_f02_written_bar_assessment.py [--out PATH]
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
ROW_ID = "F02_tunnels"


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
        self.provenance: dict[str, str] = {}

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(ROOT / "analysis/phase4_f02_written_bar_assessment.json"))
    args = ap.parse_args()

    E = Evidence()
    F = E.facts

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
    E.fact("census_triage_source_closure",
           req(crow, "measurability_triage", "source_closure", where=CENSUS), CENSUS)
    E.fact("census_baseline_sha256", req(census, "baseline_sha256", where=CENSUS), CENSUS)
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
    E.fact("registry_completion_state", req(drow, "completion_state", where=DEBT), DEBT)

    # ------------------------------------------------------------------ #
    # 3. the baseline row itself (read-only; this tool never edits it)    #
    # ------------------------------------------------------------------ #
    BASE = "analysis/mechanics_baseline.yaml"
    base = E.yaml(BASE)
    rows = req(base, "rows", where=BASE)
    row = next((r for r in rows if r.get("id") == ROW_ID), None)
    if row is None:
        raise SystemExit(f"STALE CITATION: {BASE} no longer carries {ROW_ID}")
    E.fact("row_binding_claims", len(req(row, "bindings", where=BASE)), BASE)
    E.fact("row_declared_fixtures", len(req(row, "fixture_have", where=BASE)), BASE)
    E.fact("row_declared_missing", req(row, "missing", where=BASE), BASE)
    E.fact("row_declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
    E.fact("row_declared_evidence_classes", req(row, "evidence", where=BASE), BASE)

    # Which OTHER baseline rows carry stage-2 evidence this row does not cite?
    # ⚠️ "LEVEL02" is ambiguous in this project: scene 3 (Tunnels) loads from disc dir
    # LEVEL03/, and dir LEVEL02/ belongs to scene 2 (Council Chamber) -- this row's own
    # bindings record that correction. So count the STAGE token separately from the
    # DIRECTORY token instead of grepping one string.
    stage2 = re.compile(r"[Tt]unnels|LEVEL02(?![/\\])|level02(?![/\\])")
    other = sorted(r["id"] for r in rows
                   if r.get("id") != ROW_ID and stage2.search(json.dumps(r)))
    E.fact("other_baseline_rows_naming_stage2", len(other), BASE)
    E.fact("other_baseline_rows_naming_stage2_ids", other, BASE)
    E.fact("row_artifact_path_citations",
           len(re.findall(r"(?:analysis|tools|src_re)/[\w./%-]+", json.dumps(row))), BASE)

    # ------------------------------------------------------------------ #
    # 4. this row's own artifacts                                         #
    # ------------------------------------------------------------------ #
    PROBE = "analysis/phase4_f02_debris_live_probe.json"
    probe = E.json(PROBE)
    gates = req(probe, "gates", where=PROBE)
    E.fact("live_movie", req(probe, "movie", where=PROBE), PROBE)
    E.fact("live_game_serial", req(probe, "identity", "game_serial", where=PROBE), PROBE)
    E.fact("live_pool_samples", req(probe, "pool_samples", where=PROBE), PROBE)
    E.fact("live_gate_examinations",
           sum(req(g, "examined_events", where=PROBE) for g in gates.values()), PROBE)
    E.fact("live_flags20_examinations",
           sum(req(g, "flags_0x20_examined", where=PROBE) for g in gates.values()), PROBE)
    E.fact("live_gate_leaks",
           sum(len(req(g, "records_without_gate_bit_that_passed", where=PROBE))
               for g in gates.values()), PROBE)
    E.fact("live_gates_with_zero_passes_for_any_class",
           sum(1 for g in gates.values() if req(g, "passed_events", where=PROBE) == 0), PROBE)
    E.fact("live_gates_total", len(gates), PROBE)
    E.fact("live_positive_control_passes",
           max(req(g, "passed_events", where=PROBE) for g in gates.values()), PROBE)
    E.fact("live_unpairable_passes",
           sum(req(g, "passes_unpairable", where=PROBE) for g in gates.values()), PROBE)
    E.fact("live_any_gate_truncated",
           any(req(g, "truncated", where=PROBE) for g in gates.values()), PROBE)
    E.fact("live_debris_spawns", req(probe, "debris_spawn_hits", where=PROBE), PROBE)
    E.fact("live_debris_spawn_a3_domain", req(probe, "debris_spawn_a3", where=PROBE), PROBE)
    E.fact("live_health_writes", req(probe, "health_writes", where=PROBE), PROBE)
    E.fact("live_health_writer_pcs", len(req(probe, "health_writer_pcs", where=PROBE)), PROBE)
    E.fact("live_ctor_types_censused", len(req(probe, "pool_census", where=PROBE)), PROBE)

    BIND = "analysis/phase4_f02_debris_class_bind.json"
    bind = E.json(BIND)
    E.fact("metab_rows", req(bind, "metab_rows", where=BIND), BIND)
    E.fact("walker_dispatch_entries", req(bind, "dispatch_entries", where=BIND), BIND)
    E.fact("classes_typed_statically", len(req(bind, "classes", where=BIND)), BIND)
    E.fact("pool_base_reference_sites", req(bind, "carray_refs", where=BIND), BIND)
    E.fact("debris_flags", req(bind, "debris_flags", where=BIND), BIND)
    E.fact("debris_blocked_by", req(bind, "debris_blocked_by", where=BIND), BIND)
    E.fact("record_field_chain", req(bind, "chain", where=BIND), BIND)

    TRACE = "analysis/phase4_f02_spawner_trace.json"
    trace = E.json(TRACE)
    E.fact("alloc_events", req(trace, "events", where=TRACE), TRACE)
    E.fact("alloc_callers_distinct", req(trace, "distinct_callers", where=TRACE), TRACE)
    E.fact("alloc_callers_with_arg_domains",
           len(req(trace, "per_caller_arg_domains", where=TRACE)), TRACE)
    E.fact("alloc_call_signatures", len(req(trace, "call_signatures", where=TRACE)), TRACE)

    OVL = "analysis/phase4_f02_overlay_spawner_pin.json"
    ovl = E.json(OVL)
    E.fact("spawner_overlay_image", req(ovl, "overlay_image", where=OVL), OVL)
    E.fact("spawner_callers_matched",
           f'{req(ovl, "callers_matched", where=OVL)}/{req(ovl, "callers_total", where=OVL)}', OVL)
    E.fact("spawner_pin_unique", req(ovl, "unique", where=OVL), OVL)

    CAP = "analysis/phase4_f02_debris_capture.json"
    cap = E.json(CAP)
    E.fact("capture_movie_frames", req(cap, "movie_frames", where=CAP), CAP)
    E.fact("capture_pool_samples", req(cap, "samples_taken", where=CAP), CAP)
    E.fact("capture_slots_that_changed", req(cap, "slots_that_changed", where=CAP), CAP)
    E.fact("capture_pool_slots", req(cap, "pool", "slots", where=CAP), CAP)

    ACT = "analysis/phase4_f02_actor_census.json"
    act = E.json(ACT)
    E.fact("save_anchor_occupied_slots", req(act, "occupied_slots", where=ACT), ACT)
    E.fact("save_anchor_records_changing", req(act, "records_changing", where=ACT), ACT)
    E.fact("save_anchor_pool_ram_changed", req(act, "control_pool_ram_changed", where=ACT), ACT)

    SUP = "analysis/phase4_f02_contact_action_table.json"
    sup = E.json(SUP)
    E.fact("superseded_artifact_marked", bool(req(sup, "_SUPERSEDED", where=SUP)), SUP)

    EXP = "ObsidianVault/Experiments/EXP_2026-08-04_phase4_f02_debris_damage_class.md"
    exp = E.text(EXP)
    m = re.search(r"^## Residual.*$", exp, re.M)
    if not m:
        raise SystemExit(f"STALE CITATION: {EXP} no longer has a '## Residual' section")
    E.fact("enumerated_residuals",
           len(re.findall(r"^\d+\. \*\*", exp[m.end():].split("\n## ")[0], re.M)), EXP)
    E.fact("residual_section_heading", m.group(0).strip(), EXP)

    # ------------------------------------------------------------------ #
    # 5. the movie the row's whole evidence base rests on                 #
    # ------------------------------------------------------------------ #
    MOV = F["live_movie"]
    mov = E.json(MOV)
    E.fact("evidence_movie_frames", len(req(mov, "frames", where=MOV)), MOV)
    E.fact("evidence_movie_from_boot", req(mov, "start_state", "from_boot", where=MOV), MOV)
    E.fact("evidence_movie_version", req(mov, "version", where=MOV), MOV)
    E.fact("evidence_movie_armed_while_paused", req(mov, "armed_while_paused", where=MOV), MOV)

    # every distinct movie any F02 artifact replayed
    replayed = sorted({d["movie"] for d in (probe, trace, cap) if "movie" in d})
    E.fact("distinct_movies_replayed_by_f02_artifacts", len(replayed), [PROBE, TRACE, CAP])

    # ------------------------------------------------------------------ #
    # 6. the LEVEL02 fixture corpus the row does NOT declare              #
    # ------------------------------------------------------------------ #
    AUDIT = "analysis/phase2_fixture_audit.json"
    audit = E.json(AUDIT)
    l2_mov = sorted(k for k in req(audit, "movies", where=AUDIT) if "LEVEL02" in k)
    l2_sav = sorted(k for k in req(audit, "saves", where=AUDIT) if "LEVEL02" in k.upper())
    E.fact("level02_movies_pinned", len(l2_mov), AUDIT)
    E.fact("level02_saves_pinned", len(l2_sav), AUDIT)
    E.fact("level02_e09_gate_movies_pinned",
           len([k for k in l2_mov if "/E09/" in k]), AUDIT)
    E.fact("level02_e10_hazard_movies_pinned",
           len([k for k in l2_mov if "/E10/" in k]), AUDIT)
    hundred = [k for k in l2_mov if "100%" in k]
    if len(hundred) != 1:
        raise SystemExit("expected exactly one pinned LEVEL02 100% movie; "
                         f"found {hundred}")
    HUND = hundred[0]
    E.fact("level02_100pct_movie", HUND, AUDIT)
    E.fact("level02_100pct_frames", req(audit, "movies", HUND, "frames", where=AUDIT), AUDIT)
    E.fact("level02_100pct_format_version",
           req(audit, "movies", HUND, "format_version", where=AUDIT), AUDIT)
    E.fact("level02_100pct_media_class",
           req(audit, "movies", HUND, "media_class", where=AUDIT), AUDIT)
    E.fact("level02_100pct_replayed_by_this_row", HUND in replayed, AUDIT)

    # is that unused candidate actually intact? (same predicate the census uses)
    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    fixset = E.json(FIXSET)
    hpin = req(fixset, "entries", HUND, where=FIXSET)
    E.fact("level02_100pct_centrally_pinned", HUND in req(fixset, "entries", where=FIXSET),
           FIXSET)
    E.fact("level02_100pct_bytes_match_pin",
           sha256_file(ROOT / HUND) == req(hpin, "sha256", where=FIXSET), FIXSET)

    # ⚠️ the central pin credits F02 tools with consuming the 100% run. Check it.
    gen_refs = [g for g in req(hpin, "generator_references", where=FIXSET) if "f02" in g]
    really = sum(1 for g in gen_refs if HUND in E.text(g))
    E.fact("f02_tools_credited_with_100pct_movie", len(gen_refs), FIXSET)
    E.fact("f02_tools_that_actually_reference_it", really, [FIXSET] + gen_refs)

    # ------------------------------------------------------------------ #
    # 7. source closure: what build unit owns each governing function?    #
    #    (addresses derived from this row's artifacts, never hand-typed)  #
    # ------------------------------------------------------------------ #
    SEG = "config/segments.yml"
    seg = E.yaml(SEG)

    def as_int(v) -> int:
        return v if isinstance(v, int) else int(str(v), 16)

    units = [(as_int(req(e, "start", where=SEG)), as_int(req(e, "end", where=SEG)),
              req(e, "source", where=SEG)) for e in req(seg, "attempted", where=SEG)]
    governing = {"contact_pickup_walker": as_int(req(bind, "walker", where=BIND))}
    for name, g in gates.items():
        governing[f"gate_{name}_test_pc"] = as_int(req(g, "test_pc", where=PROBE))
    for addr, label in req(trace, "watched", where=TRACE).items():
        governing[label] = as_int(addr)
    governing["overlay_debris_call_pc"] = as_int(req(ovl, "debris_call_pc", where=OVL))

    resolved, unresolved = {}, []
    for name, addr in governing.items():
        src = next((s for lo, hi, s in units if lo <= addr < hi), None)
        (resolved.setdefault(src, []).append(name) if src else unresolved.append(name))
    E.fact("governing_addresses", len(governing), [BIND, PROBE, TRACE, OVL])
    E.fact("governing_build_units", len(resolved), SEG)
    E.fact("governing_units_matching_c",
           len([s for s in resolved if s.startswith("src/")]), SEG)
    E.fact("governing_units_hand_asm",
           len([s for s in resolved if s.startswith("asm/")]), SEG)
    E.fact("governing_addresses_outside_resident_build", len(unresolved), SEG)

    OVLD = "analysis/overlay_decomp_progress.json"
    ovld = E.json(OVLD)
    ovl_name = Path(F["spawner_overlay_image"]).stem          # OVL/LEVEL03_LEVEL.BIN
    E.fact("spawner_overlay_code_functions",
           req(ovld, "per_overlay_totals", ovl_name, where=OVLD), OVLD)
    E.fact("spawner_overlay_matched_functions",
           sum(req(r, "matched_functions", where=OVLD)
               for r in req(ovld, "results", where=OVLD) if r["overlay"] == ovl_name), OVLD)

    # the src_re files for these functions self-declare their grade
    SRC_RE = "src_re/contact_alloc_80059e44.c"
    E.fact("src_re_self_declared_grade",
           "documentation-grade pseudocode" in E.text(SRC_RE), SRC_RE)

    # ------------------------------------------------------------------ #
    # 8. cross-row evidence bearing on the row's DECLARED missing item    #
    # ------------------------------------------------------------------ #
    E02D = "analysis/phase4_e02_disc_region_code_census.json"
    e02d = E.json(E02D)
    t = req(e02d, "levels", "stage02_tunnels", where=E02D)
    hist = req(t, "code_histogram", where=E02D)
    E.fact("tunnels_authored_sectors", req(t, "authored_sectors", where=E02D), E02D)
    E.fact("tunnels_region_code_histogram", hist, E02D)
    E.fact("tunnels_exit_code_sectors", hist.get("3", 0), E02D)
    E.fact("tunnels_instant_kill_sectors", hist.get("1", 0), E02D)
    E.fact("tunnels_exit_sector_ids",
           [s["sector"] for s in req(t, "nonzero_sectors", where=E02D) if s["code"] == 3], E02D)
    E.fact("e02_disc_runtime_disagreements",
           len(req(e02d, "agreement", "disagreements", where=E02D)), E02D)

    E02C = "analysis/phase4_e02_consumer_binding.json"
    e02c = E.json(E02C)
    E.fact("region_code3_consumer_branch",
           req(e02c, "callers", "player_dispatch_0x80048138", "branches", "3", where=E02C), E02C)
    E.fact("region_query_function", req(e02c, "query", "fn", where=E02C), E02C)

    # ------------------------------------------------------------------ #
    # AUTHORED JUDGMENTS against the WRITTEN bars                         #
    # ------------------------------------------------------------------ #
    half = ("this row names TWO subjects -- gates AND falling debris -- plus a declared "
            "missing objective/completion condition; the debris half carries essentially "
            "all of the row's own evidence")

    dims = {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"{CENSUS} -- {F['census_durable_reason']}. This assessment fails "
                     "loudly if that measurement ever moves off 'met'",
            "gap": None,
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the debris negative is measured on natural execution of a pinned "
                     f"pristine-media movie ({F['live_game_serial']}, v"
                     f"{F['evidence_movie_version']}, {F['evidence_movie_frames']} frames) "
                     f"with no perturbation: {F['live_gate_examinations']} gate "
                     f"examinations, {F['live_flags20_examinations']} of them on "
                     f"flags-{F['debris_flags']} records, {F['live_gate_leaks']} leaks, "
                     f"{F['live_unpairable_passes']} unpairable passes, truncated="
                     f"{F['live_any_gate_truncated']}; a POSITIVE CONTROL "
                     f"({F['live_positive_control_passes']} passes on one gate) shows the "
                     f"method detects a pass, and the spawner control fired "
                     f"{F['live_debris_spawns']} times on domain "
                     f"{F['live_debris_spawn_a3_domain']}",
            "gap": f"no oracle at all for the row's declared missing item "
                   f"('{F['row_declared_missing']}'); no executable assertion artifact is "
                   f"registered for this row (the probe measures, it does not assert); and "
                   f"the anchor is a save state, not a cold boot "
                   f"(from_boot={F['evidence_movie_from_boot']}), so load/boot behaviour is "
                   f"outside the oracle's reach",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"for the debris half the frontier IS enumerated and its residual IS "
                     f"bounded: {F['pool_base_reference_sites']} resident sites referencing "
                     f"the pool base, {F['walker_dispatch_entries']} walker-dispatch entries, "
                     f"{F['metab_rows']} metadata rows, {F['alloc_callers_distinct']} distinct "
                     f"live allocator callers over {F['alloc_events']} events, the spawner "
                     f"pinned uniquely to a FILE ({F['spawner_overlay_image']}, "
                     f"{F['spawner_callers_matched']} callers matched, unique="
                     f"{F['spawner_pin_unique']}), and {F['enumerated_residuals']} residuals "
                     f"written up under '{F['residual_section_heading']}' -- including the "
                     f"named limit that the consumer scan would still miss a pool reference "
                     f"reached through a stored pointer",
            "gap": f"{half}. No frontier is enumerated for the gate machinery or the "
                   f"objective/completion path in THIS row; scoped to the debris half alone "
                   f"this would be a met-candidate, scoped to the row as named it is not",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle, and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"every F02 artifact replays the SAME single route: "
                     f"{F['distinct_movies_replayed_by_f02_artifacts']} distinct movie across "
                     f"all of them, one level, one any% route. The pinned corpus holds "
                     f"{F['level02_movies_pinned']} LEVEL02 movies and "
                     f"{F['level02_saves_pinned']} LEVEL02 saves, of which the row declares "
                     f"{F['row_declared_fixtures']} fixtures total; the "
                     f"{F['level02_100pct_frames']}-frame 100% run (v"
                     f"{F['level02_100pct_format_version']}, "
                     f"{F['level02_100pct_media_class']}, bytes match pin="
                     f"{F['level02_100pct_bytes_match_pin']}) has never been replayed by this "
                     f"row (replayed_by_this_row={F['level02_100pct_replayed_by_this_row']})",
            "gap": "the applicability universe is unenumerated in both directions: which "
                   "stages instantiate this contact class (the experiment names a second "
                   "call site in another level and did not replay it), and which routes / "
                   "variants / exceptional paths within Tunnels are in scope. 'Every "
                   "applicable' still has no denominator",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"the contact record is typed field-by-field from the image and the "
                     f"chain is written down ({F['record_field_chain']}); "
                     f"{F['classes_typed_statically']} ctor types resolved statically against "
                     f"{F['metab_rows']} metadata rows, and the live run bounds observed value "
                     f"domains for {F['live_ctor_types_censused']} ctor types across "
                     f"{F['live_pool_samples']} pool samples",
            "gap": "three flags bits have no located consumer, so their domain is measured "
                   "but their meaning is inference; the render-attribute table's field "
                   "semantics are self-declared inferred-not-proven in the decompilation "
                   "header; and no state at all is typed for the gates or the "
                   "objective/completion condition",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"allocation and repeated use are measured live ({F['live_debris_spawns']} "
                     f"spawns, {F['alloc_events']} allocator events); reuse is measured as "
                     f"round-robin recycling ({F['capture_slots_that_changed']}/"
                     f"{F['capture_pool_slots']} slots changed over "
                     f"{F['capture_pool_samples']} samples); the load/idle phase is captured "
                     f"from a save anchor ({F['save_anchor_occupied_slots']} occupied slots, "
                     f"{F['save_anchor_records_changing']} records changing, pool RAM changed="
                     f"{F['save_anchor_pool_ram_changed']})",
            "gap": f"no cold boot in the evidence base at all "
                   f"(from_boot={F['evidence_movie_from_boot']}); retirement (the distance "
                   f"cull) is a static decode that was never sampled live; exhaustion of the "
                   f"{F['capture_pool_slots']}-slot pool was never provoked; no per-phase "
                   f"claim map is registered for this row the way F01 has one; and nothing "
                   f"covers the gates' or the objective's lifecycle",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"one native crossing is measured end-to-end and negatively: player "
                     f"traversal through a live debris field for the whole run, with health "
                     f"written {F['live_health_writes']} times from "
                     f"{F['live_health_writer_pcs']} PCs and none on a contact path; the pool "
                     f"is also crossed against the actor system with "
                     f"{F['live_positive_control_passes']} demonstrated passes for other "
                     f"classes",
            "gap": f"{F['live_gates_with_zero_passes_for_any_class']} of "
                   f"{F['live_gates_total']} pool gates never passed for ANY class in the "
                   f"traced run, so the pickup-collection and berry-projectile crossings were "
                   f"never exercised -- the row states this itself as its fixture need "
                   f"('{F['row_declared_fixture_need']}'). No combination matrix exists for "
                   f"gates x grain x exit",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the central allocator's ABI is documented and its argument domains are "
                     f"MEASURED per caller: {F['alloc_callers_with_arg_domains']} callers with "
                     f"recorded a0/a1/a3 domains over {F['alloc_call_signatures']} distinct "
                     f"call signatures; the metadata-row -> record field mapping is written "
                     f"down; the superseded predecessor artifact is explicitly marked "
                     f"(superseded_artifact_marked={F['superseded_artifact_marked']}) rather "
                     f"than deleted, which is what the contract asks for superseded claims",
            "gap": "the semantic half is unresolved with named obstructions (unconsumed flags "
                   "bits; inferred-not-proven render-attribute fields), and the gate/objective "
                   "interfaces in the stage overlay are undocumented in this row",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured, not assumed: {F['governing_addresses']} governing code "
                     f"addresses taken from this row's own artifacts resolve to "
                     f"{F['governing_build_units']} build units in the segments registry -- "
                     f"{F['governing_units_matching_c']} matching C and "
                     f"{F['governing_units_hand_asm']} hand-written byte-exact ASM. "
                     f"{F['governing_addresses_outside_resident_build']} address is overlay "
                     f"code with no resident build unit, and its image "
                     f"({F['spawner_overlay_image']}) has "
                     f"{F['spawner_overlay_matched_functions']} matched functions out of "
                     f"{F['spawner_overlay_code_functions']} in the overlay census. The "
                     f"src_re file for the allocator self-declares documentation-grade "
                     f"pseudocode ({F['src_re_self_declared_grade']}), so it is not the "
                     f"build unit and does not count. Census triage agrees: "
                     f"'{F['census_triage_source_closure']}'",
            "gap": f"byte-exact reassembly is not the written bar; C through the original "
                   f"toolchain is. Nothing in this row is even attempted at the C level, and "
                   f"the stage's own overlay has no decompilation track entry. (For "
                   f"contrast, the function that would govern the row's EXIT path is "
                   f"byte-matched C -- {F['region_query_function']} -- but it belongs to "
                   f"E02/F01, not to this row's governing set.)",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F02_tunnels measured against the nine DoD dimensions AS WRITTEN "
                    "(item 2 = enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f02_written_bar_assessment.py",
        "schema": "abl-phase4-f02-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": ROW_ID,
        "row_name": row["name"],
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
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor did not author F02's underlying evidence, but "
                               "did author this assessment, the F01 exemplar it copies, and "
                               "the F-row census whose durable_evidence result it carries "
                               "forward -- so the standard being applied and the application "
                               "of it share an author. Every state below is a submission to "
                               "a fresh detached verifier, not a promotion; `partial` and "
                               "`not_met` are as challengeable as a `met` would be",
        },
        "carried_forward": {
            "dimension": "durable_evidence",
            "from": CENSUS,
            "state": F["census_durable_state"],
            "fraction": F["census_durable_fraction"],
            "note": "measured there against pinned bytes; re-deriving it here would be a "
                    "second opinion on a settled measurement, not evidence",
        },
        "registry_disposition_for_contrast": {
            "source": DEBT,
            "completion_state": F["registry_completion_state"],
            "dimensions_met": F["registry_dimensions_met"],
            "dimensions_remaining": F["registry_dimensions_remaining"],
            "distinct_basis_strings": F["registry_distinct_bases"],
            "note": "the registry carries ONE blanket basis across all nine dimensions and "
                    "scores the row 0/9. That is a disposition, not a measurement -- and it "
                    "understates the row: durable_evidence is measured met and five other "
                    "dimensions hold real, bounded evidence",
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
                   f"unmeasured -- against the WRITTEN bars. The row is honestly "
                   f"half-answered: the falling-debris half is closed to a reviewed "
                   f"structural negative with {F['enumerated_residuals']} enumerated "
                   f"residuals, the gates half and the declared objective/completion "
                   f"condition carry no evidence in this row, and no dimension reaches met "
                   f"except the one measured elsewhere.",
        "notable": [
            f"The row's evidence base is ONE route. "
            f"{F['level02_movies_pinned']} LEVEL02 movies are already pinned "
            f"({F['level02_e09_gate_movies_pinned']} E09 gate movies, "
            f"{F['level02_e10_hazard_movies_pinned']} E10 hazard movies, plus a "
            f"{F['level02_100pct_frames']}-frame 100% Interpreter run); the row declares "
            f"{F['row_declared_fixtures']} fixtures and asks for a NEW recording. Whether "
            f"the 100% run satisfies that need is UNMEASURED here (it needs a replay) -- "
            f"but this row has been burned once before by assuming the corpus lacked a "
            f"movie it already had.",
            f"{F['f02_tools_credited_with_100pct_movie']} F02 tools are credited as "
            f"generator_references of the 100% movie in the central pin; "
            f"{F['f02_tools_that_actually_reference_it']} of them actually name that path. "
            f"The credit appears to come from a basename collision with the any% run and "
            f"should not be read as breadth coverage.",
            f"{F['other_baseline_rows_naming_stage2']} other baseline rows name this stage: "
            f"{', '.join(F['other_baseline_rows_naming_stage2_ids'])} -- and this row cites "
            f"{F['row_artifact_path_citations']} artifact paths in total, none of them "
            f"theirs. E09 binds the LEVEL02 grain-gate mechanism, which is this row's OWN "
            f"first named subject ('gates'). Separately the pinned corpus holds "
            f"{F['level02_e10_hazard_movies_pinned']} E10 LEVEL02 hazard movies (falling "
            f"rocks and pits) that no F02 artifact touches. A verifier scoping this row "
            f"should decide what belongs to F02 and what is already owned elsewhere before "
            f"any of these dimensions is re-measured.",
            f"The row's declared missing item is the stage-2 objective/completion "
            f"condition, and a cross-row artifact already bounds the exit half of it: the "
            f"disc-side region-code census locates Tunnels' "
            f"{F['tunnels_authored_sectors']} authored sectors with histogram "
            f"{F['tunnels_region_code_histogram']} -- exactly "
            f"{F['tunnels_exit_code_sectors']} exit-code sector (id "
            f"{F['tunnels_exit_sector_ids']}) and {F['tunnels_instant_kill_sectors']} "
            f"instant-kill sectors, with {F['e02_disc_runtime_disagreements']} disc/runtime "
            f"disagreements; the consumer binding gives that code's branch as: "
            f"{F['region_code3_consumer_branch']}. This is EXIT, not OBJECTIVE -- it does "
            f"not close the row's missing item, but the row does not record it at all.",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar F02] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} derived / "
          f"{doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
