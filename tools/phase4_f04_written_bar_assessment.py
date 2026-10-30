#!/usr/bin/env python3
"""Measure F04_cliffside_canyon's nine DoD dimensions against the bars AS WRITTEN.

Standard: `engineering-specs/phase4-measurement-standard-ruling.md`. One standard,
applied per-dimension, against each bar as written:

  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

Exemplars: `tools/phase4_f01_written_bar_assessment.py` (the first test case) and
`tools/phase4_f02_written_bar_assessment.py` (the sibling this copies most closely).
Same contract: JUDGMENTS are authored and attributable and carry
`written_bar`/`basis`/`gap`; every FACT they rest on is derived from a pinned
artifact at run time. `fact()` cannot record a value without naming a pinned
artifact and `req()` raises on a missing key, so a stale citation fails LOUDLY
instead of aging silently. `unmeasured` is an allowed and expected state.

WHY F04 IS ITS OWN SHAPE
------------------------
F01 was one subject driven hard. F02 was two subjects, one closed to a negative.
F04 is a row that was answered almost entirely BY CITATION: three donor rows
(B03 dandelion, D17 bird, D11 mite) supplied the mechanisms, and a single
route replay of an existing movie supplied the composition. Nothing about the
STAGE was investigated on its own terms. Measuring it therefore has to keep asking
one question per dimension: does the cited evidence establish the MECHANISM, or
does it establish the STAGE? Those are different claims, and this row's own
`missing` field concedes the difference in its retained residuals.

THIS TOOL DOES THREE THINGS PROSE CANNOT
-----------------------------------------
1. It COMPILES AND RUNS a C probe (`tools/phase4_f04_static_probe.c`) that decodes
   the pristine images. The row's own static reducer, `phase4_f04_route_analyzer.c`,
   cannot run at all today -- it opens the transient /tmp trace TSVs before doing
   anything, and those died with the 2026-08-04 session -- so its six "exact sites"
   have been unverifiable since the day they were written. The probe re-derives
   each site's EFFECTIVE ADDRESS from the instruction words.
2. It measures the row's own named retained residual -- "the Cliffside-overlay
   writer of power bit 0x10" -- instead of repeating the inference.
3. It RUNS the row's registered test module and reports the result, rather than
   assuming a checked-in test still passes.

`durable_evidence` is NOT re-derived here: it was MEASURED in
`analysis/phase4_f_row_measured_census.json` (7/7 declared fixtures intact) and is
carried forward with its fraction, failing loudly if that measurement ever moves.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a fresh
detached verifier. `analysis/mechanics_baseline.yaml` is read, never written.

Usage:
    python3 tools/phase4_f04_written_bar_assessment.py [--out PATH] [--root DIR]
    python3 tools/phase4_f04_written_bar_assessment.py --verify-fail-loud
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ROW = "F04_cliffside_canyon"

CC_FLAGS = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class Evidence:
    """Loads + pins artifacts, and records which artifact every fact came from."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.pins: list[dict] = []
        self._seen: set[str] = set()
        self.facts: dict[str, object] = {}
        self.provenance: dict[str, object] = {}

    def pin(self, rel: str) -> Path:
        p = self.root / rel
        if not p.exists():
            raise SystemExit(f"STALE CITATION: {rel} does not exist under {self.root}")
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
        if key in self.facts:
            raise SystemExit(f"fact '{key}' recorded twice")
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


# --------------------------------------------------------------------------- #
# The compiled-C static probe: build it, drive it from pinned artifacts, read   #
# the decode back. Nothing about the instruction stream is trusted from prose.  #
# --------------------------------------------------------------------------- #

def run_static_probe(E: Evidence, workdir: Path, index: dict, index_rel: str,
                     site_pcs: dict[str, str], targets: dict[str, str]) -> dict:
    src_rel = "tools/phase4_f04_static_probe.c"
    src = E.pin(src_rel)
    exe = workdir / "phase4_f04_static_probe"
    cc = os.environ.get("CC", "cc")
    proc = subprocess.run([cc, *CC_FLAGS, "-o", str(exe), str(src)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"C probe failed to build:\n{proc.stderr}")

    imgs = {i["image_id"]: i for i in req(index, "images", where=index_rel)}
    plan = []
    for iid, i in imgs.items():
        path = req(i, "path", where=index_rel)
        if not (E.root / path).exists():
            raise SystemExit(f"STALE CITATION: image {path} named by {index_rel} is absent")
        plan.append("\t".join(["IMAGE", iid, str(E.root / path),
                               req(i, "file_va_base", where=index_rel),
                               str(req(i, "header_rule", "bytes", where=index_rel))]))
    ranges = 0
    for r in req(index, "records", where=index_rel):
        if r.get("range_type") != "code":
            continue
        plan.append("\t".join(["RANGE", r["image_id"], r["entry"], r["end"]]))
        ranges += 1
    if not ranges:
        raise SystemExit(f"STALE CITATION: {index_rel} yielded no code ranges")
    for name, pc in site_pcs.items():
        plan.append("\t".join(["SITE", name, "SCUS_942_88", pc]))
    for name, addr in targets.items():
        plan.append("\t".join(["TARGET", name, addr]))

    plan_path = workdir / "plan.tsv"
    plan_path.write_text("\n".join(plan) + "\n")
    out = subprocess.run([str(exe), str(plan_path)], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"C probe exited {out.returncode}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def build_symlink_farm(dst: Path, root: Path, drop: str | None,
                       mutate: tuple[str, str, str] | None) -> Path:
    """Mirror `root` with symlinks so a single artifact can be removed or mutated."""
    farm = dst / "farm"
    farm.mkdir()
    special = "analysis"
    for child in root.iterdir():
        if child.name in {".git", ".claude"}:
            continue
        if child.name == special:
            mirror = farm / special
            mirror.mkdir()
            for f in child.iterdir():
                rel = f"{special}/{f.name}"
                if drop == rel:
                    continue
                if mutate and mutate[0] == rel:
                    doc = json.loads(f.read_text())
                    if mutate[1] not in doc:
                        raise SystemExit(f"fail-loud fixture: {rel} has no key {mutate[1]}")
                    doc[mutate[2]] = doc.pop(mutate[1])
                    (mirror / f.name).write_text(json.dumps(doc))
                    continue
                (mirror / f.name).symlink_to(f)
        else:
            (farm / child.name).symlink_to(child)
    return farm


def verify_fail_loud(root: Path) -> dict:
    """PROVE the loudness rather than asserting it, by running this tool against a
    symlink farm in which exactly one thing is wrong."""
    me = Path(__file__).resolve()
    cases = [
        {"case": "missing_artifact",
         "detail": "analysis/phase4_f04_route_analysis.json removed from the farm",
         "drop": "analysis/phase4_f04_route_analysis.json", "mutate": None},
        {"case": "renamed_key",
         "detail": "analysis/phase4_f04_route_analysis.json's 'runtime' key renamed",
         "drop": None,
         "mutate": ("analysis/phase4_f04_route_analysis.json", "runtime", "runtime_RENAMED")},
        {"case": "control_unmodified_farm",
         "detail": "the same farm with nothing wrong must still succeed",
         "drop": None, "mutate": None},
    ]
    results = []
    for c in cases:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            farm = build_symlink_farm(tmp, root, c["drop"], c["mutate"])
            out = tmp / "child_out.json"
            proc = subprocess.run(
                [sys.executable, str(me), "--root", str(farm), "--out", str(out)],
                capture_output=True, text=True)
            expect_fail = c["case"] != "control_unmodified_farm"
            results.append({
                "case": c["case"],
                "detail": c["detail"],
                "exit_code": proc.returncode,
                "output_file_written": out.exists(),
                # the farm lives in a fresh temp dir every run; normalise it out so the
                # published artifact is byte-reproducible
                "stderr_first_line": (proc.stderr.strip().splitlines() or [""])[-1]
                                     .replace(str(farm), "<FARM>")[:200],
                "expected_nonzero_exit": expect_fail,
                "passed": ((proc.returncode != 0 and not out.exists()) if expect_fail
                           else (proc.returncode == 0 and out.exists())),
            })
    return {"cases": results, "all_passed": all(r["passed"] for r in results)}


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO),
                    help="repository root to measure (used by --verify-fail-loud)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--verify-fail-loud", action="store_true",
                    help="run this tool against mutated symlink farms and prove it aborts")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_path = Path(args.out) if args.out else \
        REPO / "analysis/phase4_f04_written_bar_assessment.json"

    fail_loud = verify_fail_loud(root) if args.verify_fail_loud else None
    if fail_loud and not fail_loud["all_passed"]:
        raise SystemExit(f"fail-loud verification FAILED: {json.dumps(fail_loud, indent=1)}")

    E = Evidence(root)
    F = E.facts

    # ------------------------------------------------------------------ #
    # 1. durable_evidence -- CARRIED FORWARD from the measured census.    #
    # ------------------------------------------------------------------ #
    CENSUS = "analysis/phase4_f_row_measured_census.json"
    census = E.json(CENSUS)
    crow = req(census, "rows", ROW, where=CENSUS)
    E.fact("census_durable_state", req(crow, "durable_evidence", "state", where=CENSUS), CENSUS)
    E.fact("census_durable_fraction",
           req(crow, "durable_evidence", "intact_pinned", where=CENSUS), CENSUS)
    E.fact("census_durable_reason",
           req(crow, "durable_evidence", "reason", where=CENSUS), CENSUS)
    E.fact("census_row_status", req(crow, "status", where=CENSUS), CENSUS)
    E.fact("census_declared_evidence_classes",
           req(crow, "evidence_inventory", "declared_evidence_classes", where=CENSUS), CENSUS)
    E.fact("census_derived_evidence_classes",
           req(crow, "evidence_inventory", "derived_evidence_classes", where=CENSUS), CENSUS)
    E.fact("census_analysis_artifacts",
           req(crow, "evidence_inventory", "analysis_artifacts", where=CENSUS), CENSUS)
    E.fact("census_vault_pages",
           req(crow, "evidence_inventory", "vault_pages", where=CENSUS), CENSUS)
    E.fact("census_source_files",
           req(crow, "evidence_inventory", "source_files", where=CENSUS), CENSUS)
    E.fact("census_segments_entries",
           req(crow, "evidence_inventory", "segments_entries", where=CENSUS), CENSUS)
    E.fact("census_triage", req(crow, "measurability_triage", where=CENSUS), CENSUS)
    E.fact("census_baseline_sha256", req(census, "baseline_sha256", where=CENSUS), CENSUS)
    E.fact("census_rows_assessed", req(census, "rows_assessed", where=CENSUS), CENSUS)
    E.fact("census_durable_met_fraction",
           req(census, "durable_evidence_met_fraction", where=CENSUS), CENSUS)
    fixture_counts = sorted(
        ((r_id, len(req(r, "durable_evidence", "fixtures", where=CENSUS)))
         for r_id, r in req(census, "rows", where=CENSUS).items()),
        key=lambda kv: -kv[1])
    E.fact("f_rows_by_declared_fixture_count", fixture_counts[:4], CENSUS)
    E.fact("f04_fixture_rank_among_f_rows",
           1 + [k for k, _ in fixture_counts].index(ROW), CENSUS)
    if F["census_durable_state"] != "met":
        raise SystemExit("carried-forward durable_evidence is no longer 'met' -- "
                         "re-measure before reusing this assessment")

    # ------------------------------------------------------------------ #
    # 2. the registry's own disposition for this row                      #
    # ------------------------------------------------------------------ #
    DEBT = "analysis/phase4_closure_debt.json"
    debt = E.json(DEBT)
    drow = next((r for r in req(debt, "rows", where=DEBT) if r.get("row_id") == ROW), None)
    if drow is None:
        raise SystemExit(f"STALE CITATION: {DEBT} no longer carries {ROW}")
    E.fact("registry_dimensions_met", req(drow, "counts", "met", where=DEBT), DEBT)
    E.fact("registry_dimensions_remaining", req(drow, "counts", "remaining", where=DEBT), DEBT)
    E.fact("registry_distinct_bases",
           sorted({d["basis"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
    E.fact("registry_completion_state", req(drow, "completion_state", where=DEBT), DEBT)
    E.fact("registry_family", req(drow, "family", where=DEBT), DEBT)
    E.fact("registry_movie_count", req(drow, "movie_count", where=DEBT), DEBT)
    E.fact("registry_capsule_count", req(drow, "capsule_count", where=DEBT), DEBT)
    E.fact("registry_prior_offline_analyses",
           req(drow, "prior_offline_analysis_count", where=DEBT), DEBT)

    # ------------------------------------------------------------------ #
    # 3. the baseline row itself (read-only; this tool never edits it)    #
    # ------------------------------------------------------------------ #
    BASE = "analysis/mechanics_baseline.yaml"
    base = E.yaml(BASE)
    rows = req(base, "rows", where=BASE)
    row = next((r for r in rows if r.get("id") == ROW), None)
    if row is None:
        raise SystemExit(f"STALE CITATION: {BASE} no longer carries {ROW}")
    E.fact("row_name", req(row, "name", where=BASE), BASE)
    E.fact("row_stages", req(row, "stages", where=BASE), BASE)
    E.fact("row_status", req(row, "status", where=BASE), BASE)
    E.fact("row_evidence_classes", req(row, "evidence", where=BASE), BASE)
    E.fact("row_binding_claims", len(req(row, "bindings", where=BASE)), BASE)
    E.fact("row_declared_fixtures", req(row, "fixture_have", where=BASE), BASE)
    E.fact("row_declared_missing", req(row, "missing", where=BASE), BASE)
    E.fact("row_declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
    E.fact("row_declared_next", req(row, "next", where=BASE), BASE)
    E.fact("row_artifact_path_citations",
           len(set(re.findall(r"(?:analysis|tools|src_re|movies)/[\w %.,/-]+?\.(?:json|c|py|yaml|md)",
                              json.dumps(row)))), BASE)
    E.fact("row_synthesis_binding_count",
           sum(1 for b in req(row, "bindings", where=BASE) if "SYNTHESIZED FROM" in b), BASE)

    # `secondary_lead` is declared as one of this row's four evidence classes. What
    # IS it? The baseline header lists the legal class names; the only artifact that
    # gives the class a definition treats it as explicitly NON-authoritative.
    header = E.text(BASE)[:2000]
    E.fact("baseline_evidence_class_legend",
           " ".join(l.strip(" #") for l in header.splitlines()
                    if "evidence " in l or "secondary_lead" in l), BASE)
    E.fact("baseline_rows_declaring_secondary_lead",
           sorted(r["id"] for r in rows if "secondary_lead" in (r.get("evidence") or [])), BASE)

    f04_own = ["analysis/phase4_f04_cliffside_canyon.json",
               "analysis/phase4_f04_route_analysis.json",
               "ObsidianVault/Experiments/EXP_2026-08-03_phase4_f04_cliffside_canyon.md"]
    E.fact("f04_artifacts_citing_an_external_url",
           sorted(a for a in f04_own if "http" in E.text(a).lower()), f04_own)
    E.fact("f04_artifacts_examined_for_a_secondary_source", len(f04_own), f04_own)

    LEAD = "analysis/phase4_spin_heading.json"
    lead = E.json(LEAD)
    E.fact("secondary_lead_role", req(lead, "secondary_lead", "role", where=LEAD), LEAD)
    E.fact("secondary_lead_authority_rule",
           req(lead, "secondary_lead", "authority_rule", where=LEAD), LEAD)

    # Other baseline rows that name this stage. "LEVEL04" is the CHRONOLOGICAL level
    # here (Cliffside is scene 6, disc dir LEVEL06/), so both tokens are counted --
    # F02's lesson about ambiguous LEVELxx tokens applies in the other direction.
    # ⚠️ "LEVEL04" is AMBIGUOUS in this project. Cliffside is CHRONOLOGICAL level 4 but
    # scene 6, loading from disc dir LEVEL06/; disc dir LEVEL04/ is a DIFFERENT stage.
    # Movie filenames use the chronological number, disc paths use the directory. Count
    # the unambiguous scene tokens separately from the ambiguous one -- F02's lesson.
    unambig = re.compile(r"[Cc]liffside|scene_id=6|LEVEL06")
    ambig = re.compile(r"LEVEL04")
    named = sorted(r["id"] for r in rows
                   if r.get("id") != ROW and unambig.search(json.dumps(r)))
    amb_only = sorted(r["id"] for r in rows
                      if r.get("id") != ROW and ambig.search(json.dumps(r))
                      and not unambig.search(json.dumps(r)))
    E.fact("other_baseline_rows_naming_stage4", len(named), BASE)
    E.fact("other_baseline_rows_naming_stage4_ids", named, BASE)
    E.fact("baseline_rows_matching_only_the_ambiguous_level04_token", amb_only, BASE)

    for donor in ("B03_dandelion_glide", "D17_bird", "D11_mites_grubs"):
        d = next((r for r in rows if r.get("id") == donor), None)
        if d is None:
            raise SystemExit(f"STALE CITATION: {BASE} no longer carries donor row {donor}")
        key = donor.split("_")[0].lower()
        E.fact(f"donor_{key}_status", req(d, "status", where=BASE), BASE)
        E.fact(f"donor_{key}_stages", req(d, "stages", where=BASE), BASE)
    E.fact("donor_b03_declared_missing",
           next(req(r, "missing", where=BASE) for r in rows if r["id"] == "B03_dandelion_glide"),
           BASE)

    # ------------------------------------------------------------------ #
    # 4. this row's own artifacts                                         #
    # ------------------------------------------------------------------ #
    ROUTE = "analysis/phase4_f04_route_analysis.json"
    route = E.json(ROUTE)
    rstat = req(route, "static_asm", where=ROUTE)
    rrun = req(route, "runtime", where=ROUTE)
    E.fact("route_static_all_sites_match", req(rstat, "all_exact_sites_match", where=ROUTE), ROUTE)
    E.fact("route_static_site_pcs",
           {k: v for k, v in rstat.items() if k != "all_exact_sites_match"}, ROUTE)
    for k in ("scene_load_movie_frame", "dandelion_launch_movie_frame",
              "dandelion_handler_hits", "launch_hits", "latch11_exec_hits",
              "latch11_access_writes", "latch_first_movie_frame",
              "grounded_latch_clear_movie_frame", "latch_residence_frames",
              "first_scene6_exit_movie_frame", "scene_exit_after_ground_frames",
              "damage_branch_hits", "life_decrements_after_launch",
              "all_logs_untruncated", "ordered_success_route"):
        E.fact(f"route_{k}", req(rrun, k, where=ROUTE), ROUTE)

    MAIN = "analysis/phase4_f04_cliffside_canyon.json"
    main_doc = E.json(MAIN)
    ident = req(main_doc, "ROUTE_CLOSURE_2026-08-04", "identity", where=MAIN)
    for k in ("movie_version", "movie_frames", "armed_while_paused", "reproducible",
              "game_serial", "execution_mode", "duckstation_revision"):
        E.fact(f"route_identity_{k}", req(ident, k, where=MAIN), MAIN)
    E.fact("route_identity_hashes_present",
           sorted(k for k in ident if k.endswith("sha256")), MAIN)
    method = req(main_doc, "ROUTE_CLOSURE_2026-08-04", "method", where=MAIN)
    E.fact("route_method_disclaims_advance_to_frame",
           "No fast-forward or movie.advanceToFrame was used" in method, MAIN)
    E.fact("route_method_armed_after_state_load",
           "armed only after the state load" in method, MAIN)
    E.fact("row_bounded_exhaustion_status",
           req(main_doc, "BOUNDED_EXHAUSTION_2026-08-04", "status", where=MAIN), MAIN)
    still_open = req(main_doc, "STILL_OPEN", where=MAIN)
    E.fact("row_retained_residuals",
           [s.strip() for s in still_open.split(":", 1)[-1].split(";") if s.strip()], MAIN)
    E.fact("row_retained_residual_count",
           len([s for s in still_open.split(":", 1)[-1].split(";") if s.strip()]), MAIN)
    E.fact("kill_zone_not_closed_by_d17",
           req(main_doc, "KILL_ZONE_SYNTHESIZED_FROM_D17_2026-08-03",
               "not_fully_closed_by_d17", where=MAIN), MAIN)
    E.fact("row_pass1_did_no_new_instrumentation",
           "No new live instrumentation" in req(main_doc, "status", where=MAIN), MAIN)

    EXP = "ObsidianVault/Experiments/EXP_2026-08-03_phase4_f04_cliffside_canyon.md"
    exp = E.text(EXP)
    if "## Residuals" not in exp:
        raise SystemExit(f"STALE CITATION: {EXP} no longer has a '## Residuals' section")
    resid = exp.split("## Residuals", 1)[1].split("\n**Assessment**", 1)[0]
    E.fact("experiment_residual_items", len([s for s in resid.split(";") if s.strip()]), EXP)
    E.fact("experiment_concedes_stage_flow_unaddressed",
           "never addressed by any of the three donor rows" in exp, EXP)
    E.fact("experiment_concedes_fixture_need_unsatisfied",
           "was never satisfied by any fixture, still isn't" in exp, EXP)

    SCEN = "tools/scenarios/duckstation/phase4_f04_cliffside_canyon.yaml"
    scen = E.yaml(SCEN)
    phases = req(scen, "phases", where=SCEN)
    assertions = [a for p in phases for a in req(p, "assertions", where=SCEN)]
    E.fact("scenario_phases", len(phases), SCEN)
    E.fact("scenario_assertions", len(assertions), SCEN)
    E.fact("scenario_semantic_ids", sorted({a["semantic_id"] for a in assertions}), SCEN)
    E.fact("scenario_addresses",
           sorted({f"0x{a['address']:08X}" for a in assertions}), SCEN)
    E.fact("scenario_requires_reproducible",
           req(scen, "playback", "require_reproducible", where=SCEN), SCEN)
    E.fact("scenario_movie", req(scen, "playback", "movie", where=SCEN), SCEN)
    E.fact("scenario_assertion_ids", sorted(a["id"] for a in assertions), SCEN)
    scen_id = req(scen, "id", where=SCEN)
    named_in, results_in = [], []
    for cand in sorted((root / "analysis").glob("*.json")):
        rel = f"analysis/{cand.name}"
        body = cand.read_text(errors="ignore")
        if scen_id in body:
            named_in.append(rel)
            if any(aid in body for aid in F["scenario_assertion_ids"]):
                results_in.append(rel)
    E.fact("scenario_id_named_in_analysis_artifacts", named_in, SCEN)
    E.fact("analysis_artifacts_recording_scenario_assertion_outcomes", results_in, SCEN)

    # ------------------------------------------------------------------ #
    # 5. the row's registered test module -- RUN, not assumed             #
    # ------------------------------------------------------------------ #
    TEST = "tests/test_phase4_f04_cliffside_canyon.py"
    E.pin(TEST)
    tp = subprocess.run([sys.executable, "-m", "pytest", str(root / TEST), "-q",
                         "--no-header", "--color=no", "-p", "no:cacheprovider"],
                        capture_output=True, text=True, cwd=str(root))
    plain = re.sub(r"\x1b\[[0-9;]*m", "", tp.stdout)
    t_passed = int((re.search(r"(\d+) passed", plain) or re.match(r"(0)", "0")).group(1))
    fm = re.search(r"(\d+) failed", plain)
    t_failed = int(fm.group(1)) if fm else 0
    if not re.search(r"\d+ (passed|failed)", plain):
        raise SystemExit(f"could not parse pytest summary for {TEST}")
    # a parse that disagrees with the process's own verdict is a parse bug, not a result
    if (t_failed > 0) != (tp.returncode != 0):
        raise SystemExit(f"pytest summary parse ({t_failed} failed) contradicts exit code "
                         f"{tp.returncode} for {TEST}")
    E.fact("row_test_module_tests", t_passed + t_failed, TEST)
    E.fact("row_test_module_passed", t_passed, TEST)
    E.fact("row_test_module_failed", t_failed, TEST)
    E.fact("row_test_module_exit_code", tp.returncode, TEST)
    failing = sorted(set(re.findall(r"FAILED [^:]+::(\w+)", plain)))
    E.fact("row_test_module_failing_tests", failing, TEST)
    E.fact("row_test_module_failing_assertions",
           [a[:180] for a in sorted(set(re.findall(r"^E\s+(AssertionError.*)$",
                                                    plain, re.M)))[:1]], TEST)

    # ------------------------------------------------------------------ #
    # 6. donor evidence: what B03 / D17 / D11 actually establish          #
    # ------------------------------------------------------------------ #
    B03S = "analysis/phase4_b03_dandelion_static.json"
    b03s = E.json(B03S)
    E.fact("b03_static_corpus_files", req(b03s, "corpus", "files", where=B03S), B03S)
    E.fact("b03_static_corpus_instructions",
           req(b03s, "corpus", "instructions", where=B03S), B03S)
    lf = req(b03s, "latch_frontier", where=B03S)
    for k in ("scope", "absolute_sites", "typed_player_relative_sites", "total",
              "reads", "writes", "all_writes_literal_0_11_or_12"):
        E.fact(f"b03_latch_{k}", req(lf, k, where=B03S), B03S)
    E.fact("b03_lifecycle_clears",
           {k: v for k, v in req(b03s, "lifecycle_contract", where=B03S).items()
            if k.endswith("clear")}, B03S)
    E.fact("b03_activation_contract", req(b03s, "activation_contract", where=B03S), B03S)
    E.fact("b03_deferred_items",
           req(b03s, "bounded_exhaustion", "deferred", where=B03S), B03S)
    E.fact("b03_row_solved_flag",
           req(b03s, "bounded_exhaustion", "phase4_row_solved", where=B03S), B03S)

    B03R = "analysis/phase4_b03_dandelion_runtime.json"
    b03r = E.json(B03R)
    E.fact("b03_runtime_trace_events", req(b03r, "trace_events", where=B03R), B03R)
    E.fact("b03_runtime_truncated", req(b03r, "trace_reported_truncated", where=B03R), B03R)
    E.fact("b03_runtime_control_cycle_neutral",
           req(b03r, "control_comparison", "bounded_cycle_neutral", where=B03R), B03R)
    for k in ("latch11_access_writes", "latch_active_player_updates",
              "first_latch_active_movie_frame", "last_latch_active_movie_frame"):
        E.fact(f"b03_glide_{k}", req(b03r, "glide", k, where=B03R), B03R)
    E.fact("b03_steering_changed_velocity_pairs",
           req(b03r, "steering", "changed_velocity_pairs", where=B03R), B03R)

    B03C = "analysis/phase4_b03_dandelion_capsule.json"
    b03c = E.json(B03C)
    E.fact("b03_capsule_control_match",
           req(b03c, "evidence_identity", "registry_control_match", where=B03C), B03C)
    E.fact("b03_capsule_parse_exact", req(b03c, "validation", "parse_exact", where=B03C), B03C)
    E.fact("b03_capsule_records", req(b03c, "validation", "records", where=B03C), B03C)
    E.fact("b03_capsule_missing_domains", req(b03c, "missing_domains", where=B03C), B03C)
    # Does ANY B03 artifact record which scene its recording is in? The row cites B03
    # for the STAGE's flight mechanic; B03's own stage claim is a declaration.
    E.fact("b03_artifacts_recording_a_scene_id",
           sum(1 for a in (B03S, B03R, B03C) if "scene" in E.text(a).lower()),
           [B03S, B03R, B03C])
    E.fact("b03_artifacts_examined_for_scene_id", 3, [B03S, B03R, B03C])

    D17 = "analysis/phase4_d17_bird.json"
    d17 = E.json(D17)
    cliff = req(d17, "CLIFFSIDE_HAZARD_ENCOUNTER_2026-08-02", where=D17)
    E.fact("d17_cliffside_subclaims", sorted(cliff.keys()), D17)
    E.fact("d17_cliffside_fixture_frames",
           int(re.search(r"(\d+) frames", req(cliff, "provenance", where=D17)).group(1)), D17)
    E.fact("d17_cliffside_contact_caller_residual",
           req(cliff, "contact_caller_FUNC_8004ABF4", where=D17), D17)
    E.fact("d17_cliffside_radius_test_not_inside",
           "evaluates to NOT-inside at every sampled frame"
           in req(cliff, "contact_caller_FUNC_8004ABF4", where=D17), D17)
    E.fact("d17_bit10_search_scope",
           req(cliff, "power_flags_bit_0x10_checked_not_found", where=D17), D17)
    E.fact("d17_bit10_resident_store_sites_reported",
           len(re.findall(r"0x800[0-9a-f]{5}",
                          req(cliff, "power_flags_bit_0x10_checked_not_found", where=D17))), D17)
    E.fact("d17_bit10_hypothesis_is_overlay",
           "almost certainly OVERLAY code specific to Cliffside"
           in req(cliff, "power_flags_bit_0x10_checked_not_found", where=D17), D17)

    D13 = "analysis/phase4_d13_shell_bug_armor.json"
    d13 = E.json(D13)
    E.fact("mite_level_set_source_claim",
           "id=37/canyon_bug: LEVEL01/06/08/10" in req(d13, "status", where=D13), D13)
    E.fact("d13_says_canyon_bug_savs_manipulated_actor",
           "A third actor (id=30) briefly manipulated in canyon_bug.sav/canyon_bug_aggro.sav"
           in req(d13, "status", where=D13), D13)

    C15 = "analysis/phase4_c15_respawn_anchor.json"
    c15 = E.json(C15)
    c15_txt = json.dumps(c15)
    E.fact("row_fixture_reused_by_c15",
           "movies/Phase4/Interpreter/D17_Cliffside_Bird_Death.movie.json" in c15_txt, C15)
    E.fact("c15_names_f04_as_donor_context", "F04_cliffside_canyon" in c15_txt, C15)

    # ------------------------------------------------------------------ #
    # 7. cross-row EXIT evidence (E02) -- exit is not objective           #
    # ------------------------------------------------------------------ #
    E02D = "analysis/phase4_e02_disc_region_code_census.json"
    e02d = E.json(E02D)
    st4 = req(e02d, "levels", "stage04_cliffside_canyon", where=E02D)
    E.fact("stage4_scene_id", req(st4, "scene", where=E02D), E02D)
    E.fact("stage4_container", req(st4, "container", where=E02D), E02D)
    E.fact("stage4_save_anchor", req(st4, "save", where=E02D), E02D)
    E.fact("stage4_authored_sectors", req(st4, "authored_sectors", where=E02D), E02D)
    E.fact("stage4_runtime_sectors", req(st4, "runtime_sectors", where=E02D), E02D)
    E.fact("stage4_code_histogram", req(st4, "code_histogram", where=E02D), E02D)
    nz = req(st4, "nonzero_sectors", where=E02D)
    E.fact("stage4_nonzero_sectors", nz, E02D)
    E.fact("stage4_disc_vs_runtime_mismatches",
           len(req(st4, "disc_vs_runtime_mismatches", where=E02D)), E02D)
    E.fact("e02_campaign_disagreements",
           len(req(e02d, "agreement", "disagreements", where=E02D)), E02D)
    E.fact("e02_authored_sectors_compared",
           req(e02d, "agreement", "authored_sectors_compared", where=E02D), E02D)

    E02C = "analysis/phase4_e02_consumer_binding.json"
    e02c = E.json(E02C)
    br = req(e02c, "callers", "player_dispatch_0x80048138", "branches", where=E02C)
    E.fact("region_code2_branch", req(br, "2", where=E02C), E02C)
    E.fact("region_code3_branch", req(br, "3", where=E02C), E02C)
    E.fact("region_dispatch_gates",
           req(e02c, "callers", "player_dispatch_0x80048138", "gates", where=E02C), E02C)

    LIFE = "analysis/phase4_f01_objective_lifecycle.json"
    life = E.json(LIFE)
    arms = {str(a["code"]): a for a in req(life, "objective", "arms", where=LIFE)}
    E.fact("code2_arm_effect", req(arms, "2", "effect", where=LIFE), LIFE)
    E.fact("code3_arm_effect", req(arms, "3", "effect", where=LIFE), LIFE)
    E.fact("e02_consumer_binding_calls_code3_identical_to_code2",
           "IDENTICAL body to code 2" in req(br, "3", where=E02C), E02C)
    E.fact("code3_differs_from_code2_only_by_commit_flag",
           req(arms, "2", "effect", where=LIFE).replace("; commit flag sp+0x50=1", "")
           == req(arms, "3", "effect", where=LIFE).replace("; NO commit flag", ""), LIFE)

    # ------------------------------------------------------------------ #
    # 8. the compiled-C static probe                                      #
    # ------------------------------------------------------------------ #
    IDX = "analysis/phase4_static_frontier_index.json"
    index = E.json(IDX)
    POW = "analysis/phase4_b06_b08_powerups.json"
    powdoc = E.json(POW)
    power_word = req(powdoc, "shared_model", "power_flags_word", where=POW)
    latch_word = req(b03s, "target_800a659e_accesses", 0, "address", where=B03S)
    exit_latch = "0x800823A0"
    if exit_latch not in json.dumps(req(e02c, "callers", where=E02C)):
        raise SystemExit("STALE CITATION: E02 consumer binding no longer names the exit latch")
    E.fact("probe_target_power_word", power_word, POW)
    E.fact("probe_target_latch_word", latch_word, B03S)
    E.fact("probe_target_exit_latch", exit_latch, E02C)

    with tempfile.TemporaryDirectory() as td:
        probe = run_static_probe(
            E, Path(td), index, IDX,
            site_pcs={k: v for k, v in F["route_static_site_pcs"].items()},
            targets={"power_flags": power_word, "dandelion_latch": latch_word,
                     "exit_latch": exit_latch})
    PROBE_SRC = "tools/phase4_f04_static_probe.c"
    PROBE_SRCS = [PROBE_SRC, IDX, ROUTE, POW, B03S]
    E.fact("probe_images_decoded", len(probe["images"]), PROBE_SRCS)
    E.fact("probe_code_ranges", probe["scan"]["ranges"], PROBE_SRCS)
    E.fact("probe_instructions_decoded", probe["scan"]["instructions"], PROBE_SRCS)
    E.fact("probe_memops", probe["scan"]["memops"], PROBE_SRCS)
    E.fact("probe_memops_unresolved_base", probe["scan"]["memops_with_unresolved_base"],
           PROBE_SRCS)
    E.fact("probe_sites_missing", probe["sites_missing"], PROBE_SRCS)
    E.fact("probe_sites_unresolved", probe["sites_unresolved"], PROBE_SRCS)
    E.fact("probe_site_effective_addresses",
           {s["name"]: s["effective_address"] for s in probe["sites"]}, PROBE_SRCS)
    E.fact("probe_site_mnemonics",
           {s["name"]: s["mnemonic"] for s in probe["sites"]}, PROBE_SRCS)

    # Do the decoded route sites actually land on the semantic addresses this row's
    # own scenario asserts on? Nothing is hand-typed: both sides are read back.
    decoded = {s["effective_address"] for s in probe["sites"]}
    E.fact("probe_site_addresses_in_scenario_assertion_set",
           sorted(decoded & set(F["scenario_addresses"])), [PROBE_SRC, SCEN])
    E.fact("probe_latch_site_hits_b03_latch_word",
           probe["sites"][[s["name"] for s in probe["sites"]].index(
               "dandelion_latch11_store")]["effective_address"].lower() == latch_word.lower(),
           [PROBE_SRC, B03S])

    acc = probe["target_accesses"]

    def by(target, kind=None, image=None):
        return [a for a in acc if a["target"] == target
                and (kind is None or a["access"] == kind)
                and (image is None or a["image"] == image)]

    E.fact("power_flags_stores_all_images", len(by("power_flags", "write")), PROBE_SRCS)
    E.fact("power_flags_stores_resident",
           len(by("power_flags", "write", "SCUS_942_88")), PROBE_SRCS)
    E.fact("power_flags_stores_overlays",
           len([a for a in by("power_flags", "write") if a["image"] != "SCUS_942_88"]),
           PROBE_SRCS)
    E.fact("power_flags_set_masks",
           [f"0x{v:X}" for v in sorted({a["value"] for a in by("power_flags", "write")
                                        if a["value_form"] == "rmw_or"})], PROBE_SRCS)
    E.fact("power_flags_and_masks",
           [f"0x{v:X}" for v in sorted({a["value"] for a in by("power_flags", "write")
                                        if a["value_form"] == "rmw_and"})], PROBE_SRCS)
    E.fact("power_flags_bit_0x10_writers",
           [a["pc"] for a in by("power_flags", "write")
            if a["value_form"] == "rmw_or" and (a["value"] & 0x10)], PROBE_SRCS)
    cliff_pow = by("power_flags", "write", "LEVEL06_LEVEL")
    E.fact("cliffside_overlay_power_flags_stores",
           [{"pc": a["pc"], "form": a["value_form"], "mask": a["value_mask_hex"]}
            for a in cliff_pow], PROBE_SRCS)
    E.fact("cliffside_overlay_sets_bit_0x10",
           any(a["value"] & 0x10 for a in cliff_pow), PROBE_SRCS)

    E.fact("exit_latch_stores_all_images", len(by("exit_latch", "write")), PROBE_SRCS)
    E.fact("exit_latch_overlay_store_values",
           sorted({(a["image"], a["value_mask_hex"]) for a in by("exit_latch", "write")
                   if a["image"].startswith("LEVEL")}), PROBE_SRCS)
    E.fact("cliffside_overlay_exit_latch_stores",
           [{"pc": a["pc"], "form": a["value_form"], "value": a["value"]}
            for a in by("exit_latch", "write", "LEVEL06_LEVEL")], PROBE_SRCS)
    E.fact("level_overlays_storing_request_constant_2",
           sorted({a["image"] for a in by("exit_latch", "write")
                   if a["image"].startswith("LEVEL") and a["value_form"] == "const"
                   and a["value"] == 2}), PROBE_SRCS)
    E.fact("level_overlays_storing_request_constant_1",
           sorted({a["image"] for a in by("exit_latch", "write")
                   if a["image"].startswith("LEVEL") and a["value_form"] == "const"
                   and a["value"] == 1}), PROBE_SRCS)
    E.fact("level_overlays_with_unrecovered_request_value",
           sorted({a["image"] for a in by("exit_latch", "write")
                   if a["image"].startswith("LEVEL") and a["value_form"] != "const"}),
           PROBE_SRCS)
    E.fact("resident_request2_store_pcs",
           sorted(a["pc"] for a in by("exit_latch", "write", "SCUS_942_88")
                  if a["value_form"] == "const" and a["value"] == 2), PROBE_SRCS)

    E.fact("dandelion_latch_stores", len(by("dandelion_latch", "write")), PROBE_SRCS)
    E.fact("dandelion_latch_store_values",
           sorted({a["value"] for a in by("dandelion_latch", "write")}), PROBE_SRCS)

    # Cross-implementation reconciliation against B03's independent census.
    b03_sites = {(a["pc"].lower(), a["kind"]) for a in req(b03s, "target_800a659e_accesses",
                                                           where=B03S)}
    mine = {(a["pc"].lower(), "store" if a["access"] == "write" else "load")
            for a in by("dandelion_latch")}
    E.fact("latch_census_b03_sites", len(b03_sites), B03S)
    E.fact("latch_census_probe_sites", len(mine), PROBE_SRCS)
    E.fact("latch_census_agreeing_sites", len(b03_sites & mine), [B03S, PROBE_SRC])
    E.fact("latch_census_b03_only", sorted(b03_sites - mine), [B03S, PROBE_SRC])
    E.fact("latch_census_probe_only", sorted(mine - b03_sites), [B03S, PROBE_SRC])

    # ------------------------------------------------------------------ #
    # 9. the Cliffside overlay's own decompilation / frontier coverage    #
    # ------------------------------------------------------------------ #
    cliff_recs = [r for r in req(index, "records", where=IDX)
                  if str(r.get("image_id", "")).startswith("LEVEL06")]
    if not cliff_recs:
        raise SystemExit(f"STALE CITATION: {IDX} no longer indexes the LEVEL06 overlays")
    code_recs = [r for r in cliff_recs if r.get("range_type") == "code"]
    E.fact("cliffside_overlay_index_records", len(cliff_recs), IDX)
    E.fact("cliffside_overlay_code_functions", len(code_recs), IDX)
    E.fact("cliffside_overlay_function_names",
           sorted({r.get("name") or "unnamed" for r in code_recs}), IDX)
    E.fact("cliffside_overlay_memory_accesses",
           sum(len(r.get("memory_accesses", [])) for r in code_recs), IDX)
    E.fact("cliffside_overlay_unresolved_boundaries",
           sum(len(r.get("unresolved_boundaries", [])) for r in code_recs), IDX)
    E.fact("cliffside_overlay_functions_with_source",
           len([r for r in code_recs if r.get("source")]), IDX)

    # Which indexed overlay function owns the candidate PCs? Derived by containment,
    # never asserted -- the point of the finding is that they are all ONE function.
    # ⚠️ BOTH LEVEL06 overlays load at the SAME base, so a PC alone is ambiguous
    # across the two images; containment is resolved on (image, pc), never pc alone.
    CLIFF_IMAGE = F["stage4_container"].split("/")[0] + "_LEVEL"
    cand = [(a["image"], int(a["pc"], 16))
            for a in cliff_pow + by("exit_latch", "write", CLIFF_IMAGE)]
    cand += [(r["image_id"], int(a["pc"], 16))
             for r in code_recs if r["image_id"] == CLIFF_IMAGE
             for a in r.get("memory_accesses", [])
             if (a.get("address") or "").lower() == "0x800a6582"]
    owners = set()
    for img, pc in cand:
        for r in code_recs:
            if r["image_id"] == img and int(r["entry"], 16) <= pc < int(r["end"], 16):
                owners.add((r["image_id"], r["entry"], r.get("name")))
    E.fact("cliffside_overlay_image_for_scene6", CLIFF_IMAGE, [E02D, IDX])
    E.fact("cliffside_candidate_pcs",
           sorted(f"{i}:0x{pc:08X}" for i, pc in cand), [IDX, PROBE_SRC])
    E.fact("cliffside_candidate_owning_functions", sorted(owners), [IDX, PROBE_SRC])
    E.fact("cliffside_candidate_is_one_function", len(owners) == 1, [IDX, PROBE_SRC])

    OVLD = "analysis/overlay_decomp_progress.json"
    ovld = E.json(OVLD)
    tot = req(ovld, "per_overlay_totals", where=OVLD)
    E.fact("cliffside_overlay_decomp_totals",
           {k: tot[k] for k in ("LEVEL06_LEVEL", "LEVEL06_LEVEL1")}, OVLD)
    E.fact("cliffside_overlay_matched_functions",
           sum(req(r, "matched_functions", where=OVLD)
               for r in req(ovld, "results", where=OVLD)
               if r["overlay"].startswith("LEVEL06")), OVLD)
    E.fact("all_overlays_matched_pct",
           req(ovld, "matched", "pct_functions", where=OVLD), OVLD)

    # ------------------------------------------------------------------ #
    # 10. source closure: what build unit owns each governing function?   #
    # ------------------------------------------------------------------ #
    SEG = "config/segments.yml"
    seg = E.yaml(SEG)

    def as_int(v) -> int:
        return v if isinstance(v, int) else int(str(v), 16)

    units = [(as_int(req(e, "start", where=SEG)), as_int(req(e, "end", where=SEG)),
              req(e, "source", where=SEG)) for e in req(seg, "attempted", where=SEG)]
    governing = {name: as_int(pc) for name, pc in F["route_static_site_pcs"].items()}
    governing["region_query"] = as_int(
        req(e02c, "query", "fn", where=E02C).split()[0])
    for a in cliff_pow + by("exit_latch", "write", "LEVEL06_LEVEL"):
        governing[f"cliffside_overlay_{a['pc']}"] = as_int(a["pc"])
    resolved, unresolved = {}, []
    for name, addr in governing.items():
        src = next((s for lo, hi, s in units if lo <= addr < hi), None)
        (resolved.setdefault(src, []).append(name) if src else unresolved.append(name))
    req2_units = sorted({next((src for lo, hi, src in units
                               if lo <= int(pc, 16) < hi), "no build unit")
                         for pc in F["resident_request2_store_pcs"]})
    E.fact("resident_request2_store_build_units", req2_units, [SEG, PROBE_SRC])
    E.fact("governing_addresses", len(governing), [ROUTE, E02C, PROBE_SRC])
    E.fact("governing_build_units", sorted(resolved), SEG)
    E.fact("governing_units_matching_c",
           sorted(s for s in resolved if s.startswith("src/")), SEG)
    E.fact("governing_units_hand_asm",
           sorted(s for s in resolved if s.startswith("asm/")), SEG)
    E.fact("governing_addresses_without_build_unit", sorted(unresolved), SEG)
    E.fact("governing_addresses_in_c",
           sum(len(v) for s, v in resolved.items() if s.startswith("src/")), SEG)
    E.fact("governing_addresses_in_hand_asm",
           sum(len(v) for s, v in resolved.items() if s.startswith("asm/")), SEG)

    # ------------------------------------------------------------------ #
    # 11. the stage's fixture corpus vs what this row declares            #
    # ------------------------------------------------------------------ #
    AUDIT = "analysis/phase2_fixture_audit.json"
    audit = E.json(AUDIT)
    all_movies = req(audit, "movies", where=AUDIT)
    stage_tok = re.compile(r"LEVEL04|Cliffside")
    stage_movies = sorted(k for k in all_movies if stage_tok.search(k))
    declared = [f for f in F["row_declared_fixtures"] if f.endswith(".movie.json")]
    E.fact("stage4_movies_pinned", len(stage_movies), AUDIT)
    E.fact("stage4_movies_pinned_paths", stage_movies, AUDIT)
    E.fact("stage4_movies_declared_by_row", len(declared), [AUDIT, BASE])
    E.fact("stage4_movies_pinned_but_undeclared",
           sorted(set(stage_movies) - set(F["row_declared_fixtures"])), [AUDIT, BASE])
    E.fact("stage4_movie_frames",
           {k: req(all_movies, k, "frames", where=AUDIT) for k in stage_movies}, AUDIT)
    E.fact("stage4_distinct_movies_replayed_by_row_artifacts",
           len({F["scenario_movie"]}), [SCEN])

    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    fixset = E.json(FIXSET)
    entries = req(fixset, "entries", where=FIXSET)
    declared_all = list(F["row_declared_fixtures"])
    missing_pin = [f for f in declared_all if f not in entries]
    if missing_pin:
        raise SystemExit(f"declared fixtures absent from the central pin: {missing_pin}")
    E.fact("declared_fixture_generator_reference_counts",
           {f: len(req(entries, f, "generator_references", where=FIXSET))
            for f in declared_all}, FIXSET)
    E.fact("declared_fixtures_referenced_by_an_f04_tool",
           sum(1 for f in declared_all
               if any("f04" in g.lower()
                      for g in req(entries, f, "generator_references", where=FIXSET))),
           FIXSET)
    E.fact("declared_fixtures_with_zero_generator_references",
           sorted(f for f in declared_all
                  if not req(entries, f, "generator_references", where=FIXSET)), FIXSET)

    # start-state binding provenance: recording-time hash vs backfill
    prov = {}
    for f in declared_all + [k for k in stage_movies if k not in declared_all]:
        if not f.endswith(".movie.json"):
            continue
        mv = E.json(f)
        ss = req(mv, "start_state", where=f)
        ver = req(mv, "version", where=f)
        prov[f] = {"version": ver,
                   "frames": len(req(mv, "frames", where=f)),
                   "from_boot": req(ss, "from_boot", where=f),
                   # the arm-phase flag only exists from movie format v4
                   "armed_while_paused": (req(mv, "armed_while_paused", where=f)
                                          if ver >= 4 else None),
                   "sha256_origin": ss.get("sha256_origin",
                                           "backfill" if ss.get("sha256_backfilled")
                                           else "unstated")}
    E.fact("stage4_movie_provenance", prov, sorted(prov))
    E.fact("declared_movies_with_recording_provenance",
           sorted(k for k in declared_all
                  if k in prov and prov[k]["sha256_origin"] == "recording"),
           sorted(k for k in declared_all if k in prov))
    E.fact("undeclared_stage4_movies_with_recording_provenance",
           sorted(k for k in prov
                  if k not in declared_all and prov[k]["sha256_origin"] == "recording"),
           sorted(k for k in prov if k not in declared_all))
    E.fact("declared_movies_from_boot",
           sorted(k for k in declared_all if k in prov and prov[k]["from_boot"]),
           sorted(k for k in declared_all if k in prov))

    # a retained trace capsule for this stage's own bird hazard already exists
    CAPSET = "analysis/phase4_trace_capsule_set.json"
    capset = E.json(CAPSET)
    caps = req(capset, "capsules", where=CAPSET)
    stage_caps = [c for c in caps if stage_tok.search(c["movie"])]
    E.fact("stage4_retained_capsules",
           [{"movie": c["movie"], "frames": c["frames"],
             "control_match": c["control_match"]} for c in stage_caps], CAPSET)
    E.fact("capsule_set_complete", req(capset, "complete", where=CAPSET), CAPSET)
    E.fact("capsule_set_movie_hash_matches_disk",
           sum(1 for c in caps
               if (root / c["movie"]).exists()
               and sha256_file(root / c["movie"]) == c["movie_sha256"]), CAPSET)
    E.fact("capsule_set_size", len(caps), CAPSET)
    E.fact("stage4_capsule_cited_by_row",
           any("capsule" in json.dumps(main_doc).lower() and c["movie"] in json.dumps(main_doc)
               for c in stage_caps), [MAIN, CAPSET])

    # ------------------------------------------------------------------ #
    # AUTHORED JUDGMENTS against the WRITTEN bars                         #
    # ------------------------------------------------------------------ #
    cited = ("this row was answered BY CITATION: "
             f"{F['row_synthesis_binding_count']} of {F['row_binding_claims']} bindings are "
             f"'SYNTHESIZED FROM' another row, and the row's own artifact states that pass "
             f"performed no new instrumentation "
             f"({F['row_pass1_did_no_new_instrumentation']})")

    dims = {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"{CENSUS} -- {F['census_durable_reason']}. That is the largest "
                     f"declared fixture set of any F row bar one (rank "
                     f"{F['f04_fixture_rank_among_f_rows']} of "
                     f"{F['census_rows_assessed']}). This assessment fails loudly if that "
                     f"measurement ever moves off 'met'",
            "gap": None,
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the route claim IS measured on natural execution of a pinned "
                     f"pristine-media movie ({F['route_identity_game_serial']}, v"
                     f"{F['route_identity_movie_version']}, "
                     f"{F['route_identity_movie_frames']} frames, "
                     f"{F['route_identity_execution_mode']}, reproducible="
                     f"{F['route_identity_reproducible']}) driven at true 60 Hz, with the "
                     f"method explicitly disclaiming advanceToFrame "
                     f"({F['route_method_disclaims_advance_to_frame']}) and arming only "
                     f"after the state load ({F['route_method_armed_after_state_load']}), no "
                     f"perturbation: scene 6 loaded at frame "
                     f"{F['route_scene_load_movie_frame']}, one launch at "
                     f"{F['route_dandelion_launch_movie_frame']}, latch resident "
                     f"{F['route_latch_residence_frames']} frames, exit at "
                     f"{F['route_first_scene6_exit_movie_frame']}, with "
                     f"{F['route_damage_branch_hits']} hits on the contact path and "
                     f"{F['route_life_decrements_after_launch']} life losses, all logs "
                     f"untruncated ({F['route_all_logs_untruncated']}). A NEGATIVE control "
                     f"exists in the other direction (D17's premature-landing fixture, "
                     f"{F['d17_cliffside_fixture_frames']} frames). An executable assertion "
                     f"artifact is registered too: {F['scenario_assertions']} assertions "
                     f"over {F['scenario_phases']} phases in {SCEN}",
            "gap": f"that scenario has never been shown to RUN: its id appears in "
                   f"{len(F['scenario_id_named_in_analysis_artifacts'])} analysis artifacts "
                   f"and "
                   f"{len(F['analysis_artifacts_recording_scenario_assertion_outcomes'])} of "
                   f"them record any of its {F['scenario_assertions']} assertion outcomes, "
                   f"so 'the assertions pass' is UNMEASURED. The row's own registered test "
                   f"module is RED today ({F['row_test_module_failed']} failed / "
                   f"{F['row_test_module_passed']} passed of "
                   f"{F['row_test_module_tests']} -- "
                   f"{', '.join(F['row_test_module_failing_tests'])}), and "
                   f"{len(F['declared_movies_from_boot'])} of the "
                   f"{len(F['row_declared_fixtures'])} declared fixtures is from boot while "
                   f"{len(F['declared_movies_with_recording_provenance'])} of the 3 declared "
                   f"movies carries recording-time start-state provenance -- the rest are "
                   f"BACKFILL, whose own note says it cannot establish that the state still "
                   f"matches what the movie was recorded against",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"for the FLIGHT half the frontier is genuinely enumerated and bounded "
                     f"by B03: {F['b03_latch_total']} latch sites "
                     f"({F['b03_latch_absolute_sites']} absolute + "
                     f"{F['b03_latch_typed_player_relative_sites']} typed player-relative, "
                     f"{F['b03_latch_reads']} reads / {F['b03_latch_writes']} writes, every "
                     f"write a literal 0/11/12: {F['b03_latch_all_writes_literal_0_11_or_12']}), "
                     f"with the scope limit written down verbatim "
                     f"('{F['b03_latch_scope']}'). This assessment re-derived that census "
                     f"INDEPENDENTLY with a compiled-C decode of the shipped images and the "
                     f"two implementations agree on {F['latch_census_agreeing_sites']} of "
                     f"{F['latch_census_b03_sites']} sites. The row also carries "
                     f"{F['row_retained_residual_count']} explicitly named retained residuals",
            "gap": f"the HAZARD half's frontier is not enumerated, and measuring it here "
                   f"showed the residual was mis-shaped: D17's negative on power bit 0x10 "
                   f"was reached from a census of "
                   f"{F['d17_bit10_resident_store_sites_reported']} addresses in ONE resident "
                   f"RAM image, and concluded the writer is 'almost certainly OVERLAY code "
                   f"specific to Cliffside' ({F['d17_bit10_hypothesis_is_overlay']}). A full "
                   f"static decode of all {F['probe_images_decoded']} shipped images finds "
                   f"{F['power_flags_stores_all_images']} stores to the power word "
                   f"({F['power_flags_stores_resident']} resident + "
                   f"{F['power_flags_stores_overlays']} overlay), sets "
                   f"{F['power_flags_set_masks']} and AND-masks {F['power_flags_and_masks']} -- "
                   f"{len(F['power_flags_bit_0x10_writers'])} of them write bit 0x10, and the "
                   f"Cliffside overlay's own single power-flags store is an OR of "
                   f"{F['cliffside_overlay_power_flags_stores'][0]['mask']}, not 0x10. The "
                   f"stated hypothesis is therefore NOT supported; the residual survives with "
                   f"a different shape (a computed/pointer-relative base -- "
                   f"{F['probe_memops_unresolved_base']} of {F['probe_memops']} decoded memops "
                   f"have an unresolved base -- or code outside the "
                   f"{F['probe_code_ranges']} indexed ranges). No frontier at all is "
                   f"enumerated for the bird actor, its spawn, or the stage's enemy roster",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle, and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"the row does name a breadth claim -- the mite (id 37) appears in this "
                     f"scene, cited from D13's static scan "
                     f"({F['mite_level_set_source_claim']}) -- and B03's own scope line "
                     f"names this stage as its primary ({F['donor_b03_stages']})",
            "gap": f"every runtime conclusion in this row rests on "
                   f"{F['stage4_distinct_movies_replayed_by_row_artifacts']} route, replayed "
                   f"once. The pinned corpus already holds {F['stage4_movies_pinned']} movies "
                   f"of this stage under a LEVEL04/Cliffside name; "
                   f"{len(F['stage4_movies_pinned_but_undeclared'])} of them are undeclared "
                   f"by this row and untouched by any of its artifacts -- including a "
                   f"{F['stage4_movie_frames']['movies/Phase4/Interpreter/100% Runs/LEVEL04_Cliffside.movie.json']}"
                   f"-frame 100% Interpreter run and TWO E10 'hazard_ground_bird_LEVEL04' "
                   f"recordings of this row's own bird hazard, one of which has a validated "
                   f"retained trace capsule ({F['stage4_retained_capsules']}). "
                   f"{F['declared_fixtures_referenced_by_an_f04_tool']} of the "
                   f"{len(F['row_declared_fixtures'])} declared fixtures is referenced by any "
                   f"F04 tool. The applicability universe is unenumerated in both directions: "
                   f"which other stages instantiate the dandelion/propeller mechanism (B03 "
                   f"defers exactly that: {F['b03_deferred_items']}), and which routes, "
                   f"variants and exceptional paths within Cliffside are in scope",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"the flight latch is TYPED with a proved value domain: "
                     f"{F['dandelion_latch_stores']} static stores across every shipped image, "
                     f"values exactly {F['dandelion_latch_store_values']} (compiled-C decode, "
                     f"agreeing with B03's independent census), plus B03's four named clear "
                     f"sites ({F['b03_lifecycle_clears']}) and its activation contract "
                     f"({F['b03_activation_contract']}). The scenario types five more player "
                     f"fields by semantic id ({F['scenario_semantic_ids']})",
            "gap": f"the bird side is untyped: the actor record's two position fields, hp, "
                   f"flags and radius are READ in D17 but no value domain is bounded for any "
                   f"of them, and the hp 101-vs-50 difference is a single-fixture reading, "
                   f"not a typed field with a domain. The power word is the sharpest case: "
                   f"its set masks are now enumerated ({F['power_flags_set_masks']}) yet the "
                   f"bit this row cares about has no writer in any of them, so the observed "
                   f"value is measured and its producer is not",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"one full in-stage arc is traced end to end on natural execution: scene "
                     f"load (frame {F['route_scene_load_movie_frame']}) -> first use "
                     f"(one launch at {F['route_dandelion_launch_movie_frame']}, "
                     f"{F['route_launch_hits']} hit) -> residence "
                     f"({F['route_latch_residence_frames']} frames) -> intended clear "
                     f"({F['route_grounded_latch_clear_movie_frame']}) -> scene exit "
                     f"({F['route_first_scene6_exit_movie_frame']}, "
                     f"{F['route_scene_exit_after_ground_frames']} frames later), and B03 "
                     f"adds the retirement law (four distinct clear sites, one per exit "
                     f"condition). D17 supplies the death/respawn arc as a separate fixture",
            "gap": f"no cold boot anywhere in the evidence base "
                   f"({len(F['declared_movies_from_boot'])} of the 3 declared movies is "
                   f"from_boot); "
                   f"REPEATED use is never exercised -- the traced route launches exactly "
                   f"once, so 'take the dandelion twice' is unmeasured; exhaustion has no "
                   f"meaning assigned for this stage; and no per-phase claim map is "
                   f"registered for this row the way F01 has one",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"the row's central claim IS a cross-system one and it is measured in "
                     f"both directions: flight x hazard x scene transition on the success "
                     f"side ({F['route_damage_branch_hits']} contact hits, "
                     f"{F['route_life_decrements_after_launch']} life losses, ordered route "
                     f"{F['route_ordered_success_route']}) and the same crossing on the "
                     f"failure side in D17's fixture. B03 additionally documents "
                     f"flight x carried-actor (contact detaches any carried actor) and "
                     f"flight x propeller sharing one state field",
            "gap": f"the dandelion-to-propeller combination is explicitly DEFERRED by the "
                   f"donor row itself ({F['b03_deferred_items']}), so the one native "
                   f"combination inside this row's own mechanism family has never been run; "
                   f"the bird is never crossed with berries, the mite, or the exit trigger; "
                   f"and no combination matrix is registered. The row's own residual list "
                   f"still names cross-system audio/HUD",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the interfaces that the SUCCESS path crosses are documented and now "
                     f"instruction-verified: all {len(F['probe_site_effective_addresses'])} "
                     f"route sites decode to resolved effective addresses "
                     f"({F['probe_sites_unresolved']} unresolved, "
                     f"{F['probe_sites_missing']} missing) and "
                     f"{len(F['probe_site_addresses_in_scenario_assertion_set'])} of them land "
                     f"exactly on addresses this row's own scenario asserts against. The "
                     f"region-code interface is bound cross-row and its arms are decoded to "
                     f"the instruction: code 3 = '{F['code3_arm_effect']}' vs code 2 = "
                     f"'{F['code2_arm_effect']}', i.e. the two exit arms differ only by the "
                     f"position-commit flag "
                     f"({F['code3_differs_from_code2_only_by_commit_flag']}), under gates "
                     f"{F['region_dispatch_gates']}",
            "gap": f"the interface that actually FIRES the hazard is not documented -- D17 "
                   f"narrowed it to FUNC_8004ABF4 but its own decoded radius test evaluates "
                   f"not-inside at the closest approach "
                   f"({F['d17_cliffside_radius_test_not_inside']}), so the deciding branch is "
                   f"named as unknown with an obstruction rather than documented. The "
                   f"Cliffside overlay's own interface is undocumented in this row entirely, "
                   f"including a function that reads the grounded flag and the power word and "
                   f"then requests a scene transition",
        },
        "source_closure": {
            "state": "partial",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured, not assumed: {F['governing_addresses']} governing addresses "
                     f"taken from this row's own artifacts and from the compiled-C decode "
                     f"resolve to {len(F['governing_build_units'])} build units -- "
                     f"{F['governing_addresses_in_c']} address(es) in matching C "
                     f"({F['governing_units_matching_c']}) and "
                     f"{F['governing_addresses_in_hand_asm']} in hand-written byte-exact ASM "
                     f"({len(F['governing_units_hand_asm'])} units). The scene "
                     f"clear/restore stores this row's exit observation rests on ARE in C, "
                     f"which is more than F02 could say",
            "gap": f"the dandelion handler, the transition initiator, the player vertical "
                   f"update and the contact resolver are all hand-ASM, not C. The stage's own "
                   f"overlay is barely started: "
                   f"{F['cliffside_overlay_matched_functions']} of "
                   f"{sum(F['cliffside_overlay_decomp_totals'].values())} Cliffside overlay "
                   f"functions are matched (campaign-wide overlay track: "
                   f"{F['all_overlays_matched_pct']}%), and "
                   f"{len(F['governing_addresses_without_build_unit'])} governing addresses "
                   f"have no resident build unit at all "
                   f"({F['governing_addresses_without_build_unit']}). The row lists source "
                   f"closure among its own retained residuals",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    # The sibling measurement, read back rather than remembered.
    SIB = "analysis/phase4_f02_written_bar_assessment.json"
    sib = E.json(SIB)
    order = ["not_met", "unmeasured", "partial", "met_candidate", "met"]
    sib_dims = req(sib, "dimensions", where=SIB)
    better = sorted(k for k, v in dims.items()
                    if k in sib_dims
                    and order.index(v["state"]) > order.index(sib_dims[k]["state"]))
    worse = sorted(k for k, v in dims.items()
                   if k in sib_dims
                   and order.index(v["state"]) < order.index(sib_dims[k]["state"]))
    E.fact("sibling_row_compared", req(sib, "row_id", where=SIB), SIB)
    E.fact("sibling_counts", req(sib, "counts", where=SIB), SIB)
    E.fact("dimensions_stronger_than_sibling", better, SIB)
    E.fact("dimensions_weaker_than_sibling", worse, SIB)

    doc = {
        "_comment": "F04_cliffside_canyon measured against the nine DoD dimensions AS "
                    "WRITTEN (item 2 = enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f04_written_bar_assessment.py",
        "schema": "abl-phase4-f04-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": ROW,
        "row_name": F["row_name"],
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
            "author_conflict": "the assessor did not author F04's underlying evidence, but "
                               "did author this assessment, the C probe it runs, and the "
                               "F-row census whose durable_evidence result it carries "
                               "forward -- so the standard being applied and the application "
                               "of it share an author. Every state below is a submission to "
                               "a fresh detached verifier, not a promotion; `partial` and "
                               "`not_met` are as challengeable as a `met` would be. The two "
                               "measured falsifications below (the row's red test module, "
                               "and the bit-0x10 hypothesis) are the assessor's own new "
                               "findings and have not been independently reviewed",
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
                    "understates the row: durable_evidence is measured met and seven other "
                    "dimensions hold real, bounded evidence. The baseline row meanwhile "
                    "declares MOVE ON / bounded-exhausted, which under the vocabulary is a "
                    "stop decision and never reads as met either",
        },
        "secondary_lead_finding": {
            "question": "the row declares `secondary_lead` among its four evidence classes. "
                        "What does that make measurable?",
            "class_legend": F["baseline_evidence_class_legend"],
            "only_definition_in_the_repo": {
                "source": LEAD,
                "role": F["secondary_lead_role"],
                "authority_rule": F["secondary_lead_authority_rule"],
            },
            "rows_declaring_it": F["baseline_rows_declaring_secondary_lead"],
            "verdict": "a `secondary_lead` is a POINTER, not evidence: the only definition "
                       "in the repo calls it 'non-authoritative trigger lead only' and binds "
                       "authority to hash-verified media and executable bytes. It can raise "
                       "a claim to be tested and can never satisfy any of the nine bars. "
                       "The F-row census agrees by construction -- it derives only "
                       f"{F['census_derived_evidence_classes']} from this row's artifacts "
                       f"against the declared {F['census_declared_evidence_classes']}. So "
                       "this row's four declared classes are two measurable ones, one "
                       "operator-testimony class, and one lead; and of the "
                       f"{F['f04_artifacts_examined_for_a_secondary_source']} artifacts this "
                       f"row owns, {len(F['f04_artifacts_citing_an_external_url'])} cite an "
                       "external source, so the declared class is not traceable to a "
                       "specific lead at all. Treating it as a fourth evidence class "
                       "inflates the row's apparent support",
        },
        "compiled_c_probe": {
            "source": PROBE_SRC,
            "why": "the row's own reducer tools/phase4_f04_route_analyzer.c cannot run "
                   "today: it opens the transient /tmp trace TSVs before its static checks, "
                   "and those were deleted with the 2026-08-04 session. Its six 'exact "
                   "sites' have therefore been unverifiable since the day they were "
                   "written, and they were TEXT comparisons against ASM listings, not "
                   "decodes. This probe decodes the shipped images.",
            "build": f"{os.environ.get('CC', 'cc')} {' '.join(CC_FLAGS)}",
            "images_decoded": F["probe_images_decoded"],
            "code_ranges": F["probe_code_ranges"],
            "instructions_decoded": F["probe_instructions_decoded"],
            "route_sites": F["probe_site_effective_addresses"],
            "route_sites_unresolved": F["probe_sites_unresolved"],
            "disclosed_limit": "constants flow only inside a basic block; facts are dropped "
                               "at every branch target. The census therefore UNDER-reports "
                               f"({F['probe_memops_unresolved_base']} of "
                               f"{F['probe_memops']} memops have an unresolved base) and is "
                               "a lower bound on writers, never a total. The independent "
                               "reconciliation against B03's own census makes the size of "
                               f"that under-report visible: {F['latch_census_agreeing_sites']}"
                               f"/{F['latch_census_b03_sites']} sites agree, B03-only "
                               f"{F['latch_census_b03_only']}, probe-only "
                               f"{F['latch_census_probe_only']} (the probe-only site is "
                               "overlay code B03's resident-corpus scan could not see)",
        },
        "fail_loud_verification": fail_loud if fail_loud else {
            "run": False,
            "how": "python3 tools/phase4_f04_written_bar_assessment.py --verify-fail-loud",
            "note": "not executed in this run; the published artifact records the run in "
                    "which it was",
        },
        "fact_provenance": {
            "facts_total": len(F),
            "facts_derived_from_pinned_artifacts": len(E.provenance),
            "facts_hand_typed": len(F) - len(E.provenance),
            "rule": "facts are recorded through fact(key, value, source); a value cannot be "
                    "stored without naming a pinned artifact, every lookup is strict so a "
                    "renamed or removed key aborts the run instead of silently defaulting, "
                    "and a duplicate key aborts too. Verified, not asserted: see "
                    "fail_loud_verification",
            "by_fact": E.provenance,
        },
        "facts": F,
        "evidence_pins": E.pins,
        "dimensions": dims,
        "counts": counts,
        "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                   f"met-candidate, {counts.get('partial', 0)} partial, "
                   f"{counts.get('not_met', 0)} not met, {counts.get('unmeasured', 0)} "
                   f"unmeasured -- against the WRITTEN bars. Against the one sibling already "
                   f"measured this way ({F['sibling_row_compared']}, "
                   f"{F['sibling_counts']}), F04 is stronger on "
                   f"{F['dimensions_stronger_than_sibling']} and weaker on "
                   f"{F['dimensions_weaker_than_sibling']} -- one dimension of difference, "
                   f"because F04's single route replay is an ordered, untruncated, 60 Hz "
                   f"natural-execution observation with a complementary negative control, "
                   f"and because the stores its exit observation rests on are byte-matched "
                   f"C. It still reaches met nowhere except the dimension measured "
                   f"elsewhere, and the reason is uniform: {cited}, so what is evidenced is "
                   f"the two MECHANISMS plus their order on one route -- not the STAGE.",
        "notable": [
            f"THE ROW'S OWN REGISTERED TEST MODULE IS RED. "
            f"{TEST} reports {F['row_test_module_failed']} failed / "
            f"{F['row_test_module_passed']} passed of {F['row_test_module_tests']} "
            f"({', '.join(F['row_test_module_failing_tests'])}; "
            f"{F['row_test_module_failing_assertions']}). The test guards the claim "
            f"that STILL_OPEN flags stage-level flow as unaddressed; the 2026-08-04 "
            f"route-closure pass rewrote STILL_OPEN and the phrase went with it. The test "
            f"was right to fire -- stage-level flow WAS the thing that pass addressed -- but "
            f"nobody ran it, so the row has carried a failing guard for a week.",

            f"THE ROW'S OWN NAMED RESIDUAL IS MIS-SHAPED, and a compiled-C decode of all "
            f"{F['probe_images_decoded']} shipped images shows it. D17's negative on power "
            f"bit 0x10 came from {F['d17_bit10_resident_store_sites_reported']} addresses in "
            f"one resident RAM image and concluded the writer is 'almost certainly OVERLAY "
            f"code specific to Cliffside'. The full static census finds "
            f"{F['power_flags_stores_all_images']} stores to that word "
            f"({F['power_flags_stores_resident']} resident + "
            f"{F['power_flags_stores_overlays']} overlay), a superset of D17's list, setting "
            f"masks {F['power_flags_set_masks']} and AND-masking {F['power_flags_and_masks']}. "
            f"NONE writes bit 0x10, and the Cliffside overlay's single power-flags store is "
            f"an OR of {F['cliffside_overlay_power_flags_stores'][0]['mask']}. The negative "
            f"survives a much wider search -- which is good news -- but the hypothesis "
            f"attached to it does not, so the residual should be re-stated as "
            f"'pointer-relative or unindexed writer', not 'uncharted Cliffside overlay'.",

            f"A CANDIDATE FOR THE STAGE'S PUNISHMENT PATH IS SITTING IN AN ARTIFACT THE ROW "
            f"NEVER READ. The Cliffside overlay's own {F['cliffside_overlay_code_functions']} "
            f"indexed code functions ({F['cliffside_overlay_function_names']}) include ONE "
            f"that owns every candidate PC below -- derived by containment, not asserted: "
            f"{F['cliffside_candidate_owning_functions']} owns all of "
            f"{F['cliffside_candidate_pcs']} "
            f"(single owner: {F['cliffside_candidate_is_one_function']}). That one function "
            f"reads the player's grounded flag, read-modify-writes the power word, and "
            f"stores the scene-transition request. Across the campaign, "
            f"{len(F['level_overlays_storing_request_constant_1'])} level overlays store "
            f"request constant 1 and exactly "
            f"{len(F['level_overlays_storing_request_constant_2'])} stores constant 2 -- "
            f"{F['level_overlays_storing_request_constant_2']} "
            f"({F['cliffside_overlay_exit_latch_stores']}); "
            f"{F['level_overlays_with_unrecovered_request_value']} had an unrecovered value "
            f"and are not counted either way. What is request 2? The resident writers of "
            f"that constant are {F['resident_request2_store_pcs']}, and they resolve to "
            f"{F['resident_request2_store_build_units']} -- i.e. the player damage handler, "
            f"the same function whose stagger store at "
            f"{F['route_static_site_pcs']['contact_stagger_store']} is D17's observed "
            f"Cliffside death path. That is "
            f"a STATIC CANDIDATE ONLY -- no trace has ever put a PC in this overlay, F04's "
            f"watches were all resident addresses, and nothing here proves this function runs "
            f"in the bird encounter. But it is exactly the shape D17 described "
            f"behaviourally (land -> freeze -> fade -> lives-1) and it is one exec watch away "
            f"from being decided.",

            f"THE STAGE HAS {F['stage4_movies_pinned']} PINNED MOVIES UNDER A "
            f"LEVEL04/CLIFFSIDE NAME AND THE ROW DECLARES "
            f"{F['stage4_movies_declared_by_row']} OF THEM. Unused and undeclared: "
            f"{F['stage4_movies_pinned_but_undeclared']} -- including TWO recordings named "
            f"for this row's own hazard ('hazard_ground_bird_LEVEL04') and a 100% run. Worse "
            f"for the row's stated fixture_need ('{F['row_declared_fixture_need']}'): the two "
            f"undeclared movies with the STRONGER start-state provenance are "
            f"{F['undeclared_stage4_movies_with_recording_provenance']} (recording-time "
            f"hash), while all three DECLARED movies carry backfill provenance, whose own "
            f"note says it cannot establish that the state still matches what was recorded "
            f"against. One of the unused hazard movies also has a validated retained trace "
            f"capsule ({F['stage4_retained_capsules']}), which AGENTS.md says to query "
            f"BEFORE another live replay. ⚠️ Separately measured and NOT an F04 problem: the "
            f"capsule set's recorded movie hash matches the on-disk movie for "
            f"{F['capsule_set_movie_hash_matches_disk']} of {F['capsule_set_size']} capsules, "
            f"a repo-wide representation change, so the capsule cannot be bound to today's "
            f"movie bytes by that hash.",

            f"EXIT IS BOUND; OBJECTIVE IS NOT. The disc-side census locates this stage's "
            f"{F['stage4_authored_sectors']} authored sectors with histogram "
            f"{F['stage4_code_histogram']} -- exactly one nonzero code, sector "
            f"{F['stage4_nonzero_sectors'][0]['sector']} carrying code "
            f"{F['stage4_nonzero_sectors'][0]['code']}, with "
            f"{F['stage4_disc_vs_runtime_mismatches']} disc/runtime mismatches here and "
            f"{F['e02_campaign_disagreements']} campaign-wide over "
            f"{F['e02_authored_sectors_compared']} sectors. Code 3's arm differs from code "
            f"2's only by the position-commit flag "
            f"({F['code3_differs_from_code2_only_by_commit_flag']}): "
            f"'{F['code3_arm_effect']}'. This is EXIT evidence and it closes nothing about "
            f"the row's objective -- the row's named subjects are a flight mechanic and a "
            f"hazard, and neither is a sector code. The row does not record this census at "
            f"all.",

            f"TWO PINNED ARTIFACTS DISAGREE ABOUT CODE 3, AND THE ROW INHERITS THE OLDER "
            f"ONE. {E02C} still describes code 3 as an "
            f"'IDENTICAL body to code 2' "
            f"({F['e02_consumer_binding_calls_code3_identical_to_code2']}), while the later "
            f"instruction-level decode in {LIFE} separates them: code 2 sets the "
            f"position-commit flag and code 3 does not "
            f"('{F['code2_arm_effect']}' vs '{F['code3_arm_effect']}'). Cliffside's only "
            f"nonzero sector is a code 3, so the row's exit path is on the arm that does NOT "
            f"commit position -- a distinction the older artifact erases.",

            f"THE FLIGHT CITATION'S OWN RECORDING WAS NEVER SCENE-CHECKED. F04 cites B03 "
            f"for 'special flight' and B03's row declares 'stages: "
            f"{F['donor_b03_stages']}', but of the "
            f"{F['b03_artifacts_examined_for_scene_id']} B03 artifacts, "
            f"{F['b03_artifacts_recording_a_scene_id']} record a scene id for the recording "
            f"they analyse. What ties the dandelion to THIS stage is not B03 at all -- it is "
            f"F04's own route replay, which observed the launch while scene_id was 6. That "
            f"is the right evidence; the row should cite it for the binding instead of the "
            f"donor's declaration. (Going the other way, this row's own bird fixture is "
            f"already being consumed elsewhere: {C15} reuses it "
            f"({F['row_fixture_reused_by_c15']}) and names F04 as its donor context "
            f"({F['c15_names_f04_as_donor_context']}).)",

            f"{F['other_baseline_rows_naming_stage4']} other baseline rows name this stage "
            f"by an UNAMBIGUOUS token (Cliffside / scene_id=6 / LEVEL06): "
            f"{', '.join(F['other_baseline_rows_naming_stage4_ids'])}. A further "
            f"{len(F['baseline_rows_matching_only_the_ambiguous_level04_token'])} match only "
            f"the ambiguous 'LEVEL04' token "
            f"({', '.join(F['baseline_rows_matching_only_the_ambiguous_level04_token'])}) -- "
            f"and that token is NOT reliable here: Cliffside is chronological level 4 but "
            f"scene 6, loading from disc dir {F['stage4_container']}, while disc dir LEVEL04/ "
            f"belongs to another stage. Movie filenames use the chronological number and "
            f"disc paths use the directory, so any sweep for this row must say which it "
            f"means. This row cites "
            f"{F['row_artifact_path_citations']} artifact paths. A verifier scoping F04 "
            f"should decide what belongs to the STAGE and what is already owned by the "
            f"mechanism rows before re-measuring: on today's evidence base, deleting the "
            f"three donor citations would leave the row with one route replay.",
        ],
    }

    tmp_out = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_out.parent.mkdir(parents=True, exist_ok=True)
    tmp_out.write_text(json.dumps(doc, indent=1) + "\n")
    os.replace(tmp_out, out_path)

    print(f"[written-bar F04] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} derived / "
          f"{doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    if fail_loud:
        print("fail-loud verification: " +
              ", ".join(f"{c['case']}={'PASS' if c['passed'] else 'FAIL'}"
                        for c in fail_loud["cases"]))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
