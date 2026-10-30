#!/usr/bin/env python3
"""Measure F09_bug_bar's nine DoD dimensions against the bars AS WRITTEN.

Third test case for the uniform standard ruled in
`engineering-specs/phase4-measurement-standard-ruling.md`; the design copies
`tools/phase4_f01_written_bar_assessment.py` (the exemplar) and
`tools/phase4_f02_written_bar_assessment.py` (the first sibling). The WRITTEN
bars are:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant -- NOT
    "the unresolved set is empty" (that reading is the documented overshoot);
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "bounded-exhausted" is a STOP DECISION and never counts as met.

Why F09 next: it is the opposite shape to F02 again. F02 was a stage row whose
own subjects were half-answered. F09 is a stage row whose BOSS was driven to a
declared bounded-exhausted stop by a different row (D18) and whose ARENA is
owned by a third row (E11). The interesting question is what a D-row closure
does and does not do for the STAGE row that inherits it -- so this assessment
separates, per dimension, what D18/E11 prove about Thud and the arena from what
F09 must prove about the stage's own objective, entry/exit and layout.

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
`analysis/phase4_f_row_measured_census.json` (4/4 declared fixtures intact) and
is carried forward with its fraction, failing loudly if that measurement moves.

One measurement in this assessment is NEW rather than re-read. Every level
overlay loads at the same virtual address, so the row's fight-lane PCs name a
real instruction in ~18 different overlay images; the semantic ownership graph
resolves them to LEVEL03_LEVEL1 and the D18 artifacts to LEVEL04/LEVEL1.BIN.
`tools/phase4_f09_overlay_pin.c` (compiled C owns the instruction decoding)
settles it from bytes across every image, and this tool re-derives the
encodings it scanned from the pinned D18 artifacts so the C run cannot drift
away from the claims it is supposed to support.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a
fresh detached verifier.

Usage: python3 tools/phase4_f09_written_bar_assessment.py [--out PATH] [--no-gates]
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
ROW_ID = "F09_bug_bar"


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


def hexes(text: str) -> list[str]:
    return re.findall(r"0x[0-9A-Fa-f]{8}", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=str(ROOT / "analysis/phase4_f09_written_bar_assessment.json"))
    ap.add_argument("--no-gates", action="store_true",
                    help="skip executing this row's registered pytest gates")
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
    inv = req(crow, "evidence_inventory", where=CENSUS)
    E.fact("census_analysis_artifacts_credited",
           len(req(inv, "analysis_artifacts", where=CENSUS)), CENSUS)
    E.fact("census_source_files_credited", len(req(inv, "source_files", where=CENSUS)), CENSUS)
    E.fact("census_segments_entries", req(inv, "segments_entries", where=CENSUS), CENSUS)
    E.fact("census_vault_pages", req(inv, "vault_pages", where=CENSUS), CENSUS)

    fixtures = req(crow, "durable_evidence", "fixtures", where=CENSUS)
    in_repo = [f["path"] for f in fixtures if req(f, "kind", where=CENSUS) == "in_repo_artifact"]
    external = [f["path"] for f in fixtures if req(f, "kind", where=CENSUS) == "external_fixture"]
    E.fact("row_in_repo_artifacts", in_repo, CENSUS)
    E.fact("row_in_repo_artifact_count", len(in_repo), CENSUS)
    E.fact("row_external_fixtures", external, CENSUS)
    E.fact("row_in_repo_artifacts_git_tracked",
           sum(1 for f in fixtures
               if req(f, "kind", where=CENSUS) == "in_repo_artifact" and f.get("git_tracked")),
           CENSUS)
    if F["census_durable_state"] != "met":
        raise SystemExit("carried-forward durable_evidence is no longer 'met' -- "
                         "re-measure before reusing this assessment")

    # Independently confirm the census's git_tracked claim; a disagreement is loud.
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", *in_repo],
                             capture_output=True, text=True)
    if tracked.returncode != 0:
        raise SystemExit("census claims the in-repo artifacts are git-tracked; git disagrees: "
                         f"{tracked.stderr.strip()}")

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
    E.fact("row_binding_claims", len(req(row, "bindings", where=BASE)), BASE)
    E.fact("row_declared_fixtures", len(req(row, "fixture_have", where=BASE)), BASE)
    E.fact("row_declared_missing", req(row, "missing", where=BASE), BASE)
    E.fact("row_declared_fixture_need", req(row, "fixture_need", where=BASE), BASE)
    E.fact("row_declared_evidence_classes", req(row, "evidence", where=BASE), BASE)
    E.fact("row_declared_next", req(row, "next", where=BASE), BASE)
    E.fact("row_artifact_path_citations",
           len(set(re.findall(r"(?:analysis|tools|src|src_re|tests|config)/[\w./%-]+",
                              json.dumps(row)))), BASE)

    # Which OTHER baseline rows carry stage-9 evidence this row does not cite?
    # WARNING: the disc-directory token is ambiguous here exactly as "LEVEL02" was
    # for F02. Scene 14 (Bug Bar) loads from disc dir LEVEL04/ (LEVEL1.* variant),
    # and disc dir LEVEL04/ ALSO holds stage 7 City Entrance's LEVEL.* variant. So
    # match the STAGE/BOSS tokens and never the bare directory token.
    stage9 = re.compile(r"[Tt]hud|Bug Bar|bug_bar|scene 14|stage ?09|[Ss]tage 9")
    other = sorted(r["id"] for r in rows
                   if r.get("id") != ROW_ID and stage9.search(json.dumps(r)))
    E.fact("other_baseline_rows_naming_stage9", len(other), BASE)
    E.fact("other_baseline_rows_naming_stage9_ids", other, BASE)
    d18 = next((r for r in rows if r.get("id") == "D18_thud"), None)
    e11 = next((r for r in rows if r.get("id") == "E11_dynamic_geometry"), None)
    if d18 is None or e11 is None:
        raise SystemExit(f"STALE CITATION: {BASE} no longer carries D18_thud / "
                         "E11_dynamic_geometry, the two rows F09 inherits from")
    E.fact("d18_row_status", req(d18, "status", where=BASE), BASE)
    E.fact("d18_row_bindings", len(req(d18, "bindings", where=BASE)), BASE)
    E.fact("d18_row_missing", req(d18, "missing", where=BASE), BASE)
    E.fact("e11_row_status", req(e11, "status", where=BASE), BASE)
    E.fact("e11_row_missing", req(e11, "missing", where=BASE), BASE)
    E.fact("e11_row_fixture_need", req(e11, "fixture_need", where=BASE), BASE)
    E.fact("d18_row_records_prior_binding_falsified",
           any("FALSIFIED" in b for b in req(d18, "bindings", where=BASE)), BASE)

    # ------------------------------------------------------------------ #
    # 4. the row's own bound evidence: identity + retirement (Phase 3)    #
    # ------------------------------------------------------------------ #
    THUD3 = "analysis/phase3_thud.json"
    t3 = E.json(THUD3)
    bid = req(t3, "boss_identity", where=THUD3)
    E.fact("boss_record_addr", req(bid, "record_addr", where=THUD3), THUD3)
    E.fact("boss_actor_id", req(bid, "id", where=THUD3), THUD3)
    E.fact("boss_hp_at_load", req(bid, "hp_at_0x6e", where=THUD3), THUD3)
    E.fact("boss_live_table", req(bid, "live_table", where=THUD3), THUD3)
    E.fact("boss_vm_ip_recorded", req(bid, "mover_vm_ip_at_0x70", where=THUD3), THUD3)
    E.fact("boss_callback_0x7c", req(bid, "driver_cb_at_0x7c", where=THUD3), THUD3)
    E.fact("retirement_rule", req(t3, "defeat_threshold", "rule", where=THUD3), THUD3)
    retire_writes = req(t3, "retire_handler", "writes", where=THUD3)
    E.fact("retirement_writer_pcs", sorted(retire_writes), THUD3)
    alog = req(t3, "retire_handler", "access_log", where=THUD3)
    E.fact("retirement_log_events", req(alog, "total", where=THUD3), THUD3)
    E.fact("retirement_log_truncated", req(alog, "truncated", where=THUD3), THUD3)
    E.fact("retirement_log_watch_cap_saturated",
           req(alog, "watch_cap_saturated", where=THUD3), THUD3)
    E.fact("identity_method_is_injection",
           "poke-falsification" in req(t3, "_comment", where=THUD3), THUD3)
    E.fact("identity_media_pristine_verified",
           req(t3, "media_identity_after_connect", "hash_verification",
               "pristine_verified", where=THUD3), THUD3)
    E.fact("scene_id", req(t3, "authority", "scene_id", where=THUD3), THUD3)

    # ------------------------------------------------------------------ #
    # 5. the FSM negative and the fight law (D18, shared with F09)        #
    # ------------------------------------------------------------------ #
    FSM = "analysis/phase4_d18_thud_vm_fsm.json"
    fsm = E.json(FSM)
    replay = req(fsm, "FIGHT_REPLAY_POLL_ONLY_2026-08-03", where=FSM)
    E.fact("fsm_programs_decoded", len(req(fsm, "programs", where=FSM)), FSM)
    E.fact("fsm_replay_ip_values_seen", len(req(replay, "ip_histogram", where=FSM)), FSM)
    E.fact("fsm_replay_ip_samples", sum(req(replay, "ip_histogram", where=FSM).values()), FSM)
    E.fact("fsm_replay_is_poll_only",
           "POLL ONLY" in req(replay, "method", where=FSM), FSM)
    E.fact("fsm_verdict", req(fsm, "CONCLUSION", "fsm_verdict", where=FSM), FSM)
    E.fact("fsm_named_reopeners", len(req(fsm, "CONCLUSION", "named_reopeners", where=FSM)), FSM)
    E.fact("fsm_row_address_correction",
           req(fsm, "row_address_correction", "claim", where=FSM), FSM)
    usage = req(fsm, "census_program_usage", where=FSM)
    E.fact("fsm_shared_bank_levels",
           len({u["level"] for rows_ in usage.values() for u in rows_}), FSM)
    E.fact("fsm_shared_bank_actor_ids",
           len({u["actor_id"] for rows_ in usage.values() for u in rows_}), FSM)

    LAW = "analysis/phase4_d18_thud_fight_law.json"
    law = E.json(LAW)
    fix = req(law, "fixture", where=LAW)
    live = req(law, "FIGHT_LAW_LIVE_2026-08-04", where=LAW)
    perch = req(law, "PERCH_QUALIFIER_DECODED_2026-08-04", where=LAW)
    regimes = req(law, "DAMAGE_RESPONSE_REGIMES_2026-08-04", where=LAW)
    E.fact("fight_movie", req(fix, "movie", where=LAW), LAW)
    E.fact("fight_movie_kind", req(fix, "kind", where=LAW), LAW)
    E.fact("fight_movie_frames", req(fix, "frames", where=LAW), LAW)
    E.fact("fight_scene", req(fix, "scene", where=LAW), LAW)
    E.fact("fight_hit_events", len(req(live, "hit_frames", where=LAW)), LAW)
    E.fact("fight_counter_trajectory", req(live, "counter_trajectory", where=LAW), LAW)
    E.fact("fight_vm_ip_writes_all_by_interpreter",
           "1,644 IP writes, ALL by the VM interpreter" in req(live, "6_vm_parked", where=LAW),
           LAW)
    E.fact("perch_evaluations", req(perch, "live_proof", "evaluations", where=LAW), LAW)
    E.fact("perch_scoring_events", req(perch, "live_proof", "at_a_perch", where=LAW), LAW)
    E.fact("perch_non_scoring_events", req(perch, "live_proof", "not_at_a_perch", where=LAW), LAW)
    E.fact("perch_handler_flow_steps", len(req(perch, "handler_flow", where=LAW)), LAW)
    E.fact("overlay_file_claimed_by_d18", req(perch, "overlay", "file", where=LAW), LAW)
    E.fact("overlay_size_claimed_by_d18", req(perch, "overlay", "size", where=LAW), LAW)
    E.fact("overlay_load_base_claimed_by_d18", req(perch, "overlay", "load_base", where=LAW), LAW)
    E.fact("damage_threshold_exact", req(regimes, "threshold_exact", "note", where=LAW), LAW)
    E.fact("damage_regimes_enumerated", len(req(regimes, "regimes", where=LAW)), LAW)
    E.fact("damage_regime_method_is_poke",
           "pokes the pool HP to simula" in req(regimes, "method", where=LAW), LAW)
    E.fact("callback_role_correction", req(law, "CALLBACK_ROLE_RESOLVED", "correction",
                                           where=LAW), LAW)
    E.fact("callback_source_grade", req(law, "CALLBACK_ROLE_RESOLVED", "canon", where=LAW), LAW)
    E.fact("fight_law_residuals_closed", len(req(law, "RESIDUALS_CLOSED", where=LAW)), LAW)
    E.fact("fight_law_still_open", len(req(law, "STILL_OPEN", where=LAW)), LAW)
    E.fact("fight_law_still_open_items", req(law, "STILL_OPEN", where=LAW), LAW)

    BEX = "analysis/phase4_d18_bounded_exhaustion.json"
    bex = E.json(BEX)
    nbr = req(bex, "native_berry_reachability", where=BEX)
    swo = req(bex, "sweep_word_ownership", where=BEX)
    E.fact("d18_disposition", req(bex, "status", where=BEX), BEX)
    E.fact("d18_disposition_scope", req(bex, "scope", where=BEX), BEX)
    E.fact("d18_bounded_residuals", len(req(bex, "bounded_residuals", where=BEX)), BEX)
    E.fact("d18_bounded_residual_items", req(bex, "bounded_residuals", where=BEX), BEX)
    E.fact("d18_move_on", req(bex, "move_on", where=BEX), BEX)
    E.fact("d18_further_movie_required", req(bex, "interpreter_movie_required", where=BEX), BEX)
    E.fact("native_damage_anchors_checked", req(nbr, "anchors_checked", where=BEX), BEX)
    E.fact("native_effective_damage_set", req(nbr, "effective_thud_damage_set", where=BEX), BEX)
    E.fact("native_max_effective_damage", req(nbr, "maximum_effective_damage", where=BEX), BEX)
    E.fact("native_softlock_band_reachable",
           req(nbr, "softlock_band_30_49_reachable", where=BEX), BEX)
    E.fact("sweep_word_writers", len(req(swo, "writers", where=BEX)), BEX)
    E.fact("sweep_word_direct_references", req(swo, "direct_references", where=BEX), BEX)
    E.fact("sweep_word_owner", req(swo, "owner", where=BEX), BEX)
    E.fact("overlay_sha256_claimed_by_d18", req(swo, "overlay_sha256", where=BEX), BEX)
    inherited = req(bex, "inherited_fight_law", where=BEX)

    NBC = "analysis/phase4_d18_native_berry_closure.json"
    nbc = E.json(NBC)
    E.fact("native_berry_variants_enumerated", len(req(nbc, "variants", where=NBC)), NBC)
    E.fact("native_berry_closure_result", req(nbc, "result", where=NBC), NBC)
    E.fact("softlock_classification", req(nbc, "softlock_classification", where=NBC), NBC)

    SWEEP = "analysis/phase4_d18_sweep_refs.json"
    sweep = E.json(SWEEP)
    E.fact("sweep_reference_census", req(sweep, "reference_count", where=SWEEP), SWEEP)
    E.fact("sweep_published_actor_field", req(sweep, "published_actor_field", where=SWEEP), SWEEP)
    E.fact("sweep_census_result", req(sweep, "result", where=SWEEP), SWEEP)

    # ------------------------------------------------------------------ #
    # 6. the arena (E11's lane) and the four retained runtime artifacts   #
    # ------------------------------------------------------------------ #
    E11 = "analysis/phase4_e11_dynamic_geometry.json"
    g = E.json(E11)
    st = req(g, "static", where=E11)
    rt = req(g, "runtime", where=E11)
    E.fact("arena_controller_start", req(st, "controller", "start", where=E11), E11)
    E.fact("arena_controller_size", req(st, "controller", "size", where=E11), E11)
    E.fact("arena_controller_callsites", len(req(st, "callsites", where=E11)), E11)
    E.fact("arena_rotation_deltas", len(req(st, "rotation_deltas_s16", where=E11)), E11)
    E.fact("arena_path_limits", len(req(st, "path_limits_s16", where=E11)), E11)
    E.fact("arena_shared_vertex_materializations",
           req(st, "direct_shared_vertex_materializations", "count", where=E11), E11)
    E.fact("arena_runtime_movie_used", req(rt, "movie_used", where=E11), E11)
    E.fact("arena_runtime_execution_mode", req(rt, "execution_mode", where=E11), E11)
    E.fact("arena_runtime_frames_observed", req(rt, "round_1", "frames", where=E11), E11)
    E.fact("arena_runtime_controller_ticks", req(rt, "round_1", "controller_hits", where=E11), E11)
    E.fact("arena_runtime_truncated", req(rt, "round_1", "truncated", where=E11), E11)
    E.fact("arena_runtime_anchor_hp", req(rt, "boss", "anchor_hp", where=E11), E11)
    E.fact("arena_runtime_phase_limit", req(rt, "boss", "phase_limit", where=E11), E11)
    E.fact("arena_named_limits", len(req(g, "limits", where=E11)), E11)
    E.fact("arena_named_limit_items", req(g, "limits", where=E11), E11)
    E.fact("arena_overlay_claimed", req(g, "inputs", "bug_bar_overlay", "path", where=E11), E11)
    E.fact("arena_scene_correction",
           req(g, "scene_identity", "corrected_old_assumption", where=E11), E11)

    E11D = "analysis/phase4_e11_deep_dive.json"
    gd = E.json(E11D)
    pass2 = req(gd, "authored_pass2_max_index_by_scene", where=E11D)
    E.fact("pass2_scenes_censused", len(pass2), E11D)
    E.fact("pass2_scenes_with_authored_objects",
           sum(1 for v in pass2.values() if v >= 0), E11D)
    E.fact("pass2_bug_bar_max_index", req(pass2, str(F["scene_id"]), where=E11D), E11D)
    E.fact("e11_disposition", req(gd, "assessment", where=E11D), E11D)
    E.fact("e11_strict_status", req(gd, "strict_phase4_status", where=E11D), E11D)
    E.fact("e11_remaining_promotion_work",
           len(req(gd, "remaining_promotion_work", where=E11D)), E11D)
    E.fact("e11_executable_gate_status",
           req(gd, "closure_dimensions", "executable_gate", where=E11D), E11D)
    E.fact("e11_controls_status",
           req(gd, "closure_dimensions", "positive_negative_controls", where=E11D), E11D)

    ARENA = "analysis/phase4_thud_arena.json"
    ar = E.json(ARENA)
    asum = req(ar, "summary", where=ARENA)
    E.fact("arena_rows_bound", req(asum, "arena_rows", where=ARENA), ARENA)
    E.fact("arena_distinct_model_hashes", req(asum, "distinct_model_hashes", where=ARENA), ARENA)
    E.fact("arena_natural_contact_rows", len(req(asum, "natural_contact_rows", where=ARENA)),
           ARENA)
    E.fact("arena_controlled_contact_rows",
           len(req(asum, "controlled_contact_rows", where=ARENA)), ARENA)
    E.fact("arena_contact_health_delta", req(asum, "contact_health_delta", where=ARENA), ARENA)
    E.fact("arena_row_completion_flag", req(asum, "d18_or_f09_completed", where=ARENA), ARENA)
    E.fact("arena_forbidden_claim",
           req(ar, "bounded_interpretation", "forbidden_claim", where=ARENA), ARENA)
    E.fact("arena_still_open", req(ar, "bounded_open_frontier", "still_open", where=ARENA), ARENA)
    E.fact("arena_evidence_movie", req(ar, "fixture_census", "movie", "path", where=ARENA), ARENA)
    E.fact("arena_evidence_movie_version",
           req(ar, "fixture_census", "movie", "version", where=ARENA), ARENA)
    E.fact("arena_decoded_policy_sites",
           len(req(ar, "runtime_census", "decoded_policy", where=ARENA)), ARENA)

    COMPL = "analysis/phase4_thud_completion.json"
    cm = E.json(COMPL)
    csum = req(cm, "summary", where=COMPL)
    E.fact("completion_request_pc", req(csum, "request_instruction_pc", where=COMPL), COMPL)
    E.fact("completion_fade_pc", req(csum, "fade_instruction_pc", where=COMPL), COMPL)
    E.fact("completion_counter_transition", req(csum, "counter_transition", where=COMPL), COMPL)
    E.fact("completion_natural_vs_suppressed_scene",
           req(csum, "natural_vs_suppressed_scene", where=COMPL), COMPL)
    E.fact("completion_request_bound", req(csum, "exact_completion_request_bound", where=COMPL),
           COMPL)
    E.fact("completion_row_completion_flag", req(csum, "d18_or_f09_completed", where=COMPL),
           COMPL)
    E.fact("completion_still_open",
           req(cm, "bounded_open_frontier", "still_open", where=COMPL), COMPL)
    E.fact("completion_forbidden_claim",
           req(cm, "bounded_interpretation", "forbidden_claim", where=COMPL), COMPL)

    VOL = "analysis/phase4_thud_volley.json"
    vo = E.json(VOL)
    vsum = req(vo, "summary", where=VOL)
    E.fact("volley_natural_volleys", req(vsum, "natural_reward_volleys", where=VOL), VOL)
    E.fact("volley_total_allocations", req(vsum, "total_reward_allocations", where=VOL), VOL)
    E.fact("volley_natural_health_pickups", req(vsum, "natural_action9_pickups", where=VOL), VOL)
    E.fact("volley_natural_grain_pickups",
           req(vsum, "natural_action20_grain_pickups", where=VOL), VOL)
    E.fact("volley_row_completion_flag", req(vsum, "d18_or_f09_completed", where=VOL), VOL)

    DEF = "analysis/phase4_thud_defeat.json"
    de = E.json(DEF)
    dsum = req(de, "summary", where=DEF)
    E.fact("defeat_movies_replayed", req(dsum, "movies_replayed", where=DEF), DEF)
    E.fact("defeat_evidence_sections", len([k for k in de if not k.startswith("_")]), DEF)
    E.fact("defeat_open_frontier_axes", len(req(de, "bounded_open_frontier", where=DEF)), DEF)
    E.fact("defeat_lifecycle_open",
           req(de, "bounded_open_frontier", "lifecycle", where=DEF), DEF)
    E.fact("defeat_static_scene_asset_entry",
           req(de, "static_census", "scene", "asset_entry", where=DEF), DEF)
    E.fact("defeat_static_scene_disc_dir",
           req(de, "static_census", "scene", "disc_dir", where=DEF), DEF)
    E.fact("defeat_staged_overlay_candidates",
           sorted(req(de, "static_census", "staged_overlay_candidates", where=DEF)), DEF)

    C16 = "analysis/phase4_c16_thud_boulder_death.json"
    c16 = E.json(C16)
    E.fact("boulder_death_arena_row", req(c16, "summary", "arena_row", where=C16), C16)
    E.fact("boulder_death_natural_health_delta",
           req(c16, "summary", "natural_health_delta", where=C16), C16)
    E.fact("boulder_death_final_life_outcome",
           req(c16, "summary", "fatal_health_lives_master", where=C16), C16)
    E.fact("boulder_death_row_completion_flag",
           req(c16, "summary", "c16_d18_or_f09_completed", where=C16), C16)
    E.fact("boulder_death_static_disc_dir",
           req(c16, "context_identity", "scene_graph", "disc_dir", where=C16), C16)

    # ------------------------------------------------------------------ #
    # 7. NEW MEASUREMENT: which overlay FILE owns the fight lane?         #
    #    Compiled C owns the decoding; the encodings it scanned are       #
    #    re-derived here from the D18 artifacts so the two cannot drift.  #
    # ------------------------------------------------------------------ #
    PIN = "analysis/phase4_f09_overlay_pin.json"
    pin = E.json(PIN)
    PINSRC = "tools/phase4_f09_overlay_pin.c"
    E.pin(PINSRC)

    derivation = req(perch, "overlay", "base_derivation", where=LAW)
    law_pairs = hexes(derivation)
    if len(law_pairs) < 4:
        raise SystemExit("STALE CITATION: the fight law's base_derivation no longer "
                         "carries the (encoding, PC) pairs the overlay pin scans")
    sweep_ref0 = req(sweep, "references", 0, where=SWEEP)
    expected = {(law_pairs[0].lower(), law_pairs[1].lower()),
                (law_pairs[2].lower(), law_pairs[3].lower()),
                (req(sweep_ref0, "word", where=SWEEP).lower(),
                 req(sweep_ref0, "pc", where=SWEEP).lower())}
    scanned = {(req(t, "word", where=PIN).lower(), req(t, "pc", where=PIN).lower())
               for t in req(pin, "targets", where=PIN)}
    if scanned != expected:
        raise SystemExit("the overlay pin scanned encodings that the D18 artifacts no "
                         f"longer derive: scanned={sorted(scanned)} "
                         f"derived={sorted(expected)}")
    E.fact("overlay_pin_targets_match_d18_artifacts", True, [PIN, LAW, SWEEP])
    E.fact("overlay_pin_target_ops",
           sorted({req(t, "op", where=PIN) for t in req(pin, "targets", where=PIN)}), PIN)
    E.fact("overlay_pin_images_scanned", req(pin, "files_scanned", where=PIN), PIN)
    E.fact("overlay_pin_images_with_every_target",
           req(pin, "files_containing_every_target_exactly_once", where=PIN), PIN)
    E.fact("overlay_pin_images_with_consistent_base",
           req(pin, "files_with_one_consistent_load_base", where=PIN), PIN)
    E.fact("overlay_pin_unique", req(pin, "unique_pin", where=PIN), PIN)
    E.fact("overlay_pin_file", req(pin, "unique_pin_file", where=PIN), PIN)
    E.fact("overlay_pin_load_base", req(pin, "unique_pin_load_base", where=PIN), PIN)
    E.fact("overlay_pin_result", req(pin, "result", where=PIN), PIN)
    pinned_file = next((f for f in req(pin, "files", where=PIN)
                        if f["path"] == F["overlay_pin_file"]), None)
    if pinned_file is None:
        raise SystemExit(f"STALE CITATION: {PIN} names a pin file absent from its own list")
    E.fact("overlay_pin_file_sha256", req(pinned_file, "sha256", where=PIN), PIN)
    E.fact("overlay_pin_file_size", req(pinned_file, "size", where=PIN), PIN)
    E.fact("overlay_pin_agrees_with_d18_sha256",
           F["overlay_pin_file_sha256"] == F["overlay_sha256_claimed_by_d18"], [PIN, BEX])

    ovl_base = as_int(F["overlay_pin_load_base"])
    ovl_end = ovl_base + int(F["overlay_pin_file_size"])

    # How ambiguous WAS that VA before the byte pin? Ask the shared function census.
    FN = "analysis/functions.json"
    fnj = E.json(FN)
    fns = req(fnj, "functions", where=FN)
    counter_writer = as_int(req(inherited, "score_writer", where=BEX))
    covering = {f["overlay"] for f in fns
                if f.get("space") == "overlay"
                and as_int(f["start"]) <= counter_writer < as_int(f["end"])}
    E.fact("overlay_images_in_function_census", len(req(fnj, "overlays", where=FN)), FN)
    E.fact("overlay_images_covering_counter_writer_pc", len(covering), [FN, BEX])
    E.fact("counter_writer_pc", req(inherited, "score_writer", where=BEX), BEX)
    l04 = [f for f in fns if f.get("overlay") == F["overlay_pin_file"].split("/")[-1][:-4]]
    E.fact("pinned_overlay_functions_in_census", len(l04), FN)

    # ------------------------------------------------------------------ #
    # 8. the semantic registries: who OWNS this row's code and state?     #
    # ------------------------------------------------------------------ #
    OWN = "analysis/phase3_ownership_graph.json"
    own = E.json(OWN)
    orow = req(own, "rows", ROW_ID, where=OWN)
    E.fact("ownership_gaps", len(req(orow, "gaps", where=OWN)), OWN)
    E.fact("ownership_gap_items", req(orow, "gaps", where=OWN), OWN)
    ofns = req(orow, "functions", where=OWN)
    E.fact("ownership_functions", len(ofns), OWN)
    E.fact("ownership_functions_with_canon", sum(1 for f in ofns if f.get("canon")), OWN)
    E.fact("ownership_overlay_spaces_named",
           sorted({f["space"] for f in ofns if f["space"] != "resident"}), OWN)
    E.fact("ownership_overlay_functions",
           sum(1 for f in ofns if f["space"] != "resident"), OWN)
    pinned_image = Path(F["overlay_pin_file"]).stem            # e.g. LEVEL04_LEVEL1
    E.fact("ownership_overlay_attribution_agrees_with_byte_pin",
           all(s.split("_")[0] == pinned_image.split("_")[0]
               for s in F["ownership_overlay_spaces_named"])
           if F["ownership_overlay_spaces_named"] else None, [OWN, PIN])
    ostate = req(orow, "state", where=OWN)
    E.fact("ownership_state_addresses", len(ostate), OWN)
    E.fact("ownership_state_addresses_with_owner",
           sum(1 for s in ostate if s.get("semantic_ids")), OWN)

    SEM = "config/semantic_state.yaml"
    sem = E.yaml(SEM)
    sem_addrs = {as_int(e["address"]) for e in req(sem, "entries", where=SEM)
                 if isinstance(e.get("address"), (int, str))}
    # every overlay-resident STATE word this row's own artifacts name
    row_overlay_state = {as_int(s["address"]) for s in ostate}
    row_overlay_state.add(as_int(req(inherited, "score_counter", where=BEX)))
    row_overlay_state.add(as_int(req(swo, "target", where=BEX)))
    for tc in req(ar, "threshold_controls", where=ARENA):
        row_overlay_state.add(as_int(req(tc, "single_field", "address", where=ARENA)))
    row_overlay_state = sorted(a for a in row_overlay_state if ovl_base <= a < ovl_end)
    E.fact("semantic_state_entries_total", len(req(sem, "entries", where=SEM)), SEM)
    E.fact("row_overlay_state_addresses", len(row_overlay_state), [OWN, BEX, ARENA, PIN])
    E.fact("row_overlay_state_address_list",
           [f"0x{a:08X}" for a in row_overlay_state], [OWN, BEX, ARENA, PIN])
    E.fact("row_overlay_state_addresses_registered",
           sum(1 for a in row_overlay_state if a in sem_addrs), [SEM, OWN, BEX, ARENA])
    E.fact("semantic_state_entries_inside_the_bug_bar_overlay_window",
           sorted(f"0x{a:08X}" for a in sem_addrs if ovl_base <= a < ovl_end), [SEM, PIN])

    SITES = "config/confirmed_sites.yaml"
    sites = E.yaml(SITES)
    site_entries = req(sites, "entries", where=SITES)
    thud_sites = [s for s in site_entries if "thud" in str(s.get("id", "")).lower()]
    E.fact("confirmed_sites_total", len(site_entries), SITES)
    E.fact("confirmed_sites_for_this_row", len(thud_sites), SITES)
    E.fact("confirmed_sites_for_this_row_ids", sorted(s["id"] for s in thud_sites), SITES)
    fight_lane = {as_int(inherited[k]) for k in
                  ("damage_writer", "restore_writer", "score_writer", "kill_writer")}
    E.fact("fight_lane_writer_pcs", len(fight_lane), BEX)
    E.fact("fight_lane_writers_registered_as_confirmed_sites",
           sum(1 for a in fight_lane
               if any(as_int(s["address"]) == a for s in site_entries)), [SITES, BEX])

    # ------------------------------------------------------------------ #
    # 9. typed state: does the record registry cover this row's actor?    #
    # ------------------------------------------------------------------ #
    RECS = "config/record_types.yaml"
    recs = E.yaml(RECS)
    actor = next((r for r in req(recs, "records", where=RECS) if r["id"] == "actor_record"), None)
    if actor is None:
        raise SystemExit(f"STALE CITATION: {RECS} no longer carries actor_record")
    a_base = req(actor, "base", where=RECS)
    a_size = req(actor, "size", where=RECS)
    a_inst = req(actor, "instances", where=RECS)
    a_fields = {f["offset"]: f for f in req(actor, "fields", where=RECS)}
    boss_addr = as_int(F["boss_record_addr"])
    E.fact("actor_record_declared_base", f"0x{a_base:08X}", RECS)
    E.fact("actor_record_declared_instances", a_inst, RECS)
    E.fact("actor_record_declared_stride", a_size, RECS)
    E.fact("actor_record_typed_fields", len(a_fields), RECS)
    E.fact("boss_record_inside_declared_extent",
           a_base <= boss_addr < a_base + a_size * a_inst, [RECS, THUD3])
    named = {0x5C: "flags", 0x6E: "hp", 0x70: "vm_ip", 0x7C: "callback"}
    E.fact("row_named_actor_offsets_typed",
           sum(1 for off in named if off in a_fields), [RECS, THUD3])
    E.fact("row_named_actor_offsets_total", len(named), THUD3)
    E.fact("actor_hp_field_note", req(a_fields[0x6E], "note", where=RECS), RECS)
    E.fact("actor_hp_note_describes_this_boss",
           str(F["boss_actor_id"]) in F["actor_hp_field_note"], [RECS, THUD3])

    # ------------------------------------------------------------------ #
    # 10. source closure: what build unit owns each governing function?   #
    #     (addresses derived from this row's artifacts, never hand-typed) #
    # ------------------------------------------------------------------ #
    SEG = "config/segments.yml"
    seg = E.yaml(SEG)
    units = [(as_int(req(e, "start", where=SEG)), as_int(req(e, "end", where=SEG)),
              req(e, "source", where=SEG)) for e in req(seg, "attempted", where=SEG)]
    E.fact("resident_build_toolchain",
           req(seg, "c_toolchain", "compiler", where=SEG), SEG)

    governing: dict[str, int] = {}
    for pc in retire_writes:
        governing[f"retire_{pc}"] = as_int(pc)
    governing["driver_callback"] = as_int(F["boss_callback_0x7c"])
    for k in ("damage_writer", "restore_writer", "score_writer", "kill_writer"):
        governing[k] = as_int(req(inherited, k, where=BEX))
    for i, pc in enumerate(req(swo, "writers", where=BEX)):
        governing[f"sweep_writer_{i}"] = as_int(pc)
    governing["arena_controller"] = as_int(F["arena_controller_start"])
    for cs in req(st, "callsites", where=E11):
        governing[f"arena_callsite_{cs['pc']}"] = as_int(req(cs, "pc", where=E11))
        governing[f"arena_target_{cs['target']}"] = as_int(req(cs, "target", where=E11))
    governing["actor_state_leaf"] = as_int(req(st, "actor_state_leaf", "address", where=E11))
    governing["completion_request"] = as_int(F["completion_request_pc"])
    governing["completion_fade"] = as_int(F["completion_fade_pc"])
    for name, pc in req(ar, "runtime_census", "decoded_policy", where=ARENA).items():
        if isinstance(pc, str) and pc.startswith("0x") and len(pc) == 10:
            governing[f"arena_policy_{name}"] = as_int(pc)
    spawn = hexes(req(live, "1_spawn", where=LAW))
    vmstore = hexes(req(live, "6_vm_parked", where=LAW))
    if not spawn or not vmstore:
        raise SystemExit("STALE CITATION: the fight law no longer names the spawn / "
                         "VM-store PCs this assessment resolves to build units")
    governing["spawn_hp_writer"] = as_int(spawn[0])
    governing["vm_ip_store"] = as_int(vmstore[-1])

    resident = {n: a for n, a in governing.items() if not (ovl_base <= a < ovl_end)}
    overlay = {n: a for n, a in governing.items() if ovl_base <= a < ovl_end}
    resolved: dict[str, list[str]] = {}
    unresolved: list[str] = []
    for n, a in resident.items():
        src = next((s for lo, hi, s in units if lo <= a < hi), None)
        (resolved.setdefault(src, []).append(n) if src else unresolved.append(n))
    E.fact("governing_addresses", len(governing),
           [THUD3, BEX, E11, ARENA, COMPL, LAW])
    E.fact("governing_addresses_resident", len(resident), [PIN, THUD3, BEX, E11, ARENA, COMPL, LAW])
    E.fact("governing_addresses_in_the_bug_bar_overlay", len(overlay),
           [PIN, BEX, E11, ARENA, COMPL])
    E.fact("governing_resident_build_units", len(resolved), SEG)
    E.fact("governing_resident_units_matching_c",
           len([s for s in resolved if s.startswith("src/")]), SEG)
    E.fact("governing_resident_units_hand_asm",
           len([s for s in resolved if s.startswith("asm/")]), SEG)
    E.fact("governing_resident_matching_c_sources",
           sorted(s for s in resolved if s.startswith("src/")), SEG)
    E.fact("governing_resident_addresses_outside_any_build_unit", len(unresolved), SEG)

    OVLD = "analysis/overlay_decomp_progress.json"
    ovld = E.json(OVLD)
    ovl_name = Path(F["overlay_pin_file"]).stem
    E.fact("pinned_overlay_code_functions",
           req(ovld, "per_overlay_totals", ovl_name, where=OVLD), OVLD)
    l04_results = [r for r in req(ovld, "results", where=OVLD) if r["overlay"] == ovl_name]
    E.fact("pinned_overlay_matched_functions",
           sum(req(r, "matched_functions", where=OVLD) for r in l04_results), OVLD)
    attempted_ranges = [(as_int(a["start"]), a["source"])
                        for r in l04_results for a in req(r, "attempted", where=OVLD)]
    E.fact("pinned_overlay_matched_sources", sorted(s for _, s in attempted_ranges), OVLD)
    E.fact("pinned_overlay_matched_functions_in_the_governing_set",
           sum(1 for start, _ in attempted_ranges if start in set(overlay.values())), [OVLD, PIN])

    # ------------------------------------------------------------------ #
    # 11. the fixture corpus: which stage-9 routes exist, which are used  #
    # ------------------------------------------------------------------ #
    AUDIT = "analysis/phase2_fixture_audit.json"
    audit = E.json(AUDIT)
    movies = req(audit, "movies", where=AUDIT)
    stage9_mov = sorted(k for k in movies
                        if re.search(r"thud|LEVEL09|bugbar|BUGBAR|D18", k, re.I))
    E.fact("stage9_movies_pinned", len(stage9_mov), AUDIT)
    E.fact("stage9_movies_pinned_paths", stage9_mov, AUDIT)
    E.fact("stage9_movie_frames",
           {k: req(movies, k, "frames", where=AUDIT) for k in stage9_mov}, AUDIT)
    E.fact("stage9_movie_format_versions",
           {k: req(movies, k, "format_version", where=AUDIT) for k in stage9_mov}, AUDIT)
    E.fact("stage9_movies_pre_v4",
           sum(1 for k in stage9_mov if req(movies, k, "format_version", where=AUDIT) < 4),
           AUDIT)
    saves = req(audit, "saves", where=AUDIT)
    E.fact("stage9_saves_pinned",
           len([k for k in saves if re.search(r"thud|LEVEL09|level_09|bugbar", k, re.I)]), AUDIT)

    replayed = sorted({m for m in (F["fight_movie"], F["arena_evidence_movie"])
                       if m in stage9_mov})
    E.fact("stage9_movies_replayed_by_row_artifacts", len(replayed), [LAW, ARENA, AUDIT])
    E.fact("stage9_movies_replayed_paths", replayed, [LAW, ARENA, AUDIT])
    E.fact("stage9_movies_never_replayed_by_row_artifacts",
           sorted(set(stage9_mov) - set(replayed)), [LAW, ARENA, AUDIT])

    FIXSET = "analysis/phase0_2_external_fixture_set.json"
    fixset = E.json(FIXSET)
    entries = req(fixset, "entries", where=FIXSET)
    E.fact("stage9_movies_centrally_pinned",
           sum(1 for k in stage9_mov if k in entries), FIXSET)
    E.fact("stage9_movies_bytes_match_pin",
           sum(1 for k in stage9_mov
               if k in entries and sha256_file(ROOT / k) == entries[k]["sha256"]), FIXSET)
    E.fact("in_repo_artifacts_in_the_external_preservation_set",
           sum(1 for p in in_repo if p in entries), [FIXSET, CENSUS])
    fight_entry = req(entries, F["fight_movie"], where=FIXSET)
    E.fact("fight_movie_central_consumers", req(fight_entry, "consumers", where=FIXSET), FIXSET)
    E.fact("fight_movie_credited_to_this_row",
           f"mechanics:{ROW_ID}" in req(fight_entry, "consumers", where=FIXSET), FIXSET)
    E.fact("fight_movie_declared_by_the_row",
           F["fight_movie"] in req(row, "fixture_have", where=BASE), [BASE, LAW])

    # ------------------------------------------------------------------ #
    # 12. the campaign-wide oracle that already covers this stage         #
    # ------------------------------------------------------------------ #
    ORACLE = "analysis/phase2_completion_oracle.json"
    oracle = E.json(ORACLE)
    st9 = next((v for k, v in req(oracle, "stages", where=ORACLE).items() if "09" in k), None)
    if st9 is None:
        raise SystemExit(f"STALE CITATION: {ORACLE} no longer carries a stage-09 entry")
    E.fact("completion_oracle_movie", req(st9, "movie", where=ORACLE), ORACLE)
    E.fact("completion_oracle_frames", req(st9, "frames", where=ORACLE), ORACLE)
    E.fact("completion_oracle_target_scene", req(st9, "target_scene", where=ORACLE), ORACLE)
    E.fact("completion_oracle_replay_accepted",
           req(st9, "pristine_replay_accepted", where=ORACLE), ORACLE)
    E.fact("completion_oracle_stage_exited", req(st9, "stage_exited_by_movie_end", where=ORACLE),
           ORACLE)
    E.fact("completion_oracle_last_in_stage_frame",
           req(st9, "last_in_stage", "frame", where=ORACLE), ORACLE)
    E.fact("completion_oracle_cited_by_the_row",
           "phase2_completion_oracle" in json.dumps(row), [BASE, ORACLE])

    COV = "analysis/phase2_row_coverage.json"
    cov = E.json(COV)
    crow2 = req(cov, "rows", ROW_ID, where=COV)
    E.fact("row_coverage_status", req(crow2, "status", where=COV), COV)
    E.fact("row_coverage_unaudited_fixtures",
           len(req(crow2, "unaudited_fixtures", where=COV)), COV)

    # ------------------------------------------------------------------ #
    # 13. the collision environment (the row's own stage layout)          #
    # ------------------------------------------------------------------ #
    E02 = "analysis/phase4_e02_disc_region_code_census.json"
    e02 = E.json(E02)
    levels = req(e02, "levels", where=E02)
    s9 = next((v for k, v in levels.items() if "09" in k), None)
    if s9 is None:
        raise SystemExit(f"STALE CITATION: {E02} no longer carries a stage-09 level")
    E.fact("stage9_authored_collision_sectors", req(s9, "authored_sectors", where=E02), E02)
    E.fact("stage9_runtime_collision_sectors", req(s9, "runtime_sectors", where=E02), E02)
    E.fact("stage9_runtime_registered_tail", req(s9, "runtime_registered_tail", where=E02), E02)
    E.fact("stage9_region_code_histogram", req(s9, "code_histogram", where=E02), E02)
    E.fact("stage9_collision_container", req(s9, "container", where=E02), E02)
    tails = {k: req(v, "runtime_registered_tail", where=E02) for k, v in levels.items()}
    E.fact("levels_censused", len(levels), E02)
    E.fact("levels_with_the_same_runtime_registered_tail",
           sum(1 for v in tails.values() if v == F["stage9_runtime_registered_tail"]), E02)
    E.fact("distinct_runtime_registered_tails_campaign_wide", sorted(set(tails.values())), E02)
    authored = {k: req(v, "authored_sectors", where=E02) for k, v in levels.items()}
    E.fact("stage9_authored_sector_rank",
           sorted(authored.values()).index(F["stage9_authored_collision_sectors"]) + 1, E02)
    E.fact("second_lowest_authored_sector_count", sorted(authored.values())[1], E02)
    E.fact("stage9_runtime_registered_fraction",
           f'{F["stage9_runtime_registered_tail"]}/{F["stage9_runtime_collision_sectors"]}', E02)
    E.fact("highest_runtime_registered_fraction_is_this_stage",
           max(levels, key=lambda k: tails[k] / req(levels[k], "runtime_sectors", where=E02))
           == next(k for k in levels if "09" in k), E02)
    E.fact("e02_disc_runtime_disagreements",
           len(req(e02, "agreement", "disagreements", where=E02)), E02)
    E.fact("e02_authored_sectors_compared",
           req(e02, "agreement", "authored_sectors_compared", where=E02), E02)
    # the directory token really is ambiguous -- two stages share disc dir LEVEL04/
    dirs = [req(v, "container", where=E02).split("/")[0] for v in levels.values()]
    E.fact("stages_sharing_this_stages_disc_directory",
           dirs.count(F["stage9_collision_container"].split("/")[0]), E02)

    # ------------------------------------------------------------------ #
    # 14. Canon currency + the row's registered executable gates          #
    # ------------------------------------------------------------------ #
    SYS = "ObsidianVault/Canon/Systems/SYS_thud_bug_bar_boss.md"
    sysdoc = E.text(SYS)
    E.fact("canon_page_sections", len(re.findall(r"^#{2,3} ", sysdoc, re.M)), SYS)
    E.fact("canon_page_still_calls_the_softlock_link_untested",
           "is **untested**" in sysdoc, SYS)
    E.fact("closure_artifact_calls_the_softlock_band_unreachable",
           F["native_softlock_band_reachable"] is False, BEX)

    EXP = "ObsidianVault/Experiments/EXP_2026-08-04_phase4_d18_thud_fight_law.md"
    expdoc = E.text(EXP)
    m = re.search(r"^## Bounded disposition.*$", expdoc, re.M)
    if not m:
        raise SystemExit(f"STALE CITATION: {EXP} no longer has a "
                         "'## Bounded disposition' section")
    E.fact("experiment_bounded_disposition_heading", m.group(0).strip(), EXP)
    E.fact("experiment_declares_bounded_exhausted",
           "bounded-exhausted" in expdoc[m.end():].split("\n## ")[0], EXP)

    # Declarative behavioral scenarios. The denominator (every scenario in the
    # repo) is a directory listing and cannot be pinned, so it is not recorded;
    # the row-scoped set is evidenced by the files themselves, each pinned.
    SCEN = "tools/scenarios/duckstation"
    scen_dir = ROOT / SCEN
    if not scen_dir.is_dir():
        raise SystemExit(f"STALE CITATION: {SCEN} is not a directory")
    row_scen = [f"{SCEN}/{p.name}" for p in sorted(scen_dir.glob("*.yaml"))
                if re.search(r"thud|stage09", p.name)]
    if not row_scen:
        raise SystemExit(f"STALE CITATION: {SCEN} no longer holds a scenario for this row")
    for rel in row_scen:
        E.pin(rel)
    E.fact("declarative_scenarios_for_this_row", len(row_scen), row_scen)
    E.fact("declarative_scenario_names", [Path(p).name for p in row_scen], row_scen)

    row_artifacts = [THUD3, FSM, LAW, BEX, NBC, SWEEP, E11, E11D, ARENA, COMPL, VOL, DEF, C16]
    E.fact("row_evidence_artifacts_pinned_here", len(row_artifacts), row_artifacts)
    scen_named = sorted({d for rel in (ARENA, COMPL, VOL, DEF, C16)
                         for d in (json.loads((ROOT / rel).read_text())
                                   .get("source_dependencies") or {})
                         if d.startswith(SCEN)})
    E.fact("declarative_scenarios_named_by_retained_artifacts", len(scen_named),
           [ARENA, COMPL, VOL, DEF, C16])
    test_dir = ROOT / "tests"
    gate_files = []
    for p in sorted(test_dir.glob("test_*.py")):
        body = p.read_text(errors="ignore")
        if any(a in body for a in row_artifacts):
            rel = f"tests/{p.name}"
            E.pin(rel)
            gate_files.append(rel)
    if not gate_files:
        raise SystemExit("no registered gate covers any of this row's artifacts -- "
                         "the gate set this assessment measures has disappeared")
    E.fact("registered_gate_files", len(gate_files), gate_files)
    E.fact("registered_gate_file_names", gate_files, gate_files)

    # Every retained artifact that pins its own dependencies: are those pins live?
    declared, matching, stale = 0, 0, []
    for rel in (ARENA, COMPL, VOL, DEF, C16):
        doc = json.loads((ROOT / rel).read_text())
        for dep, want in (doc.get("source_dependencies") or {}).items():
            declared += 1
            p = ROOT / dep
            if p.exists() and sha256_file(p) == want:
                matching += 1
            else:
                stale.append(dep)
    E.fact("retained_artifact_dependency_pins_declared", declared, [ARENA, COMPL, VOL, DEF, C16])
    E.fact("retained_artifact_dependency_pins_still_matching", matching,
           [ARENA, COMPL, VOL, DEF, C16])
    E.fact("retained_artifact_dependency_pins_stale", sorted(set(stale)),
           [ARENA, COMPL, VOL, DEF, C16])

    if args.no_gates:
        E.fact("registered_gates_executed", False, gate_files)
    else:
        run = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "--color=no",
             "-p", "no:cacheprovider", *gate_files],
            cwd=str(ROOT), capture_output=True, text=True)
        out = re.sub(r"\x1b\[[0-9;]*m", "", run.stdout)
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        passed = re.search(r"(\d+) passed", tail)
        failed = re.search(r"(\d+) failed", tail)
        if not passed and not failed:
            raise SystemExit(f"could not read a pytest summary from the gate run: {tail!r}")
        E.fact("registered_gates_executed", True, gate_files)
        E.fact("registered_gate_tests_passed", int(passed.group(1)) if passed else 0, gate_files)
        E.fact("registered_gate_tests_failed", int(failed.group(1)) if failed else 0, gate_files)
        names = sorted({ln.split()[1].split("::")[0]
                        for ln in out.splitlines() if ln.startswith("FAILED ")})
        if F["registered_gate_tests_failed"] and not names:
            raise SystemExit("the gate run reported failures but no FAILED lines could be "
                             "attributed to a file -- the summary parse is wrong")
        E.fact("registered_gate_files_with_a_failure", names, gate_files)
        E.fact("registered_gate_file_failure_count", len(names), gate_files)

    # ------------------------------------------------------------------ #
    # AUTHORED JUDGMENTS against the WRITTEN bars                         #
    # ------------------------------------------------------------------ #
    inherited_note = (
        f"D18 declared this boss '{F['d18_disposition']}' and E11 declared the arena "
        f"'{F['e11_disposition']}'; under the vocabulary those are STOP DECISIONS and "
        f"never read as met for F09")
    if F["registered_gates_executed"]:
        gate_note = (
            f"{F['registered_gate_tests_failed']} of "
            f"{F['registered_gate_tests_passed'] + F['registered_gate_tests_failed']} tests "
            f"in this row's {F['registered_gate_files']} registered gate files fail on "
            f"today's tree, across {F['registered_gate_file_failure_count']} of those files")
    else:
        gate_note = (f"this row's {F['registered_gate_files']} registered gate files were "
                     f"NOT executed for this run (--no-gates), so their health is unmeasured "
                     f"here")

    dims = {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": f"CARRIED FORWARD, not re-derived: {F['census_durable_fraction']} in "
                     f"{CENSUS} -- {F['census_durable_reason']}. This assessment fails "
                     f"loudly if that measurement ever moves off 'met'. Independently "
                     f"re-confirmed here on the two axes the census names: the "
                     f"{F['row_in_repo_artifact_count']} in-repo artifacts are git-tracked "
                     f"(independently checked against git) and correctly "
                     f"absent from the external preservation set "
                     f"({F['in_repo_artifacts_in_the_external_preservation_set']} of them "
                     f"appear there), and {F['stage9_movies_bytes_match_pin']} of "
                     f"{F['stage9_movies_pinned']} pinned stage-9 movies still byte-match "
                     f"their central pin",
            "gap": f"the carried measurement covers FIXTURE INTACTNESS, not regenerability. "
                   f"Measured separately here: {gate_note}, and "
                   f"{len(F['retained_artifact_dependency_pins_stale'])} of "
                   f"{F['retained_artifact_dependency_pins_declared']} dependency pins the "
                   f"retained runtime artifacts declare about themselves no longer match "
                   f"the bytes on disk. That does not overturn 'met' on the bar as written, "
                   f"but a verifier should not read this cell as 'the evidence still "
                   f"reproduces'",
        },
        "original_oracle": {
            "state": "partial",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"the fight law is measured end-to-end on NATURAL execution of a "
                     f"from-boot pinned movie ({F['fight_movie_kind']}, "
                     f"{F['fight_movie_frames']} frames, scene {F['fight_scene']}): spawn -> "
                     f"{F['fight_hit_events']} damage events -> counter "
                     f"{F['fight_counter_trajectory']} -> kill -> retirement, every writer an "
                     f"attributed PC, and the perch qualifier proved by breakpointing the "
                     f"predicate's own test instruction ({F['perch_evaluations']} evaluations, "
                     f"{F['perch_scoring_events']} scoring, {F['perch_non_scoring_events']} "
                     f"not). The FSM negative is a poll-only natural replay "
                     f"({F['fsm_replay_ip_samples']} IP samples, "
                     f"{F['fsm_replay_ip_values_seen']} distinct values). The row also has "
                     f"real executable assertion machinery, which F-rows generally lack: "
                     f"{F['declarative_scenarios_for_this_row']} declarative DuckStation "
                     f"scenarios ({F['declarative_scenarios_named_by_retained_artifacts']} of "
                     f"them named as dependencies by the retained artifacts themselves) and "
                     f"{F['registered_gate_files']} registered gate files",
            "gap": f"three separate holes. (1) {gate_note} -- an oracle that does not run "
                   f"green is not an oracle today. (2) The row's headline identity binding is "
                   f"INJECTION by construction ('{F['retirement_rule']}' via poke), and so are "
                   f"the {F['damage_regimes_enumerated']} damage regimes and the soft-lock, "
                   f"which the closure artifact itself classifies "
                   f"'{F['softlock_classification']}'. (3) Nothing in this row asserts the "
                   f"STAGE: a from-boot completion oracle for this stage already exists "
                   f"({F['completion_oracle_movie']}, {F['completion_oracle_frames']} frames, "
                   f"pristine_replay_accepted={F['completion_oracle_replay_accepted']}) and "
                   f"the row does not cite it "
                   f"(cited={F['completion_oracle_cited_by_the_row']})",
        },
        "complete_frontier": {
            "state": "partial",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant -- not an empty unresolved set",
            "basis": f"for the FIGHT LANE the frontier is enumerated and the residual is "
                     f"explicitly bounded: {F['fight_lane_writer_pcs']} attributed lane "
                     f"writers plus {len(F['retirement_writer_pcs'])} retirement stores, the "
                     f"sweep word closed to {F['sweep_reference_census']} direct references / "
                     f"{F['sweep_word_writers']} writers owned by "
                     f"'{F['sweep_word_owner']}', the native damage domain closed to "
                     f"{F['native_effective_damage_set']} over "
                     f"{F['native_damage_anchors_checked']} anchors and "
                     f"{F['native_berry_variants_enumerated']} equipped-berry variants, "
                     f"{F['d18_bounded_residuals']} named bounded residuals and "
                     f"{F['fight_law_still_open']} named still-open items. For the ARENA, E11 "
                     f"enumerates the controller, {F['arena_controller_callsites']} callsites, "
                     f"{F['arena_rotation_deltas']} rotation deltas and the authored pass-2 "
                     f"capacity for ALL {F['pass2_scenes_censused']} retail scene DATs, with "
                     f"{F['arena_named_limits']} named limits. NEW HERE: the overlay was named "
                     f"by ADDRESS, and that address is ambiguous across "
                     f"{F['overlay_images_covering_counter_writer_pc']} overlay images; "
                     f"tools/phase4_f09_overlay_pin.c settles it from bytes -- of "
                     f"{F['overlay_pin_images_scanned']} images exactly "
                     f"{F['overlay_pin_images_with_consistent_base']} contains all three "
                     f"encodings once with one consistent load base "
                     f"({F['overlay_pin_file']} @ {F['overlay_pin_load_base']}, "
                     f"{F['overlay_pin_result']})",
            "gap": f"the enumeration is not the ROW's. The semantic ownership graph resolves "
                   f"this row's {F['ownership_overlay_functions']} overlay functions to "
                   f"{F['ownership_overlay_spaces_named']} -- a DIFFERENT LEVEL's overlay at "
                   f"the same load VA, which the byte pin above contradicts -- and "
                   f"{F['ownership_functions'] - F['ownership_functions_with_canon']} of its "
                   f"{F['ownership_functions']} functions carry no Canon page. "
                   f"{F['ownership_gaps']} state addresses are cited with no semantic-registry "
                   f"owner ({F['ownership_gap_items']}). Nothing enumerates the stage's ENTRY "
                   f"frontier (how scene {F['scene_id']} is reached, its prerequisites) and "
                   f"the row's own declared missing item is still open: "
                   f"'{F['row_declared_missing']}'. {inherited_note}",
        },
        "campaign_breadth": {
            "state": "partial",
            "written_bar": "conclusions generalize across every applicable stage, variant, "
                           "lifecycle and exceptional path -- which requires the applicable "
                           "set itself to be enumerated",
            "basis": f"unusually for an F row, two applicability universes here really are "
                     f"enumerated rather than assumed. The mover-VM program bank Thud parks "
                     f"in is joined to {F['fsm_shared_bank_actor_ids']} actor ids across "
                     f"{F['fsm_shared_bank_levels']} levels, so the FSM negative is not a "
                     f"one-actor observation; and the pass-2 geometry capacity is censused "
                     f"across all {F['pass2_scenes_censused']} retail scene DATs with "
                     f"{F['pass2_scenes_with_authored_objects']} authoring any objects. The "
                     f"stage's own collision environment is censused disc-side against "
                     f"runtime with {F['e02_disc_runtime_disagreements']} disagreements over "
                     f"{F['e02_authored_sectors_compared']} sectors",
            "gap": f"within the stage, the applicable set is not enumerated at all. Of "
                   f"{F['stage9_movies_pinned']} pinned stage-9 movies the row's artifacts "
                   f"replay {F['stage9_movies_replayed_by_row_artifacts']}; never replayed: "
                   f"{F['stage9_movies_never_replayed_by_row_artifacts']}. Retry, "
                   f"re-engagement, checkpoint and persistence are named OPEN by the row's own "
                   f"artifacts ('{F['defeat_lifecycle_open']}'), "
                   f"{F['arena_controlled_contact_rows']} of {F['arena_rows_bound']} arena "
                   f"rows were reached only by threshold control rather than naturally, and "
                   f"no variant/route taxonomy exists. 'Every applicable' still has no "
                   f"within-stage denominator",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumerating an "
                           "untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"the value domains here are unusually well bounded, and several were "
                     f"bounded by correcting a wrong type: pool +0x6E is proved a TRANSIENT "
                     f"HIT LATCH rather than health (restored two frames after every hit), the "
                     f"real counter is an overlay word whose domain is "
                     f"0..{F['perch_scoring_events']} -- one increment per qualifying hit, "
                     f"kill gated on its maximum, the scoring predicate is a position "
                     f"equality test against two literal anchors, the damage response "
                     f"partitions into {F['damage_regimes_enumerated']} regimes at an exact "
                     f"decoded guard ('{F['damage_threshold_exact']}'), and the natively "
                     f"reachable damage domain is closed to "
                     f"{F['native_effective_damage_set']}. "
                     f"{F['row_named_actor_offsets_typed']}/"
                     f"{F['row_named_actor_offsets_total']} of the actor offsets this row "
                     f"names are typed with confirmed confidence in config/record_types.yaml",
            "gap": f"none of that state is REGISTERED, and the registry that exists does not "
                   f"cover this actor. config/semantic_state.yaml holds "
                   f"{F['semantic_state_entries_total']} entries and "
                   f"{F['row_overlay_state_addresses_registered']} of this row's "
                   f"{F['row_overlay_state_addresses']} overlay state words appear in it "
                   f"(the only entry inside the Bug Bar overlay's load window, "
                   f"{F['semantic_state_entries_inside_the_bug_bar_overlay_window']}, belongs "
                   f"to the TRAINING overlay -- the same VA-collision hazard again). The "
                   f"declared actor_record extent starts at "
                   f"{F['actor_record_declared_base']} x {F['actor_record_declared_instances']} "
                   f"instances, which does NOT contain this boss's own record at "
                   f"{F['boss_record_addr']} (inside_declared_extent="
                   f"{F['boss_record_inside_declared_extent']}), and the typed hp field's note "
                   f"documents a different boss's law "
                   f"(describes_this_boss={F['actor_hp_note_describes_this_boss']}) -- the very "
                   f"field D18 proved is a latch here",
        },
        "lifecycle": {
            "state": "partial",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": f"this row has something most rows do not: a single COLD-BOOT natural "
                     f"arc covering most of the list in one fixture "
                     f"({F['fight_movie_kind']}, {F['fight_movie_frames']} frames). Load is "
                     f"the spawn write at level load; first and repeated use are "
                     f"{F['fight_hit_events']} damage events with "
                     f"{F['perch_scoring_events']} counted; exhaustion is the counter "
                     f"saturating at its target and the kill write firing there; retirement is "
                     f"instruction-bound at {F['retirement_writer_pcs']} and independently "
                     f"poke-falsified ('{F['retirement_rule']}') with a complete, untruncated "
                     f"write log ({F['retirement_log_events']} events, "
                     f"truncated={F['retirement_log_truncated']}); and objective completion -> "
                     f"scene exit is causally isolated (suppressing only "
                     f"{F['completion_request_pc']} leaves scene "
                     f"{F['completion_natural_vs_suppressed_scene'][1]} loaded)",
            "gap": f"reuse and reset are absent, and the row's own artifacts say so: "
                   f"'{F['defeat_lifecycle_open']}'. The arena half is worse -- its only "
                   f"runtime anchor is a LATE-PHASE save state "
                   f"(anchor_hp={F['arena_runtime_anchor_hp']}, "
                   f"phase_limit='{F['arena_runtime_phase_limit']}', "
                   f"movie_used={F['arena_runtime_movie_used']}), so early/mid-fight geometry "
                   f"timing, contact/damage timing and post-fight reset are unobserved; E11 "
                   f"lists {F['e11_remaining_promotion_work']} remaining promotion items and "
                   f"asks for exactly that fixture. No per-phase claim map is registered for "
                   f"this row the way F01 has one",
        },
        "cross_system_behavior": {
            "state": "met_candidate",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": f"five distinct native crossings are exercised on natural execution, each "
                     f"with a matched control and an explicit forbidden-claim boundary. "
                     f"PROJECTILE x BOSS: the boss takes damage through the ordinary berry "
                     f"dispatch, and the natively reachable delta is closed to "
                     f"{F['native_effective_damage_set']} "
                     f"(max {F['native_max_effective_damage']}). DYNAMIC GEOMETRY x PLAYER "
                     f"DAMAGE: {F['arena_natural_contact_rows']} of {F['arena_rows_bound']} "
                     f"arena rows contact the player naturally for "
                     f"{F['arena_contact_health_delta']} health, the remaining "
                     f"{F['arena_controlled_contact_rows']} by threshold-only control at equal "
                     f"origin. BOSS ARENA x DEATH/LIVES: a row-"
                     f"{F['boulder_death_arena_row']} contact made fatal on the final life "
                     f"yields {F['boulder_death_final_life_outcome']} (health/lives/master). "
                     f"REWARD DROPS x PICKUP ECONOMY: {F['volley_natural_volleys']} volleys / "
                     f"{F['volley_total_allocations']} allocations produce "
                     f"{F['volley_natural_health_pickups']} natural health pickups and "
                     f"{F['volley_natural_grain_pickups']} grain pickups. OBJECTIVE x SCENE "
                     f"TRANSITION: the completion request is causally isolated from the fade "
                     f"request and from retirement",
            "gap": f"no registered combination matrix exists, so 'native combinations' has no "
                   f"declared target set to measure against -- the five crossings are the ones "
                   f"the recording happened to contain. Two arena rows are control-only, the "
                   f"soft-lock crossing is '{F['softlock_classification']}', and the canonical "
                   f"bar text names combinations (carry+damage, powers+jump) that this stage "
                   f"may or may not admit -- unresolved. A verifier decides whether crossings "
                   f"exercised without an enumerated target set can meet the written bar",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"the resident<->overlay interface is documented at instruction level and "
                     f"two of its corrections are the useful kind: pool +0x6E is the SHARED "
                     f"FIELD across the boundary (resident dispatch writes it, the overlay "
                     f"restores it, the overlay zeroes it to hand back to generic retirement), "
                     f"and the actor's +0x7C entry point was re-documented from 'driver "
                     f"callback' to what it is -- '{F['callback_role_correction']}' -- against "
                     f"{F['callback_source_grade']}. The sweep word's publication path is "
                     f"documented to the actor field {F['sweep_published_actor_field']}. "
                     f"{F['confirmed_sites_for_this_row']} sites are registered with MOD "
                     f"contracts in config/confirmed_sites.yaml",
            "gap": f"the overlay side has essentially no documented ABI: "
                   f"{F['fight_lane_writers_registered_as_confirmed_sites']} of "
                   f"{F['fight_lane_writer_pcs']} fight-lane writers are registered as "
                   f"confirmed sites, the pinned overlay has "
                   f"{F['pinned_overlay_code_functions']} code functions in the census with "
                   f"{F['pinned_overlay_matched_functions']} matched and "
                   f"{F['pinned_overlay_matched_functions_in_the_governing_set']} of those in "
                   f"this row's governing set. Worse for interface identity: the largest "
                   f"retained runtime artifact still binds its STATIC overlay provenance to "
                   f"the falsified routing (asset_entry "
                   f"'{F['defeat_static_scene_asset_entry']}', disc dir "
                   f"'{F['defeat_static_scene_disc_dir']}', staged candidates "
                   f"{F['defeat_staged_overlay_candidates']}) -- the exact claim the D18 row "
                   f"records as falsified "
                   f"(records_falsification={F['d18_row_records_prior_binding_falsified']}). "
                   f"Its runtime observations are unaffected; its file-level provenance is not",
        },
        "source_closure": {
            "state": "not_met",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"measured, not assumed: {F['governing_addresses']} governing code "
                     f"addresses derived from this row's own artifacts split into "
                     f"{F['governing_addresses_resident']} resident and "
                     f"{F['governing_addresses_in_the_bug_bar_overlay']} inside the Bug Bar "
                     f"overlay's load window. The resident ones resolve to "
                     f"{F['governing_resident_build_units']} build units -- "
                     f"{F['governing_resident_units_matching_c']} matching C through the "
                     f"original toolchain ({F['resident_build_toolchain']}) and "
                     f"{F['governing_resident_units_hand_asm']} hand-written byte-exact ASM, "
                     f"with {F['governing_resident_addresses_outside_any_build_unit']} outside "
                     f"any unit. The C ones are {F['governing_resident_matching_c_sources']}",
            "gap": f"every writer that makes this fight what it is lives in the overlay, and "
                   f"the overlay has {F['pinned_overlay_matched_functions']} matched function "
                   f"of {F['pinned_overlay_code_functions']} -- and "
                   f"{F['pinned_overlay_matched_functions_in_the_governing_set']} of the "
                   f"matched set is in the governing set, so the hit latch, the counter, the "
                   f"perch gate and the kill have no C at all. The three resident C units that "
                   f"DO exist are peripheral (a sound-cue callback, an animation setter, a "
                   f"transform leaf); the retirement path and the berry dispatch are hand ASM. "
                   f"Note the census triage understates this in the other direction: it says "
                   f"'{F['census_triage_source_closure']}', which measures REGISTRATION -- "
                   f"measured against the row's real governing addresses there are "
                   f"{F['governing_resident_units_matching_c']}",
        },
    }

    counts: dict[str, int] = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F09_bug_bar measured against the nine DoD dimensions AS WRITTEN "
                    "(item 2 = enumerated; residuals = explicitly bounded), per "
                    "engineering-specs/phase4-measurement-standard-ruling.md. Judgments "
                    "authored; every fact derived from a pinned artifact at run time. "
                    "Regenerate: tools/phase4_f09_written_bar_assessment.py",
        "schema": "abl-phase4-f09-written-bar-assessment/1",
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
            "author_conflict": "the assessor did not author F09's underlying evidence, but "
                               "did author this assessment, the F01/F02 assessments whose "
                               "design it copies, the F-row census whose durable_evidence "
                               "result it carries forward, and the one NEW measurement in it "
                               "(tools/phase4_f09_overlay_pin.c) -- so on the overlay-file "
                               "question the tool, the claim and the judgment share an "
                               "author. Every state below is a submission to a fresh detached "
                               "verifier, not a promotion; `partial` and `not_met` are as "
                               "challengeable as `met_candidate`",
        },
        "carried_forward": {
            "dimension": "durable_evidence",
            "from": CENSUS,
            "state": F["census_durable_state"],
            "fraction": F["census_durable_fraction"],
            "note": "measured there against pinned bytes; re-deriving it here would be a "
                    "second opinion on a settled measurement, not evidence",
        },
        "inherited_dispositions": {
            "note": "F09's boss and arena were driven by OTHER rows. Their stop decisions are "
                    "recorded here for contrast and are never read as met for this row.",
            "D18_thud": {"disposition": F["d18_disposition"],
                         "scope": F["d18_disposition_scope"],
                         "baseline_status": F["d18_row_status"],
                         "move_on": F["d18_move_on"]},
            "E11_dynamic_geometry": {"disposition": F["e11_disposition"],
                                     "strict_status": F["e11_strict_status"],
                                     "baseline_status": F["e11_row_status"],
                                     "remaining_promotion_work":
                                         F["e11_remaining_promotion_work"]},
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
                    "scores the row 0/9 met. That is a disposition, not a measurement -- and "
                    "it also records movie_count "
                    f"{F['registry_movie_count']} for a row whose evidence rests on "
                    f"{F['stage9_movies_replayed_by_row_artifacts']} replayed movies",
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
                   f"unmeasured -- against the WRITTEN bars. The boss fight is the "
                   f"best-evidenced object in this row by a distance (from-boot natural "
                   f"fight law, instruction-bound writers, enumerated value domains, "
                   f"declarative scenarios and registered gates), and it belongs to D18; what "
                   f"F09 owns as a STAGE -- entry, layout, the arena's visible mapping, retry "
                   f"and reset -- is where every gap sits.",
        "notable": [
            f"THE PREMISE 'Bug Bar authors one collision sector with 45 runtime-registered, "
            f"making it the only genuinely dynamic arena' is HALF WRONG, measured. The "
            f"authored count is right ({F['stage9_authored_collision_sectors']} sector, "
            f"histogram {F['stage9_region_code_histogram']}, rank "
            f"{F['stage9_authored_sector_rank']} of {F['levels_censused']} -- the campaign "
            f"minimum, next lowest {F['second_lowest_authored_sector_count']}). The 45 is "
            f"NOT Bug-Bar-specific: the runtime-registered tail is "
            f"{F['distinct_runtime_registered_tails_campaign_wide']} in "
            f"{F['levels_with_the_same_runtime_registered_tail']}/{F['levels_censused']} "
            f"levels -- a constant engine-side tail, not dynamic arena geometry. What IS "
            f"distinctive survives the correction: at "
            f"{F['stage9_runtime_registered_fraction']} this stage has the campaign's highest "
            f"runtime-registered fraction "
            f"({F['highest_runtime_registered_fraction_is_this_stage']}), i.e. almost none of "
            f"its collision environment is authored on disc.",
            f"THE ROW'S OVERLAY IS ATTRIBUTED TO THE WRONG FILE in the semantic registry. "
            f"Every level overlay loads at the same VA, so the counter writer "
            f"{F['counter_writer_pc']} names a real instruction in "
            f"{F['overlay_images_covering_counter_writer_pc']} of the "
            f"{F['overlay_images_in_function_census']} censused overlay images; the ownership "
            f"graph picks {F['ownership_overlay_spaces_named']}. Settled here from bytes: of "
            f"{F['overlay_pin_images_scanned']} images (all overlays plus the resident EXE) "
            f"exactly {F['overlay_pin_images_with_consistent_base']} contains the three "
            f"fight-lane encodings once each with one consistent load base -- "
            f"{F['overlay_pin_file']} @ {F['overlay_pin_load_base']}, sha256 agreeing with "
            f"D18's own overlay pin ({F['overlay_pin_agrees_with_d18_sha256']}). Any future "
            f"F09 work that resolves an overlay address by VA alone will land in another "
            f"level.",
            f"THE ROW'S OWN GATES DO NOT RUN GREEN. {gate_note}. Two distinct causes, both "
            f"measured: {len(F['retained_artifact_dependency_pins_stale'])} of "
            f"{F['retained_artifact_dependency_pins_declared']} self-declared dependency pins "
            f"no longer match on-disk bytes (the central fixture manifest has legitimately "
            f"been regenerated since), and the largest retained artifacts still assert the "
            f"pre-correction scene routing, so the gate that recomputes routing now fails "
            f"BECAUSE the project fixed the claim. Neither is evidence corruption; both mean "
            f"the row's regression surface is not currently protecting it.",
            f"THE ROW UNDER-DECLARES ITS OWN EVIDENCE BASE. It declares "
            f"{F['row_declared_fixtures']} fixtures and cites "
            f"{F['row_artifact_path_citations']} artifact paths, while the census credits "
            f"{F['census_analysis_artifacts_credited']} analysis artifacts and this "
            f"assessment pins {F['row_evidence_artifacts_pinned_here']} that carry "
            f"F09-labelled evidence -- "
            f"including four large retained runtime artifacts (arena, completion, volley, "
            f"defeat) that the baseline row never names. The from-boot fight movie that the "
            f"fight law rests on is not in fixture_have "
            f"(declared={F['fight_movie_declared_by_the_row']}) and the central pin credits "
            f"it to D18 only (credited_to_F09={F['fight_movie_credited_to_this_row']}), "
            f"even though the row's own `next` field names it.",
            f"CANON IS ONE ARTIFACT STALE on the soft-lock. The system page still calls the "
            f"mega-berry link untested "
            f"(untested={F['canon_page_still_calls_the_softlock_link_untested']}), while "
            f"{NBC} closes it: {F['native_berry_variants_enumerated']} equipped-berry variants "
            f"over {F['native_damage_anchors_checked']} anchors give the effective set "
            f"{F['native_effective_damage_set']} and "
            f"softlock_band_reachable={F['native_softlock_band_reachable']} "
            f"({F['native_berry_closure_result']}). This narrows a named residual the row "
            f"still carries.",
            f"UNMEASURED HERE, and named so a verifier does not read silence as absence: "
            f"whether the {len(F['stage9_movies_never_replayed_by_row_artifacts'])} pinned "
            f"stage-9 routes this row never replays would move campaign_breadth or supply "
            f"E11's requested lifecycle coverage (that needs a replay, not a re-read); and "
            f"whether every gate failure is pin staleness rather than a real regression "
            f"({gate_note}) -- each was inspected as stale, but 'inspected' is not 'gated'.",
        ],
    }

    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar F09] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"facts: {doc['fact_provenance']['facts_derived_from_pinned_artifacts']} derived / "
          f"{doc['fact_provenance']['facts_hand_typed']} hand-typed  "
          f"({len(E.pins)} artifacts pinned)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
