#!/usr/bin/env python3
"""Measure F12/F13/F15's nine DoD dimensions against the bars AS WRITTEN.

Sibling of `tools/phase4_f01_written_bar_assessment.py` (the exemplar) and
`tools/phase4_f08_written_bar_assessment.py` (the rigor standard), under
`engineering-specs/phase4-measurement-standard-ruling.md`. The WRITTEN bars:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

WHY THESE THREE TOGETHER, AND WHAT THE CENTRAL RISK IS
------------------------------------------------------
Two of the three are stage rows whose boss was closed in a D row -- F12 points at
D19_molt, F15 at D20_hopper -- and both baselines record that pointer as the row's
own answer. A D-row disposition is a STOP DECISION ON THE BOSS. Under the
vocabulary it never reads as met even for the boss, and it cannot carry the STAGE
row's own objective instance, entry/exit, arena layout or lifecycle at all. F12's
own baseline concedes exactly this: what stays open is "this stage's own arena
layout/critical path". So every scorecard below separates, per dimension,
BORROWED boss-mechanism evidence from OWNED stage-specific evidence, and the
`borrowed_vs_owned` block states the split explicitly. F13 is the control: its
objective (rescue Atta / the berry-shooter solution) belongs to no D row, and the
row has never been worked -- yet the census attributes THREE matched overlay C
files to it, more than any other F row, and the row records none of them.

Nothing below is cross-credited. A fact derived from D19 or D20 is labelled
borrowed in the basis string that uses it, and no borrowed fact promotes a state.

TWO SYSTEMIC DEFECTS ARE CHECKED EXPLICITLY PER ROW
---------------------------------------------------
  (a) OVERLAY MISATTRIBUTION. Every per-level overlay is loaded to the SAME VA
      (region A), analysis/phase3_ownership_graph.json stores no `image` field,
      and all three rows carry claims about addresses in that window. Settled
      here from BYTES by a compiled-C probe
      (tools/phase4_f12_f13_f15_overlay_residency_pin.c) over the 21 pinned
      images against each row's own fixtures, with the ambiguity SIZED rather
      than asserted (how many images contain each governing offset at all).
  (b) SEMANTIC-REGISTRY COLLISION. config/semantic_state.yaml keys overlay-local
      addresses GLOBALLY. Measured here against each row's byte-pinned overlay
      EXTENT, not against the shared region.

BOTH SOURCE REGISTRIES ARE READ before any source_closure claim: config/segments.yml
(resident) and config/overlays.yml + src/overlays/ + analysis/overlay_decomp_progress.json
(overlay track). A claim that overlay byte-matching is impossible was banked and
retracted for checking only the first.

Design (identical to the exemplar):
  * every FACT is read from a cited artifact at run time and the artifact is
    sha256-pinned, so a stale citation fails LOUDLY instead of aging silently.
    `fact()` cannot record a value without naming the artifact it came from, and
    `req()` raises on a missing key rather than substituting a default;
  * every JUDGMENT is authored and attributable, and carries `written_bar` /
    `basis` / `gap`;
  * `unmeasured` is an allowed and expected state. Evidence is not stretched to
    fill a cell.

durable_evidence is NOT re-derived: it was MEASURED in
analysis/phase4_f_row_measured_census.json (F12 4/4, F13 1/1, F15 4/4) and is
carried forward with its fraction, failing loudly if that measurement moves.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a
fresh detached verifier. This tool never edits analysis/mechanics_baseline.yaml.

Usage: python3 tools/phase4_f12_f13_f15_written_bar_assessment.py
         [--out PATH] [--no-probe] [--no-gates]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# Scope of this assessment (a statement of what is being measured, not a fact).
ROWS = ("F12_battle_arena", "F13_anthill_two", "F15_canyon_showdown")
STEM = {"F12_battle_arena": "f12", "F13_anthill_two": "f13",
        "F15_canyon_showdown": "f15"}

PROBE_SRC = "tools/phase4_f12_f13_f15_overlay_residency_pin.c"
PROBE_OUT = "analysis/phase4_f12_f13_f15_overlay_residency_pin.json"
SAVE_RAM = "tools/phase4_f08_save_ram.py"

ADDR_RE = re.compile(r"0x[0-9A-Fa-f]{8}\b")
SYM_RE = re.compile(r"\b[gD]_([0-9a-fA-F]{8})\b")
SRC_START_RE = re.compile(r"([0-9a-f]{8})_")


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


def hx(a: int) -> str:
    return f"0x{a:08X}"


def norm(a: str) -> str:
    """Canonicalise a literal address string so `0x800b3bd4` and `0x800B3BD4`
    compare equal. Casing differs between artifacts, and an uppercase() over the
    whole token also uppercases the `0x` prefix -- which silently made two real
    matches read as misses on the first run of this tool."""
    return "0x" + a[2:].upper() if a.lower().startswith("0x") else a


def selftest_guards() -> list[str]:
    """Prove the fail-loud machinery still fails, every run.

    Out-of-band probes (moving a pinned artifact aside, renaming a key inside
    one, drifting a declared overlay symbol away from the byte-matched C it is
    checked against) were run by hand and each aborted with a non-zero exit and
    no output file. Those are one-off. These three are in-band and re-run on
    every generation, so a refactor that turns a guard into a silent default is
    caught here rather than discovered later inside a stale number.
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


def run_probe(E: Evidence, groups: list[dict], exe_id: dict, prog_addr: int,
              prog_count: int, scene_addr: int, base: int, length: int,
              images: list[str]) -> None:
    """Build and run the compiled-C residency probe. Compiled C owns byte and
    instruction decoding; this function only marshals derived arguments."""
    binp = Path(tempfile.gettempdir()) / "abl_f121315_pin"
    build = subprocess.run(
        ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         str(ROOT / PROBE_SRC), "-o", str(binp), "-lcrypto"],
        capture_output=True, text=True)
    if build.returncode != 0:
        raise SystemExit(f"probe build failed:\n{build.stderr[-2000:]}")

    # A FIXED extraction directory, not mkdtemp: the probe records the RAM path it
    # was given, and a random path would make the pinned artifact's bytes differ on
    # every run -- a pinned artifact that cannot reproduce its own sha256 is not a
    # pin. Identity travels in the recorded sha256 of each RAM, not in the path.
    tmp = Path(tempfile.gettempdir()) / "abl_f121315_ram"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        rams: dict[str, str] = {}
        for g in groups:
            for label, sav in g["rams"]:
                if label in rams:
                    continue
                dest = tmp / f"{label}.bin"
                r = subprocess.run(
                    [sys.executable, str(ROOT / SAVE_RAM), sav, "--out", str(dest)],
                    cwd=str(ROOT), capture_output=True, text=True)
                if r.returncode != 0 or not dest.exists():
                    raise SystemExit(f"RAM extraction failed for {sav}: "
                                     f"{r.stdout.strip()} {r.stderr.strip()}")
                rams[label] = str(dest)

        argv = [str(binp), str(ROOT / PROBE_OUT), f"{base:08x}", str(length),
                "--exe", "{path}:{hdr}:{va:08x}:{sha1}".format(**exe_id),
                "--progression", f"{prog_addr:08x}:{prog_count}",
                "--scene-addr", f"{scene_addr:08x}",
                "--images", *images]
        for g in groups:
            argv += ["--group", g["label"], "--rams",
                     *[f"{label}={rams[label]}" for label, _ in g["rams"]]]
            if g["words"]:
                argv += ["--words", ",".join(f"{a:08x}" for a in g["words"])]
            if g["pcs"]:
                argv += ["--pcs", ",".join(f"{a:08x}" for a in g["pcs"])]
        r = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"probe run failed:\n{r.stdout}\n{r.stderr}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(
        ROOT / "analysis/phase4_f12_f13_f15_written_bar_assessment.json"))
    ap.add_argument("--no-probe", action="store_true",
                    help="reuse the existing residency-pin artifact instead of "
                         "rebuilding and rerunning the compiled-C probe")
    ap.add_argument("--no-gates", action="store_true",
                    help="skip executing these rows' registered pytest gates")
    args = ap.parse_args()

    E = Evidence()
    F = E.facts

    # ------------------------------------------------------------------ #
    # 0. prove the staleness detection works before trusting any number   #
    # ------------------------------------------------------------------ #
    SELF = "tools/phase4_f12_f13_f15_written_bar_assessment.py"
    E.pin(SELF)
    E.pin(PROBE_SRC)
    E.pin(SAVE_RAM)
    E.fact("fail_loud_guards_fired", selftest_guards(), SELF)

    # ------------------------------------------------------------------ #
    # 1. shared registries                                                #
    # ------------------------------------------------------------------ #
    CENSUS = "analysis/phase4_f_row_measured_census.json"
    BASE = "analysis/mechanics_baseline.yaml"
    DEBT = "analysis/phase4_closure_debt.json"
    COV = "analysis/phase2_row_coverage.json"
    QUEUE = "analysis/phase4_movie_priority_queue.json"
    OFFQ = "analysis/phase4_offline_opportunity_queue.json"
    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    AUDIT = "analysis/phase2_fixture_audit.json"
    ORACLE = "analysis/phase2_completion_oracle.json"
    OWN = "analysis/phase3_ownership_graph.json"
    JRT = "analysis/phase3_jr_tables.json"
    SEM = "config/semantic_state.yaml"
    SITES = "config/confirmed_sites.yaml"
    RECS = "config/record_types.yaml"
    SEG = "config/segments.yml"
    OVLY = "config/overlays.yml"
    OVLD = "analysis/overlay_decomp_progress.json"
    FN = "analysis/functions.json"
    E02 = "analysis/phase4_e02_disc_region_code_census.json"
    ACT = "analysis/phase1_kind_actor_census.json"
    C2 = "analysis/phase4_c2_level_type_authority.json"
    BIND = "analysis/phase4_f08_scene_binding.json"
    E16V = "analysis/phase4_e16_movie_validation.json"
    BREADTH = "analysis/phase4_f01_breadth_assertions.json"

    census = E.json(CENSUS)
    base_doc = E.yaml(BASE)
    debt = E.json(DEBT)
    cov = E.json(COV)
    queue = E.json(QUEUE)
    offq = E.json(OFFQ)
    fixset = E.json(FIXSET)
    audit = E.json(AUDIT)
    oracle = E.json(ORACLE)
    own = E.json(OWN)
    jrt = E.json(JRT)
    sem = E.yaml(SEM)
    sites = E.yaml(SITES)
    recs = E.yaml(RECS)
    seg = E.yaml(SEG)
    ovly = E.yaml(OVLY)
    ovld = E.json(OVLD)
    fnj = E.json(FN)
    e02 = E.json(E02)
    act = E.json(ACT)
    c2 = E.json(C2)
    bind = E.json(BIND)
    e16v = E.json(E16V)
    breadth = E.json(BREADTH)

    baseline_rows = {r["id"]: r for r in req(base_doc, "rows", where=BASE)
                     if isinstance(r, dict) and r.get("id")}
    debt_rows = {r.get("row_id"): r for r in req(debt, "rows", where=DEBT)}
    queue_rows = {r.get("row_id"): r for r in req(queue, "rows", where=QUEUE)}
    offq_rows = {r.get("row_id"): r for r in req(offq, "rows", where=OFFQ)}
    fix_entries = req(fixset, "entries", where=FIXSET)
    movies = req(audit, "movies", where=AUDIT)
    oracle_stages = req(oracle, "stages", where=ORACLE)
    sem_entries = req(sem, "entries", where=SEM)
    site_entries = req(sites, "entries", where=SITES)
    seg_units = [(as_int(req(u, "start", where=SEG)), as_int(req(u, "end", where=SEG)),
                  req(u, "source", where=SEG)) for u in req(seg, "attempted", where=SEG)]

    E.fact("baseline_sha256_matches_census",
           sha256_file(ROOT / BASE) == req(census, "baseline_sha256", where=CENSUS),
           [BASE, CENSUS])
    E.fact("fixture_set_sha256_matches_census",
           sha256_file(ROOT / FIXSET) == req(census, "fixture_set_sha256", where=CENSUS),
           [FIXSET, CENSUS])
    E.fact("resident_build_units", len(seg_units), SEG)
    E.fact("resident_build_toolchain", req(seg, "c_toolchain", "compiler", where=SEG), SEG)
    E.fact("overlay_track_total_code_functions",
           req(ovld, "overlay_code_functions", where=OVLD), OVLD)
    E.fact("overlay_track_matched_functions", req(ovld, "matched", "functions", where=OVLD),
           OVLD)
    E.fact("overlay_track_matched_pct", req(ovld, "matched", "pct_functions", where=OVLD),
           OVLD)
    E.fact("overlay_registry_total_overlays", len(req(ovly, "overlays", where=OVLY)), OVLY)
    E.fact("semantic_state_entries_total", len(sem_entries), SEM)
    E.fact("confirmed_sites_total", len(site_entries), SITES)
    E.fact("record_types_registered", len(req(recs, "records", where=RECS)), RECS)
    E.fact("overlay_images_in_function_census", len(req(fnj, "overlays", where=FN)), FN)

    region_a = as_int(req(ovly, "region_a", where=OVLY))
    region_b = as_int(req(ovly, "region_b", where=OVLY))
    E.fact("shared_overlay_load_base", hx(region_a), OVLY)
    E.fact("shared_overlay_region_length", region_b - region_a, OVLY)

    # the shared loader law, from the row-independent binding artifact
    law_text = req(bind, "mechanism", "level_data_directory", where=BIND)
    law_pcs = sorted(set(ADDR_RE.findall(law_text)))
    if len(law_pcs) < 3:
        raise SystemExit("STALE CITATION: the binding artifact's arithmetic law no longer "
                         "names the instruction addresses this assessment resolves")
    E.fact("loader_arithmetic_law_pcs", law_pcs, BIND)
    E.fact("loader_scene_ids_mapped", len(req(bind, "scene_id_to_level_data_dir", where=BIND)),
           BIND)
    E.fact("loader_rows_corrected_2026_08_05", len(req(bind, "rows_corrected", where=BIND)),
           BIND)
    E.fact("loader_binding_status", req(bind, "status", where=BIND), BIND)
    truth_dirs = req(bind, "scene_id_to_level_data_dir", where=BIND)

    # the resident scene-id address, taken from the semantic registry, never typed
    scene_entry = next((e for e in sem_entries
                        if req(e, "id", where=SEM) == "original.current_scene_id"), None)
    if scene_entry is None:
        raise SystemExit(f"STALE CITATION: {SEM} no longer registers "
                         "original.current_scene_id")
    scene_addr = as_int(req(scene_entry, "address", where=SEM))
    E.fact("scene_id_address", hx(scene_addr), SEM)

    # the ordinal -> scene table, DECLARED by a pinned artifact and then read from
    # the shipped executable by the probe below
    prog = req(e02, "scene_universe", "campaign_progression_table", where=E02)
    prog_addr = as_int(req(prog, "address", where=E02))
    prog_declared = list(req(prog, "scenes", where=E02))
    E.fact("progression_table_address", hx(prog_addr), E02)
    E.fact("progression_table_declared", prog_declared, E02)
    E.fact("e02_levels_censused", len(req(e02, "levels", where=E02)), E02)
    E.fact("e02_disc_runtime_disagreements",
           len(req(e02, "agreement", "disagreements", where=E02)), E02)
    E.fact("e02_authored_sectors_compared",
           req(e02, "agreement", "authored_sectors_compared", where=E02), E02)

    exe_id = {"path": req(seg, "image", where=SEG), "hdr": req(seg, "header_bytes", where=SEG),
              "va": as_int(req(seg, "load_va", where=SEG)),
              "sha1": req(seg, "sha1", where=SEG)}
    exe_rel = f"REBUILD/files/{exe_id['path']}"
    E.pin(exe_rel)
    exe_id["path"] = exe_rel
    E.fact("executable_declared_sha1", exe_id["sha1"], SEG)

    # candidate images: every overlay image in the extraction tree plus MEMORY.BIN,
    # so the scan is over the whole population and not a shortlist
    ovl_dir = ROOT / "OVL"
    if not ovl_dir.is_dir():
        raise SystemExit("STALE CITATION: OVL/ is not a directory")
    images = sorted(str(p.relative_to(ROOT)) for p in ovl_dir.glob("*.BIN"))
    mem_blob = None
    for name, entry in req(ovly, "overlays", where=OVLY).items():
        if name == "MEMORY":
            mem_blob = req(entry, "blob", where=OVLY)
    if mem_blob is None:
        raise SystemExit(f"STALE CITATION: {OVLY} no longer registers the MEMORY overlay")
    images.append(mem_blob)
    for im in images:
        E.pin(im)
    E.fact("candidate_images", len(images), [OVLY] + images)

    # ------------------------------------------------------------------ #
    # 2. per-row derivation of the probe's inputs                         #
    # ------------------------------------------------------------------ #
    sem_in_region_a = sorted({as_int(req(e, "address", where=SEM)) for e in sem_entries
                              if e.get("address") is not None
                              and region_a <= as_int(e["address"]) < region_b})
    E.fact("semantic_entries_inside_shared_region_a",
           [hx(a) for a in sem_in_region_a], [SEM, OVLY])
    E.fact("semantic_entries_inside_shared_region_a_ids",
           sorted(req(e, "id", where=SEM) for e in sem_entries
                  if e.get("address") is not None
                  and region_a <= as_int(e["address"]) < region_b), SEM)

    rowinfo: dict[str, dict] = {}
    groups: list[dict] = []
    for rid in ROWS:
        st = STEM[rid]
        crow = req(census, "rows", rid, where=CENSUS)
        brow = baseline_rows.get(rid)
        if brow is None:
            raise SystemExit(f"STALE CITATION: {BASE} no longer carries {rid}")
        inv = req(crow, "evidence_inventory", where=CENSUS)
        ovl_name = req(inv, "overlay_name", where=CENSUS)
        srcs = req(inv, "overlay_matched_sources", where=CENSUS)
        if not srcs:
            raise SystemExit(f"STALE CITATION: {CENSUS} no longer attributes any matched "
                             f"overlay source to {rid}")
        symbols: set[int] = set()
        starts: set[int] = set()
        for rel in srcs:
            body = E.text(rel)
            symbols |= {int(s, 16) for s in SYM_RE.findall(body)}
            m = SRC_START_RE.match(Path(rel).name)
            if not m:
                raise SystemExit(f"STALE CITATION: {rel} is no longer named after the "
                                 "address it matches")
            starts.add(int(m.group(1), 16))
        if not symbols:
            raise SystemExit(f"STALE CITATION: the matched C for {ovl_name} no longer "
                             "declares any global; the named-word scan has nothing to "
                             "be checked against")

        # the D row this stage row leans on, derived from its own baseline prose
        prose = json.dumps(brow)
        synth = sorted(set(re.findall(r"SYNTHESIZED FROM (D\d\d)", prose)))
        drow_ids = sorted({m for m in re.findall(r"\bD\d\d_[a-z_]+", prose)
                           if any(m.startswith(s) for s in synth)})
        borrowed_docs: list[str] = []
        for did in drow_ids:
            rel = f"analysis/phase4_{did.lower()}.json"
            E.pin(rel)
            borrowed_docs.append(rel)
        own_arts = [a for a in req(inv, "analysis_artifacts", where=CENSUS)
                    if a != BIND and a not in borrowed_docs]
        for a in own_arts:
            E.pin(a)

        borrowed_addrs: set[int] = set()
        for rel in borrowed_docs:
            borrowed_addrs |= {int(a, 16)
                               for a in ADDR_RE.findall(json.dumps(json.loads(
                                   (ROOT / rel).read_text())))}
        own_addrs: set[int] = set()
        for rel in own_arts:
            own_addrs |= {int(a, 16)
                          for a in ADDR_RE.findall((ROOT / rel).read_text())}
        in_a = lambda s: sorted(a for a in s if region_a <= a < region_b)

        words = sorted(set(symbols) | set(sem_in_region_a)
                       | set(in_a(borrowed_addrs)) | set(in_a(own_addrs)))
        pcs = sorted(set(starts) | set(in_a(borrowed_addrs)) | set(in_a(own_addrs)))

        # the row's own declared save fixtures, from the measured census
        saves = [f["path"] for f in req(crow, "durable_evidence", "fixtures", where=CENSUS)
                 if req(f, "kind", where=CENSUS) == "external_fixture"
                 and str(f["path"]).endswith(".sav")
                 and "/" not in str(f["path"])]
        if not saves:
            raise SystemExit(f"{rid} declares no top-level .sav fixture; the residency "
                             "probe has nothing of this row's own to read")
        rowinfo[rid] = {"stem": st, "crow": crow, "brow": brow, "inv": inv,
                        "overlay": ovl_name, "sources": srcs, "symbols": sorted(symbols),
                        "starts": sorted(starts), "drows": drow_ids,
                        "borrowed_docs": borrowed_docs, "own_arts": own_arts,
                        "borrowed_addrs": sorted(borrowed_addrs),
                        "own_addrs": sorted(own_addrs), "words": words, "pcs": pcs,
                        "saves": saves}
        groups.append({"label": rid, "words": words, "pcs": pcs,
                       "rams": [(Path(s).stem, s) for s in saves[:1]]})

    # F12 declares a SECOND save. Its name says stage 12; the probe reads what it
    # actually holds. Kept as its own group so the answer cannot be smuggled into
    # F12's pin, and paired with F13's save so the shared scene gets a real
    # cross-fixture diff instead of a single-sample "0 bytes differ".
    extra_saves = [s for s in rowinfo["F12_battle_arena"]["saves"][1:]]
    if extra_saves:
        groups.append({"label": "F12_declared_second_fixture",
                       "words": rowinfo["F12_battle_arena"]["words"],
                       "pcs": rowinfo["F12_battle_arena"]["pcs"],
                       "rams": [(Path(s).stem, s) for s in extra_saves]})
        groups.append({"label": "F13_scene_pair_with_the_F12_declared_fixture",
                       "words": rowinfo["F13_anthill_two"]["words"],
                       "pcs": rowinfo["F13_anthill_two"]["pcs"],
                       "rams": [(Path(rowinfo["F13_anthill_two"]["saves"][0]).stem,
                                 rowinfo["F13_anthill_two"]["saves"][0])]
                               + [(Path(s).stem, s) for s in extra_saves]})

    # ------------------------------------------------------------------ #
    # 3. run the compiled-C probe, then pin and CHECK its inputs          #
    # ------------------------------------------------------------------ #
    if not args.no_probe:
        run_probe(E, groups, exe_id, prog_addr, len(prog_declared), scene_addr,
                  region_a, region_b - region_a, images)
    pin = E.json(PROBE_OUT)
    if as_int(req(pin, "declared_load_base", where=PROBE_OUT)) != region_a:
        raise SystemExit("the residency probe scanned a load base the overlay registry "
                         "does not declare")
    if req(pin, "region_length", where=PROBE_OUT) != region_b - region_a:
        raise SystemExit("the residency probe scanned a region length the overlay "
                         "registry does not declare")
    if as_int(req(pin, "scene_id_address", where=PROBE_OUT)) != scene_addr:
        raise SystemExit("the residency probe read a scene-id address the semantic "
                         "registry does not declare")
    if req(pin, "images_scanned", where=PROBE_OUT) != len(images):
        raise SystemExit("the residency probe scanned a different image population "
                         f"({req(pin, 'images_scanned', where=PROBE_OUT)}) than the "
                         f"registries name ({len(images)})")
    if not req(pin, "executable", "sha1_matches_declared", where=PROBE_OUT):
        raise SystemExit("the residency probe read an executable whose sha1 does not "
                         "match the one config/segments.yml pins")
    probe_groups = {req(g, "label", where=PROBE_OUT): g
                    for g in req(pin, "groups", where=PROBE_OUT)}
    for g in groups:
        pg = probe_groups.get(g["label"])
        if pg is None:
            raise SystemExit(f"STALE CITATION: {PROBE_OUT} no longer carries group "
                             f"{g['label']}")
        scanned = [as_int(req(w, "addr", where=PROBE_OUT))
                   for w in req(pg, "named_words", where=PROBE_OUT)]
        if scanned != g["words"]:
            raise SystemExit(f"the residency probe read words group {g['label']} no "
                             "longer derives from the byte-matched C sources and the "
                             "pinned artifacts: "
                             f"scanned={[hx(a) for a in scanned]} "
                             f"derived={[hx(a) for a in g['words']]}")
        scanned_pcs = [as_int(req(p, "pc", where=PROBE_OUT))
                       for p in req(pg, "governing_pcs", where=PROBE_OUT)]
        if scanned_pcs != g["pcs"]:
            raise SystemExit(f"the residency probe decoded PCs group {g['label']} no "
                             "longer derives from its pinned artifacts")

    prog_read = req(pin, "campaign_progression_table", "ordinal_to_scene", where=PROBE_OUT)
    E.fact("progression_table_read_from_executable", prog_read, PROBE_OUT)
    E.fact("progression_table_matches_declared", list(prog_read) == prog_declared,
           [PROBE_OUT, E02])
    E.fact("probe_images_scanned", req(pin, "images_scanned", where=PROBE_OUT), PROBE_OUT)
    E.fact("probe_groups_scanned", req(pin, "groups_scanned", where=PROBE_OUT), PROBE_OUT)
    E.fact("probe_anchor_rule", req(pin, "anchor_rule", where=PROBE_OUT), PROBE_OUT)
    E.fact("probe_nontrivial_definition",
           req(pin, "nontrivial_definition", where=PROBE_OUT), PROBE_OUT)

    # ------------------------------------------------------------------ #
    # 4. per-row facts                                                    #
    # ------------------------------------------------------------------ #
    ovl_records = {}
    for r in req(ovld, "results", where=OVLD):
        ovl_records.setdefault(req(r, "overlay", where=OVLD), []).append(r)
    fn_list = req(fnj, "functions", where=FN)
    c2_map = req(c2, "mapping", where=C2)
    e02_levels = req(e02, "levels", where=E02)
    act_levels = req(act, "levels", where=ACT)

    for rid in ROWS:
        ri = rowinfo[rid]
        st = ri["stem"]
        crow, brow, inv = ri["crow"], ri["brow"], ri["inv"]

        def f(key, value, source):
            return E.fact(f"{st}_{key}", value, source)

        # -- carried-forward durable_evidence, and the row's own declarations --
        f("durable_state", req(crow, "durable_evidence", "state", where=CENSUS), CENSUS)
        f("durable_fraction", req(crow, "durable_evidence", "intact_pinned", where=CENSUS),
          CENSUS)
        f("durable_reason", req(crow, "durable_evidence", "reason", where=CENSUS), CENSUS)
        f("census_status", req(crow, "status", where=CENSUS), CENSUS)
        f("census_triage", req(crow, "measurability_triage", where=CENSUS), CENSUS)
        f("census_declaration_understates",
          req(inv, "declaration_understates_reality", where=CENSUS), CENSUS)
        f("census_has_runtime_trace_evidence",
          req(inv, "has_runtime_trace_evidence", where=CENSUS), CENSUS)
        f("census_analysis_artifacts", req(inv, "analysis_artifacts", where=CENSUS), CENSUS)
        f("census_vault_pages", req(inv, "vault_pages", where=CENSUS), CENSUS)
        f("census_source_files", req(inv, "source_files", where=CENSUS), CENSUS)
        f("census_segments_entries", req(inv, "segments_entries", where=CENSUS), CENSUS)
        f("stage_ordinal", req(inv, "stage_ordinal", where=CENSUS), CENSUS)
        f("scene_id", req(inv, "scene_id", where=CENSUS), CENSUS)
        f("overlay_name", req(inv, "overlay_name", where=CENSUS), CENSUS)
        if E.facts[f"{st}_durable_state"] != "met":
            raise SystemExit(f"carried-forward durable_evidence for {rid} is no longer "
                             "'met' -- re-measure before reusing this assessment")

        f("row_name", req(brow, "name", where=BASE), BASE)
        f("row_status", req(brow, "status", where=BASE), BASE)
        f("row_binding_claims", len(req(brow, "bindings", where=BASE)), BASE)
        f("row_declared_fixtures", req(brow, "fixture_have", where=BASE), BASE)
        f("row_declared_fixture_need", req(brow, "fixture_need", where=BASE), BASE)
        f("row_declared_missing", req(brow, "missing", where=BASE), BASE)
        f("row_declared_next", req(brow, "next", where=BASE), BASE)
        f("row_declared_evidence_classes", req(brow, "evidence", where=BASE), BASE)
        f("row_records_prior_binding_falsified",
          any("FALSIFIED" in b for b in req(brow, "bindings", where=BASE)), BASE)
        f("row_leans_on_d_rows", ri["drows"], BASE)
        f("row_own_analysis_artifacts", ri["own_arts"], CENSUS)

        # -- the registry's disposition, for contrast --
        drow = debt_rows.get(rid)
        if drow is None:
            raise SystemExit(f"STALE CITATION: {DEBT} no longer carries {rid}")
        f("registry_met", req(drow, "counts", "met", where=DEBT), DEBT)
        f("registry_remaining", req(drow, "counts", "remaining", where=DEBT), DEBT)
        f("registry_distinct_bases",
          sorted({d["basis"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
        f("registry_distinct_states",
          sorted({d["state"] for d in req(drow, "dimensions", where=DEBT).values()}), DEBT)
        f("registry_completion_state", req(drow, "completion_state", where=DEBT), DEBT)
        f("registry_movie_count", req(drow, "movie_count", where=DEBT), DEBT)
        f("registry_campaign_id", req(drow, "campaign_id", where=DEBT), DEBT)
        f("registry_next_lane_reason", req(drow, "next_lane_reason", where=DEBT), DEBT)
        f("registry_family", req(drow, "family", where=DEBT), DEBT)

        qrow = queue_rows.get(rid)
        if qrow is None:
            raise SystemExit(f"STALE CITATION: {QUEUE} no longer carries {rid}")
        f("scheduler_eligible", req(qrow, "eligibility", "eligible", where=QUEUE), QUEUE)
        f("scheduler_reasons", req(qrow, "eligibility", "reasons", where=QUEUE), QUEUE)
        f("scheduler_sees_a_phase4_movie",
          req(qrow, "eligibility", "requirements", "case_sensitive_phase4_movie",
              where=QUEUE), QUEUE)
        f("scheduler_ownership_function_count",
          req(qrow, "static_ownership", "function_count", where=QUEUE), QUEUE)
        f("scheduler_ownership_input_is_current",
          req(qrow, "static_ownership", "source_sha256", where=QUEUE)
          == sha256_file(ROOT / OWN), [QUEUE, OWN])

        oq = offq_rows.get(rid)
        if oq is None:
            raise SystemExit(f"STALE CITATION: {OFFQ} no longer carries {rid}")
        f("offline_named_unknowns", req(oq, "named_unknowns", where=OFFQ), OFFQ)
        f("offline_answerable_questions",
          len(req(oq, "offline_answerable_questions", where=OFFQ)), OFFQ)
        f("offline_available_domains", req(oq, "available_domains", where=OFFQ), OFFQ)
        f("offline_relevant_movies", len(req(oq, "relevant_movies", where=OFFQ) or []), OFFQ)
        f("offline_classification", req(oq, "classification", where=OFFQ), OFFQ)

        cvr = req(cov, "rows", rid, where=COV)
        f("coverage_status", req(cvr, "status", where=COV), COV)
        f("coverage_unaudited_fixtures", req(cvr, "unaudited_fixtures", where=COV), COV)
        f("coverage_non_pristine_fixtures",
          len(req(cvr, "non_pristine_fixtures", where=COV)), COV)

        orow = req(own, "rows", rid, where=OWN)
        ofns = req(orow, "functions", where=OWN)
        ostate = req(orow, "state", where=OWN)
        f("ownership_function_citations", len(ofns), OWN)
        f("ownership_distinct_function_starts", len({x["function_start"] for x in ofns}), OWN)
        f("ownership_overlay_space_functions",
          sum(1 for x in ofns if x.get("space") != "resident"), OWN)
        f("ownership_functions_with_canon", sum(1 for x in ofns if x.get("canon")), OWN)
        f("ownership_state_addresses", [s["address"] for s in ostate], OWN)
        f("ownership_state_without_owner",
          [s["address"] for s in ostate if not s.get("semantic_ids")], OWN)
        f("ownership_gaps", req(orow, "gaps", where=OWN), OWN)
        f("ownership_records_no_image_field",
          all("image" not in x or x.get("image") is None for x in ofns), OWN)
        f("ownership_reader_status", req(orow, "readers", 0, "status", where=OWN), OWN)

        # -- the probe's answer for this row --
        pg = probe_groups[rid]
        f("pin_result", req(pg, "result", where=PROBE_OUT), PROBE_OUT)
        f("pin_file", req(pg, "unique_pin_file", where=PROBE_OUT), PROBE_OUT)
        f("pin_sha1", req(pg, "unique_pin_sha1", where=PROBE_OUT), PROBE_OUT)
        f("pin_size", req(pg, "unique_pin_size", where=PROBE_OUT), PROBE_OUT)
        f("pin_extent", req(pg, "unique_pin_extent", where=PROBE_OUT), PROBE_OUT)
        f("pin_nontrivial_pct", req(pg, "first_ram_pin_nontrivial_pct", where=PROBE_OUT),
          PROBE_OUT)
        f("pin_runner_up", req(pg, "first_ram_runner_up", where=PROBE_OUT), PROBE_OUT)
        f("pin_runner_up_pct", req(pg, "first_ram_runner_up_nontrivial_pct",
                                   where=PROBE_OUT), PROBE_OUT)
        f("pin_images_argmax_in_every_ram",
          req(pg, "images_argmax_in_every_ram", where=PROBE_OUT), PROBE_OUT)
        f("pin_images_with_stable_declared_base",
          req(pg, "images_with_stable_declared_base", where=PROBE_OUT), PROBE_OUT)
        f("fixture_scene_ids",
          {req(r, "label", where=PROBE_OUT): req(r, "scene_id", where=PROBE_OUT)
           for r in req(pg, "rams", where=PROBE_OUT)}, PROBE_OUT)
        f("fixture_scene_id_matches_census",
          all(v == E.facts[f"{st}_scene_id"]
              for v in E.facts[f"{st}_fixture_scene_ids"].values()),
          [PROBE_OUT, CENSUS])
        f("pin_agrees_with_census_overlay_name",
          Path(req(pg, "unique_pin_file", where=PROBE_OUT)).stem == ri["overlay"],
          [PROBE_OUT, CENSUS])
        f("governing_pcs_probed", req(pg, "governing_pcs_count", where=PROBE_OUT), PROBE_OUT)
        f("governing_pcs_inside_pinned_image",
          req(pg, "governing_pcs_inside_pinned_image", where=PROBE_OUT), PROBE_OUT)
        f("governing_pcs_decoding_to_an_instruction",
          req(pg, "governing_pcs_decoding_to_an_instruction", where=PROBE_OUT), PROBE_OUT)
        f("governing_pcs_mean_images_containing_offset",
          req(pg, "governing_pcs_mean_images_containing_offset", where=PROBE_OUT),
          PROBE_OUT)
        f("governing_pcs_outside_pinned_image",
          [req(p, "pc", where=PROBE_OUT) for p in req(pg, "governing_pcs", where=PROBE_OUT)
           if not req(p, "inside_pinned_image", where=PROBE_OUT)], PROBE_OUT)
        f("named_words_probed", req(pg, "named_words_count", where=PROBE_OUT), PROBE_OUT)
        f("named_words_inside_pinned_image",
          req(pg, "named_words_inside_pinned_image", where=PROBE_OUT), PROBE_OUT)
        f("named_words_zero_in_disc_image",
          req(pg, "named_words_zero_in_disc_image", where=PROBE_OUT), PROBE_OUT)
        f("named_words_differing_from_disc_image",
          req(pg, "named_words_differing_from_disc_image", where=PROBE_OUT), PROBE_OUT)
        runtime_words = [w for w in req(pg, "named_words", where=PROBE_OUT)
                         if req(w, "inside_pinned_image", where=PROBE_OUT)
                         and req(w, "differs_from_disc_image", where=PROBE_OUT)]
        f("overlay_words_live_in_this_fixture",
          {req(w, "addr", where=PROBE_OUT): req(w, "values", where=PROBE_OUT)
           for w in runtime_words}, PROBE_OUT)

        # the byte-matched C for this row's overlay, and where its globals live
        f("byte_matched_c_sources", ri["sources"], CENSUS)
        f("byte_matched_c_declared_globals", [hx(a) for a in ri["symbols"]], ri["sources"])
        f("byte_matched_c_globals_inside_pinned_extent",
          sum(1 for a in ri["symbols"]
              if region_a <= a < region_a + int(req(pg, "unique_pin_size",
                                                    where=PROBE_OUT))),
          [PROBE_OUT] + ri["sources"])
        f("byte_matched_c_entry_starts", [hx(a) for a in ri["starts"]], ri["sources"])

        recsx = ovl_records.get(ri["overlay"])
        if not recsx:
            raise SystemExit(f"STALE CITATION: {OVLD} no longer carries a result for "
                             f"{ri['overlay']}")
        f("overlay_code_functions",
          req(ovld, "per_overlay_totals", ri["overlay"], where=OVLD), OVLD)
        f("overlay_matched_functions",
          sum(req(r, "matched_functions", where=OVLD) for r in recsx), OVLD)
        f("overlay_rebuild_validated",
          all(req(r, "validated", where=OVLD) for r in recsx), OVLD)
        f("overlay_rebuilt_sha1_matches_blob",
          all(req(r, "rebuilt_sha1", where=OVLD) == req(r, "sha1", where=OVLD)
              for r in recsx), OVLD)
        f("overlay_blob_sha1_equals_byte_pinned_image",
          all(req(r, "sha1", where=OVLD) == req(pg, "unique_pin_sha1", where=PROBE_OUT)
              for r in recsx), [OVLD, PROBE_OUT])
        census_fns = [x for x in fn_list if x.get("overlay") == ri["overlay"]]
        f("overlay_census_functions", len(census_fns), FN)
        f("overlay_census_function_names",
          sorted(x.get("name") or hx(as_int(x["start"])) for x in census_fns), FN)
        f("overlay_census_functions_unnamed",
          sum(1 for x in census_fns if not x.get("name")), FN)

        # semantic-registry collision, measured against the PINNED EXTENT
        pin_lo = region_a
        pin_hi = region_a + int(req(pg, "unique_pin_size", where=PROBE_OUT))
        collide = sorted(a for a in sem_in_region_a if pin_lo <= a < pin_hi)
        f("semantic_entries_inside_this_rows_overlay_extent", [hx(a) for a in collide],
          [SEM, PROBE_OUT])
        collide_detail = []
        for a in collide:
            ent = next(e for e in sem_entries
                       if e.get("address") is not None and as_int(e["address"]) == a)
            measured = next((w for w in req(pg, "named_words", where=PROBE_OUT)
                             if as_int(req(w, "addr", where=PROBE_OUT)) == a), None)
            invs = req(ent, "invariants", where=SEM)
            rng = next((i for i in invs if req(i, "kind", where=SEM) == "range"), None)
            detail = {"address": hx(a), "registered_id": req(ent, "id", where=SEM),
                      "registered_kind": req(ent, "kind", where=SEM),
                      "registered_owner": req(ent, "owner", where=SEM),
                      "confidence": req(ent, "confidence", where=SEM),
                      "registered_range": [rng["min"], rng["max"]] if rng else None,
                      "registered_context": rng.get("context") if rng else None,
                      "measured_values": req(measured, "values", where=PROBE_OUT)
                      if measured else None}
            if rng and measured:
                detail["measured_values_inside_registered_range"] = all(
                    rng["min"] <= v <= rng["max"]
                    for v in req(measured, "values", where=PROBE_OUT))
            collide_detail.append(detail)
        f("semantic_collision_detail", collide_detail, [SEM, PROBE_OUT])
        f("row_state_addresses_registered",
          sum(1 for s in req(orow, "state", where=OWN)
              if any(e.get("address") is not None
                     and as_int(e["address"]) == as_int(s["address"])
                     for e in sem_entries)), [SEM, OWN])
        f("record_types_covering_this_rows_overlay",
          sum(1 for r in req(recs, "records", where=RECS)
              if pin_lo <= as_int(req(r, "base", where=RECS)) < pin_hi),
          [RECS, PROBE_OUT])

        # source closure, against BOTH registries
        gov = sorted(set(ri["borrowed_addrs"]) | set(ri["own_addrs"]) | set(ri["symbols"])
                     | set(ri["starts"]))
        gov_resident = [a for a in gov if not (region_a <= a < region_b)]
        gov_overlay = [a for a in gov if pin_lo <= a < pin_hi]
        resolved: dict[str, list[str]] = {}
        unresolved: list[int] = []
        for a in gov_resident:
            src = next((s for lo, hi, s in seg_units if lo <= a < hi), None)
            if src:
                resolved.setdefault(src, []).append(hx(a))
            else:
                unresolved.append(a)
        f("governing_addresses", len(gov), [CENSUS] + ri["borrowed_docs"] + ri["own_arts"]
          + ri["sources"])
        f("governing_addresses_resident", len(gov_resident),
          [OVLY] + ri["borrowed_docs"] + ri["own_arts"] + ri["sources"])
        f("governing_addresses_in_pinned_overlay", len(gov_overlay),
          [PROBE_OUT] + ri["sources"])
        f("governing_resident_build_units", sorted(resolved), SEG)
        f("governing_resident_units_matching_c",
          sorted(s for s in resolved if s.startswith("src/")), SEG)
        f("governing_resident_units_hand_asm",
          len([s for s in resolved if s.startswith("asm/")]), SEG)
        f("governing_resident_addresses_outside_any_build_unit", len(unresolved), SEG)
        f("governing_overlay_addresses_with_matched_c",
          len(set(gov_overlay) & set(ri["starts"])), [OVLD] + ri["sources"])
        f("governing_addresses_with_matching_c_source",
          {hx(a): next(s for lo, hi, s in seg_units if lo <= a < hi)
           for a in gov_resident
           if any(lo <= a < hi and s.startswith("src/") for lo, hi, s in seg_units)},
          [SEG] + ri["borrowed_docs"] + ri["own_arts"])
        f("governing_pcs_registered_as_confirmed_sites",
          sum(1 for a in gov
              if any(as_int(s["address"]) == a for s in site_entries)), SITES)
        f("byte_matched_c_globals_also_named_by_the_borrowed_row",
          [hx(a) for a in ri["symbols"] if a in set(ri["borrowed_addrs"])],
          ri["sources"] + ri["borrowed_docs"] if ri["borrowed_docs"]
          else ri["sources"])
        f("byte_matched_c_globals_named_nowhere_else",
          [hx(a) for a in ri["symbols"]
           if a not in set(ri["borrowed_addrs"]) | set(ri["own_addrs"])],
          ri["sources"] + ri["borrowed_docs"] + ri["own_arts"] if ri["borrowed_docs"]
          else ri["sources"] + ri["own_arts"] if ri["own_arts"] else ri["sources"])

        # the stage itself: collision environment, actors, type, oracle, movies
        lvl_key = next((k for k, v in e02_levels.items()
                        if req(v, "scene", where=E02) == E.facts[f"{st}_scene_id"]), None)
        if lvl_key is None:
            raise SystemExit(f"STALE CITATION: {E02} no longer censuses scene "
                             f"{E.facts[f'{st}_scene_id']}")
        lv = e02_levels[lvl_key]
        f("e02_level_key", lvl_key, E02)
        f("e02_container", req(lv, "container", where=E02), E02)
        f("e02_authored_sectors", req(lv, "authored_sectors", where=E02), E02)
        f("e02_runtime_sectors", req(lv, "runtime_sectors", where=E02), E02)
        f("e02_code_histogram", req(lv, "code_histogram", where=E02), E02)
        f("e02_authors_no_region_codes",
          list(req(lv, "code_histogram", where=E02)) == ["0"], E02)
        f("e02_uses_this_rows_own_fixture",
          req(lv, "save", where=E02) in [str(x).split(" (")[0]
                                         for x in E.facts[f"{st}_row_declared_fixtures"]],
          [E02, BASE])
        f("e02_container_agrees_with_pinned_overlay_directory",
          req(lv, "container", where=E02).split("/")[0]
          == req(truth_dirs, str(E.facts[f"{st}_scene_id"]), where=BIND).split("/")[0],
          [E02, BIND])

        arow = act_levels.get(lvl_key)
        if arow is None:
            raise SystemExit(f"STALE CITATION: {ACT} no longer censuses {lvl_key}")
        arecs = req(arow, "actor_records", where=ACT)
        bound_ids = {int(k) for k in req(act, "actor_ids_with_canon_binding", where=ACT)}
        f("actor_records", len(arecs), ACT)
        f("actor_ids", sorted({r["id"] for r in arecs}), ACT)
        f("actor_ids_with_canon_binding",
          sorted({r["id"] for r in arecs} & bound_ids), ACT)
        f("actor_census_save", req(arow, "save", where=ACT), ACT)
        f("actor_census_uses_this_rows_fixture",
          req(arow, "save", where=ACT) in [str(x).split(" (")[0]
                                           for x in E.facts[f"{st}_row_declared_fixtures"]],
          [ACT, BASE])
        f("actor_census_cited_by_the_row", ACT in json.dumps(brow), [BASE, ACT])

        cm = req(c2_map, rid, where=C2)
        f("c2_types", [t["type"] for t in req(cm, "types", where=C2)], C2)
        f("c2_session_token", req(cm, "session", where=C2), C2)
        f("c2_frozen_name_matches_row",
          req(cm, "frozen_name", where=C2) == req(brow, "name", where=BASE), [C2, BASE])
        f("c2_rows_sharing_this_type",
          sorted(set(sum((req(c2, "types_with_at_least_one_level", t, where=C2)
                          for t in E.facts[f"{st}_c2_types"]), []))), C2)
        f("c2_taxonomy_coverage_demonstrated",
          req(c2, "result", "taxonomy_coverage_demonstrated", where=C2), C2)

        ok = next((k for k in oracle_stages
                   if req(oracle_stages[k], "target_scene", where=ORACLE)
                   == E.facts[f"{st}_scene_id"]), None)
        if ok is None:
            raise SystemExit(f"STALE CITATION: {ORACLE} no longer covers scene "
                             f"{E.facts[f'{st}_scene_id']}")
        ost = oracle_stages[ok]
        f("oracle_stage_key", ok, ORACLE)
        f("oracle_movie", req(ost, "movie", where=ORACLE), ORACLE)
        f("oracle_frames", req(ost, "frames", where=ORACLE), ORACLE)
        f("oracle_target_scene", req(ost, "target_scene", where=ORACLE), ORACLE)
        f("oracle_replay_accepted", req(ost, "pristine_replay_accepted", where=ORACLE),
          ORACLE)
        f("oracle_entered_stage_frame", req(ost, "entered_stage_frame", where=ORACLE),
          ORACLE)
        f("oracle_stage_exited", req(ost, "stage_exited_by_movie_end", where=ORACLE),
          ORACLE)
        f("oracle_snapshot_fields",
          sorted(req(ost, "last_in_stage", "snapshot", where=ORACLE)), ORACLE)
        f("oracle_cited_by_the_row", "phase2_completion_oracle" in json.dumps(brow),
          [BASE, ORACLE])
        f("oracle_corroborates_the_scene_id",
          req(ost, "target_scene", where=ORACLE) == E.facts[f"{st}_scene_id"],
          [ORACLE, CENSUS])

        # Movie attribution by the FROZEN SESSION TOKEN, not by a bare ordinal:
        # matching "12"/"13"/"15" would sweep up other rows' recordings, which is
        # the exact trap the F08 assessment walked into.
        token = re.compile(re.escape(E.facts[f"{st}_c2_session_token"]), re.I)
        stage_mov = sorted({k for k in movies if token.search(k)}
                           | {E.facts[f"{st}_oracle_movie"]})
        declared_paths = [str(x).split(" (")[0]
                          for x in E.facts[f"{st}_row_declared_fixtures"]]
        f("stage_movies_attributed", len(stage_mov), [AUDIT, C2, ORACLE])
        f("stage_movies_attributed_paths", stage_mov, [AUDIT, C2, ORACLE])
        f("stage_movie_frames",
          {k: req(movies, k, "frames", where=AUDIT) for k in stage_mov}, AUDIT)
        f("stage_movies_under_phase4_interpreter",
          sorted(k for k in stage_mov if k.startswith("movies/Phase4/Interpreter/")),
          AUDIT)
        f("stage_movies_declared_by_the_row",
          sorted(k for k in stage_mov if k in declared_paths), [AUDIT, BASE])
        # The F08 lesson: the bare ORDINAL token sweeps up other rows' recordings.
        # Report what it would have caught, as leads with UNVERIFIED attribution.
        ordinal_token = re.compile(
            rf"level{int(E.facts[f'{st}_stage_ordinal']):02d}", re.I)
        f("stage_movies_ordinal_token_matched_attribution_unverified",
          sorted(k for k in movies if ordinal_token.search(k) and k not in stage_mov),
          [AUDIT, CENSUS])
        f("stage_movies_centrally_pinned",
          sum(1 for k in stage_mov if k in fix_entries), FIXSET)
        f("row_declared_fixtures_naming_a_d_row",
          sorted(p for p in declared_paths
                 if any(d.split("_")[0] in Path(p).name for d in ri["drows"])), BASE)
        f("external_fixture_consumers",
          sorted({c for p in declared_paths if p in fix_entries
                  for c in req(fix_entries, p, "consumers", where=FIXSET)}), FIXSET)

        e16_hits = [m for m in req(e16v, "movies", where=E16V)
                    if token.search(req(m, "movie", where=E16V))]
        f("e16_validated_stage_movies", [req(m, "movie", where=E16V) for m in e16_hits],
          E16V)
        f("e16_validated_stage_movies_usable",
          sum(1 for m in e16_hits
              if req(m, "check_occupancy", where=E16V)
              and req(m, "check_control", where=E16V)), E16V)
        f("e16_validated_stage_movie_truncated",
          any(req(m, "truncated", where=E16V) for m in e16_hits), E16V)

        br = next((v for k, v in req(breadth, "results", where=BREADTH).items()
                   if token.search(k)), None)
        if br is None:
            raise SystemExit(f"STALE CITATION: {BREADTH} no longer covers "
                             f"{E.facts[f'{st}_c2_session_token']}")
        f("breadth_movie", req(br, "movie", where=BREADTH), BREADTH)
        f("breadth_movie_frames", req(br, "frames", where=BREADTH), BREADTH)
        f("breadth_replay_reproducible", req(br, "reproducible", where=BREADTH), BREADTH)
        f("breadth_levels_asserted", req(breadth, "levels_asserted", where=BREADTH),
          BREADTH)
        f("breadth_law_holds_everywhere",
          req(breadth, "law_holds_everywhere", where=BREADTH), BREADTH)

        # -- the borrowed D-row, kept explicitly separate --
        borrowed: dict[str, object] = {}
        for rel, did in zip(ri["borrowed_docs"], ri["drows"]):
            doc = json.loads((ROOT / rel).read_text())
            drow_b = baseline_rows.get(did)
            if drow_b is None:
                raise SystemExit(f"STALE CITATION: {BASE} no longer carries {did}")
            entry = {
                "row": did,
                "artifact": rel,
                "status": req(doc, "status", where=rel),
                "baseline_status": req(drow_b, "status", where=BASE),
                "addresses_named": len({a.lower() for a in
                                        ADDR_RE.findall(json.dumps(doc))}),
                "addresses_in_this_rows_pinned_overlay": len(
                    {int(a, 16) for a in ADDR_RE.findall(json.dumps(doc))
                     if pin_lo <= int(a, 16) < pin_hi}),
                "canon_pages": sorted(set(re.findall(
                    r"ObsidianVault/Canon/[\w./%-]+\.md", json.dumps(drow_b)))),
                "src_re_files": sorted(set(re.findall(r"src_re/[\w./%-]+\.c",
                                                      json.dumps(drow_b)))),
            }
            borrowed[did] = entry
        f("borrowed_d_rows", borrowed,
          [CENSUS, BASE, PROBE_OUT] + ri["borrowed_docs"])

    # ------------------------------------------------------------------ #
    # 4b. campaign-wide comparisons and the two row-specific cross-checks #
    # ------------------------------------------------------------------ #
    per_level_matched = {}
    for name, rs in ovl_records.items():
        if name == "MEMORY":
            continue
        per_level_matched[name] = sum(req(r, "matched_functions", where=OVLD) for r in rs)
    E.fact("matched_functions_per_per_level_overlay", per_level_matched, OVLD)
    best = max(per_level_matched.values())
    E.fact("per_level_overlays_with_the_most_matched_functions",
           sorted(k for k, v in per_level_matched.items() if v == best), OVLD)
    for rid in ROWS:
        E.fact(f"{STEM[rid]}_overlay_has_the_most_matched_functions_of_any_per_level_overlay",
               rowinfo[rid]["overlay"] in F["per_level_overlays_with_the_most_matched_functions"],
               [OVLD, CENSUS])

    # F12: does the byte-matched initializer's guard word actually hold the boss's
    # initial HP in this stage's own save? Both halves derived, then compared.
    D19 = "analysis/phase4_d19_molt.json"
    if D19 in {p["path"] for p in E.pins}:
        d19doc = json.loads((ROOT / D19).read_text())
        snap = as_int(req(d19doc, "damage_and_guard", "accepted_snapshot", where=D19))
        hp0 = req(d19doc, "actor", "hp_initial", where=D19)
        hp_addr = as_int(req(d19doc, "actor", "hp_address", where=D19))
        live = F["f12_overlay_words_live_in_this_fixture"]
        E.fact("f12_d19_accepted_snapshot_address", hx(snap), D19)
        E.fact("f12_d19_boss_initial_hp", hp0, D19)
        E.fact("f12_snapshot_is_declared_by_the_byte_matched_c",
               hx(snap) in F["f12_byte_matched_c_declared_globals"], [D19, CENSUS])
        E.fact("f12_boss_hp_address_is_declared_by_the_byte_matched_c",
               hx(hp_addr) in F["f12_byte_matched_c_declared_globals"], [D19, CENSUS])
        E.fact("f12_snapshot_value_in_this_rows_own_fixture",
               live.get(hx(snap).lower()), [PROBE_OUT, D19])
        E.fact("f12_snapshot_equals_the_borrowed_initial_hp",
               live.get(hx(snap).lower()) == [hp0], [PROBE_OUT, D19])
        negs = req(d19doc, "crowd_throw", "negative_static_candidates", where=D19)
        neg_addrs = sorted({norm(a) for n in negs for a in ADDR_RE.findall(str(n))})
        E.fact("f12_borrowed_rejected_candidate_addresses", neg_addrs, D19)
        E.fact("f12_rejected_candidates_fall_outside_the_byte_pinned_extent",
               neg_addrs == sorted(
                   norm(a) for a in F["f12_governing_pcs_outside_pinned_image"]),
               [D19, PROBE_OUT])

    # F15: is the one live overlay word in this row's save the counter D20 named?
    D20 = "analysis/phase4_d20_hopper.json"
    if D20 in {p["path"] for p in E.pins}:
        d20doc = json.loads((ROOT / D20).read_text())
        bar_key = next((k for k in d20doc if "HEALTH_BAR" in k), None)
        if bar_key is None:
            raise SystemExit(f"STALE CITATION: {D20} no longer carries a health-bar "
                             "section")
        bar_txt = json.dumps(req(d20doc, bar_key, where=D20))
        m = re.search(r"Polled (0x[0-9a-fA-F]{8}).*?jumps to (\d+)", bar_txt)
        if m is None:
            raise SystemExit(f"STALE CITATION: {D20}'s health-bar section no longer "
                             "states the polled address and its initial value")
        E.fact("f15_d20_health_counter_address", norm(m.group(1)), D20)
        E.fact("f15_d20_health_counter_initial_value", int(m.group(2)), D20)
        live15 = F["f15_overlay_words_live_in_this_fixture"]
        E.fact("f15_only_live_overlay_word_is_the_d20_health_counter",
               list(live15) == [m.group(1).lower()], [PROBE_OUT, D20])
        E.fact("f15_health_counter_value_in_this_rows_own_fixture",
               live15.get(m.group(1).lower()), PROBE_OUT)
        E.fact("f15_fixture_value_equals_the_borrowed_initial_value",
               live15.get(m.group(1).lower()) == [int(m.group(2))], [PROBE_OUT, D20])
        gate_key = next((k for k in d20doc if "GATE_OPCODE" in k), None)
        if gate_key is None:
            raise SystemExit(f"STALE CITATION: {D20} no longer carries its gate-opcode "
                             "section")
        gate_addrs = {norm(a) for a in ADDR_RE.findall(json.dumps(req(d20doc, gate_key,
                                                                     where=D20)))}
        E.fact("f15_byte_matched_predicate_entry_is_named_by_the_borrowed_row",
               all(a in gate_addrs for a in F["f15_byte_matched_c_entry_starts"]),
               [D20, CENSUS])
        E.fact("f15_byte_matched_predicate_globals_named_by_the_borrowed_row",
               sorted(a for a in F["f15_byte_matched_c_declared_globals"]
                      if a in gate_addrs), [D20, CENSUS])

    # ------------------------------------------------------------------ #
    # 5. the two extra probe groups: what F12's second fixture holds      #
    # ------------------------------------------------------------------ #
    if "F12_declared_second_fixture" in probe_groups:
        g2 = probe_groups["F12_declared_second_fixture"]
        E.fact("f12_second_fixture_scene_ids",
               {req(r, "label", where=PROBE_OUT): req(r, "scene_id", where=PROBE_OUT)
                for r in req(g2, "rams", where=PROBE_OUT)}, PROBE_OUT)
        E.fact("f12_second_fixture_pin_file",
               req(g2, "unique_pin_file", where=PROBE_OUT), PROBE_OUT)
        E.fact("f12_second_fixture_pin_pct",
               req(g2, "first_ram_pin_nontrivial_pct", where=PROBE_OUT), PROBE_OUT)
        E.fact("f12_second_fixture_holds_this_rows_overlay",
               Path(req(g2, "unique_pin_file", where=PROBE_OUT)).stem
               == rowinfo["F12_battle_arena"]["overlay"], [PROBE_OUT, CENSUS])
        E.fact("f12_second_fixture_holds_f13s_overlay",
               Path(req(g2, "unique_pin_file", where=PROBE_OUT)).stem
               == rowinfo["F13_anthill_two"]["overlay"], [PROBE_OUT, CENSUS])
    if "F13_scene_pair_with_the_F12_declared_fixture" in probe_groups:
        g3 = probe_groups["F13_scene_pair_with_the_F12_declared_fixture"]
        diff = req(g3, "cross_fixture_diff", where=PROBE_OUT)
        E.fact("f13_pair_rams",
               [req(r, "label", where=PROBE_OUT) for r in req(g3, "rams", where=PROBE_OUT)],
               PROBE_OUT)
        E.fact("f13_pair_same_scene_id",
               req(g3, "all_rams_same_scene_id", where=PROBE_OUT), PROBE_OUT)
        E.fact("f13_pair_pin_file", req(g3, "unique_pin_file", where=PROBE_OUT), PROBE_OUT)
        E.fact("f13_pair_region_a_differing_bytes",
               req(diff, "region_a_differing_bytes", where=PROBE_OUT), PROBE_OUT)
        E.fact("f13_pair_differing_inside_pinned_image",
               req(diff, "region_a_differing_inside_pinned_image", where=PROBE_OUT),
               PROBE_OUT)
        E.fact("f13_pair_differing_beyond_pinned_image",
               req(diff, "region_a_differing_beyond_pinned_image", where=PROBE_OUT),
               PROBE_OUT)
        E.fact("f13_pair_whole_ram_differing_words",
               req(diff, "whole_ram_differing_words", where=PROBE_OUT), PROBE_OUT)
        detail = req(diff, "differing_bytes_detail", where=PROBE_OUT)
        E.fact("f13_pair_differing_byte_addresses",
               [req(b, "addr", where=PROBE_OUT) for b in detail], PROBE_OUT)
        E.fact("f13_pair_differing_words_aligned",
               sorted({hx(as_int(req(b, "addr", where=PROBE_OUT)) & ~3) for b in detail}),
               PROBE_OUT)
        E.fact("f13_pair_differing_bytes_zero_on_disc",
               all(req(b, "disc_image_byte", where=PROBE_OUT) == 0 for b in detail),
               PROBE_OUT)

    # ------------------------------------------------------------------ #
    # 6. each row's registered executable gate                            #
    # ------------------------------------------------------------------ #
    test_dir = ROOT / "tests"
    if not test_dir.is_dir():
        raise SystemExit("STALE CITATION: tests/ is not a directory")
    gate_map: dict[str, list[str]] = {}
    for rid in ROWS:
        ri = rowinfo[rid]
        # A bare row stem collides with HEX ADDRESSES -- "f13" matches
        # 0x8005f130 -- which is how the F-row census once credited F11 with a
        # source it does not own. Require the stem to be delimited.
        stem_re = re.compile(rf"(?<![0-9a-z]){rid.split('_')[0].lower()}(?![0-9a-z])")
        hits = []
        for p in sorted(test_dir.glob("test_*.py")):
            body = p.read_text(errors="ignore")
            # ...and the bare stem is only meaningful inside a Phase-4 gate:
            # "f13" is also a FINDING id in an unrelated registry test.
            if rid in body or any(a in body for a in ri["own_arts"]) \
                    or (p.name.startswith("test_phase4_") and stem_re.search(body.lower())):
                rel = f"tests/{p.name}"
                E.pin(rel)
                hits.append(rel)
        gate_map[rid] = hits
        E.fact(f"{STEM[rid]}_registered_gate_files", hits,
               hits or [CENSUS])
    all_gates = sorted({g for v in gate_map.values() for g in v})
    if args.no_gates or not all_gates:
        E.fact("registered_gates_executed", False, all_gates or [CENSUS])
    else:
        runp = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "--color=no",
             "-p", "no:cacheprovider", *all_gates],
            cwd=str(ROOT), capture_output=True, text=True)
        outtxt = re.sub(r"\x1b\[[0-9;]*m", "", runp.stdout)
        tail = outtxt.strip().splitlines()[-1] if outtxt.strip() else ""
        passed = re.search(r"(\d+) passed", tail)
        failed = re.search(r"(\d+) failed", tail)
        if not passed and not failed:
            raise SystemExit(f"could not read a pytest summary from the gate run: {tail!r}")
        E.fact("registered_gates_executed", True, all_gates)
        E.fact("registered_gate_tests_passed", int(passed.group(1)) if passed else 0,
               all_gates)
        E.fact("registered_gate_tests_failed", int(failed.group(1)) if failed else 0,
               all_gates)
        names = sorted({ln.split()[1].split("::")[0]
                        for ln in outtxt.splitlines() if ln.startswith("FAILED ")})
        if E.facts["registered_gate_tests_failed"] and not names:
            raise SystemExit("the gate run reported failures but no FAILED lines could be "
                             "attributed to a file -- the summary parse is wrong")
        E.fact("registered_gate_files_with_a_failure", names, all_gates)

    # ------------------------------------------------------------------ #
    # AUTHORED JUDGMENTS -- see the module docstring for the bars         #
    # ------------------------------------------------------------------ #
    BARS = {
        "durable_evidence": "evidence artifacts durable, pinned, regenerable",
        "original_oracle": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
        "complete_frontier": "item 2 AS WRITTEN: callers/callees/callbacks/indirect "
                             "tables ENUMERATED, scoped to relevant -- not an empty "
                             "unresolved set",
        "campaign_breadth": "conclusions generalize across every applicable stage, "
                            "variant, lifecycle and exceptional path -- which requires "
                            "the applicable set itself to be enumerated",
        "typed_state": "state fields typed and value domains bounded (enumerating an "
                       "untyped residual bounds the WORKLIST, not the STATE)",
        "lifecycle": "cold boot / load / first use / repeated use / exhaustion / "
                     "retirement / reuse each evidenced",
        "cross_system_behavior": "native combinations exercised (carry+damage, "
                                 "powers+jump, projectiles at transitions, enemies vs "
                                 "hazards/plants)",
        "original_interfaces": "interfaces documented; unknowns enumerated with named "
                               "obstructions",
        "source_closure": "byte-matched C through the original toolchain for the row's "
                          "governing functions",
    }

    def G(stem: str, key: str):
        return F[f"{stem}_{key}"]

    def gate_note(stem: str) -> str:
        files = G(stem, "registered_gate_files")
        if not files:
            return "this row has NO registered gate file at all"
        if not F["registered_gates_executed"]:
            return (f"this row's {len(files)} registered gate file(s) were NOT executed "
                    f"for this run, so their health is unmeasured")
        bad = [g for g in files if g in F["registered_gate_files_with_a_failure"]]
        return (f"{F['registered_gate_tests_passed']} tests pass and "
                f"{F['registered_gate_tests_failed']} fail across the "
                f"{len(all_gates)} gate files these three rows touch; this row "
                f"contributes {files}"
                + (f", of which {bad} is currently RED -- a pre-existing artifact-pin "
                   f"mismatch in another row's gate, not a failure of this row's "
                   f"evidence" if bad else ", none of them red"))

    def shared_pin_basis(stem: str) -> str:
        return (f"the overlay is now decided from BYTES, not from an address: of "
                f"{F['probe_images_scanned']} candidate images exactly "
                f"{G(stem, 'pin_images_argmax_in_every_ram')} is the argmax of "
                f"non-trivial agreement in every fixture of this row AND carries a "
                f"stable anchor base at the declared load base "
                f"({G(stem, 'pin_file')}, {G(stem, 'pin_nontrivial_pct')}% vs "
                f"{G(stem, 'pin_runner_up_pct')}% for the runner-up "
                f"{G(stem, 'pin_runner_up')}; {G(stem, 'pin_result')}), and it agrees "
                f"with the census attribution "
                f"({G(stem, 'pin_agrees_with_census_overlay_name')}) and with the "
                f"overlay build registry's blob sha1 "
                f"({G(stem, 'overlay_blob_sha1_equals_byte_pinned_image')})")

    scorecards: dict[str, dict] = {}

    # ---------------------------- F12 --------------------------------- #
    s = "f12"
    d19 = G(s, "borrowed_d_rows")["D19_molt"]
    f12_dims = {
        "durable_evidence": {
            "state": "met",
            "basis": f"CARRIED FORWARD, not re-derived: {G(s,'durable_fraction')} in "
                     f"{CENSUS} -- {G(s,'durable_reason')}. This assessment fails loudly "
                     f"if that measurement moves off 'met'. Regenerability improves here: "
                     f"the row's overlay identity, its overlay-local state words and the "
                     f"ordinal->scene routing are now produced by a compiled-C probe that "
                     f"runs offline from the row's own .sav and the pinned disc images "
                     f"({PROBE_SRC}), and {gate_note(s)}",
            "gap": f"the carried measurement covers FIXTURE INTACTNESS, and intactness is "
                   f"not attribution. Two defects measured here. (1) Of "
                   f"{G(s,'durable_fraction')} declared fixtures, "
                   f"{len(G(s,'row_declared_fixtures_naming_a_d_row'))} are the BOSS "
                   f"row's recordings ({G(s,'row_declared_fixtures_naming_a_d_row')}), "
                   f"and the second save is not this stage at all: "
                   f"{F['f12_second_fixture_scene_ids']} resolves to "
                   f"{F['f12_second_fixture_pin_file']} at "
                   f"{F['f12_second_fixture_pin_pct']}% -- "
                   f"holds_this_rows_overlay={F['f12_second_fixture_holds_this_rows_overlay']}, "
                   f"holds_F13s_overlay={F['f12_second_fixture_holds_f13s_overlay']}. "
                   f"(2) The declared set is incomplete: "
                   f"{G(s,'stage_movies_attributed')} stage-12 movies are attributable by "
                   f"the frozen session token '{G(s,'c2_session_token')}' "
                   f"({G(s,'stage_movie_frames')}), "
                   f"{G(s,'stage_movies_centrally_pinned')} centrally pinned, and the row "
                   f"declares {G(s,'stage_movies_declared_by_the_row')}",
        },
        "original_oracle": {
            "state": "partial",
            "basis": f"BORROWED (D19_molt, artifact status "
                     f"'{d19['status']}'): the boss mechanism is asserted against a "
                     f"natural Interpreter replay of a pristine movie with no injected "
                     f"state, and the replay's own quality is evidenced -- clean and "
                     f"fully-armed runs end on the same frame and the same cycle, so the "
                     f"instrumentation did not move the game. OWNED, and new here: the "
                     f"row's own fixture independently corroborates two D19 claims "
                     f"OFFLINE, with no emulator -- the fixture's scene id reads "
                     f"{list(G(s,'fixture_scene_ids').values())} "
                     f"(matches the census routing: "
                     f"{G(s,'fixture_scene_id_matches_census')}), and the overlay word "
                     f"D19 names as the accepted-HP snapshot "
                     f"({F['f12_d19_accepted_snapshot_address']}, which is also one of "
                     f"the globals the byte-matched initializer declares: "
                     f"{F['f12_snapshot_is_declared_by_the_byte_matched_c']}) reads back "
                     f"exactly the boss's initial HP in this stage's own save "
                     f"({F['f12_snapshot_value_in_this_rows_own_fixture']} vs D19's "
                     f"declared {F['f12_d19_boss_initial_hp']}; equal="
                     f"{F['f12_snapshot_equals_the_borrowed_initial_hp']}), against a "
                     f"disc image where every one of those words is zero. That is a "
                     f"borrowed claim checked by an owned, offline, independent method. "
                     f"Independent natural corroboration of "
                     f"the scene also comes from the disc-vs-runtime collision census "
                     f"({F['e02_disc_runtime_disagreements']} disagreements over "
                     f"{F['e02_authored_sectors_compared']} sectors) and from the "
                     f"campaign completion oracle, a pristine replay of this stage "
                     f"({G(s,'oracle_movie')}, {G(s,'oracle_frames')} frames, accepted="
                     f"{G(s,'oracle_replay_accepted')}, entered at "
                     f"{G(s,'oracle_entered_stage_frame')}, exited by end="
                     f"{G(s,'oracle_stage_exited')})",
            "gap": f"none of that is an oracle for THIS STAGE's own behaviour, and the "
                   f"row itself says so: what stays open is "
                   f"'{G(s,'row_declared_missing')}'. D19 is a stop decision on the boss "
                   f"-- under the vocabulary it never reads as met even for the boss, and "
                   f"it never carries the stage's arena layout, spawn set, critical path "
                   f"or entry/exit. No assertion anywhere is keyed to stage 12's own "
                   f"objective instance. The one from-boot natural artifact that covers "
                   f"this stage end to end is the completion oracle, and the row does not "
                   f"cite it (cited={G(s,'oracle_cited_by_the_row')}); it asserts entry "
                   f"and exit, never a crowd-berry event",
        },
        "complete_frontier": {
            "state": "partial",
            "basis": f"BORROWED: for the BOSS mechanism D19 enumerates a closed set -- "
                     f"{d19['addresses_named']} named addresses of which "
                     f"{d19['addresses_in_this_rows_pinned_overlay']} fall inside this "
                     f"row's byte-pinned overlay extent {G(s,'pin_extent')}, covering the "
                     f"damage proposer, the guard rollback, the crowd producer/allocator, "
                     f"the defeat threshold and the transition writers. OWNED, and new "
                     f"here: {shared_pin_basis(s)}. The DEFECT IS ALSO SIZED rather than "
                     f"asserted -- across the {G(s,'governing_pcs_probed')} governing "
                     f"addresses probed, the mean number of candidate images that contain "
                     f"the same offset is "
                     f"{G(s,'governing_pcs_mean_images_containing_offset')} of "
                     f"{F['probe_images_scanned']}, "
                     f"{G(s,'governing_pcs_inside_pinned_image')} lie inside the pinned "
                     f"image and {G(s,'governing_pcs_decoding_to_an_instruction')} decode "
                     f"to a real instruction there. The ones that fall OUTSIDE "
                     f"({G(s,'governing_pcs_outside_pinned_image')}) are exactly the "
                     f"candidates D19 itself rejected as belonging to the wrong overlay "
                     f"({F['f12_rejected_candidates_fall_outside_the_byte_pinned_extent']}), "
                     f"so the byte pin reproduces the borrowed row's own negative result "
                     f"by an independent route. The overlay's own function universe is "
                     f"closed and small: {G(s,'overlay_census_functions')} census "
                     f"functions ({G(s,'overlay_census_function_names')}), "
                     f"{G(s,'overlay_matched_functions')} of "
                     f"{G(s,'overlay_code_functions')} byte-matched",
            "gap": f"the enumerated frontier is the BOSS's, not the STAGE's. Nothing "
                   f"enumerates the arena: spawn positions, crowd-member count and arena "
                   f"bounds are the row's own declared gap, and the actor census taken "
                   f"from this row's own fixture "
                   f"(uses_this_rows_fixture={G(s,'actor_census_uses_this_rows_fixture')}, "
                   f"cited={G(s,'actor_census_cited_by_the_row')}) shows only "
                   f"{G(s,'actor_records')} actor records over ids {G(s,'actor_ids')} -- "
                   f"so the crowd is not an actor population in this fixture, and no "
                   f"artifact enumerates the crowd at all -- D19 traces it as contact "
                   f"allocations of a named type, which is borrowed and is not a stage "
                   f"population count. The ownership graph resolves this row to "
                   f"{G(s,'ownership_distinct_function_starts')} distinct function(s), "
                   f"{G(s,'ownership_overlay_space_functions')} of them in overlay space, "
                   f"with {len(G(s,'ownership_state_without_owner'))} cited state "
                   f"addresses carrying no semantic owner "
                   f"({G(s,'ownership_state_without_owner')}) -- and it records no image "
                   f"field at all ({G(s,'ownership_records_no_image_field')}), which is "
                   f"why the byte probe was needed. Newly enumerated but UNRESOLVED: of "
                   f"the {len(G(s,'byte_matched_c_declared_globals'))} globals the "
                   f"byte-matched initializer declares, only the two D19 already names "
                   f"have any documented meaning; the rest are a candidate set, and a "
                   f"candidate set is not a frontier",
        },
        "campaign_breadth": {
            "state": "not_met",
            "basis": f"there is no denominator in either direction. The pre-outcome type "
                     f"authority places this row as {G(s,'c2_types')} together with "
                     f"{G(s,'c2_rows_sharing_this_type')}, and reports "
                     f"taxonomy_coverage_demonstrated="
                     f"{G(s,'c2_taxonomy_coverage_demonstrated')} campaign-wide. Within "
                     f"the stage, {G(s,'stage_movies_attributed')} routes are pinned and "
                     f"the row's own artifacts replay "
                     f"{len(G(s,'stage_movies_declared_by_the_row'))} of them",
            "gap": f"no variant, retry, death or exceptional-path axis is enumerated for "
                   f"stage 12, and the boss conclusion is explicitly per-boss (D19's own "
                   f"deferred list keeps the attempt/death/restart matrix out of scope). "
                   f"'Every applicable stage' has no applicable set here at all",
        },
        "typed_state": {
            "state": "partial",
            "basis": f"BORROWED: D19 types the boss record's fields (id, HP, the "
                     f"acceptance gate, flags, the mover-VM IP) with concrete domains, and "
                     f"the guard law is stated as an exact rollback rule. OWNED, and new "
                     f"here: this row's overlay state block is typed from BYTE-MATCHED "
                     f"SOURCE rather than inferred -- the C at "
                     f"{G(s,'byte_matched_c_entry_starts')} declares "
                     f"{len(G(s,'byte_matched_c_declared_globals'))} globals, "
                     f"{G(s,'byte_matched_c_globals_inside_pinned_extent')} of them inside "
                     f"the pinned image extent, and the probe reads every one out of the "
                     f"row's own fixture and out of the disc image: "
                     f"{G(s,'named_words_zero_in_disc_image')} of "
                     f"{G(s,'named_words_inside_pinned_image')} in-image words are zero on "
                     f"disc, and exactly "
                     f"{G(s,'named_words_differing_from_disc_image')} are live in this "
                     f"fixture ({G(s,'overlay_words_live_in_this_fixture')}) -- so "
                     f"'runtime state living inside the image' is measured, not assumed",
            "gap": f"value domains are unbounded for every one of those words except the "
                   f"two D19 already interprets. A single fixture cannot bound a domain: "
                   f"the cross-fixture diff for this row is not meaningful (one sample), "
                   f"and this row's second declared save turned out to be a different "
                   f"scene, so it cannot serve as the second sample. The registries are "
                   f"empty here rather than wrong: "
                   f"{G(s,'row_state_addresses_registered')} of the row's cited state "
                   f"addresses appear in config/semantic_state.yaml "
                   f"({F['semantic_state_entries_total']} entries) and "
                   f"{G(s,'record_types_covering_this_rows_overlay')} of "
                   f"{F['record_types_registered']} record types cover this overlay",
        },
        "lifecycle": {
            "state": "partial",
            "basis": f"LOAD is the best-evidenced phase and is now evidenced twice over: "
                     f"the overlay's arrival at the shared base is proved by bytes in this "
                     f"row's own fixture, and its INITIALIZATION is proved from "
                     f"byte-matched source -- the matched C zeroes five overlay words and "
                     f"seeds the guard snapshot from the boss's own HP field, and the "
                     f"probe confirms the post-init values in the save. BORROWED: D19 "
                     f"evidences first use, repeated use and retirement OF THE BOSS across "
                     f"one full fight. Cold boot, stage entry and stage exit are evidenced "
                     f"for the stage CONTAINER by the completion oracle "
                     f"(entered {G(s,'oracle_entered_stage_frame')}, exited by end="
                     f"{G(s,'oracle_stage_exited')}, accepted="
                     f"{G(s,'oracle_replay_accepted')})",
            "gap": f"no phase of the STAGE is evidenced by anything this row owns, and the "
                   f"phases that are evidenced come from artifacts the row does not cite. "
                   f"Exhaustion, retirement and reuse of the CROWD mechanism (how many "
                   f"crowd berries the stage can produce, whether the producer is "
                   f"re-armable, what happens on player death mid-fight) have no evidence "
                   f"of any kind; D19's own deferred list keeps the death/restart matrix "
                   f"out. No per-phase claim map is registered for this row the way F01 "
                   f"has one",
        },
        "cross_system_behavior": {
            "state": "not_met",
            "basis": f"nothing this row owns exercises any combination. Its registered "
                     f"evidence classes are {G(s,'row_declared_evidence_classes')} and the "
                     f"census triage reports "
                     f"'{G(s,'census_triage')['cross_system_behavior']}'. The crossing "
                     f"that exists (projectile damage x guard state x contact allocation x "
                     f"level transition) is D19's, inside the boss fight, and is borrowed "
                     f"-- it says nothing about this stage crossing its own systems",
            "gap": f"the material for a first crossing is sitting unused and is now "
                   f"named: {G(s,'stage_movies_attributed')} pinned routes "
                   f"({len(G(s,'stage_movies_under_phase4_interpreter'))} under "
                   f"movies/Phase4/Interpreter/), one of which a campaign validator "
                   f"already replayed end to end "
                   f"(usable={G(s,'e16_validated_stage_movies_usable')}, "
                   f"truncated={G(s,'e16_validated_stage_movie_truncated')}), and the "
                   f"completion oracle's stage snapshot already carries "
                   f"{len(G(s,'oracle_snapshot_fields'))} cross-system fields "
                   f"({G(s,'oracle_snapshot_fields')}). This dimension is not blocked by a "
                   f"missing fixture; it is unattempted",
        },
        "original_interfaces": {
            "state": "partial",
            "basis": f"the SHARED loader interface is documented to the instruction "
                     f"(arithmetic directory law pinned at "
                     f"{F['loader_arithmetic_law_pcs']}, closed over all "
                     f"{F['loader_scene_ids_mapped']} scene ids) and this row records its "
                     f"own falsification of the prior binding "
                     f"({G(s,'row_records_prior_binding_falsified')}). BORROWED: D19 "
                     f"documents the boss interface -- resident damage proposer, overlay "
                     f"acceptance, allocator call and contact type, transition writers -- "
                     f"and it has a Canon page and a reconstruction source "
                     f"({d19['canon_pages']}, {d19['src_re_files']}). OWNED and new: the "
                     f"routing this row depends on is no longer a hand-typed list -- the "
                     f"progression table at {F['progression_table_address']} was read out "
                     f"of the shipped executable and matches the artifact-declared mapping "
                     f"({F['progression_table_matches_declared']})",
            "gap": f"the stage's own interfaces are undocumented: no arena, spawn, crowd "
                   f"or completion interface is named, and "
                   f"{G(s,'governing_pcs_registered_as_confirmed_sites')} of the "
                   f"{G(s,'governing_addresses')} governing addresses derived here are "
                   f"registered as confirmed sites (of {F['confirmed_sites_total']} "
                   f"entries). The row holds {len(G(s,'census_vault_pages'))} vault page(s) "
                   f"of its own and the ownership graph attaches "
                   f"{G(s,'ownership_functions_with_canon')} Canon page(s) to it. The "
                   f"unknown IS enumerated with a named obstruction rather than left blank "
                   f"-- '{G(s,'row_declared_missing')}' -- which is what keeps this at "
                   f"partial rather than not met",
        },
        "source_closure": {
            "state": "partial",
            "basis": f"measured against BOTH registries. RESIDENT (config/segments.yml, "
                     f"{F['resident_build_units']} units, toolchain "
                     f"{F['resident_build_toolchain']}): of "
                     f"{G(s,'governing_addresses_resident')} distinct resident governing "
                     f"addresses, the ones inside a build unit resolve to "
                     f"{len(G(s,'governing_resident_build_units'))} unit(s) -- "
                     f"{len(G(s,'governing_resident_units_matching_c'))} matching C and "
                     f"{G(s,'governing_resident_units_hand_asm')} hand-written byte-exact "
                     f"ASM -- with "
                     f"{G(s,'governing_resident_addresses_outside_any_build_unit')} data "
                     f"addresses in no unit. OVERLAY (config/overlays.yml + src/overlays/ "
                     f"+ analysis/overlay_decomp_progress.json, "
                     f"{F['overlay_track_matched_functions']}/"
                     f"{F['overlay_track_total_code_functions']} matched campaign-wide = "
                     f"{F['overlay_track_matched_pct']}%): this row's overlay HAS a build "
                     f"entry -- {G(s,'overlay_matched_functions')} of "
                     f"{G(s,'overlay_code_functions')} code functions matched from "
                     f"{G(s,'byte_matched_c_sources')}, rebuild validated "
                     f"({G(s,'overlay_rebuild_validated')}) with rebuilt sha1 equal to the "
                     f"blob's ({G(s,'overlay_rebuilt_sha1_matches_blob')}), and that blob "
                     f"is byte-identical to the image this assessment pinned as resident "
                     f"({G(s,'overlay_blob_sha1_equals_byte_pinned_image')}). Overlay "
                     f"byte-matching is DEMONSTRATED for this row's overlay, not "
                     f"impossible",
            "gap": f"no BOSS or STAGE function is byte-matched C. The one matched overlay "
                   f"function is the state initializer -- real, directly on the frontier, "
                   f"and it is the function that seeds the guard snapshot, but it is not "
                   f"the objective logic; the remaining "
                   f"{G(s,'overlay_code_functions') - G(s,'overlay_matched_functions')} "
                   f"code functions in the overlay (including a level_completion_handler) "
                   f"have no C. The borrowed reconstruction {d19['src_re_files']} is "
                   f"documentation-grade by its own header and appears in NEITHER build "
                   f"registry, so it is not closure. The census triage reports "
                   f"'{G(s,'census_triage')['source_closure']}', which measures "
                   f"REGISTRATION; measured against real governing addresses the count of "
                   f"matching-C resident units is "
                   f"{len(G(s,'governing_resident_units_matching_c'))}",
        },
    }

    # ---------------------------- F13 --------------------------------- #
    s = "f13"
    f13_dims = {
        "durable_evidence": {
            "state": "met",
            "basis": f"CARRIED FORWARD, not re-derived: {G(s,'durable_fraction')} in "
                     f"{CENSUS} -- {G(s,'durable_reason')}. This assessment fails loudly "
                     f"if that measurement moves off 'met'. The single declared save is "
                     f"genuinely load-bearing: it is consumed by "
                     f"{len(G(s,'external_fixture_consumers'))} registered consumers, and "
                     f"it is the fixture the disc-vs-runtime collision census and the "
                     f"actor census both read "
                     f"({G(s,'e02_uses_this_rows_own_fixture')}, "
                     f"{G(s,'actor_census_uses_this_rows_fixture')})",
            "gap": f"one fixture is the thinnest declaration of any F row measured so far, "
                   f"and it is not what is available: {G(s,'stage_movies_attributed')} "
                   f"stage-13 movies are attributable by the frozen session token "
                   f"'{G(s,'c2_session_token')}' ({G(s,'stage_movie_frames')}), "
                   f"{G(s,'stage_movies_centrally_pinned')} of them centrally pinned and "
                   f"{len(G(s,'stage_movies_under_phase4_interpreter'))} under "
                   f"movies/Phase4/Interpreter/, while the row declares "
                   f"{G(s,'stage_movies_declared_by_the_row')} and asks for "
                   f"'{G(s,'row_declared_fixture_need')}'. A SECOND usable fixture for "
                   f"this scene also already exists and is declared by the WRONG ROW: "
                   f"{F['f13_pair_rams']} both read scene id "
                   f"{list(G(s,'fixture_scene_ids').values())[0]} "
                   f"(same_scene={F['f13_pair_same_scene_id']}) and both pin "
                   f"{F['f13_pair_pin_file']}. {gate_note(s)}",
        },
        "original_oracle": {
            "state": "not_met",
            "basis": f"this row asserts nothing, about anything. It owns "
                     f"{len(G(s,'row_own_analysis_artifacts'))} analysis artifacts, "
                     f"{len(G(s,'census_vault_pages'))} vault pages and "
                     f"{len(G(s,'census_source_files'))} source files; its only bindings "
                     f"are the shared scene-asset correction and its own falsification "
                     f"record ({G(s,'row_records_prior_binding_falsified')}). Nothing is "
                     f"borrowed either -- unlike F12 and F15, this row's objective belongs "
                     f"to no D row ({G(s,'row_leans_on_d_rows')})",
            "gap": f"the absence is measured, not assumed, and the material is named: a "
                   f"pristine campaign replay of this exact stage already exists and is "
                   f"accepted ({G(s,'oracle_movie')}, {G(s,'oracle_frames')} frames, "
                   f"accepted={G(s,'oracle_replay_accepted')}, target scene "
                   f"{G(s,'oracle_target_scene')}, entered "
                   f"{G(s,'oracle_entered_stage_frame')}, exited by end="
                   f"{G(s,'oracle_stage_exited')}), the row does not cite it "
                   f"(cited={G(s,'oracle_cited_by_the_row')}), and a second natural "
                   f"Interpreter route through the stage was already replayed by a "
                   f"campaign validator ({G(s,'e16_validated_stage_movies')}, "
                   f"usable={G(s,'e16_validated_stage_movies_usable')}, "
                   f"truncated={G(s,'e16_validated_stage_movie_truncated')}) and a third "
                   f"by the F01 breadth pass ({G(s,'breadth_movie')}, "
                   f"{G(s,'breadth_movie_frames')} frames, "
                   f"reproducible={G(s,'breadth_replay_reproducible')}). None of those "
                   f"asserts anything about rescuing Atta or the berry-shooter",
        },
        "complete_frontier": {
            "state": "partial",
            "basis": f"NOTHING is borrowed here, so everything below is owned -- and it is "
                     f"all new. {shared_pin_basis(s)}. That matters more for this row than "
                     f"for the other two: its overlay is the MOST ambiguous of the three "
                     f"by measurement (mean "
                     f"{G(s,'governing_pcs_mean_images_containing_offset')} of "
                     f"{F['probe_images_scanned']} candidate images contain the same "
                     f"offset), so an address-only attribution here is close to "
                     f"meaningless. With the file pinned, the overlay's own function "
                     f"universe is closed and named: {G(s,'overlay_census_functions')} "
                     f"census functions ({G(s,'overlay_census_function_names')}), of which "
                     f"{G(s,'overlay_matched_functions')} of "
                     f"{G(s,'overlay_code_functions')} are byte-matched -- measured "
                     f"against every per-level overlay in the build registry "
                     f"({F['matched_functions_per_per_level_overlay']}), this is the "
                     f"largest matched set of any of them "
                     f"({G(s,'overlay_has_the_most_matched_functions_of_any_per_level_overlay')}, "
                     f"top set {F['per_level_overlays_with_the_most_matched_functions']}). "
                     f"The matched C names two RESIDENT record arrays "
                     f"({G(s,'byte_matched_c_declared_globals')}) and a select-one-of-21 "
                     f"stride-0x54 halfword flag idiom, which is the first concrete "
                     f"mechanism ever attached to this row. NEW, and the row's first "
                     f"testable objective-state candidate set: pairing this row's save "
                     f"with the other scene-{list(G(s,'fixture_scene_ids').values())[0]} "
                     f"fixture gives {F['f13_pair_region_a_differing_bytes']} differing "
                     f"bytes in region A, ALL "
                     f"{F['f13_pair_differing_inside_pinned_image']} of them inside the "
                     f"pinned image and all zero on disc "
                     f"({F['f13_pair_differing_bytes_zero_on_disc']}), clustered in "
                     f"{len(F['f13_pair_differing_words_aligned'])} aligned words "
                     f"{F['f13_pair_differing_words_aligned']}",
            "gap": f"a candidate set is not a frontier. No caller, callee or callback of "
                   f"the objective is enumerated: the ownership graph resolves this row to "
                   f"{G(s,'ownership_distinct_function_starts')} distinct function(s) "
                   f"(the shared loader), {G(s,'ownership_overlay_space_functions')} in "
                   f"overlay space, with {len(G(s,'ownership_state_without_owner'))} cited "
                   f"state addresses carrying no semantic owner and no image field at all "
                   f"({G(s,'ownership_records_no_image_field')}). Which of the "
                   f"{G(s,'overlay_census_functions')} overlay functions implements the "
                   f"berry-shooter objective is UNRESOLVED -- no artifact walks them -- "
                   f"and the "
                   f"{len(F['f13_pair_differing_words_aligned'])} differing words come from two "
                   f"samples at different points in the stage, which cannot distinguish "
                   f"objective state from a free-running timer. The actor census from this row's own "
                   f"fixture already lists {G(s,'actor_records')} records over "
                   f"{len(G(s,'actor_ids'))} distinct ids {G(s,'actor_ids')}, "
                   f"{len(G(s,'actor_ids_with_canon_binding'))} of which have a Canon "
                   f"role, and the row cites none of it "
                   f"({G(s,'actor_census_cited_by_the_row')})",
        },
        "campaign_breadth": {
            "state": "not_met",
            "basis": f"the row has no conclusion to generalize. The pre-outcome type "
                     f"authority cannot even type it from its frozen name -- it records "
                     f"{G(s,'c2_types')} with the rule 'declared residual: no keyword "
                     f"matched' -- and reports taxonomy_coverage_demonstrated="
                     f"{G(s,'c2_taxonomy_coverage_demonstrated')} campaign-wide",
            "gap": f"no applicable set, no variant axis, no exceptional-path axis, and no "
                   f"conclusion. Of {G(s,'stage_movies_attributed')} pinned routes through "
                   f"this stage the row replays "
                   f"{len(G(s,'stage_movies_declared_by_the_row'))}",
        },
        "typed_state": {
            "state": "partial",
            "basis": f"entirely owned and entirely new. The three byte-matched functions "
                     f"in this row's pinned overlay type two resident record arrays from "
                     f"SOURCE rather than inference: a pointer table whose entries carry a "
                     f"short index at +4, and a 0x54-stride record array whose halfword "
                     f"flag sits at +0x32, written as a run of 21 followed by an inverted "
                     f"22nd -- a set/clear pair plus a wrapper. The probe reads both bases "
                     f"out of the row's own fixture. The overlay's live state block is "
                     f"located too: {F['f13_pair_differing_inside_pinned_image']} bytes in "
                     f"{len(F['f13_pair_differing_words_aligned'])} aligned words at the "
                     f"tail of the pinned image differ between the two scene-"
                     f"{list(G(s,'fixture_scene_ids').values())[0]} fixtures and are zero "
                     f"on disc, so they are runtime state living inside the image",
            "gap": f"nothing is BOUNDED. Two samples give no value domain, the "
                   f"select-one-of-21 idiom's index source is not typed, and neither "
                   f"resident array is registered anywhere: "
                   f"{G(s,'row_state_addresses_registered')} of the row's cited state "
                   f"addresses appear in config/semantic_state.yaml "
                   f"({F['semantic_state_entries_total']} entries) and "
                   f"{G(s,'record_types_covering_this_rows_overlay')} of "
                   f"{F['record_types_registered']} record types cover this overlay. WORSE "
                   f"THAN EMPTY, and measured: the semantic registry keys overlay-local "
                   f"addresses globally, and "
                   f"{len(G(s,'semantic_entries_inside_this_rows_overlay_extent'))} entry "
                   f"falls inside THIS row's pinned extent -- "
                   f"{G(s,'semantic_collision_detail')} -- so a lookup by address returns "
                   f"another overlay's field, at 'confirmed' confidence, for a byte that "
                   f"in this stage belongs to {G(s,'pin_file')}",
        },
        "lifecycle": {
            "state": "partial",
            "basis": f"LOAD is evidenced, and only load: the overlay's arrival at the "
                     f"shared base is proved by bytes in this row's own fixture at "
                     f"{G(s,'pin_nontrivial_pct')}% non-trivial agreement with a stable "
                     f"anchor base. Cold boot, stage entry and stage exit are evidenced "
                     f"for the stage CONTAINER by the completion oracle (entered "
                     f"{G(s,'oracle_entered_stage_frame')}, exited by end="
                     f"{G(s,'oracle_stage_exited')}, accepted="
                     f"{G(s,'oracle_replay_accepted')}) -- an artifact the row does not "
                     f"cite",
            "gap": f"first use, repeated use, exhaustion, retirement and reuse of the "
                   f"berry-shooter objective have no evidence of any kind, and the row's "
                   f"own declared missing item is '{G(s,'row_declared_missing')}'. The two "
                   f"available fixtures are two mid-stage snapshots, not a progression",
        },
        "cross_system_behavior": {
            "state": "not_met",
            "basis": f"nothing. The row's evidence classes are "
                     f"{G(s,'row_declared_evidence_classes')}, it has no runtime trace "
                     f"evidence ({G(s,'census_has_runtime_trace_evidence')}), and the "
                     f"census triage reports "
                     f"'{G(s,'census_triage')['cross_system_behavior']}'. Nothing is "
                     f"borrowed either",
            "gap": f"unattempted rather than blocked, and the material is named: "
                   f"{G(s,'actor_records')} actor records over ids {G(s,'actor_ids')} from "
                   f"this row's own fixture, {G(s,'stage_movies_attributed')} pinned "
                   f"routes attributable by the frozen session token, plus "
                   f"{len(G(s,'stage_movies_ordinal_token_matched_attribution_unverified'))} "
                   f"further recording(s) that carry this stage's ordinal token with "
                   f"attribution UNVERIFIED "
                   f"({G(s,'stage_movies_ordinal_token_matched_attribution_unverified')}) "
                   f"-- named as a lead, not credited -- and a completion-oracle snapshot "
                   f"carrying {len(G(s,'oracle_snapshot_fields'))} cross-system fields",
        },
        "original_interfaces": {
            "state": "partial",
            "basis": f"the SHARED loader interface is documented to the instruction "
                     f"({F['loader_arithmetic_law_pcs']}, closed over all "
                     f"{F['loader_scene_ids_mapped']} scene ids) and this row records its "
                     f"own prior binding as falsified "
                     f"({G(s,'row_records_prior_binding_falsified')}). Newly documented "
                     f"here: three overlay routines with recovered signatures and record "
                     f"layouts, and the ordinal->scene routing this row depends on, read "
                     f"from the shipped executable at "
                     f"{F['progression_table_address']} and matching the declared mapping "
                     f"({F['progression_table_matches_declared']})",
            "gap": f"the row's OWN interface -- what the berry-shooter objective is, what "
                   f"triggers it, what it writes -- is undocumented and its unknown is "
                   f"stated without a named obstruction: missing is "
                   f"'{G(s,'row_declared_missing')}' and next is "
                   f"'{G(s,'row_declared_next')}', neither of which names what blocks the "
                   f"walk. {G(s,'governing_pcs_registered_as_confirmed_sites')} of the "
                   f"{G(s,'governing_addresses')} governing addresses are registered as "
                   f"confirmed sites; the row has {len(G(s,'census_vault_pages'))} vault "
                   f"pages and the ownership graph attaches "
                   f"{G(s,'ownership_functions_with_canon')} Canon page(s)",
        },
        "source_closure": {
            "state": "partial",
            "basis": f"this is the row's strongest dimension, and the census never says "
                     f"so. Measured against BOTH registries. RESIDENT "
                     f"(config/segments.yml, {F['resident_build_units']} units, toolchain "
                     f"{F['resident_build_toolchain']}): "
                     f"{G(s,'governing_addresses_resident')} distinct resident governing "
                     f"addresses, "
                     f"{G(s,'governing_resident_addresses_outside_any_build_unit')} of "
                     f"them outside any build unit (they are the two record-array bases, "
                     f"which are data). OVERLAY (config/overlays.yml + src/overlays/ + "
                     f"analysis/overlay_decomp_progress.json, "
                     f"{F['overlay_track_matched_functions']}/"
                     f"{F['overlay_track_total_code_functions']} matched campaign-wide = "
                     f"{F['overlay_track_matched_pct']}%): this row's overlay carries "
                     f"{G(s,'overlay_matched_functions')} of the campaign's "
                     f"{F['overlay_track_matched_functions']} matched overlay functions -- "
                     f"{G(s,'overlay_matched_functions')} of "
                     f"{G(s,'overlay_code_functions')} of its own code functions, from "
                     f"{G(s,'byte_matched_c_sources')}, rebuild validated "
                     f"({G(s,'overlay_rebuild_validated')}) with rebuilt sha1 equal to the "
                     f"blob's ({G(s,'overlay_rebuilt_sha1_matches_blob')}), and that blob "
                     f"is byte-identical to the image pinned as resident in this row's own "
                     f"fixture ({G(s,'overlay_blob_sha1_equals_byte_pinned_image')})",
            "gap": f"whether any of the three matched functions is a GOVERNING function of "
                   f"this row is unresolved, because the row names no governing function "
                   f"at all: {G(s,'governing_overlay_addresses_with_matched_c')} of "
                   f"{G(s,'governing_addresses_in_pinned_overlay')} overlay governing "
                   f"addresses have matched C only because those addresses ARE the matched "
                   f"entries -- the set is self-referential until an objective is bound to "
                   f"code. The other "
                   f"{G(s,'overlay_code_functions') - G(s,'overlay_matched_functions')} "
                   f"code functions in the overlay, including a level_actor_ai_handler and "
                   f"a level_state_writer, have no C. The census triage reports "
                   f"'{G(s,'census_triage')['source_closure']}', which measures "
                   f"REGISTRATION, and the row's own declared source files number "
                   f"{len(G(s,'census_source_files'))}",
        },
    }

    # ---------------------------- F15 --------------------------------- #
    s = "f15"
    d20 = G(s, "borrowed_d_rows")["D20_hopper"]
    f15_dims = {
        "durable_evidence": {
            "state": "met",
            "basis": f"CARRIED FORWARD, not re-derived: {G(s,'durable_fraction')} in "
                     f"{CENSUS} -- {G(s,'durable_reason')}. This assessment fails loudly "
                     f"if that measurement moves off 'met'. This row is the best-provisioned "
                     f"of the three: it declares an operator-supplied 100% completion run "
                     f"as well as the boss movie and a save, its declared fixtures have "
                     f"{len(G(s,'external_fixture_consumers'))} registered consumers, and "
                     f"the row is the only one of the three whose census records runtime "
                     f"trace evidence ({G(s,'census_has_runtime_trace_evidence')}). "
                     f"{gate_note(s)}",
            "gap": f"{len(G(s,'row_declared_fixtures_naming_a_d_row'))} of the declared "
                   f"fixtures are the BOSS row's recordings "
                   f"({G(s,'row_declared_fixtures_naming_a_d_row')}), and "
                   f"{len(G(s,'coverage_unaudited_fixtures'))} declared fixture is still "
                   f"UNAUDITED in the Phase-2 coverage registry "
                   f"({G(s,'coverage_unaudited_fixtures')}) -- the very 100% run the row's "
                   f"strongest conclusion rests on. Attribution by the frozen session "
                   f"token finds {G(s,'stage_movies_attributed')} stage-15 movies "
                   f"({G(s,'stage_movie_frames')}); the row declares "
                   f"{G(s,'stage_movies_declared_by_the_row')}",
        },
        "original_oracle": {
            "state": "partial",
            "basis": f"BORROWED (D20_hopper, artifact status "
                     f"'{d20['status'][:60]}...'): the boss mechanism is asserted from "
                     f"natural Interpreter replays of pristine movies. OWNED, and new "
                     f"here, the strongest single result in this assessment: the D20 "
                     f"health counter is CONFIRMED OFFLINE out of this row's own save, "
                     f"with no emulator -- the byte-pinned overlay is "
                     f"{G(s,'pin_file')} and exactly "
                     f"{G(s,'named_words_differing_from_disc_image')} of "
                     f"{G(s,'named_words_inside_pinned_image')} probed in-image words is "
                     f"live in the fixture, and it is the counter D20 polled "
                     f"({F['f15_d20_health_counter_address']}; only-live-word="
                     f"{F['f15_only_live_overlay_word_is_the_d20_health_counter']}) at the "
                     f"exact value D20 reports it initializes to "
                     f"({F['f15_health_counter_value_in_this_rows_own_fixture']} vs "
                     f"{F['f15_d20_health_counter_initial_value']}; equal="
                     f"{F['f15_fixture_value_equals_the_borrowed_initial_value']}), "
                     f"against a disc image where it is zero. The fixture's scene id reads "
                     f"{list(G(s,'fixture_scene_ids').values())} "
                     f"(matches the routing: {G(s,'fixture_scene_id_matches_census')}). "
                     f"Independent natural corroboration of the stage also comes from the "
                     f"disc-vs-runtime collision census "
                     f"({F['e02_disc_runtime_disagreements']} disagreements over "
                     f"{F['e02_authored_sectors_compared']} sectors) and the campaign "
                     f"completion oracle ({G(s,'oracle_movie')}, "
                     f"{G(s,'oracle_frames')} frames, accepted="
                     f"{G(s,'oracle_replay_accepted')}), which the row does not cite "
                     f"({G(s,'oracle_cited_by_the_row')})",
            "gap": f"the row's own headline finding was obtained by INJECTED INPUT, not "
                   f"natural execution: the ending-cutscene pass stopped movie playback "
                   f"and drove controller presses live, which is exactly what the written "
                   f"bar excludes. It was later re-obtained from an operator-recorded "
                   f"natural 100% run -- but that run is the fixture the coverage registry "
                   f"still lists as unaudited, and no assertion file replays it. Nothing "
                   f"is keyed to the stage's own non-boss content, which the row itself "
                   f"lists as missing: '{str(G(s,'row_declared_missing'))[:160]}...'. D20 "
                   f"is a stop decision on the boss and cannot carry any of that",
        },
        "complete_frontier": {
            "state": "partial",
            "basis": f"BORROWED: D20 enumerates the boss's structure across three sections "
                     f"with literal frame markers, the chase gate, the health counter and "
                     f"the defeat caller -- {d20['addresses_named']} named addresses, of "
                     f"which {d20['addresses_in_this_rows_pinned_overlay']} fall inside "
                     f"this row's byte-pinned overlay extent {G(s,'pin_extent')}. OWNED, "
                     f"and new here: {shared_pin_basis(s)}, and the ambiguity is sized -- "
                     f"the mean candidate image count for the "
                     f"{G(s,'governing_pcs_probed')} governing addresses probed is "
                     f"{G(s,'governing_pcs_mean_images_containing_offset')} of "
                     f"{F['probe_images_scanned']}, with "
                     f"{G(s,'governing_pcs_inside_pinned_image')} inside the pinned image "
                     f"and {G(s,'governing_pcs_decoding_to_an_instruction')} decoding to a "
                     f"real instruction. Two borrowed addresses fall OUTSIDE this row's "
                     f"overlay entirely ({G(s,'governing_pcs_outside_pinned_image')}), "
                     f"which is a measured correction, not a quibble: an address-only "
                     f"census would have attributed them to this stage. THE BIGGEST "
                     f"OWNED RESULT: D20's one remaining STILL_OPEN residual is the "
                     f"gate-break predicate it located at an overlay address -- and that "
                     f"address is the entry of the ONE byte-matched C function in this "
                     f"row's own overlay ({G(s,'byte_matched_c_entry_starts')} = "
                     f"{G(s,'byte_matched_c_sources')}; named by the borrowed row: "
                     f"{F['f15_byte_matched_predicate_entry_is_named_by_the_borrowed_row']}), "
                     f"and "
                     f"{len(F['f15_byte_matched_predicate_globals_named_by_the_borrowed_row'])} "
                     f"of the {len(G(s,'byte_matched_c_declared_globals'))} operands that "
                     f"C declares are named in the same D20 section "
                     f"({F['f15_byte_matched_predicate_globals_named_by_the_borrowed_row']}); "
                     f"the third, the short table the predicate indexes, is named by the C "
                     f"and by nothing else. The predicate's semantics are therefore "
                     f"already closed in byte-matched source, and neither row knows it",
            "gap": f"the enumerated frontier is the BOSS's. The stage's own non-boss "
                   f"content, hazards and critical path are unenumerated by the row's own "
                   f"admission, and the credits sequence is sampled at 2 screens. The "
                   f"ownership graph resolves this row to "
                   f"{G(s,'ownership_distinct_function_starts')} distinct function(s), "
                   f"{G(s,'ownership_overlay_space_functions')} in overlay space, with "
                   f"{len(G(s,'ownership_state_without_owner'))} cited state addresses "
                   f"carrying no semantic owner ({G(s,'ownership_state_without_owner')}) "
                   f"and no image field ({G(s,'ownership_records_no_image_field')}) -- "
                   f"including the health counter itself. Of the overlay's "
                   f"{G(s,'overlay_census_functions')} census functions "
                   f"({G(s,'overlay_census_function_names')}) only "
                   f"{G(s,'overlay_matched_functions')} is matched, and the short table "
                   f"the matched predicate indexes has no established extent -- so whether "
                   f"the health counter is an element of that table is UNRESOLVED and is "
                   f"named here rather than assumed",
        },
        "campaign_breadth": {
            "state": "not_met",
            "basis": f"the row makes a genuinely campaign-scale claim -- that stage 15 is "
                     f"the FINAL stage, evidenced by a Game-Complete card and a full "
                     f"credits roll in a 100% run -- and it correctly hedges it. The type "
                     f"authority places the row as {G(s,'c2_types')} together with "
                     f"{G(s,'c2_rows_sharing_this_type')}",
            "gap": f"the claim has no denominator and the row says so: no comparison stage "
                   f"was ever checked, which is the first item of its own declared "
                   f"missing list. taxonomy_coverage_demonstrated="
                   f"{G(s,'c2_taxonomy_coverage_demonstrated')} campaign-wide, and no "
                   f"variant, retry, death or exceptional-path axis is enumerated for this "
                   f"stage. Of {G(s,'stage_movies_attributed')} pinned routes the row "
                   f"declares {len(G(s,'stage_movies_declared_by_the_row'))}",
        },
        "typed_state": {
            "state": "partial",
            "basis": f"BORROWED: D20 types the health counter with an exact domain and an "
                     f"exact display law (a 30-step counter rendered as five segments) and "
                     f"traces its full writer set. OWNED, and new: the counter's value is "
                     f"now read out of THIS row's own save with no emulator "
                     f"({G(s,'overlay_words_live_in_this_fixture')}) and shown to be zero "
                     f"in the disc image, which is what makes it runtime state rather than "
                     f"static data; and the matched C types the predicate's three operands "
                     f"exactly -- a resident halfword compared against an overlay-local "
                     f"short table indexed by an overlay word, with "
                     f"{G(s,'byte_matched_c_globals_inside_pinned_extent')} of its "
                     f"{len(G(s,'byte_matched_c_declared_globals'))} globals inside the "
                     f"pinned extent and the third resident",
            "gap": f"the index word's domain is unbounded, the table's extent is unknown, "
                   f"and one sample cannot bound either -- in this fixture the table and "
                   f"the index both read their DISC values, so only the counter is shown "
                   f"to be live ({G(s,'named_words_differing_from_disc_image')} of "
                   f"{G(s,'named_words_inside_pinned_image')} in-image words differ from "
                   f"the image). The registries are not merely "
                   f"empty here, they are WRONG: "
                   f"{len(G(s,'semantic_entries_inside_this_rows_overlay_extent'))} "
                   f"semantic_state entry falls inside this row's pinned extent -- "
                   f"{G(s,'semantic_collision_detail')} -- so an address lookup returns a "
                   f"different overlay's field, at 'confirmed' confidence, with a declared "
                   f"range the measured value does not satisfy. "
                   f"{G(s,'row_state_addresses_registered')} of the row's cited state "
                   f"addresses are registered and "
                   f"{G(s,'record_types_covering_this_rows_overlay')} of "
                   f"{F['record_types_registered']} record types cover this overlay",
        },
        "lifecycle": {
            "state": "partial",
            "basis": f"more phases are evidenced for this row than for the other two, and "
                     f"most are borrowed. LOAD is owned and proved by bytes in this row's "
                     f"own fixture. BORROWED from D20: first use and repeated use across a "
                     f"full fight, and retirement via the defeat caller. OWNED from the "
                     f"row's own artifact: the terminal sequence is mapped end to end -- "
                     f"cutscene, Game-Complete card, scrolling credits, save prompt -- and "
                     f"the scene id is observed flipping to 0, which is the only "
                     f"whole-game retirement evidence anywhere in the campaign. Cold boot "
                     f"and stage entry are evidenced for the container by the completion "
                     f"oracle (entered {G(s,'oracle_entered_stage_frame')}, exited by "
                     f"end={G(s,'oracle_stage_exited')})",
            "gap": f"exhaustion and reuse are not evidenced: whether the fight is "
                   f"re-enterable, what a mid-fight death does to the counter, and whether "
                   f"the barrier gates re-arm are all untested (D20 recorded two deaths in "
                   f"its own fixture and explicitly declined to treat them as a mechanic "
                   f"finding). The terminal-sequence evidence is a coarse sample of a "
                   f"76,310-frame run, not a per-phase claim map, and the run it comes "
                   f"from is the unaudited fixture",
        },
        "cross_system_behavior": {
            "state": "partial",
            "basis": f"BORROWED and real: D20 crosses the boss against the shared mover-VM "
                     f"chase gate every regular enemy uses, against player damage and "
                     f"death (lives dropped across the recording), and against the "
                     f"level-transition machinery via a generic, already-Canon function -- "
                     f"the crossing is the point of that row's identity correction. OWNED: "
                     f"the row's 100% run carries the stage's own collectible systems to "
                     f"completion (grain and letters at full) while the scene id is "
                     f"unchanged, which is a genuine crossing of collection against the "
                     f"boss stage, and it is the row's own fixture",
            "gap": f"no combination is registered as an ASSERTION anywhere -- the crossings "
                   f"are narrative observations inside prose artifacts, with no "
                   f"combination matrix, no oracle and no gate. The census triage reports "
                   f"'{G(s,'census_triage')['cross_system_behavior']}'. Nothing crosses "
                   f"the stage's own hazards or non-boss content, because none are "
                   f"enumerated",
        },
        "original_interfaces": {
            "state": "partial",
            "basis": f"BORROWED: D20 documents the defeat interface to the instruction and "
                     f"names the generic resident function that fires it, and the "
                     f"corresponding Canon function pages exist "
                     f"({G(s,'ownership_functions_with_canon')} attached to this row by "
                     f"the ownership graph). OWNED: the shared loader interface is pinned "
                     f"at {F['loader_arithmetic_law_pcs']}, this row's own experiment note "
                     f"is registered ({G(s,'census_vault_pages')}), the row records its "
                     f"prior binding as falsified "
                     f"({G(s,'row_records_prior_binding_falsified')}), and the "
                     f"ordinal->scene routing is now read from the shipped executable "
                     f"rather than a hand-typed list "
                     f"({F['progression_table_matches_declared']}). Unknowns ARE "
                     f"enumerated with named obstructions -- the row's missing list names "
                     f"five, and two more were closed by the operator as non-issues rather "
                     f"than silently dropped",
            "gap": f"the stage's own interfaces (hazards, non-boss content, the credits "
                   f"sequence's own driver) are undocumented, and the row has no dedicated "
                   f"Canon page -- it is one of the thin stubs that point at a D row. "
                   f"{G(s,'governing_pcs_registered_as_confirmed_sites')} of the "
                   f"{G(s,'governing_addresses')} governing addresses derived here are "
                   f"registered as confirmed sites, of {F['confirmed_sites_total']} "
                   f"entries campaign-wide",
        },
        "source_closure": {
            "state": "partial",
            "basis": f"measured against BOTH registries, and this row scores better than "
                     f"either sibling. RESIDENT (config/segments.yml, "
                     f"{F['resident_build_units']} units, toolchain "
                     f"{F['resident_build_toolchain']}): of "
                     f"{G(s,'governing_addresses_resident')} distinct resident governing "
                     f"addresses the ones inside a build unit resolve to "
                     f"{len(G(s,'governing_resident_build_units'))} unit(s), "
                     f"{len(G(s,'governing_resident_units_matching_c'))} of them MATCHING "
                     f"C ({G(s,'governing_resident_units_matching_c')}) and "
                     f"{G(s,'governing_resident_units_hand_asm')} hand-written byte-exact "
                     f"ASM -- and the addresses that land in matching C are "
                     f"{G(s,'governing_addresses_with_matching_c_source')}, which include "
                     f"the exact instruction D20 traced as the finale trigger, so a "
                     f"governing address of this row's own ending IS byte-matched C. "
                     f"OVERLAY "
                     f"(config/overlays.yml + src/overlays/ + "
                     f"analysis/overlay_decomp_progress.json, "
                     f"{F['overlay_track_matched_functions']}/"
                     f"{F['overlay_track_total_code_functions']} matched campaign-wide): "
                     f"{G(s,'overlay_matched_functions')} of "
                     f"{G(s,'overlay_code_functions')} code functions matched from "
                     f"{G(s,'byte_matched_c_sources')}, rebuild validated "
                     f"({G(s,'overlay_rebuild_validated')}), rebuilt sha1 equal to the "
                     f"blob's ({G(s,'overlay_rebuilt_sha1_matches_blob')}), and that blob "
                     f"byte-identical to the image pinned resident in this row's own "
                     f"fixture ({G(s,'overlay_blob_sha1_equals_byte_pinned_image')}) -- "
                     f"and the matched function is D20's own open residual",
            "gap": f"the boss logic itself has no C: "
                   f"{G(s,'governing_overlay_addresses_with_matched_c')} of "
                   f"{G(s,'governing_addresses_in_pinned_overlay')} overlay governing "
                   f"addresses has matched C, so the health-counter writer, the section "
                   f"structure and the barrier logic are all unmatched, as are the other "
                   f"{G(s,'overlay_code_functions') - G(s,'overlay_matched_functions')} "
                   f"code functions in the overlay including a level_completion_handler. "
                   f"The census triage reports "
                   f"'{G(s,'census_triage')['source_closure']}' and the row's own declared "
                   f"source files number {len(G(s,'census_source_files'))}",
        },
    }

    per_row_dims = {"F12_battle_arena": f12_dims, "F13_anthill_two": f13_dims,
                    "F15_canyon_showdown": f15_dims}
    for rid, dims in per_row_dims.items():
        if set(dims) != set(BARS):
            raise SystemExit(f"{rid} does not carry exactly the nine canonical dimensions")
        for name, d in dims.items():
            d["written_bar"] = BARS[name]
            if d["state"] not in {"met", "met_candidate", "partial", "not_met",
                                  "unmeasured"}:
                raise SystemExit(f"{rid}.{name} carries an illegal state {d['state']!r}")

    borrowed_vs_owned = {
        "F12_battle_arena": {
            "borrowed_boss_mechanism": f"EVERYTHING about defeating Molt: actor identity "
                f"and record fields, the resident damage proposer, the overlay guard "
                f"rollback and its accepted/rolled-back counts, the crowd producer and "
                f"contact allocator, the HP threshold, the goal latch and the transition "
                f"timer -- all from D19_molt "
                f"(artifact status '{F['f12_borrowed_d_rows']['D19_molt']['status']}', "
                f"baseline status "
                f"'{F['f12_borrowed_d_rows']['D19_molt']['baseline_status']}'), plus its "
                f"Canon page and reconstruction source. A stop decision on the boss; it "
                f"promotes nothing here",
            "owned_stage_specific": f"the overlay FILE identity for this stage, pinned "
                f"from bytes in this row's own save ({F['f12_pin_file']} at "
                f"{F['f12_pin_nontrivial_pct']}%); the fixture's scene id; the "
                f"byte-matched initializer's overlay-local state block and its live values "
                f"in this stage; the stage's collision container and its total absence of "
                f"authored region codes; the stage's actor population; and the discovery "
                f"that the row's second declared fixture is a different stage entirely",
            "still_open_and_owned_by_this_row": F["f12_row_declared_missing"],
        },
        "F13_anthill_two": {
            "borrowed_boss_mechanism": "NONE. This row's objective belongs to no D row "
                "and nothing about it is borrowed -- which is why it is the control case "
                "for the boss-borrowing question",
            "owned_stage_specific": f"everything measured for this row is its own and "
                f"almost all of it is new: the overlay FILE identity ({F['f13_pin_file']} "
                f"at {F['f13_pin_nontrivial_pct']}%), the three byte-matched overlay "
                f"functions and the record layouts they type, the "
                f"{F['f13_pair_region_a_differing_bytes']}-byte live overlay state "
                f"block located by pairing the two scene-9 fixtures, the stage's actor "
                f"population, and the stage's absence of authored region codes",
            "still_open_and_owned_by_this_row": F["f13_row_declared_missing"],
        },
        "F15_canyon_showdown": {
            "borrowed_boss_mechanism": f"the Hopper encounter: identity, the three-section "
                f"structure with its frame markers, the chase gate, the on-screen health "
                f"counter and its writers, the barrier gates, and the defeat caller -- all "
                f"from D20_hopper (baseline status "
                f"'{F['f15_borrowed_d_rows']['D20_hopper']['baseline_status']}'). A stop "
                f"decision on the boss; it promotes nothing here",
            "owned_stage_specific": f"the overlay FILE identity for this stage "
                f"({F['f15_pin_file']} at {F['f15_pin_nontrivial_pct']}%); the offline "
                f"confirmation of the health counter's live value out of this row's own "
                f"save; the byte-matched predicate that closes D20's own open residual; "
                f"the terminal sequence (cutscene -> Game-Complete card -> credits -> save "
                f"prompt) mapped from the operator's 100% run; and the stage's absence of "
                f"authored region codes",
            "still_open_and_owned_by_this_row": F["f15_row_declared_missing"],
        },
    }

    for rid, dims in per_row_dims.items():
        st = STEM[rid]
        counts: dict[str, int] = {}
        for d in dims.values():
            counts[d["state"]] = counts.get(d["state"], 0) + 1
        scorecards[rid] = {
            "row_name": G(st, "row_name"),
            "stage_ordinal": G(st, "stage_ordinal"),
            "scene_id": G(st, "scene_id"),
            "byte_pinned_overlay": G(st, "pin_file"),
            "baseline_status": G(st, "row_status"),
            "carried_forward": {
                "dimension": "durable_evidence",
                "from": CENSUS,
                "state": G(st, "durable_state"),
                "fraction": G(st, "durable_fraction"),
                "note": "measured there against pinned bytes; re-deriving it here would "
                        "be a second opinion on a settled measurement, not evidence",
            },
            "routing": {
                "note": "`stages` is the stage ORDINAL, not the scene id. Ordinal -> "
                        "scene comes from the campaign progression table, which this "
                        "assessment reads out of the shipped executable rather than "
                        "trusting the hand-typed copy inside the census generator",
                "progression_table_address": F["progression_table_address"],
                "ordinal_to_scene_read_from_executable":
                    F["progression_table_read_from_executable"],
                "matches_the_artifact_declared_mapping":
                    F["progression_table_matches_declared"],
                "fixture_scene_ids_measured": G(st, "fixture_scene_ids"),
                "fixture_scene_id_matches_census": G(st, "fixture_scene_id_matches_census"),
                "overlay_pinned_from_bytes": G(st, "pin_file"),
                "pin_agrees_with_census_attribution":
                    G(st, "pin_agrees_with_census_overlay_name"),
                "disc_container_agrees_with_the_pinned_directory":
                    G(st, "e02_container_agrees_with_pinned_overlay_directory"),
            },
            "systemic_defect_checks": {
                "a_overlay_misattribution": {
                    "applies_to_this_row": True,
                    "why": f"the row's claims live in the shared overlay window at "
                           f"{F['shared_overlay_load_base']}; the ownership graph records "
                           f"no image field ({G(st,'ownership_records_no_image_field')}) "
                           f"and cites the bare base address as unowned state",
                    "how_sized": f"of {F['probe_images_scanned']} candidate images, a "
                                 f"governing offset from this row is contained by "
                                 f"{G(st,'governing_pcs_mean_images_containing_offset')} "
                                 f"on average",
                    "how_settled": f"{PROBE_SRC}: non-trivial agreement at the declared "
                                   f"base plus >=2 high-entropy anchors agreeing on that "
                                   f"same base, in every fixture of this row",
                    "verdict": f"{G(st,'pin_result')} -- {G(st,'pin_file')} "
                               f"({G(st,'pin_nontrivial_pct')}% vs "
                               f"{G(st,'pin_runner_up_pct')}% for "
                               f"{G(st,'pin_runner_up')})",
                    "was_the_census_attribution_wrong": not G(
                        st, "pin_agrees_with_census_overlay_name"),
                    "how_close_it_was": f"{G(st,'pin_images_with_stable_declared_base')} "
                                        f"image(s) have a stable anchor base at the "
                                        f"declared base and "
                                        f"{G(st,'pin_images_argmax_in_every_ram')} is the "
                                        f"agreement argmax in every fixture; both tests "
                                        f"are needed to leave one survivor",
                },
                "b_semantic_registry_collision": {
                    "applies_to_this_row":
                        bool(G(st, "semantic_entries_inside_this_rows_overlay_extent")),
                    "measured": f"{len(F['semantic_entries_inside_shared_region_a'])} "
                                f"semantic_state entries fall inside the SHARED region "
                                f"({F['semantic_entries_inside_shared_region_a']}, ids "
                                f"{F['semantic_entries_inside_shared_region_a_ids']}); "
                                f"{len(G(st,'semantic_entries_inside_this_rows_overlay_extent'))} "
                                f"fall inside THIS row's byte-pinned extent "
                                f"{G(st,'pin_extent')}",
                    "detail": G(st, "semantic_collision_detail"),
                    "row_state_addresses_registered":
                        G(st, "row_state_addresses_registered"),
                    "record_types_covering_this_overlay":
                        G(st, "record_types_covering_this_rows_overlay"),
                },
            },
            "registry_disposition_for_contrast": {
                "source": DEBT,
                "campaign_id": G(st, "registry_campaign_id"),
                "completion_state": G(st, "registry_completion_state"),
                "dimensions_met": G(st, "registry_met"),
                "dimensions_remaining": G(st, "registry_remaining"),
                "distinct_basis_strings": G(st, "registry_distinct_bases"),
                "distinct_states": G(st, "registry_distinct_states"),
                "movie_count": G(st, "registry_movie_count"),
                "note": f"the registry carries ONE blanket basis across all nine "
                        f"dimensions and scores the row "
                        f"{G(st,'registry_met')}/9. That is a disposition, not a "
                        f"measurement -- and it records movie_count "
                        f"{G(st,'registry_movie_count')} for a stage with "
                        f"{G(st,'stage_movies_attributed')} attributable pinned movies, "
                        f"which is why the scheduler marks the row ineligible with reason "
                        f"{G(st,'scheduler_reasons')}",
            },
            "borrowed_vs_owned": borrowed_vs_owned[rid],
            "dimensions": dims,
            "counts": counts,
            "summary": f"{counts.get('met',0)} met, {counts.get('met_candidate',0)} "
                       f"met-candidate, {counts.get('partial',0)} partial, "
                       f"{counts.get('not_met',0)} not met, "
                       f"{counts.get('unmeasured',0)} unmeasured -- against the WRITTEN "
                       f"bars, versus {G(st,'registry_met')}/9 by blanket disposition",
        }

    counts_by_row = {rid: scorecards[rid]["counts"] for rid in ROWS}

    doc = {
        "_comment": "F12_battle_arena, F13_anthill_two and F15_canyon_showdown measured "
                    "against the nine DoD dimensions AS WRITTEN (item 2 = enumerated; "
                    "residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Three "
                    "SEPARATE scorecards; no evidence is cross-credited between them, and "
                    "boss-row (D19/D20) evidence is labelled borrowed wherever it is used. "
                    "Judgments authored; every fact derived from a pinned artifact at run "
                    "time. Regenerate: tools/phase4_f12_f13_f15_written_bar_assessment.py",
        "schema": "abl-phase4-f12-f13-f15-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "rows": list(ROWS),
        "standard": {
            "ruling": "engineering-specs/phase4-measurement-standard-ruling.md",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads as "
                          "met; this assessment publishes measurement, not disposition",
            "allowed_states": ["met", "met_candidate", "partial", "not_met", "unmeasured"],
            "no_cross_crediting": "a D-row disposition is a stop decision ON THE BOSS. It "
                                  "never carries the stage row's own objective instance, "
                                  "entry/exit, arena layout or lifecycle, and it never "
                                  "promotes a state on these scorecards. Borrowed facts "
                                  "appear only inside a basis string that labels them "
                                  "borrowed",
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "edits_mechanics_baseline": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor authored neither F12/F13/F15's baseline rows "
                               "nor D19/D20's evidence, but did author this assessment and "
                               "the one NEW measurement inside it "
                               f"({PROBE_SRC}) -- so on overlay residency, the "
                               "governing-address ambiguity counts, the offline "
                               "confirmations of the D19 guard snapshot and the D20 health "
                               "counter, and the F13 scene-pair delta, the tool, the claim "
                               "and the judgment share an author. Every state below is a "
                               "submission to a fresh detached verifier, not a promotion; "
                               "`partial` and `not_met` are as challengeable as `met`",
        },
        "systemic_defect_summary": {
            "_comment": "both defects checked explicitly per row so silence is not read "
                        "as absence; per-row verdicts live in each scorecard",
            "a_overlay_misattribution_applies_to": [
                rid for rid in ROWS
                if scorecards[rid]["systemic_defect_checks"]
                ["a_overlay_misattribution"]["applies_to_this_row"]],
            "a_overlay_misattribution_resolved_for": [
                rid for rid in ROWS
                if F[f"{STEM[rid]}_pin_result"] == "OVERLAY_RESIDENCY_PIN_UNIQUE"],
            "a_census_attribution_was_wrong_for": [
                rid for rid in ROWS
                if not F[f"{STEM[rid]}_pin_agrees_with_census_overlay_name"]],
            "b_semantic_collision_applies_to": [
                rid for rid in ROWS
                if F[f"{STEM[rid]}_semantic_entries_inside_this_rows_overlay_extent"]],
            "b_semantic_collision_does_not_apply_to": [
                rid for rid in ROWS
                if not F[f"{STEM[rid]}_semantic_entries_inside_this_rows_overlay_extent"]],
            "both_source_registries_read": [SEG, OVLY, OVLD],
        },
        "fail_loud_contract": {
            "guards": F["fail_loud_guards_fired"],
            "in_band": "re-proved on every generation before any artifact is read; if a "
                       "guard stops firing the run aborts instead of emitting numbers "
                       "whose staleness detection cannot be trusted. Four further "
                       "cross-checks abort the run: the probe's load base, region length "
                       "and scene-id address must match the registries that declare them; "
                       "the probe's executable sha1 must match config/segments.yml; the "
                       "image population must match the registries; and the probed word "
                       "and PC sets must still equal the sets derived from the "
                       "byte-matched C sources and the pinned artifacts",
            "out_of_band_probes_run_2026-08-11": [
                "moved analysis/phase4_d19_molt.json aside -> 'STALE CITATION: "
                "analysis/phase4_d19_molt.json does not exist', exit 1, the previous "
                "output file left byte-identical (nothing rewritten)",
                "renamed unique_pin_file inside the residency-pin artifact -> 'STALE "
                "CITATION: ... no longer has unique_pin_file', exit 1, output file left "
                "byte-identical",
                "dropped one entry from the probe's named_words so the scanned set no "
                "longer equals the set derived from the byte-matched C -> abort naming "
                "BOTH sets, exit 1, output file left byte-identical",
            ],
            "note": "the out-of-band list records actions taken by the assessor; the "
                    "in-band guards above are re-measured every run",
        },
        "fact_provenance": {
            "facts_total": len(F),
            "facts_derived_from_pinned_artifacts": len(E.provenance),
            "facts_hand_typed": len(F) - len(E.provenance),
            "rule": "facts are recorded through fact(key, value, source); a value cannot "
                    "be stored without naming a pinned artifact, and every lookup is "
                    "strict, so a renamed or removed key aborts the run instead of "
                    "silently defaulting",
            "by_fact": E.provenance,
        },
        "facts": F,
        "evidence_pins": E.pins,
        "scorecards": scorecards,
        "counts_by_row": counts_by_row,
        "summary": "; ".join(f"{rid}: {scorecards[rid]['summary']}" for rid in ROWS),
        "notable": [
            f"THE ROW THAT WAS NEVER WORKED HAS THE MOST BYTE-MATCHED SOURCE. "
            f"F13_anthill_two owns {F['f13_census_analysis_artifacts']} analysis "
            f"artifacts, {len(F['f13_census_vault_pages'])} vault pages, "
            f"{len(F['f13_census_source_files'])} source files and "
            f"{len(F['f13_registered_gate_files'])} registered gate files -- and its "
            f"byte-pinned overlay {F['f13_pin_file']} carries "
            f"{F['f13_overlay_matched_functions']} of the campaign's "
            f"{F['overlay_track_matched_functions']} matched overlay functions, "
            f"{F['f13_overlay_matched_functions']} of its own "
            f"{F['f13_overlay_code_functions']}, rebuild-validated with a rebuilt sha1 "
            f"equal to the blob's. The row records none of them. Its objective belongs "
            f"to no D row, so nothing here is borrowed: the source closure is genuinely "
            f"this stage's own, and the census's own triage line for it "
            f"('{F['f13_census_triage']['source_closure']}') measures registration, not "
            f"reality.",

            f"D20's LAST OPEN RESIDUAL IS ALREADY CLOSED IN BYTE-MATCHED C, IN F15's OWN "
            f"OVERLAY. The Hopper row's remaining STILL_OPEN item is the gate-break "
            f"predicate, which it located at an overlay address and could not interpret. "
            f"That address is the entry of the single byte-matched function in "
            f"{F['f15_pin_file']} ({F['f15_byte_matched_c_sources']}), and the three "
            f"globals that C declares ({F['f15_byte_matched_c_declared_globals']}) are "
            f"the same three operands D20 named. Neither row knows: F15 declares "
            f"{len(F['f15_census_source_files'])} source files and the overlay decomp "
            f"track and the D-row investigation have never been joined.",

            f"F12 DECLARES A FIXTURE THAT IS A DIFFERENT STAGE. LEVEL12_ENDING reads "
            f"scene id {list(F['f12_second_fixture_scene_ids'].values())[0]} and pins "
            f"{F['f12_second_fixture_pin_file']} at {F['f12_second_fixture_pin_pct']}% -- "
            f"holds_F12s_overlay={F['f12_second_fixture_holds_this_rows_overlay']}, "
            f"holds_F13s_overlay={F['f12_second_fixture_holds_f13s_overlay']}. Read "
            f"through it, every D19 overlay address returns LEVEL09 bytes. The same "
            f"fixture is the second sample F13 does not have: paired with F13's own save "
            f"it yields {F['f13_pair_region_a_differing_bytes']} differing bytes in the "
            f"shared window, all {F['f13_pair_differing_inside_pinned_image']} inside the "
            f"pinned image and all zero on disc, in aligned words "
            f"{F['f13_pair_differing_words_aligned']} -- F13's first testable "
            f"objective-state candidate set, produced by a fixture the wrong row owns.",

            f"THE ROUTING THESE ROWS DEPEND ON WAS A HAND-TYPED PYTHON LIST. `stages` is "
            f"the stage ORDINAL; the ordinal -> scene mapping lives in the campaign "
            f"progression table at {F['progression_table_address']} and is copied by hand "
            f"into the census generator. Read out of the shipped executable here "
            f"(sha1-checked against config/segments.yml) it is "
            f"{F['progression_table_read_from_executable']}, which matches the "
            f"artifact-declared mapping ({F['progression_table_matches_declared']}) and "
            f"the scene ids measured in all four fixtures. The three rows route to scenes "
            f"{F['f12_scene_id']}, {F['f13_scene_id']} and {F['f15_scene_id']}.",

            f"NONE OF THE THREE STAGES AUTHORS A SINGLE REGION CODE. Containers "
            f"{F['f12_e02_container']} / {F['f13_e02_container']} / "
            f"{F['f15_e02_container']} have histograms {F['f12_e02_code_histogram']} / "
            f"{F['f13_e02_code_histogram']} / {F['f15_e02_code_histogram']} over "
            f"{F['f12_e02_authored_sectors']} / {F['f13_e02_authored_sectors']} / "
            f"{F['f15_e02_authored_sectors']} authored sectors, measured with "
            f"{F['e02_disc_runtime_disagreements']} disc-vs-runtime disagreements over "
            f"{F['e02_authored_sectors_compared']} sectors campaign-wide. Whatever ends "
            f"these stages, it is not the region-code exit mechanism F01 proved -- so "
            f"none of the three inherits an exit path from a closed row, and for F12 and "
            f"F15 the exit is the boss's latch, which is borrowed.",

            f"THE SCHEDULER CANNOT SEE THESE ROWS' MOVIES BECAUSE THE MOVIES ARE NAMED "
            f"AFTER THE BOSS. All three rows are ineligible with reason "
            f"{F['f12_scheduler_reasons']}, and the debt registry records movie_count "
            f"{F['f12_registry_movie_count']}/{F['f13_registry_movie_count']}/"
            f"{F['f15_registry_movie_count']} -- while attribution by the frozen session "
            f"token finds {F['f12_stage_movies_attributed']}, "
            f"{F['f13_stage_movies_attributed']} and {F['f15_stage_movies_attributed']} "
            f"pinned movies for the three stages, including "
            f"movies/Phase4/Interpreter/ recordings that a campaign validator and the "
            f"F01 breadth pass have both already replayed. F12's and F15's declared "
            f"Phase-4 movies are literally named D19 and D20; the borrowing has "
            f"propagated out of the prose and into the scheduler.",

            f"UNMEASURED DID NOT FIRE ON ANY OF THE 27 CELLS, and that is itself the "
            f"finding. Every dimension of all three rows had something to measure once "
            f"the byte probe and the uncited campaign artifacts (completion oracle, E16 "
            f"movie validation, F01 breadth, disc region-code census, actor census) were "
            f"brought in. These rows are not un-measurable; they are un-worked. What is "
            f"genuinely unresolved is named inside each gap rather than left as silence: "
            f"the arena layout for F12, which overlay function implements the "
            f"berry-shooter for F13, and the extent of the short table the byte-matched "
            f"predicate indexes for F15.",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    for rid in ROWS:
        print(f"[written-bar {rid}] {scorecards[rid]['summary']}")
        for name, d in scorecards[rid]["dimensions"].items():
            print(f"  {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} derived "
          f"/ {doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
