#!/usr/bin/env python3
"""Measure F06_birdnest and F14_riverbed_flight against the nine DoD bars AS WRITTEN.

Two SEPARATE scorecards in one artifact, per
`engineering-specs/phase4-measurement-standard-ruling.md`. The design copies the
exemplar `tools/phase4_f01_written_bar_assessment.py` and its most rigorous
sibling `tools/phase4_f09_written_bar_assessment.py`. The WRITTEN bars are:

  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

WHY THESE TWO ROWS TOGETHER, AND WHY THE EVIDENCE IS KEPT APART
---------------------------------------------------------------
Both are stage rows whose in-scene evidence was produced by OTHER rows -- F06 by
D17_bird (the bird itself), F14 by C16/C15 (a contact death and the respawn
initializer). Both therefore test the same discipline from opposite ends: F06 is
registered `partial` with five fixtures and a rich prose row, F14 is registered
`external_lead` with three save states and a two-sentence row -- and the measured
result inverts part of that expectation.

Keeping them apart is STRUCTURAL, not a promise. Facts are recorded into
per-row namespaces, and each row's judgments are built by a function that is
handed ONLY its own fact dict plus an explicitly shared one. F14's facts are not
in scope when F06's basis strings are written, and vice versa; a cross-row credit
would be a NameError, not a slip.

Design (identical to the exemplar):
  * every FACT is read from a cited artifact at run time and the artifact is
    sha256-pinned, so a stale citation fails LOUDLY instead of aging silently.
    `fact()` cannot record a value without naming the artifact it came from, and
    `req()` raises on a missing key rather than substituting a default;
  * every JUDGMENT is authored and attributable, and carries `written_bar` /
    `basis` / `gap`;
  * `unmeasured` is an allowed state, and open questions are named in `notable`
    rather than being papered over.

durable_evidence is NOT re-derived here: it was MEASURED in
`analysis/phase4_f_row_measured_census.json` (F06 5/5, F14 3/3 declared fixtures
intact) and is carried forward with its fraction, failing loudly if either
measurement moves off `met`.

TWO NEW MEASUREMENTS, both by compiled C (`tools/phase4_f06_f14_overlay_pin.c`):
every per-level overlay loads at 0x800B39A0, so each row's governing overlay
addresses decode to a real instruction in 14-19 of the 20 censused overlay
images and NO artifact in this repository can name the owning FILE from an
address. This tool derives file-independent constraints from each row's own
pinned runtime evidence, hands them to the C probe, scans all 21 images, and
records the result -- including when it disagrees with a retained artifact.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a
fresh detached verifier. `analysis/mechanics_baseline.yaml` is read only.

Usage: python3 tools/phase4_f06_f14_written_bar_assessment.py [--out PATH] [--no-gates]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
F06 = "F06_birdnest"
F14 = "F14_riverbed_flight"
PIN_SRC = "tools/phase4_f06_f14_overlay_pin.c"
F06_PIN = "analysis/phase4_f06_overlay_pin.json"
F14_PIN = "analysis/phase4_f14_overlay_pin.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class Evidence:
    """Loads + pins artifacts and records which artifact every fact came from.

    Facts live in per-scope namespaces so a row cannot silently spend another
    row's evidence: `facts["F06_birdnest"]`, `facts["F14_riverbed_flight"]` and
    `facts["shared"]` are distinct dicts, and the judgment builders only ever
    receive their own plus `shared`.
    """

    SCOPES = (F06, F14, "shared")

    def __init__(self) -> None:
        self.pins: list[dict] = []
        self._seen: set[str] = set()
        self.facts: dict[str, dict] = {s: {} for s in self.SCOPES}
        self.provenance: dict[str, dict] = {s: {} for s in self.SCOPES}

    def pin(self, rel: str) -> Path:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"STALE CITATION: {rel} does not exist")
        if rel not in self._seen:
            self._seen.add(rel)
            self.pins.append({"path": rel, "sha256": sha256_file(p)})
        return p

    def repin(self, rel: str) -> Path:
        """Re-pin a file this run regenerated (the C probe outputs)."""
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"STALE CITATION: {rel} does not exist")
        self.pins = [x for x in self.pins if x["path"] != rel]
        self._seen.add(rel)
        self.pins.append({"path": rel, "sha256": sha256_file(p)})
        return p

    def json(self, rel: str) -> dict:
        return json.loads(self.pin(rel).read_text())

    def yaml(self, rel: str) -> dict:
        return yaml.safe_load(self.pin(rel).read_text())

    def text(self, rel: str) -> str:
        return self.pin(rel).read_text(errors="ignore")

    def fact(self, scope: str, key: str, value, source):
        """Record a fact. Impossible to record one without naming its artifact."""
        if scope not in self.facts:
            raise SystemExit(f"fact '{key}' names unknown scope {scope!r}")
        srcs = [source] if isinstance(source, str) else list(source)
        if not srcs:
            raise SystemExit(f"fact '{key}' names no artifact")
        for s in srcs:
            if s not in self._seen:
                raise SystemExit(f"fact '{key}' cites unpinned artifact {s}")
        self.facts[scope][key] = value
        self.provenance[scope][key] = srcs[0] if len(srcs) == 1 else srcs
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


def width_bytes(w: str) -> int:
    m = re.fullmatch(r"[us](8|16|32)", str(w))
    if not m:
        raise SystemExit(f"unrecognised width {w!r} in the record registry")
    return int(m.group(1)) // 8


def baseline_row(rows: list, row_id: str, where: str) -> dict:
    row = next((r for r in rows if r.get("id") == row_id), None)
    if row is None:
        raise SystemExit(f"STALE CITATION: {where} no longer carries {row_id}")
    return row


def debt_row(debt: dict, row_id: str, where: str) -> dict:
    row = next((r for r in req(debt, "rows", where=where) if r.get("row_id") == row_id),
               None)
    if row is None:
        raise SystemExit(f"STALE CITATION: {where} no longer carries {row_id}")
    return row


def _mirror(tmp: Path, mutate: dict[str, object]) -> Path:
    """A read-only mirror of ROOT with a few files removed or rewritten.

    Everything is symlinked except the directories a mutation touches (and
    `tools/`, so the copied entry point resolves ROOT to the mirror). The two
    probe OUTPUT files are materialised as real copies so a child run can never
    write through a symlink into the real repository.
    """
    tmp.mkdir(parents=True)
    materialise = {Path(F06_PIN).parts[0], Path(F14_PIN).parts[0], "tools"}
    materialise |= {Path(r).parts[0] for r in mutate}
    for child in ROOT.iterdir():
        if child.name not in materialise:
            (tmp / child.name).symlink_to(child)
    for d in sorted(materialise):
        src, dst = ROOT / d, tmp / d
        dst.mkdir()
        for f in src.iterdir():
            rel = f"{d}/{f.name}"
            if rel in mutate:
                if mutate[rel] is None:
                    continue
                (dst / f.name).write_text(json.dumps(mutate[rel]))
            elif rel in (F06_PIN, F14_PIN) or (d == "tools" and f.is_file()):
                # tools/ entries are COPIED: Path(__file__).resolve() follows a
                # symlink, which would silently put ROOT back in the real repo.
                shutil.copyfile(f, dst / f.name)
            else:
                (dst / f.name).symlink_to(f)
    return tmp


def fail_loud_probes(tmpdir: Path) -> list[dict]:
    """Prove the fail-loud paths actually fail, rather than asserting they do."""
    me = Path(__file__).name

    def load(rel):
        return json.loads((ROOT / rel).read_text())

    census_broken = load("analysis/phase4_f_row_measured_census.json")
    census_broken["rows"][F14]["durable_evidence"]["state"] = "partial"
    c16_broken = load("analysis/phase4_c16_flight_death.json")
    c16_broken["summary"].pop("scene")
    d17_moved = load("analysis/phase4_d17_defeat.json")
    fields = d17_moved["by_field"]
    hp_field = next(k for k in fields if int(k, 16) == int(d17_moved["located"]["addr"], 16)
                    + 0x6E)
    fields[hp_field]["writer_pcs"] = [["0x800b3f88" if p.lower() == "0x800b3f8c" else p, n]
                                      for p, n in fields[hp_field]["writer_pcs"]]

    cases = [
        ("missing_artifact", {"analysis/phase4_d17_defeat.json": None},
         "STALE CITATION", "an artifact this assessment cites is deleted"),
        ("renamed_key", {"analysis/phase4_c16_flight_death.json": c16_broken},
         "no longer has", "a cited key is removed from an artifact that still exists"),
        ("carried_measurement_moved",
         {"analysis/phase4_f_row_measured_census.json": census_broken},
         "no longer 'met'", "the carried-forward durable_evidence measurement changes"),
        ("overlay_pin_stops_being_unique",
         {"analysis/phase4_d17_defeat.json": d17_moved},
         "overlay pin is NOT unique",
         "a governing writer PC moves so the byte pin no longer resolves to one file"),
    ]
    results = []
    for i, (name, mutate, expect, why) in enumerate(cases):
        work = tmpdir / f"probe{i}"
        if work.exists():
            shutil.rmtree(work)
        _mirror(work, mutate)
        r = subprocess.run([sys.executable, str(work / "tools" / me), "--no-gates",
                            "--no-probe-suite", "--out", str(work / "out.json")],
                           capture_output=True, text=True, cwd=str(work))
        msg = (r.stderr + r.stdout).strip().splitlines()
        results.append({
            "probe": name,
            "simulates": why,
            "expected_substring": expect,
            "exit_code": r.returncode,
            "message": msg[-1][:220] if msg else "",
            "failed_loudly": r.returncode != 0 and expect in (r.stderr + r.stdout),
        })
        shutil.rmtree(work, ignore_errors=True)
    return results


def run_pin_probe(binary: Path, out_rel: str, label: str, base: int, specs: list[str],
                  images: list[str]) -> None:
    cmd = [str(binary), str(ROOT / out_rel), label, f"{base:08x}", ",".join(specs),
           *images]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(f"overlay pin probe failed for {label}: {r.stderr.strip()}")


def gate_files_for(artifacts: list[str]) -> list[str]:
    """Gates that reference an artifact by full path OR by basename.

    Tests in this repo build paths as ROOT / "analysis" / "x.json", so matching
    only the full relative path silently finds nothing.
    """
    needles = {a for a in artifacts} | {Path(a).name for a in artifacts}
    found = []
    for p in sorted((ROOT / "tests").glob("test_*.py")):
        body = p.read_text(errors="ignore")
        if any(n in body for n in needles):
            found.append(f"tests/{p.name}")
    return found


def run_gates(files: list[str]) -> tuple[int, int, list[str]]:
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "--color=no",
         "-p", "no:cacheprovider", *files],
        cwd=str(ROOT), capture_output=True, text=True)
    out = re.sub(r"\x1b\[[0-9;]*m", "", run.stdout)
    tail = out.strip().splitlines()[-1] if out.strip() else ""
    passed = re.search(r"(\d+) passed", tail)
    failed = re.search(r"(\d+) failed", tail)
    if not passed and not failed:
        raise SystemExit(f"could not read a pytest summary from the gate run: {tail!r}")
    names = sorted({ln.split()[1].split("::")[0]
                    for ln in out.splitlines() if ln.startswith("FAILED ")})
    npass = int(passed.group(1)) if passed else 0
    nfail = int(failed.group(1)) if failed else 0
    if nfail and not names:
        raise SystemExit("the gate run reported failures but no FAILED lines could be "
                         "attributed to a file -- the summary parse is wrong")
    return npass, nfail, names


# --------------------------------------------------------------------------- #
#  AUTHORED JUDGMENTS -- each builder sees ONLY its own row's facts + shared.  #
# --------------------------------------------------------------------------- #
def build_f06_dims(F: dict, S: dict) -> dict:
    return {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"the measured F-row census -- {F['census_durable_reason']}. This "
                     f"assessment fails loudly if that measurement moves off 'met'. "
                     f"Independently re-confirmed on the axis the census names: "
                     f"{F['fixtures_bytes_match_central_pin']} of "
                     f"{F['declared_fixture_count']} declared fixtures still byte-match "
                     f"their entry in the central external-fixture manifest, and "
                     f"{F['own_gate_health']} ({F['inherited_gate_health']})",
            "gap": f"the carried measurement covers FIXTURE INTACTNESS, not regenerability "
                   f"or credit. {F['unaudited_fixtures']} of this row's declared fixtures "
                   f"is still unaudited in phase2_row_coverage, and the 100% run the row's "
                   f"two newest findings rest on is NOT credited to this row in the central "
                   f"manifest (consumers name only the fixture audit: "
                   f"credited_to_row={F['hundred_pct_movie_credited_to_row']}). Of the "
                   f"{F['stage_movies_pinned_strict']} stage-6-named movies centrally "
                   f"pinned, the row declares {F['stage_movies_declared_strict']}",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the mechanical core is natural and non-injected: the defeat trace is "
                     f"a passive access log over an operator-recorded Interpreter replay "
                     f"({F['defeat_movie']}, {F['defeat_frames']} frames, "
                     f"{F['defeat_event_total']} events, ring truncated="
                     f"{F['defeat_ring_truncated']}) that attributes every write to the "
                     f"bird's record by PC -- {F['defeat_fields_attributed']} fields, "
                     f"{F['defeat_distinct_writer_pcs']} distinct writer PCs, the "
                     f"{F['defeat_hp_events']} hp decrements all from one PC "
                     f"({F['defeat_damage_pcs']}) with deltas {F['defeat_deltas']}, and the "
                     f"halt program installed once by {F['defeat_halt_installer_pc']}. The "
                     f"row also has an executable identity oracle for its headline scene "
                     f"claim ({F['scenario_names']}, {F['scenario_assertions']} pinned-anchor "
                     f"assertions) and its own gate file passes",
            "gap": f"three holes, one of them now measured as a wrong answer. (1) NOTHING IN "
                   f"THIS ROW ASSERTS THE STAGE: a from-boot completion oracle for stage 6 "
                   f"already exists ({F['completion_oracle_movie']}, "
                   f"{F['completion_oracle_frames']} frames, target scene "
                   f"{F['completion_oracle_target_scene']}, "
                   f"pristine_replay_accepted={F['completion_oracle_replay_accepted']}, "
                   f"stage_exited={F['completion_oracle_stage_exited']}) and the row does not "
                   f"cite it (cited={F['completion_oracle_cited_by_row']}). (2) The row's own "
                   f"new findings are SCREENSHOT READING plus operator testimony -- the "
                   f"results-banner counters were decoded by eye, and one of those readings "
                   f"is falsified below. (3) The bird's own damage producer (the mega "
                   f"homing-berry plant) is inferred from its effect, never observed: the "
                   f"row records it as '{F['unexamined_producer']}'",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"for the FIGHT LANE the write frontier is genuinely enumerated rather "
                     f"than sampled: an untruncated access log gives the COMPLETE writer set "
                     f"per field with counts, so the residual is bounded by the ring rather "
                     f"than by attention ({F['defeat_fields_attributed']} fields, "
                     f"{F['defeat_distinct_writer_pcs']} writer PCs, "
                     f"{F['defeat_overlay_writer_pcs']} of them in the overlay). The VM side "
                     f"is decoded to instruction level (halt program "
                     f"{F['halt_program_range']}, wander program "
                     f"{F['wander_program_range']}), and the stage's collision environment is "
                     f"censused disc-side against runtime with "
                     f"{S['e02_disc_runtime_disagreements']} disagreements over "
                     f"{S['e02_authored_sectors_compared']} sectors -- for this stage "
                     f"{F['authored_collision_sectors']} authored sectors with histogram "
                     f"{F['region_code_histogram']}, i.e. NO region-code sector at all, so "
                     f"this stage's exit is provably not the region-code trigger that ends "
                     f"the campaign's other levels. NEW HERE: the overlay was named by "
                     f"ADDRESS, and that address is ambiguous across "
                     f"{F['overlay_images_covering_governing_pcs_max']} of "
                     f"{S['overlay_images_in_function_census']} censused images; the compiled "
                     f"probe settles it from bytes -- of {F['overlay_pin_images_scanned']} "
                     f"images exactly {F['overlay_pin_images_satisfying']} satisfies all "
                     f"{F['overlay_pin_spec_count']} necessary conditions "
                     f"({F['overlay_pin_file']} @ {F['overlay_pin_load_base']}, "
                     f"{F['overlay_pin_result']}), agreeing with the census's declared "
                     f"overlay ({F['overlay_pin_agrees_with_census_name']})",
            "gap": f"the enumeration stops at the boundary of what one movie wrote. No "
                   f"caller/callee/callback frontier exists for the overlay at all: the "
                   f"semantic ownership graph resolves this row to "
                   f"{F['ownership_functions']} functions, "
                   f"{F['ownership_overlay_functions']} of them in overlay space, and lists "
                   f"{F['ownership_gaps']} state addresses with no registry owner "
                   f"({F['ownership_gap_items']}) -- one of which is the overlay base "
                   f"itself. The stage's ENTRY frontier (how scene "
                   f"{F['scene_id']} is reached and what gates it) is unenumerated, and so is "
                   f"the exit request now that the region-code path is excluded. The row's "
                   f"residual list is explicit and itemised ({F['declared_missing_items']} "
                   f"named items), which satisfies the EXIT-GATE bar, but item 2 asks for "
                   f"enumeration and {F['inherited_open_items']} of those items are inherited "
                   f"from D17 rather than owned here",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"the row does make a cross-stage claim and it declares its own "
                     f"denominator honestly: the results-banner comparison is Birdnest vs "
                     f"Hopper, and the row records that only Birdnest was tested. Within the "
                     f"stage, {F['stage_movies_pinned_strict']} stage-6-named movies plus "
                     f"{F['bird_movies_pinned_other_tokens']} bird-token movies are centrally "
                     f"pinned and the row's artifacts replay "
                     f"{F['stage_movies_replayed_by_row']}",
            "gap": f"'every applicable' has no denominator here, in either direction. Across "
                   f"stages the banner claim rests on 2 of {S['e02_levels_censused']} "
                   f"censused levels. Within the stage nothing enumerates routes, variants or "
                   f"exceptional paths: the never-replayed pinned routes are "
                   f"{F['stage_movies_never_replayed']}, re-engagement after defeat is "
                   f"untested, and the row's own newly-surfaced exceptional path -- this "
                   f"level's first-ever-entry FMV -- has NO fixture and was never attempted. "
                   f"The one genuinely campaign-wide law in this row's own subject area was "
                   f"established by a DIFFERENT row a day later and is not cited here (see "
                   f"notable). "
                   f"{len(F['bird_movies_belonging_to_another_stage'])} of the bird-token "
                   f"movies in the corpus belong to a "
                   f"different stage entirely "
                   f"({F['bird_movies_belonging_to_another_stage']}), so even the corpus "
                   f"boundary needs stating before a denominator can exist",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"every actor field this row's evidence touches is typed with confirmed "
                     f"confidence in the record registry "
                     f"({F['row_named_actor_offsets_typed']}/"
                     f"{F['row_named_actor_offsets_total']} offsets), the boss record "
                     f"{F['boss_record_addr']} lies inside the declared extent "
                     f"({S['actor_record_declared_base']} x "
                     f"{S['actor_record_declared_instances']} x "
                     f"{S['actor_record_declared_stride']} bytes, "
                     f"inside={F['boss_record_inside_declared_extent']}), and the domains are "
                     f"bounded by observation rather than assumed: hp runs "
                     f"{F['hp_at_settle']} -> {F['hp_final_observed']} over "
                     f"{F['defeat_hp_events']} decrements in exactly two regimes "
                     f"({F['defeat_deltas']}, the -3 phase fully restored), the VM IP domain "
                     f"is the {F['vm_ip_values_seen']} values "
                     f"{F['vm_ip_value_list']}, and the registry's own hp note already states "
                     f"this threshold law verbatim ('{S['actor_hp_field_note']}')",
            "gap": f"the note names a DIFFERENT boss (describes_this_boss="
                   f"{F['actor_hp_note_names_this_boss']}); the law transferring is D17's "
                   f"claim, not a typing of this actor. Nothing overlay-local is typed at "
                   f"all: {F['overlay_state_addresses_registered']} of this row's overlay "
                   f"addresses appear in config/semantic_state.yaml, whose only entries "
                   f"inside an overlay load window are "
                   f"{S['semantic_state_overlay_window_entries']} -- and measured against "
                   f"this row's byte-pinned window, "
                   f"{len(F['semantic_entries_inside_this_rows_overlay_window'])} of them "
                   f"fall inside it, so the exposure here is non-registration rather than "
                   f"the known VA collision. Measured new "
                   f"here: {F['absolute_form_writers']} of {F['overlay_pin_spec_count']} "
                   f"overlay writers are $at-absolute stores whose immediates are the low "
                   f"half of the pool address itself, so the overlay hard-codes this actor's "
                   f"POOL SLOT rather than taking a pointer -- a typed-state fact no registry "
                   f"records. And one registered value domain in this row is simply wrong "
                   f"(the results-banner third counter, see notable)",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"the middle of the list is evidenced end to end inside one natural "
                     f"replay: first and repeated use are {F['defeat_hp_events']} attributed "
                     f"damage events, exhaustion is the threshold regime change, and "
                     f"RETIREMENT is instruction-bound -- a single write by "
                     f"{F['defeat_halt_installer_pc']} at frame "
                     f"{F['defeat_first_halt_frame']} parks the mover VM in a null program "
                     f"({F['halt_program_range']}), after which "
                     f"{F['post_halt_position_writer_count']} position writers continue, so "
                     f"'retreat' is bounded as overlay-driven translation rather than AI. "
                     f"Load is the chunk-31 spawn the D17 row documents, and the level's own "
                     f"completion/cutscene tail is mapped across "
                     f"{F['hundred_pct_movie_frames']} frames of the 100% run",
            "gap": f"cold boot, reuse and reset are absent, and two of them are absent by "
                   f"fixture. Every fixture this row replays is state-anchored; the only "
                   f"from-boot route through this stage is the uncited completion-oracle "
                   f"movie. Re-engagement (a second fight in one session) is recorded "
                   f"untested. The level's first-ever-entry FMV -- a lifecycle phase the "
                   f"operator confirmed exists -- has never been captured, and the row itself "
                   f"says the needed capture '{F['entry_fmv_fixture_status']}'. No per-phase "
                   f"claim map is registered for this row the way F01 has one",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"four native crossings are exercised on natural execution. BOSS x "
                     f"PLAYER DAMAGE: the bird's attack drops Flik's true health twice early "
                     f"in the encounter. PICKUP x BOSS BEHAVIOUR: obtaining the gold berry "
                     f"moves the bird's Y from {F['gold_berry_y_before']} to "
                     f"{F['gold_berry_y_after']} at the operator-named frame. SEED PLANT x "
                     f"PROJECTILE x BOSS: the damage arrives through the same berry dispatch "
                     f"PC that damages another boss ({F['defeat_damage_pcs']}), which is a "
                     f"real shared-system crossing rather than a bespoke path. OBJECTIVE x "
                     f"UI/FMV: defeat leads to the results banner and, on a first 100% "
                     f"completion, a reward cutscene whose trigger the operator confirmed",
            "gap": f"no combination matrix is registered, so 'native combinations' has no "
                   f"target set; and unlike the crossings other rows register, NONE of these "
                   f"has a matched control -- no suppression, no negative arm, no "
                   f"forbidden-claim boundary. The plant half of the plant-x-boss crossing is "
                   f"entirely unexamined, so the crossing is observed at its downstream end "
                   f"only. The UI crossing is the one that was read wrong",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the resident side of the interface is documented at instruction level "
                     f"and is SHARED rather than bespoke: the mover-VM contract (op at record "
                     f"+0x70, dispatch through the shared loop tail), the berry damage "
                     f"dispatch PC common to two bosses, and the type-0x3f kind-0x30 contact "
                     f"handler that writes the setpiece trigger are all named with addresses. "
                     f"The scene-asset interface was CORRECTED and re-pinned for this row: "
                     f"disc dir is arithmetic, not a table read "
                     f"('{S['scene_dir_law']}'), and this row is one of "
                     f"{S['rows_with_wrong_scene_asset_binding']} whose prior binding was "
                     f"falsified ({F['scene_binding_claimed']} -> "
                     f"{F['scene_binding_truth']}). NEW HERE: the overlay->pool interface is "
                     f"absolute-addressed, which is itself an interface fact",
            "gap": f"the overlay side has no documented ABI and no registered contract: "
                   f"{F['confirmed_sites_for_row']} entries in config/confirmed_sites.yaml "
                   f"name this row's sites, {F['ownership_overlay_functions']} overlay "
                   f"functions are attributed to the row in the ownership graph, and the "
                   f"pinned overlay has {F['pinned_overlay_code_functions']} code functions "
                   f"in the census. The unknowns are enumerated in prose but most carry no "
                   f"NAMED OBSTRUCTION -- they are listed as not-worth-chasing or "
                   f"needs-a-fixture, which is a priority, not an obstruction",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured against BOTH registries, not assumed. "
                     f"{F['governing_addresses']} governing code addresses derived from this "
                     f"row's own artifacts split into {F['governing_resident']} resident and "
                     f"{F['governing_overlay']} inside the overlay load window. RESIDENT "
                     f"(config/segments.yml, toolchain {S['resident_build_toolchain']}): all "
                     f"{F['governing_resident_in_a_build_unit']} that land in a build unit "
                     f"resolve to {F['governing_resident_units']} units, of which "
                     f"{F['governing_resident_units_matching_c']} are matching C and "
                     f"{F['governing_resident_units_hand_asm']} are hand-written byte-exact "
                     f"ASM. OVERLAY (config/overlays.yml + src/overlays/ + "
                     f"analysis/overlay_decomp_progress.json): the pinned overlay "
                     f"{F['overlay_registered_in_overlays_yml']} registered in the overlay "
                     f"build registry and has {F['pinned_overlay_matched_functions']} matched "
                     f"of {F['pinned_overlay_code_functions']} code functions",
            "gap": f"there is no byte-matched C anywhere in this row's governing set, on "
                   f"either track, so the dimension cannot be partial. The campaign-wide "
                   f"overlay track stands at {S['overlay_track_matched']}/"
                   f"{S['overlay_track_functions']} functions "
                   f"({S['overlay_track_pct']}%) across "
                   f"{S['overlays_registered_for_build']} registered overlays, and this row's "
                   f"is not among them -- note that a claim that overlay byte-matching is "
                   f"impossible would be false: {S['overlays_registered_for_build']} overlays "
                   f"and {S['overlay_track_matched']} functions are already matched, just not "
                   f"this one. The census triage says '{F['census_triage_source_closure']}', "
                   f"which measures REGISTRATION; measured against real governing addresses "
                   f"the answer is the same, zero",
        },
    }


def build_f14_dims(F: dict, S: dict) -> dict:
    return {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"the measured F-row census -- {F['census_durable_reason']}. This "
                     f"assessment fails loudly if that measurement moves off 'met'. "
                     f"Independently re-confirmed: "
                     f"{F['fixtures_bytes_match_central_pin']} of "
                     f"{F['declared_fixture_count']} declared fixtures still byte-match the "
                     f"central manifest, all {F['fixtures_credited_to_row_centrally']} are "
                     f"credited to this row by name there, and phase2_row_coverage records "
                     f"{F['unaudited_fixtures']} unaudited fixtures",
            "gap": f"intactness is not health. The two retained artifacts that carry this "
                   f"row's only runtime and static-census evidence FAIL their registered "
                   f"gates today -- {F['inherited_gate_health']}; "
                   f"{F['own_gate_health']} -- and the recomputation the "
                   f"gate performs is what proves the retained routing is stale rather than "
                   f"the evidence corrupt. Separately the row declares "
                   f"{F['declared_movie_count']} movies while "
                   f"{F['stage_movies_pinned_strict']} stage-14 movies are centrally pinned",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the one deep observation in this scene is real natural-execution "
                     f"evidence with a matched control, which most F rows lack: from the "
                     f"centrally pinned pristine anchor ({F['flight_fixture']}, media class "
                     f"{F['flight_fixture_media_class']}) the natural branch reaches health "
                     f"{F['natural_fatal_health']} and the ordinary resident respawn restores "
                     f"{F['ordinary_respawn_health_lives']} (health, lives), with the fatal "
                     f"boundary bound to an exact frame/cycle/PC/SP and the entry call "
                     f"decoded to its instruction word and register arguments; the control "
                     f"changes ONE actor state bit at the matched boundary, preserves "
                     f"frame/cycle/PC/SP ({F['matched_outcome_frame_cycle_pc_sp']}), and "
                     f"removes the damage call entirely, with "
                     f"{F['response_only_ram_difference_count']} main-RAM difference. It is "
                     f"registered as a declarative scenario "
                     f"({F['behavioural_scenario_names']}) with an exec-hit-count assertion, "
                     f"and the row's headline scene claim has its own identity oracle "
                     f"({F['identity_scenario_assertions']} pinned-anchor assertions)",
            "gap": f"none of that is an oracle for THIS ROW'S SUBJECT, and the artifact says "
                   f"so in its own words: '{F['forbidden_claim']}' with "
                   f"c16_or_f14_completed={F['row_completion_flag']}. The row's declared "
                   f"missing item is '{F['declared_missing']}' and nothing in the repository "
                   f"asserts flight, companion or chase behaviour at all. The scenario that "
                   f"does exist cannot be trusted green today: "
                   f"{F['inherited_gate_health']}. "
                   f"And a from-boot completion oracle for stage 14 already exists "
                   f"({F['completion_oracle_movie']}, {F['completion_oracle_frames']} frames, "
                   f"target scene {F['completion_oracle_target_scene']}, accepted="
                   f"{F['completion_oracle_replay_accepted']}) which the row does not cite "
                   f"(cited={F['completion_oracle_cited_by_row']})",
        },
        "complete_frontier": {
            "state": "not_met",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"three adjacent frontiers in this scene ARE enumerated, each with "
                     f"declared scope limits: the respawn-writer census is exhaustive for "
                     f"direct absolute stores over {F['catalog_staged_inputs']} pinned "
                     f"LEVEL.BIN images ({F['catalog_direct_writes']} writes in "
                     f"{F['catalog_writer_files']} files, {F['catalog_zero_writer_files']} "
                     f"files explicitly zero) and names this stage's initializer, its four "
                     f"decoded stores and its single resident call site "
                     f"({F['level08_entry_call_sites']}); the stage's collision environment "
                     f"is censused disc-side against runtime with "
                     f"{S['e02_disc_runtime_disagreements']} disagreements over "
                     f"{S['e02_authored_sectors_compared']} sectors, giving "
                     f"{F['authored_collision_sectors']} authored sectors and exactly "
                     f"{F['region_code_sector_count']} non-zero region-code sector "
                     f"(histogram {F['region_code_histogram']}); and the overlay file is now "
                     f"pinned from bytes rather than named from an address -- of "
                     f"{F['overlay_pin_images_scanned']} images exactly "
                     f"{F['overlay_pin_images_satisfying']} contains all "
                     f"{F['overlay_pin_spec_count']} evidence-derived encodings with one "
                     f"consistent load base ({F['overlay_pin_file']} @ "
                     f"{F['overlay_pin_load_base']})",
            "gap": f"none of that is this row's own frontier, and this row's own frontier is "
                   f"neither enumerated nor bounded. Its entire residual statement is "
                   f"'{F['declared_missing']}' -- {F['declared_missing_items']} item, no "
                   f"named obstruction, which fails the EXIT-GATE bar as well as item 2. "
                   f"Zero functions in flight/companion/chase are identified; the contact "
                   f"actor's own type word stays '{F['actor_type_word']}' classified "
                   f"'{F['actor_owner_classification']}'; the ownership graph resolves the "
                   f"row to {F['ownership_functions']} resident dispatcher addresses with "
                   f"{F['ownership_gaps']} unowned state addresses "
                   f"({F['ownership_gap_items']}); and the one strong lead nobody has "
                   f"followed is measured here -- the single region-code-{F['exit_region_code']} "
                   f"sector at index {F['exit_region_sector_index']}, runtime origin "
                   f"{F['exit_region_runtime_origin']}, which by the campaign's own exit law "
                   f"is the shape of a stage-exit trigger",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"the row inherits two real denominators without owning either: the "
                     f"respawn-writer census covers {F['catalog_staged_inputs']}/"
                     f"{F['catalog_staged_inputs']} staged LEVEL.BIN images and names its own "
                     f"scope limits ('{F['catalog_still_unknown']}'), and the collision "
                     f"census covers {S['e02_levels_censused']} levels",
            "gap": f"the row has no conclusion of its own to generalize. Within the stage the "
                   f"applicable set is not enumerated and not sampled: of "
                   f"{F['stage_movies_pinned_strict']} centrally pinned stage-14 movies "
                   f"(including a {F['largest_stage_movie_frames']}-frame 100% run) the row's "
                   f"artifacts replay {F['stage_movies_replayed_by_row']}; its three declared "
                   f"fixtures are all save states. The inherited census's own scope excludes "
                   f"the LEVEL1.* variants and pointer-mediated writers, so even the "
                   f"inherited denominator is a declared subset. Note the corpus token trap "
                   f"measured here: the bare token 'riverbed' also matches "
                   f"{F['riverbed_movies_belonging_to_another_row']} movies belonging to a "
                   f"different row's stage, so a breadth claim keyed on it would "
                   f"double-count",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"the values this scene's evidence touches are unusually precisely "
                     f"bounded, because they are decoded constants rather than samples: the "
                     f"stage's safe/live anchor tuple is {F['level08_safe_tuple']} recovered "
                     f"from {F['level08_direct_writes']} stores whose widths, base and source "
                     f"registers and target addresses are all decoded, and the same tuple was "
                     f"then live-qualified ({F['level08_initializer_live_qualified']}). The "
                     f"contact actor's fields are typed by the shared record registry and its "
                     f"record {F['actor_record_addr']} lies inside the declared extent "
                     f"(inside={F['actor_inside_declared_extent']}); id, flags, callback and "
                     f"source pointer are all asserted by value in the registered scenario",
            "gap": f"the row's own state is entirely untyped -- flight, companion and chase "
                   f"have no fields, no widths and no domains, which is the whole of its "
                   f"declared missing item. The actor that IS typed is unclassified at the "
                   f"level that matters ('{F['actor_owner_classification']}'), "
                   f"{F['overlay_state_addresses_registered']} of this row's addresses appear "
                   f"in config/semantic_state.yaml, and the record registry disagrees with "
                   f"this row's own artifact about slot numbering: the declared base "
                   f"{S['actor_record_declared_base']} puts this actor at index "
                   f"{F['actor_index_from_declared_base']} while the artifact calls it slot "
                   f"{F['actor_pool_slot_claimed']}, implying a pool base of "
                   f"{F['actor_pool_base_implied']} -- exactly "
                   f"{F['declared_base_minus_implied_strides']} stride above the base the "
                   f"evidence counts from",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"the load and death/respawn phases are evidenced to instruction level "
                     f"for this scene. LOAD: the resident call at "
                     f"{F['level08_entry_call_sites']} (instruction word "
                     f"{F['resident_scene8_call_word']}) enters the overlay initializer at "
                     f"{F['level08_runtime_start']}, whose {F['level08_size']} resident bytes "
                     f"match the pristine file slice exactly "
                     f"({F['level08_exact_pristine_match']}) -- and this assessment's byte "
                     f"probe independently pins that slice to one image out of "
                     f"{F['overlay_pin_images_scanned']}. FIRST USE and RETIREMENT: one "
                     f"contact, one death at health {F['natural_fatal_health']}, one ordinary "
                     f"respawn to {F['ordinary_respawn_health_lives']}, all frame- and "
                     f"cycle-bound",
            "gap": f"cold boot, repeated use, exhaustion and reuse are absent, and the "
                   f"stage's own lifecycle -- entry into flight, chase start and end, "
                   f"objective completion, exit -- is entirely unobserved. Every anchor is a "
                   f"save state; the only from-boot route is the uncited completion-oracle "
                   f"movie. The catalog that supplies the load half still records "
                   f"'{F['catalog_still_unknown']}', i.e. it does not itself know this "
                   f"initializer runs -- the live qualification lives in a different artifact "
                   f"and was never folded back",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"one crossing is exercised properly and it spans four systems at once: "
                     f"ACTOR CONTACT x PLAYER DAMAGE x DEATH/LIVES x OVERLAY RESPAWN "
                     f"INITIALIZER, on natural execution, from a pristine anchor, with a "
                     f"single-bit control at a matched boundary that suppresses the whole "
                     f"chain (damage call, death, respawn and the LEVEL08 initializer) while "
                     f"changing {F['response_only_ram_difference_count']} byte of main RAM, "
                     f"plus an independent same-entry source control that moves only the "
                     f"expected anchor component. The crossing is registered as a runnable "
                     f"scenario rather than prose",
            "gap": f"it is one crossing, and it is a SPECIAL-STAGE instance of the ORDINARY "
                   f"law -- the artifact's own reading is that this context reuses the "
                   f"ordinary proximity path, and it forbids generalising "
                   f"('{F['forbidden_claim']}'). No flight-specific combination exists: no "
                   f"carry+damage, no powers, no projectile-at-transition, nothing involving "
                   f"the companion. No combination matrix is registered, so there is no "
                   f"target set to measure the one crossing against",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the resident->overlay interface for this stage is documented at the "
                     f"instruction level and is the strongest interface evidence either of "
                     f"this assessment's rows has: call site {F['level08_entry_call_sites']}, "
                     f"instruction word {F['resident_scene8_call_word']}, resolved target "
                     f"{F['level08_runtime_start']}, return {F['resident_scene8_call_return']}, "
                     f"with the callee's four stores decoded to base/source register and "
                     f"target address. The actor interface is likewise concrete (callback "
                     f"{F['actor_callback']}, source backlink {F['actor_source_pointer']}, "
                     f"type word {F['actor_type_word']}). The scene-asset interface was "
                     f"corrected and re-pinned for this row: "
                     f"{F['scene_binding_claimed']} -> {F['scene_binding_truth']}, one of "
                     f"{S['rows_with_wrong_scene_asset_binding']} rows corrected by the same "
                     f"law ('{S['scene_dir_law']}')",
            "gap": f"the unknowns are not enumerated with obstructions -- they are one "
                   f"sentence. {F['confirmed_sites_for_row']} sites are registered in "
                   f"config/confirmed_sites.yaml for this row and the overlay has no ABI at "
                   f"all. Worse for interface IDENTITY: the artifact carrying all of the "
                   f"above still binds its static provenance to the FALSIFIED routing "
                   f"(asset_entry '{F['retained_static_asset_entry']}', disc dir "
                   f"'{F['retained_static_disc_dir']}', overlays "
                   f"{F['retained_static_overlays']}), which the corrected binding, the "
                   f"collision census container ({F['collision_container']}) and this "
                   f"assessment's byte pin ({F['overlay_pin_file']}) all contradict. Its "
                   f"runtime observations are unaffected; its file-level provenance is not",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured against BOTH registries. {F['governing_addresses']} governing "
                     f"code addresses derived from this row's own scene evidence split into "
                     f"{F['governing_resident']} resident and {F['governing_overlay']} inside "
                     f"the overlay load window. RESIDENT (config/segments.yml, toolchain "
                     f"{S['resident_build_toolchain']}): "
                     f"{F['governing_resident_in_a_build_unit']} land in a build unit, "
                     f"resolving to {F['governing_resident_units']} units of which "
                     f"{F['governing_resident_units_matching_c']} are matching C and "
                     f"{F['governing_resident_units_hand_asm']} are hand-written byte-exact "
                     f"ASM. OVERLAY (config/overlays.yml + src/overlays/ + "
                     f"analysis/overlay_decomp_progress.json): the byte-pinned overlay "
                     f"{F['overlay_registered_in_overlays_yml']} registered for build and has "
                     f"{F['pinned_overlay_matched_functions']} matched of "
                     f"{F['pinned_overlay_code_functions']} code functions",
            "gap": f"zero byte-matched C on either track for this row's governing set. The "
                   f"overlay track is not impossible -- {S['overlay_track_matched']} functions "
                   f"across {S['overlays_registered_for_build']} registered overlays are "
                   f"already matched ({S['overlay_track_pct']}% of "
                   f"{S['overlay_track_functions']}) -- this overlay is simply not registered "
                   f"among them, and the initializer this row depends on is a "
                   f"{F['level08_size']}-byte function that the catalog has already decoded "
                   f"store by store, i.e. the cheapest overlay-C candidate either row offers. "
                   f"The census triage says '{F['census_triage_source_closure']}'",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(
        ROOT / "analysis/phase4_f06_f14_written_bar_assessment.json"))
    ap.add_argument("--no-gates", action="store_true",
                    help="skip executing the rows' registered pytest gates")
    ap.add_argument("--no-probe-suite", action="store_true",
                    help="skip the fail-loud self-probes (set for the child runs the "
                         "probe suite itself launches)")
    args = ap.parse_args()

    E = Evidence()
    S = E.facts["shared"]
    A = E.facts[F06]
    B = E.facts[F14]

    # ------------------------------------------------------------------ #
    # 0. the standard this assessment is measured against                 #
    # ------------------------------------------------------------------ #
    RULING = "engineering-specs/phase4-measurement-standard-ruling.md"
    ruling = E.text(RULING)
    E.fact("shared", "ruling_states_item2_is_enumerated",
           "enumerated" in ruling.lower() and "not the standard" in ruling, RULING)
    E.fact("shared", "ruling_states_bounded_exhausted_never_met",
           "never counts as met" in ruling or "never be read as" in ruling, RULING)

    # ------------------------------------------------------------------ #
    # 1. durable_evidence -- CARRIED FORWARD from the measured census.    #
    # ------------------------------------------------------------------ #
    CENSUS = "analysis/phase4_f_row_measured_census.json"
    census = E.json(CENSUS)
    E.fact("shared", "census_baseline_sha256", req(census, "baseline_sha256", where=CENSUS),
           CENSUS)
    E.fact("shared", "census_fixture_set_sha256",
           req(census, "fixture_set_sha256", where=CENSUS), CENSUS)
    E.fact("shared", "census_rows_assessed", req(census, "rows_assessed", where=CENSUS),
           CENSUS)
    E.fact("shared", "census_durable_met_fraction",
           req(census, "durable_evidence_met_fraction", where=CENSUS), CENSUS)

    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    fixset = E.json(FIXSET)
    fx_entries = req(fixset, "entries", where=FIXSET)

    crows = {}
    for scope, row_id in ((F06, F06), (F14, F14)):
        crow = req(census, "rows", row_id, where=CENSUS)
        crows[scope] = crow
        de = req(crow, "durable_evidence", where=CENSUS)
        E.fact(scope, "census_durable_state", req(de, "state", where=CENSUS), CENSUS)
        E.fact(scope, "census_durable_fraction", req(de, "intact_pinned", where=CENSUS),
               CENSUS)
        E.fact(scope, "census_durable_reason", req(de, "reason", where=CENSUS), CENSUS)
        E.fact(scope, "census_row_status", req(crow, "status", where=CENSUS), CENSUS)
        inv = req(crow, "evidence_inventory", where=CENSUS)
        E.fact(scope, "census_analysis_artifacts",
               len(req(inv, "analysis_artifacts", where=CENSUS)), CENSUS)
        E.fact(scope, "census_analysis_artifact_paths",
               req(inv, "analysis_artifacts", where=CENSUS), CENSUS)
        E.fact(scope, "census_vault_pages", len(req(inv, "vault_pages", where=CENSUS)),
               CENSUS)
        E.fact(scope, "census_source_files", len(req(inv, "source_files", where=CENSUS)),
               CENSUS)
        E.fact(scope, "census_segments_entries", req(inv, "segments_entries", where=CENSUS),
               CENSUS)
        E.fact(scope, "census_stage_ordinal", req(inv, "stage_ordinal", where=CENSUS),
               CENSUS)
        E.fact(scope, "scene_id", req(inv, "scene_id", where=CENSUS), CENSUS)
        E.fact(scope, "census_overlay_name", req(inv, "overlay_name", where=CENSUS), CENSUS)
        E.fact(scope, "census_has_runtime_trace_evidence",
               req(inv, "has_runtime_trace_evidence", where=CENSUS), CENSUS)
        E.fact(scope, "census_triage_source_closure",
               req(crow, "measurability_triage", "source_closure", where=CENSUS), CENSUS)
        fixtures = req(de, "fixtures", where=CENSUS)
        E.fact(scope, "declared_fixture_count", len(fixtures), CENSUS)
        E.fact(scope, "fixtures_bytes_match_central_pin",
               sum(1 for f in fixtures if f.get("bytes_match_pin")), CENSUS)
        if req(de, "state", where=CENSUS) != "met":
            raise SystemExit(f"carried-forward durable_evidence for {scope} is no longer "
                             "'met' -- re-measure before reusing this assessment")
        # independent: is each declared fixture credited to THIS row centrally?
        credited = 0
        for f in fixtures:
            path = req(f, "path", where=CENSUS)
            entry = fx_entries.get(path)
            if entry and f"mechanics:{scope}" in entry.get("consumers", []):
                credited += 1
        E.fact(scope, "fixtures_credited_to_row_centrally", credited, [FIXSET, CENSUS])

    # ------------------------------------------------------------------ #
    # 2. registry dispositions (contrast only) + the baseline rows        #
    # ------------------------------------------------------------------ #
    DEBT = "analysis/phase4_closure_debt.json"
    debt = E.json(DEBT)
    for scope in (F06, F14):
        drow = debt_row(debt, scope, DEBT)
        E.fact(scope, "registry_dimensions_met", req(drow, "counts", "met", where=DEBT), DEBT)
        E.fact(scope, "registry_dimensions_remaining",
               req(drow, "counts", "remaining", where=DEBT), DEBT)
        E.fact(scope, "registry_distinct_bases",
               sorted({d["basis"] for d in req(drow, "dimensions", where=DEBT).values()}),
               DEBT)
        E.fact(scope, "registry_distinct_states",
               sorted({d["state"] for d in req(drow, "dimensions", where=DEBT).values()}),
               DEBT)
        E.fact(scope, "registry_completion_state",
               req(drow, "completion_state", where=DEBT), DEBT)
        E.fact(scope, "registry_movie_count", req(drow, "movie_count", where=DEBT), DEBT)
        E.fact(scope, "registry_campaign_id", req(drow, "campaign_id", where=DEBT), DEBT)

    BASE = "analysis/mechanics_baseline.yaml"
    base = E.yaml(BASE)
    rows = req(base, "rows", where=BASE)
    rowdocs = {F06: baseline_row(rows, F06, BASE), F14: baseline_row(rows, F14, BASE)}
    for scope, row in rowdocs.items():
        E.fact(scope, "row_name", req(row, "name", where=BASE), BASE)
        E.fact(scope, "row_status", req(row, "status", where=BASE), BASE)
        E.fact(scope, "row_declared_stages", req(row, "stages", where=BASE), BASE)
        E.fact(scope, "row_binding_claims", len(req(row, "bindings", where=BASE)), BASE)
        E.fact(scope, "declared_evidence_classes", req(row, "evidence", where=BASE), BASE)
        E.fact(scope, "declared_missing", req(row, "missing", where=BASE), BASE)
        E.fact(scope, "declared_missing_items",
               len([x for x in req(row, "missing", where=BASE).split(";") if x.strip()]),
               BASE)
        E.fact(scope, "declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
        E.fact(scope, "declared_next", req(row, "next", where=BASE), BASE)
        E.fact(scope, "declared_fixtures", req(row, "fixture_have", where=BASE), BASE)
        E.fact(scope, "declared_movie_count",
               sum(1 for f in req(row, "fixture_have", where=BASE) if ".movie.json" in f),
               BASE)
        E.fact(scope, "row_artifact_path_citations",
               len(set(re.findall(r"(?:analysis|tools|src|src_re|tests|config)/[\w./%-]+",
                                  json.dumps(row)))), BASE)

    # ------------------------------------------------------------------ #
    # 3. the corrected scene->asset law (shared; corrects BOTH rows)      #
    # ------------------------------------------------------------------ #
    # The ROW->SCENE mapping is itself derived, never assumed: `stages` in the
    # baseline is the stage ORDINAL, and the campaign progression table at
    # 0x80077FA0 maps ordinal -> scene id.
    SAG = "analysis/phase3_scene_asset_graph.json"
    sag = E.json(SAG)
    numbering = req(sag, "operator_level_numbering", where=SAG)
    tab = re.search(r"\[([-\d,\s]+)\]", numbering)
    if not tab:
        raise SystemExit(f"STALE CITATION: {SAG} no longer carries the progression table")
    progression = [int(x) for x in tab.group(1).split(",")]
    E.fact("shared", "progression_table_source",
           re.search(r"0x[0-9A-Fa-f]{8}", numbering).group(0), SAG)
    E.fact("shared", "progression_table", progression, SAG)
    E.fact("shared", "progression_table_entries", len(progression), SAG)

    SB = "analysis/phase4_f08_scene_binding.json"
    sb = E.json(SB)
    E.fact("shared", "scene_dir_law",
           req(sb, "mechanism", "level_data_directory", where=SB), SB)
    E.fact("shared", "scene_dir_law_index_form",
           req(sb, "mechanism", "index_form", where=SB), SB)
    wrong = req(sb, "rows_with_wrong_scene_asset_binding", where=SB)
    E.fact("shared", "rows_with_wrong_scene_asset_binding", len(wrong), SB)
    E.fact("shared", "scene_binding_residency_confirmations",
           len(req(sb, "residency_confirmation", where=SB)), SB)
    for scope in (F06, F14):
        entry = next((w for w in wrong if w.get("row") == scope), None)
        if entry is None:
            raise SystemExit(f"STALE CITATION: {SB} no longer records the falsified scene "
                             f"binding for {scope}")
        E.fact(scope, "scene_binding_claimed", req(entry, "claimed", where=SB), SB)
        E.fact(scope, "scene_binding_truth", req(entry, "truth", where=SB), SB)
        E.fact(scope, "scene_binding_scene", req(entry, "scene", where=SB), SB)
        ordinal = int(req(rowdocs[scope], "stages", where=BASE))
        if not 0 <= ordinal < len(progression):
            raise SystemExit(f"{scope}: stage ordinal {ordinal} is outside the progression "
                             "table this assessment derived")
        E.fact(scope, "stage_ordinal_from_baseline", ordinal, BASE)
        E.fact(scope, "scene_from_progression_table", progression[ordinal], [SAG, BASE])
        E.fact(scope, "row_mapping_agrees_three_ways",
               progression[ordinal] == E.facts[scope]["scene_id"]
               == req(entry, "scene", where=SB), [SAG, BASE, CENSUS, SB])

    # ------------------------------------------------------------------ #
    # 4. shared registries: build tracks, record types, semantic state    #
    # ------------------------------------------------------------------ #
    SEG = "config/segments.yml"
    seg = E.yaml(SEG)
    units = [(as_int(req(e, "start", where=SEG)), as_int(req(e, "end", where=SEG)),
              req(e, "source", where=SEG)) for e in req(seg, "attempted", where=SEG)]
    E.fact("shared", "resident_build_toolchain",
           req(seg, "c_toolchain", "compiler", where=SEG), SEG)
    E.fact("shared", "resident_build_units_declared", len(units), SEG)

    OVLY = "config/overlays.yml"
    ovly = E.yaml(OVLY)
    ovly_reg = req(ovly, "overlays", where=OVLY)
    E.fact("shared", "overlays_registered_for_build", len(ovly_reg), OVLY)
    E.fact("shared", "overlay_registry_names", sorted(ovly_reg), OVLY)
    E.fact("shared", "overlay_load_base_registered",
           f"0x{as_int(req(ovly, 'region_a', where=OVLY)):08X}", OVLY)

    OVLD = "analysis/overlay_decomp_progress.json"
    ovld = E.json(OVLD)
    E.fact("shared", "overlay_track_functions",
           req(ovld, "overlay_code_functions", where=OVLD), OVLD)
    E.fact("shared", "overlay_track_matched",
           req(ovld, "matched", "functions", where=OVLD), OVLD)
    E.fact("shared", "overlay_track_pct", req(ovld, "matched", "pct_functions", where=OVLD),
           OVLD)
    per_ovl = req(ovld, "per_overlay_totals", where=OVLD)

    RECS = "config/record_types.yaml"
    recs = E.yaml(RECS)
    actor = next((r for r in req(recs, "records", where=RECS) if r["id"] == "actor_record"),
                 None)
    if actor is None:
        raise SystemExit(f"STALE CITATION: {RECS} no longer carries actor_record")
    a_base = req(actor, "base", where=RECS)
    a_size = req(actor, "size", where=RECS)
    a_inst = req(actor, "instances", where=RECS)
    a_fields = {f["offset"]: f for f in req(actor, "fields", where=RECS)}
    E.fact("shared", "actor_record_declared_base", f"0x{a_base:08X}", RECS)
    E.fact("shared", "actor_record_declared_stride", a_size, RECS)
    E.fact("shared", "actor_record_declared_instances", a_inst, RECS)
    E.fact("shared", "actor_record_typed_fields", len(a_fields), RECS)
    E.fact("shared", "actor_hp_field_note", req(a_fields[0x6E], "note", where=RECS), RECS)

    SEM = "config/semantic_state.yaml"
    sem = E.yaml(SEM)
    sem_entries = req(sem, "entries", where=SEM)
    sem_addrs = {}
    for e in sem_entries:
        a = e.get("address")
        if isinstance(a, (int, str)):
            sem_addrs[as_int(a)] = req(e, "id", where=SEM)
    ovl_region = as_int(req(ovly, "region_a", where=OVLY))
    E.fact("shared", "semantic_state_entries_total", len(sem_entries), SEM)
    E.fact("shared", "semantic_state_overlay_window_entries",
           sorted(f"0x{a:08X}={i}" for a, i in sem_addrs.items() if a >= ovl_region),
           [SEM, OVLY])

    SITES = "config/confirmed_sites.yaml"
    sites = E.yaml(SITES)
    site_entries = req(sites, "entries", where=SITES)
    site_addrs = {as_int(req(s, "address", where=SITES)) for s in site_entries}
    E.fact("shared", "confirmed_sites_total", len(site_entries), SITES)

    FN = "analysis/functions.json"
    fnj = E.json(FN)
    fns = req(fnj, "functions", where=FN)
    E.fact("shared", "overlay_images_in_function_census",
           len(req(fnj, "overlays", where=FN)), FN)

    E02 = "analysis/phase4_e02_disc_region_code_census.json"
    e02 = E.json(E02)
    levels = req(e02, "levels", where=E02)
    E.fact("shared", "e02_levels_censused", len(levels), E02)
    E.fact("shared", "e02_disc_runtime_disagreements",
           len(req(e02, "agreement", "disagreements", where=E02)), E02)
    E.fact("shared", "e02_authored_sectors_compared",
           req(e02, "agreement", "authored_sectors_compared", where=E02), E02)

    ORACLE = "analysis/phase2_completion_oracle.json"
    oracle = E.json(ORACLE)
    ostages = req(oracle, "stages", where=ORACLE)

    AUDIT = "analysis/phase2_fixture_audit.json"
    audit = E.json(AUDIT)
    movies = req(audit, "movies", where=AUDIT)

    OWN = "analysis/phase3_ownership_graph.json"
    own = E.json(OWN)

    COV = "analysis/phase2_row_coverage.json"
    cov = E.json(COV)

    # per-row wiring of the shared registries
    stage_keys = {F06: "stage06_birdnest", F14: "stage14_riverbed_flight"}
    for scope, skey in stage_keys.items():
        lvl = req(levels, skey, where=E02)
        E.fact(scope, "collision_container", req(lvl, "container", where=E02), E02)
        E.fact(scope, "collision_scene", req(lvl, "scene", where=E02), E02)
        E.fact(scope, "authored_collision_sectors",
               req(lvl, "authored_sectors", where=E02), E02)
        E.fact(scope, "runtime_collision_sectors", req(lvl, "runtime_sectors", where=E02),
               E02)
        E.fact(scope, "region_code_histogram", req(lvl, "code_histogram", where=E02), E02)
        nz = req(lvl, "nonzero_sectors", where=E02)
        E.fact(scope, "region_code_sector_count", len(nz), E02)
        if nz:
            E.fact(scope, "exit_region_code", req(nz[0], "code", where=E02), E02)
            E.fact(scope, "exit_region_sector_index", req(nz[0], "sector", where=E02), E02)
            E.fact(scope, "exit_region_runtime_origin",
                   req(nz[0], "runtime_origin", where=E02), E02)
        E.fact(scope, "collision_disc_vs_runtime_mismatches",
               len(req(lvl, "disc_vs_runtime_mismatches", where=E02)), E02)

        st = req(ostages, skey, where=ORACLE)
        E.fact(scope, "completion_oracle_movie", req(st, "movie", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_frames", req(st, "frames", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_target_scene",
               req(st, "target_scene", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_replay_accepted",
               req(st, "pristine_replay_accepted", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_stage_exited",
               req(st, "stage_exited_by_movie_end", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_entry_frame",
               req(st, "entered_stage_frame", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_enemy_quota_in_stage",
               req(st, "last_in_stage", "snapshot", "enemy_quota", where=ORACLE), ORACLE)
        E.fact(scope, "completion_oracle_cited_by_row",
               "phase2_completion_oracle" in json.dumps(rowdocs[scope])
               or req(st, "movie", where=ORACLE) in json.dumps(rowdocs[scope]),
               [BASE, ORACLE])

        orow = req(own, "rows", scope, where=OWN)
        ofns = req(orow, "functions", where=OWN)
        E.fact(scope, "ownership_functions", len(ofns), OWN)
        E.fact(scope, "ownership_overlay_functions",
               sum(1 for f in ofns if f.get("space") != "resident"), OWN)
        E.fact(scope, "ownership_functions_with_canon",
               sum(1 for f in ofns if f.get("canon")), OWN)
        E.fact(scope, "ownership_gaps", len(req(orow, "gaps", where=OWN)), OWN)
        E.fact(scope, "ownership_gap_items", req(orow, "gaps", where=OWN), OWN)
        E.fact(scope, "ownership_state_addresses", len(req(orow, "state", where=OWN)), OWN)

        crow2 = req(cov, "rows", scope, where=COV)
        E.fact(scope, "row_coverage_status", req(crow2, "status", where=COV), COV)
        E.fact(scope, "unaudited_fixtures",
               len(req(crow2, "unaudited_fixtures", where=COV)), COV)

    # ------------------------------------------------------------------ #
    # 5. F06's own evidence: the bird, the defeat trace, the banner       #
    # ------------------------------------------------------------------ #
    F06ART = "analysis/phase4_f06_birdnest.json"
    f06 = E.json(F06ART)
    E.fact(F06, "row_artifact_status", req(f06, "status", where=F06ART)[:200], F06ART)
    E.fact(F06, "row_artifact_still_open_items",
           len([x for x in req(f06, "STILL_OPEN", where=F06ART).split(";") if x.strip()]),
           F06ART)
    stop = req(f06, "STOPPING_POINT_JUSTIFIED_2026-08-03", where=F06ART)
    E.fact(F06, "stopping_point_is_operator_confirmed",
           "operator" in req(stop, "conclusion", where=F06ART).lower(), F06ART)
    E.fact(F06, "unexamined_producer",
           req(stop, "one_promising_lead_not_chased", where=F06ART)[:180], F06ART)
    E.fact(F06, "entry_fmv_fixture_status",
           req(stop, "needs_a_fixture_not_available", where=F06ART)[:160], F06ART)
    banner = req(f06, "RESULTS_SCREEN_COUNTERS_DECODED_2026-08-03", where=F06ART)
    E.fact(F06, "banner_reading_registered", req(banner, "result", where=F06ART), F06ART)
    E.fact(F06, "banner_claims_seed_tokens",
           "seed-token" in req(banner, "result", where=F06ART), F06ART)
    hund = req(f06, "F06_100PCT_RUN_FULL_ENDING_MAPPED_2026-08-03", where=F06ART)
    E.fact(F06, "hundred_pct_movie_frames",
           int(re.search(r"([\d,]+) frames", req(hund, "trigger", where=F06ART))
               .group(1).replace(",", "")), F06ART)

    D17B = "analysis/phase4_d17_bird.json"
    d17 = E.json(D17B)
    seqk = "COMBAT_SEQUENCE_2026-08-02"
    E.fact(F06, "d17_row_status", req(d17, "status", where=D17B)[:120], D17B)
    E.fact(F06, "d17_identity_scene_result",
           req(d17, "LEVEL_IDENTITY_2026-08-02", "result", where=D17B), D17B)
    gold = req(d17, seqk, "gold_berry_launches_the_bird_up", where=D17B)
    gy = re.search(r"Y jumps from (-?\d+) to (-?\d+)", gold)
    if not gy:
        raise SystemExit(f"STALE CITATION: {D17B} no longer records the gold-berry Y jump")
    E.fact(F06, "gold_berry_y_before", int(gy.group(1)), D17B)
    E.fact(F06, "gold_berry_y_after", int(gy.group(2)), D17B)
    E.fact(F06, "d17_still_open_items",
           len([x for x in req(d17, "STILL_OPEN", where=D17B).split(";") if x.strip()]),
           D17B)

    D17D = "analysis/phase4_d17_defeat.json"
    dd = E.json(D17D)
    E.fact(F06, "defeat_movie", req(dd, "movie", where=D17D), D17D)
    E.fact(F06, "defeat_frames", req(dd, "frames", where=D17D), D17D)
    E.fact(F06, "defeat_event_total", req(dd, "event_total", where=D17D), D17D)
    E.fact(F06, "defeat_ring_truncated", req(dd, "ring_truncated", where=D17D), D17D)
    E.fact(F06, "boss_record_addr", req(dd, "located", "addr", where=D17D), D17D)
    E.fact(F06, "hp_at_settle", req(dd, "located", "hp_at_settle", where=D17D), D17D)
    by_field = req(dd, "by_field", where=D17D)
    E.fact(F06, "defeat_fields_attributed", len(by_field), D17D)
    all_writers = {pc for v in by_field.values() for pc, _ in req(v, "writer_pcs",
                                                                 where=D17D)}
    E.fact(F06, "defeat_distinct_writer_pcs", len(all_writers), D17D)
    ovl_writers = sorted(p for p in all_writers if as_int(p) >= ovl_region)
    E.fact(F06, "defeat_overlay_writer_pcs", len(ovl_writers), [D17D, OVLY])
    E.fact(F06, "defeat_overlay_writer_pc_list", ovl_writers, [D17D, OVLY])
    dmg = req(dd, "findings", "2_damage_instruction", where=D17D)
    E.fact(F06, "defeat_hp_events", len(req(dmg, "hp_decrements", where=D17D)), D17D)
    E.fact(F06, "defeat_damage_pcs", req(dmg, "distinct_damage_pcs", where=D17D), D17D)
    E.fact(F06, "defeat_deltas", sorted(req(dmg, "deltas", where=D17D)), D17D)
    E.fact(F06, "hp_final_observed",
           req(dmg, "hp_decrements", -1, "to", where=D17D), D17D)
    halt = req(dd, "findings", "1_defeat_installs_a_halt_program", where=D17D)
    E.fact(F06, "defeat_halt_installer_pc", req(halt, "installed_by_pc", where=D17D), D17D)
    E.fact(F06, "defeat_first_halt_frame", req(halt, "first_halt_frame", where=D17D), D17D)
    E.fact(F06, "vm_ip_values_seen", len(req(halt, "ip_values_seen", where=D17D)), D17D)
    E.fact(F06, "vm_ip_value_list", req(halt, "ip_values_seen", where=D17D), D17D)
    E.fact(F06, "halt_program_range",
           req(dd, "static_basis", "halt_program", "range", where=D17D), D17D)
    E.fact(F06, "wander_program_range",
           req(dd, "static_basis", "wander_program", "range", where=D17D), D17D)
    post = req(dd, "findings", "3_what_moves_the_bird_after_the_halt",
               "position_writers_after_halt", where=D17D)
    E.fact(F06, "post_halt_position_writer_count",
           sum(len(v) for v in post.values()), D17D)

    E.fact(F06, "inherited_open_items",
           sum(1 for x in req(rowdocs[F06], "missing", where=BASE).split(";")
               if "inherited" in x.lower()), BASE)

    # ------------------------------------------------------------------ #
    # 6. F14's own evidence: the scene-8 contact death + the initializer  #
    # ------------------------------------------------------------------ #
    C16F = "analysis/phase4_c16_flight_death.json"
    c16 = E.json(C16F)
    csum = req(c16, "summary", where=C16F)
    E.fact(F14, "flight_fixture", req(c16, "fixture_census", "save", "path", where=C16F),
           C16F)
    E.fact(F14, "flight_fixture_media_class",
           req(c16, "fixture_census", "save", "media_class", where=C16F), C16F)
    E.fact(F14, "flight_scene", req(csum, "scene", where=C16F), C16F)
    E.fact(F14, "natural_fatal_health", req(csum, "natural_fatal_health", where=C16F), C16F)
    E.fact(F14, "ordinary_respawn_health_lives",
           req(csum, "ordinary_respawn_health_lives", where=C16F), C16F)
    E.fact(F14, "response_only_ram_difference_count",
           req(csum, "response_only_main_ram_difference_count", where=C16F), C16F)
    E.fact(F14, "matched_outcome_frame_cycle_pc_sp",
           req(csum, "matched_outcome_frame_cycle_pc_sp", where=C16F), C16F)
    E.fact(F14, "row_completion_flag", req(csum, "c16_or_f14_completed", where=C16F), C16F)
    E.fact(F14, "level08_initializer_live_qualified",
           req(csum, "level08_respawn_initializer_live_qualified", where=C16F), C16F)
    E.fact(F14, "level08_safe_tuple", req(csum, "level08_fixed_safe_live_tuple", where=C16F),
           C16F)
    E.fact(F14, "forbidden_claim",
           req(c16, "bounded_interpretation", "forbidden_claim", where=C16F), C16F)
    E.fact(F14, "bounded_open_flight_scope",
           req(c16, "bounded_open_frontier", "flight_scope", where=C16F), C16F)
    ao = req(c16, "exact_invocation", "actor_owner", where=C16F)
    E.fact(F14, "actor_record_addr", req(ao, "address", where=C16F), C16F)
    E.fact(F14, "actor_pool_slot_claimed", req(ao, "pool_slot", where=C16F), C16F)
    E.fact(F14, "actor_id", req(ao, "id", where=C16F), C16F)
    E.fact(F14, "actor_callback", req(ao, "callback", where=C16F), C16F)
    E.fact(F14, "actor_source_pointer", req(ao, "source_pointer", where=C16F), C16F)
    tw = req(c16, "context_identity", "retained_type_word_frontier", where=C16F)
    E.fact(F14, "actor_type_word", req(tw, "type_word", where=C16F), C16F)
    E.fact(F14, "actor_owner_classification",
           req(tw, "owner_classification", where=C16F), C16F)
    sg = req(c16, "context_identity", "scene_graph", where=C16F)
    E.fact(F14, "retained_static_asset_entry", req(sg, "asset_entry", where=C16F), C16F)
    E.fact(F14, "retained_static_disc_dir", req(sg, "disc_dir", where=C16F), C16F)
    E.fact(F14, "retained_static_overlays", sorted(req(sg, "overlays", where=C16F)), C16F)
    sh = req(c16, "shared_c15_level08_respawn_activation", where=C16F)
    E.fact(F14, "resident_scene8_call_word",
           req(sh, "static_policy", "resident_scene8_call", "instruction_word", where=C16F),
           C16F)
    E.fact(F14, "resident_scene8_call_return",
           req(sh, "static_policy", "resident_scene8_call", "return", where=C16F), C16F)
    E.fact(F14, "level08_exact_pristine_match",
           req(sh, "runtime_identity", "exact_pristine_match", where=C16F), C16F)
    runtime_slice_sha = req(sh, "runtime_identity", "sha256", where=C16F)
    runtime_slice_len = req(sh, "runtime_identity", "length", where=C16F)
    runtime_slice_addr = req(sh, "runtime_identity", "address", where=C16F)

    CAT = "analysis/phase4_respawn_writer_catalog.json"
    cat = E.json(CAT)
    csum2 = req(cat, "summary", where=CAT)
    E.fact(F14, "catalog_staged_inputs", req(csum2, "staged_input_count", where=CAT), CAT)
    E.fact(F14, "catalog_writer_files", req(csum2, "writer_file_count", where=CAT), CAT)
    E.fact(F14, "catalog_direct_writes", req(csum2, "direct_write_count", where=CAT), CAT)
    E.fact(F14, "catalog_zero_writer_files",
           len(req(csum2, "zero_direct_writer_paths", where=CAT)), CAT)
    E.fact(F14, "catalog_scan_method", req(cat, "scan_contract", "method", where=CAT), CAT)
    E.fact(F14, "catalog_still_unknown",
           req(cat, "bounded_interpretation", "still_unknown", where=CAT), CAT)
    l08 = req(cat, "writer_functions", "LEVEL08/LEVEL.BIN", where=CAT)
    E.fact(F14, "level08_blob", req(l08, "path", where=CAT), CAT)
    E.fact(F14, "level08_runtime_start", req(l08, "runtime_start", where=CAT), CAT)
    E.fact(F14, "level08_size", req(l08, "size", where=CAT), CAT)
    E.fact(F14, "level08_evidence_scope", req(l08, "evidence_scope", where=CAT), CAT)
    E.fact(F14, "level08_entry_call_sites",
           req(l08, "static_resident_entry_call_sites", where=CAT), CAT)
    l08w = req(l08, "direct_writes", where=CAT)
    E.fact(F14, "level08_direct_writes", len(l08w), CAT)
    E.fact(F14, "level08_slice_sha256_matches_runtime",
           req(l08, "sha256", where=CAT) == runtime_slice_sha, [CAT, C16F])

    # ------------------------------------------------------------------ #
    # 7. NEW MEASUREMENT: which overlay FILE owns each row's addresses?   #
    #    Compiled C owns the decoding; the constraints are derived here   #
    #    from each row's own pinned runtime evidence.                     #
    # ------------------------------------------------------------------ #
    E.pin(PIN_SRC)
    gcc = shutil.which("gcc")
    if gcc is None:
        raise SystemExit("no gcc on PATH: the overlay pin probe is not optional -- "
                         "compiled C owns instruction decoding in this project")
    probe = Path("/tmp/phase4_f06_f14_overlay_pin")
    build = subprocess.run([gcc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                            str(ROOT / PIN_SRC), "-o", str(probe), "-lcrypto"],
                           capture_output=True, text=True)
    if build.returncode != 0:
        raise SystemExit(f"overlay pin probe failed to build: {build.stderr.strip()}")

    images = ["REBUILD/files/SCUS_942.88"] + sorted(
        f"OVL/{p.name}" for p in (ROOT / "OVL").glob("*.BIN"))
    if len(images) < 10:
        raise SystemExit("the overlay image set collapsed; refusing to pin against it")
    for rel in images:
        E.pin(rel)
    E.fact("shared", "overlay_images_scanned_by_probe", len(images), images)

    # --- F06: necessary conditions from the runtime write log + typed widths
    rec_base = as_int(A["boss_record_addr"])
    f06_specs, f06_spec_desc = [], []
    for faddr in sorted(by_field, key=lambda k: as_int(k)):
        pcs = [pc for pc, _ in req(by_field, faddr, "writer_pcs", where=D17D)
               if as_int(pc) >= ovl_region]
        if not pcs:
            continue
        off = as_int(faddr) - rec_base
        if off not in a_fields:
            raise SystemExit(f"STALE CITATION: {RECS} no longer types actor offset "
                             f"0x{off:02X}, which {D17D} observed being written")
        w = width_bytes(req(a_fields[off], "width", where=RECS))
        for pc in sorted(pcs, key=as_int):
            f06_specs.append(f"S={as_int(pc):08x}:{w}:{as_int(faddr):08x}")
            f06_spec_desc.append({"pc": pc, "field_address": faddr,
                                  "record_offset": f"0x{off:02X}",
                                  "registry_field": req(a_fields[off], "name", where=RECS),
                                  "width_bytes": w})
    if len(f06_specs) < 4:
        raise SystemExit("too few F06 overlay writer constraints could be derived; "
                         "the defeat trace no longer supports the pin")
    run_pin_probe(probe, F06_PIN, F06, ovl_region, f06_specs, images)
    f06pin = json.loads(E.repin(F06_PIN).read_text())

    # --- F14: literal encodings from the catalog + the live-verified slice hash
    f14_specs = [f"W={as_int(req(w, 'instruction_word', where=CAT)):08x}:"
                 f"{as_int(req(w, 'runtime_address', where=CAT)):08x}" for w in l08w]
    f14_specs.append(f"H={runtime_slice_sha}:{runtime_slice_len}:"
                     f"{as_int(runtime_slice_addr):08x}")
    run_pin_probe(probe, F14_PIN, F14, ovl_region, f14_specs, images)
    f14pin = json.loads(E.repin(F14_PIN).read_text())

    for scope, pin, pinrel, ncons in ((F06, f06pin, F06_PIN, len(f06_specs)),
                                      (F14, f14pin, F14_PIN, len(f14_specs))):
        E.fact(scope, "overlay_pin_spec_count", ncons, pinrel)
        E.fact(scope, "overlay_pin_images_scanned", req(pin, "files_scanned", where=pinrel),
               pinrel)
        E.fact(scope, "overlay_pin_images_satisfying",
               req(pin, "files_satisfying_every_spec", where=pinrel), pinrel)
        E.fact(scope, "overlay_pin_images_with_consistent_base",
               req(pin, "files_with_one_consistent_load_base", where=pinrel), pinrel)
        E.fact(scope, "overlay_pin_unique", req(pin, "unique_pin", where=pinrel), pinrel)
        E.fact(scope, "overlay_pin_file", req(pin, "unique_pin_file", where=pinrel), pinrel)
        E.fact(scope, "overlay_pin_load_base",
               req(pin, "unique_pin_load_base", where=pinrel), pinrel)
        E.fact(scope, "overlay_pin_result", req(pin, "result", where=pinrel), pinrel)
        if not req(pin, "unique_pin", where=pinrel):
            raise SystemExit(f"{scope}: the overlay pin is NOT unique "
                             f"({req(pin, 'result', where=pinrel)}) -- this assessment's "
                             "overlay-owner facts must not be published as settled")
        pf = next((f for f in req(pin, "files", where=pinrel)
                   if f["path"].endswith(req(pin, "unique_pin_file", where=pinrel)
                                         .split("/")[-1])), None)
        if pf is None:
            raise SystemExit(f"STALE CITATION: {pinrel} names a pin file absent from its "
                             "own list")
        E.fact(scope, "overlay_pin_file_sha256", req(pf, "sha256", where=pinrel), pinrel)
        E.fact(scope, "overlay_pin_file_size", req(pf, "size", where=pinrel), pinrel)
        pin_name = Path(req(pin, "unique_pin_file", where=pinrel)).stem
        E.fact(scope, "overlay_pin_overlay_name", pin_name, pinrel)
        E.fact(scope, "overlay_pin_agrees_with_census_name",
               pin_name == E.facts[scope]["census_overlay_name"], [pinrel, CENSUS])

    # the F06 probe additionally reports which writers are absolute-form
    pinned_f06 = next(f for f in req(f06pin, "files", where=F06_PIN)
                      if f["path"].endswith(Path(A["overlay_pin_file"]).name))
    E.fact(F06, "absolute_form_writers",
           sum(1 for r in req(pinned_f06, "spec_results", where=F06_PIN)
               if r.get("absolute_form")), F06_PIN)
    E.fact(F06, "overlay_writer_decodes",
           [{"pc": r["pc"], "op": r.get("op"), "imm": r.get("imm")}
            for r in req(pinned_f06, "spec_results", where=F06_PIN)], F06_PIN)
    E.fact(F06, "overlay_writer_spec_derivation", f06_spec_desc, [D17D, RECS])
    E.fact(F14, "overlay_pin_agrees_with_collision_container",
           Path(B["overlay_pin_file"]).stem.split("_")[0]
           == B["collision_container"].split("/")[0], [F14_PIN, E02])
    E.fact(F14, "overlay_pin_contradicts_retained_static_overlays",
           Path(B["overlay_pin_file"]).stem not in B["retained_static_overlays"],
           [F14_PIN, C16F])

    # how ambiguous WAS each address before the byte pin?
    for scope, pcs in ((F06, [as_int(p) for p in A["defeat_overlay_writer_pc_list"]]),
                       (F14, [as_int(runtime_slice_addr)]
                             + [as_int(req(w, "runtime_address", where=CAT)) for w in l08w])):
        cover = []
        for a in pcs:
            cover.append(len({f["overlay"] for f in fns
                              if f.get("space") == "overlay"
                              and as_int(f["start"]) <= a < as_int(f["end"])}))
        E.fact(scope, "overlay_images_covering_governing_pcs_max", max(cover), FN)
        E.fact(scope, "overlay_images_covering_governing_pcs_min", min(cover), FN)

    # ------------------------------------------------------------------ #
    # 8. source closure -- BOTH registries, per row                       #
    # ------------------------------------------------------------------ #
    governing = {
        F06: {f"writer_{pc}": as_int(pc) for pc in all_writers},
        F14: {
            "overlay_initializer": as_int(runtime_slice_addr),
            "resident_entry_call": as_int(req(l08, "static_resident_entry_call_sites", 0,
                                              where=CAT)),
            "actor_callback": as_int(req(ao, "callback", where=C16F)),
            "damage_call_site": as_int(req(c16, "exact_invocation", "entry",
                                           "link_call_address", where=C16F)),
            "damage_entry": as_int(req(c16, "exact_invocation", "entry", "pc", where=C16F)),
            "returned_to": as_int(req(c16, "exact_invocation", "returned_to", where=C16F)),
        },
    }
    for w in l08w:
        governing[F14][f"init_store_{req(w, 'runtime_address', where=CAT)}"] = \
            as_int(req(w, "runtime_address", where=CAT))

    for scope in (F06, F14):
        g = governing[scope]
        ovl_name = E.facts[scope]["overlay_pin_overlay_name"]
        ovl_end = ovl_region + int(E.facts[scope]["overlay_pin_file_size"])
        resident = {n: a for n, a in g.items() if not (ovl_region <= a < ovl_end)}
        overlay = {n: a for n, a in g.items() if ovl_region <= a < ovl_end}
        resolved: dict[str, list[str]] = {}
        unresolved: list[str] = []
        for n, a in resident.items():
            src = next((s for lo, hi, s in units if lo <= a < hi), None)
            (resolved.setdefault(src, []).append(n) if src else unresolved.append(n))
        srcs = [CAT, C16F] if scope == F14 else [D17D]
        E.fact(scope, "governing_addresses", len(g), srcs)
        E.fact(scope, "governing_resident", len(resident), srcs + [OVLY])
        E.fact(scope, "governing_overlay", len(overlay), srcs + [OVLY])
        E.fact(scope, "governing_resident_in_a_build_unit",
               len(resident) - len(unresolved), SEG)
        E.fact(scope, "governing_resident_units", len(resolved), SEG)
        E.fact(scope, "governing_resident_units_matching_c",
               len([s for s in resolved if s.startswith("src/")]), SEG)
        E.fact(scope, "governing_resident_units_hand_asm",
               len([s for s in resolved if s.startswith("asm/")]), SEG)
        E.fact(scope, "governing_resident_unit_sources", sorted(resolved), SEG)
        E.fact(scope, "governing_resident_outside_any_build_unit", len(unresolved), SEG)
        E.fact(scope, "overlay_registered_in_overlays_yml",
               "IS" if ovl_name in ovly_reg else "is NOT", OVLY)
        E.fact(scope, "pinned_overlay_code_functions",
               req(per_ovl, ovl_name, where=OVLD), OVLD)
        matched = [r for r in req(ovld, "results", where=OVLD) if r["overlay"] == ovl_name]
        E.fact(scope, "pinned_overlay_matched_functions",
               sum(req(r, "matched_functions", where=OVLD) for r in matched), OVLD)
        E.fact(scope, "confirmed_sites_for_row",
               sum(1 for a in g.values() if a in site_addrs), [SITES] + srcs)
        E.fact(scope, "overlay_state_addresses_registered",
               sum(1 for a in g.values() if ovl_region <= a and a in sem_addrs),
               [SEM] + srcs)
        # defect (b): is any semantic-registry entry keyed INSIDE this row's own
        # overlay load window? Measured, never asserted from inspection.
        collide = sorted(f"0x{a:08X}={i}" for a, i in sem_addrs.items()
                         if ovl_region <= a < ovl_end)
        E.fact(scope, "semantic_entries_inside_this_rows_overlay_window", collide,
               [SEM, OVLY, F06_PIN if scope == F06 else F14_PIN])
        E.fact(scope, "va_collision_present_in_this_rows_window", bool(collide),
               [SEM, OVLY, F06_PIN if scope == F06 else F14_PIN])

    # actor-record containment, per row, from each row's own record address
    A_rec = as_int(A["boss_record_addr"])
    E.fact(F06, "boss_record_inside_declared_extent",
           a_base <= A_rec < a_base + a_size * a_inst, [RECS, D17D])
    E.fact(F06, "row_named_actor_offsets_total", len(by_field), D17D)
    E.fact(F06, "row_named_actor_offsets_typed",
           sum(1 for f in by_field if (as_int(f) - A_rec) in a_fields), [RECS, D17D])
    boss_blurb = req(d17, "TWO_DISTINCT_BIRD_MANIFESTATIONS_2026-08-02",
                     "combat_actor_id30", where=D17B)
    boss_id = re.search(r"id=(\d+)", boss_blurb)
    if not boss_id:
        raise SystemExit(f"STALE CITATION: {D17B} no longer names the combat actor's id")
    E.fact(F06, "boss_actor_id", int(boss_id.group(1)), D17B)
    E.fact(F06, "actor_hp_note_names_this_boss",
           "bird" in S["actor_hp_field_note"].lower()
           or boss_id.group(1) in S["actor_hp_field_note"], [RECS, D17B])
    B_rec = as_int(B["actor_record_addr"])
    E.fact(F14, "actor_inside_declared_extent",
           a_base <= B_rec < a_base + a_size * a_inst, [RECS, C16F])
    E.fact(F14, "actor_index_from_declared_base", (B_rec - a_base) // a_size, [RECS, C16F])
    implied_pool_base = B_rec - int(B["actor_pool_slot_claimed"]) * a_size
    E.fact(F14, "actor_pool_base_implied", f"0x{implied_pool_base:08X}", [RECS, C16F])
    E.fact(F14, "declared_base_minus_implied_strides",
           (a_base - implied_pool_base) // a_size, [RECS, C16F])

    # ------------------------------------------------------------------ #
    # 9. the fixture corpus, keyed on STAGE ORDINAL tokens (with traps)   #
    # ------------------------------------------------------------------ #
    def corpus(strict: str, wider: str | None, other_stage: str | None):
        strict_set = sorted(k for k in movies if re.search(strict, k, re.I))
        wide_set = sorted(k for k in movies if wider and re.search(wider, k, re.I))
        other = sorted(k for k in wide_set if other_stage
                       and re.search(other_stage, k, re.I))
        return strict_set, [k for k in wide_set if k not in other], other

    f06_strict, f06_wide, f06_other = corpus(r"LEVEL06|birdnest", r"bird|D17",
                                             r"cliffside|LEVEL04")
    E.fact(F06, "stage_movies_pinned_strict", len(f06_strict), AUDIT)
    E.fact(F06, "stage_movies_pinned_strict_paths", f06_strict, AUDIT)
    E.fact(F06, "bird_movies_pinned_other_tokens", len(f06_wide), AUDIT)
    E.fact(F06, "bird_movies_belonging_to_another_stage", f06_other, AUDIT)
    f06_declared = set(f.split(" (")[0] for f in A["declared_fixtures"])
    E.fact(F06, "stage_movies_declared_strict",
           len([k for k in f06_strict if k in f06_declared]), [AUDIT, BASE])
    f06_replayed = sorted({A["defeat_movie"]} | {k for k in f06_strict + f06_wide
                                                 if k in f06_declared})
    E.fact(F06, "stage_movies_replayed_by_row", len(f06_replayed), [AUDIT, BASE, D17D])
    E.fact(F06, "stage_movies_never_replayed",
           sorted(set(f06_strict) - set(f06_replayed)), [AUDIT, BASE, D17D])
    hp_movie = next((k for k in f06_strict if "100%" in k), None)
    if hp_movie is None:
        raise SystemExit("STALE CITATION: the pinned 100% stage-6 movie has disappeared")
    E.fact(F06, "hundred_pct_movie_credited_to_row",
           f"mechanics:{F06}" in req(fx_entries, hp_movie, "consumers", where=FIXSET),
           FIXSET)

    f14_strict, f14_wide, _ = corpus(r"LEVEL14|riverbedflight", r"riverbed", None)
    E.fact(F14, "stage_movies_pinned_strict", len(f14_strict), AUDIT)
    E.fact(F14, "stage_movies_pinned_strict_paths", f14_strict, AUDIT)
    E.fact(F14, "largest_stage_movie_frames",
           max(req(movies, k, "frames", where=AUDIT) for k in f14_strict), AUDIT)
    E.fact(F14, "riverbed_movies_belonging_to_another_row",
           len([k for k in f14_wide if k not in f14_strict]), AUDIT)
    E.fact(F14, "stage_movies_replayed_by_row", 0, [AUDIT, BASE])
    E.fact(F14, "stage_movies_never_replayed", f14_strict, [AUDIT, BASE])

    # ------------------------------------------------------------------ #
    # 10. declarative scenarios + registered gates, per row               #
    # ------------------------------------------------------------------ #
    SCEN = "tools/scenarios/duckstation"
    scen_dir = ROOT / SCEN
    if not scen_dir.is_dir():
        raise SystemExit(f"STALE CITATION: {SCEN} is not a directory")
    scen_match = {
        F06: re.compile(r"stage06_birdnest|birdnest", re.I),
        F14: re.compile(r"stage14_riverbed_flight|riverbed_flight|scene8_level08", re.I),
    }
    for scope, pat in scen_match.items():
        rel = [f"{SCEN}/{p.name}" for p in sorted(scen_dir.glob("*.yaml"))
               if pat.search(p.name)]
        if not rel:
            raise SystemExit(f"STALE CITATION: {SCEN} no longer holds a scenario for {scope}")
        for r in rel:
            E.pin(r)
        E.fact(scope, "declarative_scenarios", len(rel), rel)
        E.fact(scope, "declarative_scenario_names", [Path(p).name for p in rel], rel)
        ident = [p for p in rel if "stage_identity" in p]
        behav = [p for p in rel if "stage_identity" not in p]
        E.fact(scope, "identity_scenario_assertions",
               sum(len(ph.get("assertions", []))
                   for p in ident
                   for ph in yaml.safe_load((ROOT / p).read_text())["phases"]), ident or rel)
        E.fact(scope, "behavioural_scenarios", len(behav), rel)
        E.fact(scope, "behavioural_scenario_names", [Path(p).name for p in behav],
               behav or rel)
        E.fact(scope, "scenario_names", [Path(p).name for p in rel], rel)
        E.fact(scope, "scenario_assertions",
               sum(len(ph.get("assertions", []))
                   for p in rel
                   for ph in yaml.safe_load((ROOT / p).read_text())["phases"]), rel)

    own_artifacts = {F06: [F06ART], F14: []}
    inherited_artifacts = {F06: [D17B, D17D], F14: [C16F, CAT]}
    for scope in (F06, F14):
        og = gate_files_for(own_artifacts[scope]) if own_artifacts[scope] else []
        if own_artifacts[scope] and not og:
            raise SystemExit(f"{scope}: no registered gate references its own artifact "
                             f"{own_artifacts[scope]} -- the gate set this assessment "
                             "measures has disappeared")
        ig = [g for g in gate_files_for(inherited_artifacts[scope]) if g not in og]
        if not ig:
            raise SystemExit(f"{scope}: no registered gate references its inherited "
                             f"artifacts {inherited_artifacts[scope]}")
        for g in og + ig:
            E.pin(g)
        E.fact(scope, "own_gate_files", len(og), og or [CENSUS])
        E.fact(scope, "own_gate_file_names", og, og or [CENSUS])
        E.fact(scope, "inherited_gate_files", len(ig), ig)
        E.fact(scope, "inherited_gate_file_names", ig, ig)
        if args.no_gates:
            for k in ("own_gate_tests_passed", "own_gate_tests_failed",
                      "inherited_gate_tests_passed", "inherited_gate_tests_failed"):
                E.fact(scope, k, None, og + ig or [CENSUS])
            E.fact(scope, "inherited_gate_files_with_a_failure", None, og + ig or [CENSUS])
            E.fact(scope, "gates_executed", False, og + ig or [CENSUS])
            E.fact(scope, "own_gate_health",
                   f"this row's {len(og)} own gate file(s) were NOT executed for this run "
                   f"(--no-gates), so their health is unmeasured here", og or [CENSUS])
            E.fact(scope, "inherited_gate_health",
                   f"this row's {len(ig)} inherited gate file(s) were NOT executed for this "
                   f"run (--no-gates), so their health is unmeasured here", ig)
        else:
            E.fact(scope, "gates_executed", True, og + ig or [CENSUS])
            if og:
                p, f, _ = run_gates(og)
            else:
                p, f = 0, 0
            E.fact(scope, "own_gate_tests_passed", p, og or [CENSUS])
            E.fact(scope, "own_gate_tests_failed", f, og or [CENSUS])
            E.fact(scope, "own_gate_health",
                   (f"{f} of {p + f} tests in this row's {len(og)} OWN gate file(s) fail "
                    f"today" if og else
                    "this row has NO gate file of its own -- no registered test references "
                    "an artifact this row owns"), og or [CENSUS])
            p2, f2, names = run_gates(ig)
            E.fact(scope, "inherited_gate_tests_passed", p2, ig)
            E.fact(scope, "inherited_gate_tests_failed", f2, ig)
            E.fact(scope, "inherited_gate_files_with_a_failure", names, ig)
            E.fact(scope, "inherited_gate_health",
                   f"{f2} of {p2 + f2} tests in the {len(ig)} INHERITED gate file(s) fail "
                   f"today" + (f", in {names}" if names else ""), ig)

    # ------------------------------------------------------------------ #
    # 11. CROSS-CHECK: F06's registered banner reading vs the C05 proof   #
    # ------------------------------------------------------------------ #
    C05 = "analysis/phase4_c05_three_tokens.json"
    c05 = E.json(C05)
    ev = req(c05, "RESULTS_SCREEN_EVALUATOR_FOUND_2026-08-04", where=C05)
    an = req(c05, "COUNTER_ANIMATION_CLOSED_2026-08-04", where=C05)
    E.fact(F06, "c05_results_function", req(ev, "what_it_actually_is", where=C05)[:90], C05)
    E.fact(F06, "c05_third_axis_condition",
           req(ev, "the_three_conditions_proven_by_construction", "enemies", where=C05),
           C05)
    E.fact(F06, "c05_third_numerator_law",
           req(an, "three_numerators", "enemies", where=C05), C05)
    E.fact(F06, "c05_grain_denominator_is_universal",
           req(an, "grain_denominator_is_universal", where=C05)[:200], C05)
    E.fact(F06, "c05_used_this_rows_fixture",
           any(k in req(ev, "live_method", where=C05) for k in f06_strict), [C05, AUDIT])
    E.fact(F06, "c05_explicitly_replaces_the_seed_reading",
           "seed" in req(ev, "the_three_conditions_proven_by_construction",
                         "significance", where=C05).lower(), C05)
    ident_scen = f"{SCEN}/stage_identity_stage06_birdnest.yaml"
    E.pin(ident_scen)
    quota_assert = next(
        (a for ph in yaml.safe_load((ROOT / ident_scen).read_text())["phases"]
         for a in ph.get("assertions", []) if a["id"].endswith("enemy_quota")), None)
    if quota_assert is None:
        raise SystemExit("STALE CITATION: the stage-6 identity scenario no longer asserts "
                         "the enemy quota")
    E.fact(F06, "enemy_quota_at_pinned_anchor", req(quota_assert, "expected", where=ident_scen),
           ident_scen)
    E.fact(F06, "enemy_quota_address_matches_c05_condition",
           f"0x{req(quota_assert, 'address', where=ident_scen):08X}".lower()
           in A["c05_third_axis_condition"].lower(), [ident_scen, C05])
    E.fact(F06, "banner_third_denominator_matches_enemy_quota",
           str(A["enemy_quota_at_pinned_anchor"]) in A["banner_reading_registered"]
           and A["enemy_quota_at_pinned_anchor"]
           == A["completion_oracle_enemy_quota_in_stage"],
           [F06ART, ident_scen, ORACLE])

    CANON = "ObsidianVault/Canon/Functions/FUNC_800B7DA0_results_screen_evaluate_and_draw.md"
    canon = E.text(CANON)
    E.fact(F06, "canon_banks_the_enemy_axis",
           "third axis is enemies" in canon.lower(), CANON)
    SYS = "ObsidianVault/Canon/Systems/SYS_bird_boss.md"
    sysdoc = E.text(SYS)
    E.fact(F06, "canon_system_page_is_the_d_row",
           "D17_bird" in sysdoc and "F06" in sysdoc, SYS)
    E.fact(F06, "canon_system_page_sections", len(re.findall(r"^#{2,3} ", sysdoc, re.M)), SYS)
    EXP = "ObsidianVault/Experiments/EXP_2026-08-03_phase4_f06_birdnest.md"
    exp = E.text(EXP)
    E.fact(F06, "row_experiment_page_sections", len(re.findall(r"^#{2,3} ", exp, re.M)), EXP)
    E.fact(F06, "row_experiment_page_still_calls_the_counter_a_seed_total",
           "seed-token" in exp, EXP)

    # ------------------------------------------------------------------ #
    # 12. build the two scorecards -- each sees ONLY its own facts        #
    # ------------------------------------------------------------------ #
    dims = {F06: build_f06_dims(A, S), F14: build_f14_dims(B, S)}
    counts = {}
    for scope, d in dims.items():
        c: dict[str, int] = {}
        for v in d.values():
            c[v["state"]] = c.get(v["state"], 0) + 1
        if len(d) != 9:
            raise SystemExit(f"{scope}: {len(d)} dimensions scored, expected 9")
        counts[scope] = c

    def summarize(scope):
        c = counts[scope]
        return (f"{c.get('met', 0)} met, {c.get('met_candidate', 0)} met-candidate, "
                f"{c.get('partial', 0)} partial, {c.get('not_met', 0)} not met, "
                f"{c.get('unmeasured', 0)} unmeasured")

    if args.no_probe_suite:
        probes = None
    else:
        probes = fail_loud_probes(Path("/tmp/abl_f06_f14_failloud"))
        if not all(p["failed_loudly"] for p in probes):
            raise SystemExit(
                "a fail-loud path did NOT fail loudly: "
                f"{[p['probe'] for p in probes if not p['failed_loudly']]} -- this "
                "assessment's staleness guarantee is not real, so it must not be published")

    doc = {
        "_comment": "F06_birdnest and F14_riverbed_flight measured against the nine DoD "
                    "dimensions AS WRITTEN (item 2 = enumerated; residuals = explicitly "
                    "bounded), per engineering-specs/phase4-measurement-standard-ruling.md. "
                    "TWO separate scorecards: facts live in per-row namespaces and each "
                    "row's judgments are built from its own facts plus a shared set only. "
                    "Judgments authored; every fact derived from a pinned artifact at run "
                    "time. Regenerate: tools/phase4_f06_f14_written_bar_assessment.py",
        "schema": "abl-phase4-f06-f14-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "rows_assessed": [F06, F14],
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
            "author_conflict": "the assessor authored neither row's underlying evidence, but "
                               "did author this assessment and BOTH new measurements in it "
                               "(tools/phase4_f06_f14_overlay_pin.c and the necessary "
                               "conditions handed to it), so on the overlay-owner question "
                               "the tool, the claim and the judgment share an author. Every "
                               "state below is a submission to a fresh detached verifier, "
                               "not a promotion; `partial` and `not_met` are as challengeable "
                               "as `met`.",
            "reads_only": ["analysis/mechanics_baseline.yaml"],
        },
        "row_separation": {
            "mechanism": "facts are namespaced per row; build_f06_dims() and "
                         "build_f14_dims() each receive only their own fact dict plus the "
                         "shared one, so citing the other row's evidence would raise "
                         "NameError rather than quietly cross-credit",
            "shared_facts": sorted(S),
            "d_row_discipline": "D17_bird's closure, C16's contact-death closure and C15's "
                                "respawn-writer census are recorded as INHERITED. None of "
                                "them is read as evidence for a stage row's own objective, "
                                "entry or exit claims.",
        },
        "row_mapping": {
            "note": "`stages` in the baseline is the stage ORDINAL, not a scene id. The "
                    "campaign progression table maps ordinal -> scene, and the scene -> "
                    "disc directory is arithmetic. Every step is derived here, never "
                    "assumed, and cross-checked against the census and the corrected "
                    "binding.",
            "progression_table_source": S["progression_table_source"],
            "progression_table": S["progression_table"],
            F06: {"stage_ordinal": A["stage_ordinal_from_baseline"],
                  "scene_from_progression_table": A["scene_from_progression_table"],
                  "census_scene_id": A["scene_id"],
                  "corrected_binding": A["scene_binding_truth"],
                  "collision_container": A["collision_container"],
                  "overlay_pinned_from_bytes": A["overlay_pin_file"],
                  "agrees_three_ways": A["row_mapping_agrees_three_ways"]},
            F14: {"stage_ordinal": B["stage_ordinal_from_baseline"],
                  "scene_from_progression_table": B["scene_from_progression_table"],
                  "census_scene_id": B["scene_id"],
                  "corrected_binding": B["scene_binding_truth"],
                  "collision_container": B["collision_container"],
                  "overlay_pinned_from_bytes": B["overlay_pin_file"],
                  "agrees_three_ways": B["row_mapping_agrees_three_ways"]},
        },
        "carried_forward": {
            "dimension": "durable_evidence",
            "from": CENSUS,
            F06: {"state": A["census_durable_state"], "fraction": A["census_durable_fraction"]},
            F14: {"state": B["census_durable_state"], "fraction": B["census_durable_fraction"]},
            "note": "measured there against pinned bytes; re-deriving it here would be a "
                    "second opinion on a settled measurement, not evidence",
        },
        "systemic_defects_checked": {
            "a_overlay_misattribution": {
                "defect": "every per-level overlay loads at the same base, so an overlay "
                          "address decodes to a valid instruction in most images and an "
                          "address-keyed registry picks the wrong file",
                F06: {
                    "affected": True,
                    "how": "the row's six governing writers are overlay PCs ambiguous across "
                           f"up to {A['overlay_images_covering_governing_pcs_max']} of "
                           f"{S['overlay_images_in_function_census']} censused images; no "
                           "artifact in the repository pinned the owning FILE, and the "
                           "ownership graph attributes ZERO overlay functions to the row "
                           "(non-attribution rather than misattribution)",
                    "settled_here": f"{A['overlay_pin_file']} @ {A['overlay_pin_load_base']} "
                                    f"({A['overlay_pin_result']}), agreeing with the census's "
                                    f"declared overlay ({A['overlay_pin_agrees_with_census_name']})",
                },
                F14: {
                    "affected": True,
                    "how": "the retained runtime artifact's own static scene graph names "
                           f"overlays {B['retained_static_overlays']} for this scene -- the "
                           "pre-correction routing -- while its catalog half names a "
                           "different file; the addresses are ambiguous across up to "
                           f"{B['overlay_images_covering_governing_pcs_max']} images",
                    "settled_here": f"{B['overlay_pin_file']} @ {B['overlay_pin_load_base']} "
                                    f"({B['overlay_pin_result']}); contradicts the retained "
                                    f"static overlays "
                                    f"({B['overlay_pin_contradicts_retained_static_overlays']}) "
                                    f"and agrees with the collision census container "
                                    f"({B['overlay_pin_agrees_with_collision_container']})",
                },
            },
            "b_semantic_registry_va_collision": {
                "defect": "config/semantic_state.yaml keys overlay-local addresses globally, "
                          "so a training-overlay entry can appear to own another level's word",
                "entries_inside_any_overlay_window": S["semantic_state_overlay_window_entries"],
                F06: {
                    "affected": A["va_collision_present_in_this_rows_window"],
                    "how": f"measured, not inspected: "
                           f"{len(A['semantic_entries_inside_this_rows_overlay_window'])} "
                           f"registry entries fall inside this row's byte-pinned overlay "
                           f"window ({A['overlay_pin_file_size']} bytes from "
                           f"{A['overlay_pin_load_base']}) "
                           f"-- {A['semantic_entries_inside_this_rows_overlay_window']}. The "
                           f"row itself registers "
                           f"{A['overlay_state_addresses_registered']} overlay addresses, so "
                           f"the exposure here is NON-registration, not collision",
                },
                F14: {
                    "affected": B["va_collision_present_in_this_rows_window"],
                    "how": f"measured, not inspected: "
                           f"{len(B['semantic_entries_inside_this_rows_overlay_window'])} "
                           f"registry entries fall inside this row's byte-pinned overlay "
                           f"window ({B['overlay_pin_file_size']} bytes from "
                           f"{B['overlay_pin_load_base']}) "
                           f"-- {B['semantic_entries_inside_this_rows_overlay_window']}. The "
                           f"row itself registers "
                           f"{B['overlay_state_addresses_registered']} overlay addresses",
                },
                "standing_hazard": "both rows are one registration away from the collision: "
                                   "any future entry keyed by bare VA inside 0x800B39A0+ "
                                   "would land in 20 overlays at once",
            },
        },
        "registry_disposition_for_contrast": {
            "source": DEBT,
            F06: {"completion_state": A["registry_completion_state"],
                  "dimensions_met": A["registry_dimensions_met"],
                  "dimensions_remaining": A["registry_dimensions_remaining"],
                  "distinct_basis_strings": A["registry_distinct_bases"],
                  "movie_count": A["registry_movie_count"]},
            F14: {"completion_state": B["registry_completion_state"],
                  "dimensions_met": B["registry_dimensions_met"],
                  "dimensions_remaining": B["registry_dimensions_remaining"],
                  "distinct_basis_strings": B["registry_distinct_bases"],
                  "movie_count": B["registry_movie_count"]},
            "note": "both rows carry ONE blanket basis across all nine dimensions and score "
                    "0/9. That is a disposition, not a measurement.",
        },
        "fail_loud_probes": {
            "note": "the staleness guarantee is PROVEN here, not asserted: each probe "
                    "rebuilds a read-only mirror of the repository with one artifact "
                    "deleted or one key removed, re-runs this tool inside it, and requires "
                    "a non-zero exit carrying the expected message. The run aborts if any "
                    "probe fails to fail.",
            "executed": probes is not None,
            "results": probes,
        },
        "fact_provenance": {
            "facts_total": sum(len(v) for v in E.facts.values()),
            "facts_derived_from_pinned_artifacts": sum(len(v) for v in E.provenance.values()),
            "facts_hand_typed": sum(len(v) for v in E.facts.values())
                                - sum(len(v) for v in E.provenance.values()),
            "rule": "facts are recorded through fact(scope, key, value, source); a value "
                    "cannot be stored without naming a pinned artifact, and every lookup is "
                    "strict, so a renamed or removed key aborts the run instead of silently "
                    "defaulting",
            "by_scope": {k: len(v) for k, v in E.facts.items()},
            "by_fact": E.provenance,
        },
        "facts": E.facts,
        "evidence_pins": E.pins,
        "rows": {
            F06: {
                "row_name": A["row_name"],
                "registry_status": A["row_status"],
                "stage_ordinal": A["census_stage_ordinal"],
                "scene_id": A["scene_id"],
                "overlay_pinned_from_bytes": A["overlay_pin_file"],
                "dimensions": dims[F06],
                "counts": counts[F06],
                "summary": f"{summarize(F06)} -- against the WRITTEN bars. The bird is the "
                           f"best-evidenced object in this row and it belongs to D17: an "
                           f"untruncated natural-replay write log that attributes every "
                           f"field write to a PC. What F06 owns as a STAGE -- entry, the "
                           f"objective's own producer, the results banner, re-engagement, "
                           f"the entry FMV -- is where every gap sits, and one registered "
                           f"stage claim is falsified by a later row (see notable).",
            },
            F14: {
                "row_name": B["row_name"],
                "registry_status": B["row_status"],
                "stage_ordinal": B["census_stage_ordinal"],
                "scene_id": B["scene_id"],
                "overlay_pinned_from_bytes": B["overlay_pin_file"],
                "dimensions": dims[F14],
                "counts": counts[F14],
                "summary": f"{summarize(F14)} -- against the WRITTEN bars. The registry "
                           f"calls this row `external_lead` with the thinnest entry of any F "
                           f"row, and that under-describes what exists in its scene: a "
                           f"natural pristine-anchor death with a single-bit causal control, "
                           f"a registered behavioural scenario, an instruction-level "
                           f"resident->overlay call and an exhaustive 11-image static census. "
                           f"None of it is about flight, companion or chase -- the row's own "
                           f"entire subject -- and the artifacts that carry it forbid the "
                           f"generalisation and fail their gates today.",
            },
        },
        "notable": [
            f"F06's REGISTERED RESULTS-BANNER READING IS FALSIFIED, and by a row that used "
            f"F06's own fixture. The baseline binding says the third counter '00/09' is 'this "
            f"level's own seed-token total' "
            f"(claims_seed_tokens={A['banner_claims_seed_tokens']}). One day later C05 found "
            f"the renderer ({A['c05_results_function']}) by replaying THIS row's 100% movie "
            f"(used_this_rows_fixture={A['c05_used_this_rows_fixture']}) and proved the third "
            f"axis is ENEMIES by the condition itself: '{A['c05_third_axis_condition']}', "
            f"numerator '{A['c05_third_numerator_law']}'. Two independent pinned anchors put "
            f"this stage's enemy quota at {A['enemy_quota_at_pinned_anchor']} (the stage-6 "
            f"identity scenario and the completion oracle's in-stage snapshot, agreeing="
            f"{A['banner_third_denominator_matches_enemy_quota']}), and the quota address the "
            f"scenario asserts is the same address C05's condition tests "
            f"({A['enemy_quota_address_matches_c05_condition']}). C05 also shows the '/50' is "
            f"a hardcoded literal on every level, so the row's corollary that 'seed-token "
            f"targets are level-specific' has no subject. Canon already banks the enemy axis "
            f"({A['canon_banks_the_enemy_axis']}); the baseline row and this row's experiment "
            f"page do not (page still says seed-token="
            f"{A['row_experiment_page_still_calls_the_counter_a_seed_total']}).",

            f"F06'S EXIT CANNOT BE THE REGION-CODE TRIGGER. The disc-side collision census "
            f"gives this stage {A['authored_collision_sectors']} authored sectors with "
            f"histogram {A['region_code_histogram']} -- not one non-zero region code, against "
            f"{S['e02_disc_runtime_disagreements']} disc-vs-runtime disagreements over "
            f"{S['e02_authored_sectors_compared']} sectors campaign-wide. F14 is the mirror "
            f"image: {B['authored_collision_sectors']} authored sectors with exactly "
            f"{B['region_code_sector_count']} code-{B.get('exit_region_code')} sector at index "
            f"{B.get('exit_region_sector_index')}, runtime origin "
            f"{B.get('exit_region_runtime_origin')}. Neither row records either fact, and for "
            f"F14 it is the single cheapest lead in the row.",

            f"BOTH OVERLAY OWNERS WERE UNPINNED AND ARE NOW PINNED FROM BYTES. F06's writers "
            f"decode to real instructions in up to "
            f"{A['overlay_images_covering_governing_pcs_max']} images; the probe leaves "
            f"{A['overlay_pin_images_satisfying']} standing ({A['overlay_pin_file']}, sha256 "
            f"{A['overlay_pin_file_sha256'][:12]}...). F14's initializer address is ambiguous "
            f"across {B['overlay_images_covering_governing_pcs_max']}; the probe leaves "
            f"{B['overlay_pin_images_satisfying']} ({B['overlay_pin_file']}). The F06 result "
            f"also produced an interface fact nobody recorded: "
            f"{A['absolute_form_writers']} of {A['overlay_pin_spec_count']} overlay writers "
            f"are $at-absolute stores carrying the low half of the POOL ADDRESS, so that "
            f"overlay hard-codes the actor's slot instead of taking a pointer.",

            f"F14'S GATES FAIL BECAUSE THE PROJECT FIXED THE CLAIM, exactly the F09 pattern. "
            f"{B['inherited_gate_health']}; the recomputation reports the "
            f"routing now resolving to the corrected directory while the retained artifact "
            f"still stores '{B['retained_static_disc_dir']}' / "
            f"{B['retained_static_overlays']}. Both the corrected binding "
            f"({B['scene_binding_claimed']} -> {B['scene_binding_truth']}) and this "
            f"assessment's independent byte pin agree against the retained artifact. Not "
            f"evidence corruption -- but the row's regression surface is not protecting it.",

            f"THE CATALOG THAT SUPPLIES F14'S LOAD PHASE DOES NOT KNOW ITS OWN FINDING RAN. "
            f"It still records '{B['catalog_still_unknown']}' while the flight-death artifact "
            f"reports level08_respawn_initializer_live_qualified="
            f"{B['level08_initializer_live_qualified']} and this assessment confirms the "
            f"resident 108-byte slice hashes to the pinned file slice "
            f"({B['level08_slice_sha256_matches_runtime']}). One artifact is a fold-back away "
            f"from closing a named residual in another row.",

            f"BOTH ROWS IGNORE A FROM-BOOT ORACLE THAT ALREADY EXISTS. Stage 6: "
            f"{A['completion_oracle_movie']} ({A['completion_oracle_frames']} frames, enters "
            f"at {A['completion_oracle_entry_frame']}, exits by end="
            f"{A['completion_oracle_stage_exited']}, cited={A['completion_oracle_cited_by_row']}). "
            f"Stage 14: {B['completion_oracle_movie']} ({B['completion_oracle_frames']} "
            f"frames, cited={B['completion_oracle_cited_by_row']}). F14 additionally declares "
            f"{B['declared_movie_count']} movies while {B['stage_movies_pinned_strict']} "
            f"stage-14 movies are centrally pinned, one of them "
            f"{B['largest_stage_movie_frames']} frames long.",

            f"TOKEN TRAPS MEASURED, NOT ASSUMED. 'LEVELnn' means the STAGE ORDINAL in the "
            f"movie corpus but the SCENE-DERIVED DISC DIRECTORY on disc, so stage 6 lives in "
            f"{A['collision_container']} and stage 14 in {B['collision_container']}. The bare "
            f"token 'bird' pulls in {len(A['bird_movies_belonging_to_another_stage'])} movies "
            f"from another stage ({A['bird_movies_belonging_to_another_stage']}), and the "
            f"bare token 'riverbed' pulls in "
            f"{B['riverbed_movies_belonging_to_another_row']} movies belonging to "
            f"F05_riverbed_run. Any breadth count keyed on those tokens is wrong before it "
            f"starts.",

            f"UNMEASURED HERE, named so a verifier does not read silence as absence: (1) "
            f"whether C05's counter law actually EXPLAINS F06's static-zero banner is NOT "
            f"settled -- C05 supplies the instruction-level mechanism the row said it lacked, "
            f"but the specific check (read the enemy TOTAL 0x80082258 and the screen "
            f"countdown at the frames the row sampled) was not run here and needs a replay; "
            f"(2) whether the region-code-{B.get('exit_region_code')} sector is F14's stage "
            f"exit -- the shape matches the campaign's exit law but no run confirms it here; "
            f"(3) whether the {len(B['stage_movies_never_replayed'])} never-replayed stage-14 "
            f"routes would move campaign_breadth for F14 (that needs a replay, not a re-read); "
            f"(4) whether either row's overlay is a cheap byte-match candidate -- F14's "
            f"{B['level08_size']}-byte initializer is already decoded store by store, which "
            f"is suggestive, not measured.",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    for scope in (F06, F14):
        print(f"[written-bar {scope}] {summarize(scope)}")
        for name, d in dims[scope].items():
            print(f"  {d['state']:14s} {name}")
    fp = doc["fact_provenance"]
    print(f"facts: {fp['facts_derived_from_pinned_artifacts']} derived / "
          f"{fp['facts_hand_typed']} hand-typed  ({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
