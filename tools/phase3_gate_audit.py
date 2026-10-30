#!/usr/bin/env python3
"""Phase-3 EXIT-GATE audit — computes the five gate bullets themselves.

phase3_knowledge_audit.py checks that each FINDING is banked. This checks the
PHASE: it computes each of the five exit-gate bullets from committed evidence and
fails while any is open. The roadmap now requires phase closure to be SHOWN, not
asserted — "a knowledge-closure audit showing that its confirmed findings are
discoverable, represented in the machine layers, linked to evidence, guarded, and
reproducible from a clean checkout." This is that audit.

Each bullet is a COMPUTED predicate over real artifacts, never a hand-set flag —
same discipline as every other Phase-3 tool.

Usage: python3 tools/phase3_gate_audit.py
Output: analysis/phase3_gate_audit.json   (exit 1 while any bullet is open)
"""
from __future__ import annotations

import json
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import phase3_coverage_matrix as coverage_matrix  # noqa: E402
import phase3_evidence_inventory as evidence_inventory  # noqa: E402
import phase3_duckstation_rpc_manifest as rpc_manifest  # noqa: E402
import knowledge_closure_audit  # noqa: E402


def load(rel):
    return json.loads((ROOT / rel).read_text())


@lru_cache(maxsize=1)
def computed_coverage():
    """Recompute package predicates from raw inputs in this process.

    The retained matrix is a freshness target, not an authority.  This prevents
    a hand-edited ``overall_met``/``met`` flag from turning the gate green.
    """
    return coverage_matrix.build_matrix()


def bullet_1_frontier():
    """Every Phase-1 mechanic maps to a bounded semantic frontier. A behavior can
    remain an external lead when its known functions/state and next evidence are
    explicit; that is a mapped frontier, not a false behavioral closure."""
    g = load("analysis/phase3_ownership_graph.json")
    residuals = sorted(rid for rid, r in g["rows"].items() if r["gaps"])
    package = computed_coverage()["work_packages"]["WP1"]
    graph_gap_free = not residuals
    return graph_gap_free and package["met"], {
        "mechanics": g["totals"]["mechanics"],
        "address_bound": g["totals"]["bound"],
        "residuals": residuals,
        "ownership_graph_gap_free": graph_gap_free,
        "work_package_met": package["met"],
        "rows_with_open_frontier": sorted(package["rows_with_open_frontier"]),
        "note": ("A07 remains an external lead with an explicit branch/trigger "
                 "residual. An address/function binding alone is not a complete "
                 "frontier: assets, overlay, readers/writers and lifecycle are also "
                 "binding WP1 facets."),
    }


def bullet_2_state_owned():
    """Every owned state has owner, width, domain, readers/writers, init, reset,
    overlay lifetime — or an explicit blocker."""
    sem = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    life = load("analysis/phase3_semantic_lifetime.json")["entries"]
    xr = load("analysis/phase3_xrefs.json")["entries"]
    reg = {e["id"]: e for e in sem["entries"] if isinstance(e.get("address"), int)}
    incomplete = []
    invalid = {}
    for eid, e in reg.items():
        owner = bool(e.get("owner"))
        width = e.get("width") is not None or e.get("kind") in ("table", "function")
        domain = (bool(e.get("invariants")) or bool(e.get("domain"))
                  or e.get("kind") in ("table", "function"))
        li = life.get(eid, {})
        xe = xr.get(eid, {})
        rw = xe.get("statically_referenced") or bool(xe.get("no_static_xref_because"))
        reasons = []
        ol = li.get("overlay_lifetime")
        init = li.get("init")
        reset = li.get("reset")
        blocker = li.get("blocker")
        static_writers = int(xe.get("writer_count", 0))
        declared_writers = len(e.get("writers") or [])
        if ol not in ("resident_rom", "resident_ram", "overlay"):
            reasons.append(f"invalid overlay_lifetime {ol!r}")
        if not init or not reset:
            reasons.append("missing init/reset")
        if ol == "resident_rom":
            if e["address"] >= 0x80082800:
                reasons.append("address above loaded image cannot be ROM")
            if static_writers or declared_writers:
                reasons.append("state with static or declared writers cannot be immutable ROM")
            if li.get("measured") is not False:
                reasons.append("ROM classification must be a derivation, not a live measurement")
        if reset == "unchanged_zero":
            if li.get("before") != 0 or li.get("after") != 0:
                reasons.append("unchanged_zero without a 0->0 observation")
            if init != "unknown":
                reasons.append("0->0 observation cannot establish initialization")
            if not isinstance(blocker, dict) or blocker.get("kind") != \
                    "insufficient_transition_evidence":
                reasons.append("0->0 observation lacks an explicit evidence blocker")
        if init == "zeroed_at_load" and li.get("before") == li.get("after") == 0:
            reasons.append("zeroed_at_load inferred only from unchanged 0->0")
        if init == "unknown" or reset == "unknown":
            if not isinstance(blocker, dict) or not blocker.get("kind"):
                reasons.append("unknown lifecycle answer lacks an explicit blocker")
        lifetime = not reasons
        if reasons:
            invalid[eid] = reasons
        if not (owner and width and domain and lifetime and rw):
            incomplete.append(eid)
    package2 = computed_coverage()["work_packages"]["WP2"]
    package6 = computed_coverage()["work_packages"]["WP6"]
    semantic_registry_met = not incomplete
    return semantic_registry_met and package2["met"] and package6["met"], {
        "owned_entries": len(reg),
        "incomplete": incomplete,
        "semantically_invalid": sorted(invalid),
        "invalid_reasons": invalid,
        "semantic_registry_met": semantic_registry_met,
        "state_scope_work_package_met": package2["met"],
        "ownership_model_work_package_met": package6["met"],
        "missing_scope_groups": package2["missing_scope_groups"],
        "ownership_model_gaps": sorted(package6["ownership_model_gaps"]),
        "explicit_lifecycle_blockers": sorted(
            eid for eid, li in life.items() if isinstance(li.get("blocker"), dict)),
    }


def bullet_3_dispatch_and_overlays():
    """All indirect dispatch AND overlay boundaries enumerated."""
    dm = load("analysis/phase3_dispatch_map.json")
    jr = load("analysis/phase3_jr_tables.json")
    jalr = load("analysis/phase3_jalr_callbacks.json")
    ov = load("analysis/phase3_overlay_map.json")
    # every jr site is classified (table / computed / unresolved) and every jalr
    # is classified; overlays are mapped
    jr_ok = (jr["classification"]["table_dispatch"]
             + jr["classification"]["computed_code_jump"]
             + jr["classification"]["unresolved"]) == jr["jr_sites"]
    jalr_ok = sum(jalr["classification"].values()) == jalr["jalr_sites"]
    ov_ok = ov["overlays"] >= 18
    package4 = computed_coverage()["work_packages"]["WP4"]
    package7 = computed_coverage()["work_packages"]["WP7"]
    enumeration_met = jr_ok and jalr_ok and ov_ok
    return enumeration_met and package4["met"] and package7["met"], {
        "indirect_sites": dm["indirect_sites"]["total"],
        "jr_classified": jr_ok, "jalr_classified": jalr_ok,
        "overlays_mapped": ov["overlays"],
        "enumeration_met": enumeration_met,
        "dispatch_work_package_met": package4["met"],
        "scene_load_unload_work_package_met": package7["met"],
        "scene_graph_gaps": package7["gaps"],
    }


def bullet_4_hook_contracts():
    """Every hook cave honors its declared contract, machine-checked against the
    PINNED full-module image: it corrupts no live register it did not DECLARE in
    `clobbers`, commits no structural hazard (k0/k1, split load-delay, no terminal
    `j resume`, an unreimplemented displaced branch, a jump into the trampoline),
    and every intentional continuation change is declared and surfaced.

    `hard_violations == 0` is NECESSARY but NOT SUFFICIENT — on a clone without the
    patched image, discharge is 0 and nothing is checked, yet hard_violations is
    still 0. So this ALSO requires: (a) the on-disk image MATCHES the manifest hash
    pin (a stale image is not trusted); (b) ZERO obligated hooks are still `owed`
    (module absent from the image); and (c) every obligated hook is DISCHARGED
    against its built cave or honestly DEGRADED with a stated reason (recovered
    extent / undecoded jr). Vacuous green is not met."""
    h = load("analysis/phase3_hook_contracts.json")
    s = h["summary"]
    obligated = [c for c in h["contracts"].values() if c.get("obligations")]
    discharged = s["obligations_DISCHARGED_against_the_built_cave"]
    degraded = s.get("degraded_recovered_or_undecoded", 0)
    unverified = s.get("cave_UNVERIFIED_analysis_too_coarse", 0)
    owed = s.get("module_not_in_this_image_obligation_owed", 0)
    image_matches = bool(s.get("patched_image_matches_pin"))
    patched_pinned = image_matches and bool(h.get("patched_fixture_sha256"))
    # every obligated hook accounted as discharged OR honestly degraded; a lingering
    # cave_unverified or owed hook is NOT accounted.
    accounted = ((discharged + degraded) >= len(obligated)
                 and unverified == 0 and owed == 0) if obligated else True
    met = (s["hard_violations"] == 0 and patched_pinned and accounted)
    return met, {
        "hooks": s["hooks"],
        "hard_violations": s["hard_violations"],
        "patched_image_pinned": patched_pinned,
        "patched_image_matches_pin": image_matches,
        "obligated_hooks": len(obligated),
        "discharged_against_cave": discharged,
        "degraded_with_reason": degraded,
        "cave_unverified_remaining": unverified,
        "module_owed": owed,
        "refused_needs_review": s["refused_needs_review"],
    }


def bullet_5_unknowns_visible():
    """Unknowns remain visible and cannot silently become confirmed. Computed
    DIRECTLY from the findings registry and the record accounting — NOT from the
    knowledge-audit result, which would be circular (the knowledge audit is a
    separate check; the gate must not consume its verdict). Met = every finding
    carries an explicit confidence + residuals (unknowns named, not hidden), and
    every typed record still declares its unknown byte spans."""
    findings = yaml.safe_load(
        (ROOT / "config" / "phase3_findings.yaml").read_text())["findings"]
    rec = load("analysis/phase3_record_types.json")
    VOCAB = {"confirmed", "partial", "inferred", "disproven", "blocked"}
    findings_ok = all(f.get("confidence") in VOCAB
                      and str(f.get("residuals") or "").strip()
                      for f in findings)
    spans_ok = all(r["unknown_bytes"] >= 0 and
                   (r["unknown_bytes"] == 0 or r["unknown_spans"])
                   for r in rec["records"].values())
    package5 = computed_coverage()["work_packages"]["WP5"]
    package9 = computed_coverage()["work_packages"]["WP9"]
    local_unknowns_met = findings_ok and spans_ok
    return local_unknowns_met and package5["met"] and package9["met"], {
        "findings": len(findings),
        "all_findings_have_confidence_and_residuals": findings_ok,
        "record_unknown_accounting_intact": spans_ok,
        "local_unknowns_met": local_unknowns_met,
        "record_family_work_package_met": package5["met"],
        "contradiction_work_package_met": package9["met"],
        "missing_record_families": package5["missing_record_families"],
        "documentation_contradictions": package9["documentation_contradictions"],
    }


def coverage_matrix_status():
    retained = load("analysis/phase3_coverage_matrix.json")
    matrix = computed_coverage()
    unmet = sorted(
        key for key, pkg in matrix["work_packages"].items() if not pkg["met"])
    retained_cmp = dict(retained)
    computed_cmp = dict(matrix)
    retained_cmp.pop("generated", None)
    computed_cmp.pop("generated", None)
    fresh = retained_cmp == computed_cmp
    return matrix["overall_met"] and not unmet and fresh, {
        "overall_met": matrix["overall_met"],
        "unmet_packages": unmet,
        "retained_artifact_fresh": fresh,
        "packages": {key: pkg["description"] for key, pkg in matrix["work_packages"].items()},
    }


def evidence_inventory_status():
    retained = load("analysis/phase3_evidence_inventory.json")
    computed = evidence_inventory.build_inventory()
    retained_cmp = dict(retained)
    computed_cmp = dict(computed)
    retained_cmp.pop("generated", None)
    computed_cmp.pop("generated", None)
    fresh = retained_cmp == computed_cmp
    return computed["closure_ready"] and fresh, {
        "closure_ready": computed["closure_ready"],
        "retained_artifact_fresh": fresh,
        "summary": computed["summary"],
    }


def debugger_api_documentation_status():
    """Recompute retained RPC lists/counts and their generated documentation.

    The gate also compares this retained snapshot with ``~/duckstation`` itself.
    The prior design delegated that decisive predicate to a separate local-media
    command, allowing the gate to remain MET after the dispatcher or binary had
    changed.  Closure now fails on absent, unparsable, or drifted external source.
    """
    retained = load("analysis/phase3_duckstation_rpc_manifest.json")
    markdown = (ROOT / "tools/duckstation_rpc_method_manifest.md").read_text()
    canon = (ROOT / "ObsidianVault/Canon/Indexes/DuckStation_API_Index.md").read_text()
    retained_gaps = rpc_manifest.retained_gaps(retained, markdown, canon)
    current_gaps = rpc_manifest.current_fork_gaps(retained)
    gaps = [*retained_gaps, *current_gaps]
    counts = retained.get("methods", {}).get("counts", {})
    return not gaps, {
        "computed_from_method_lists": True,
        "current_fork_compared_by_gate": True,
        "current_fork_fresh": not current_gaps,
        "counts": counts,
        "source_revision": retained.get("source", {}).get("revision"),
        "dispatcher_sha256": retained.get("source", {}).get("dispatcher_sha256"),
        "retained_gaps": retained_gaps,
        "current_fork_gaps": current_gaps,
        "gaps": gaps,
    }


def upstream_durability_status():
    """Recompute source/fixture/address durability below the legacy phase labels.

    Phase-0..2 ``knowledge_status`` labels remain historical and intentionally
    partial; they are not predicates.  The Phase-3 dependency is the concrete
    absence of matrix, import, source-pin, fixture-pin, and address-promotion
    gaps in the current tracked snapshot.
    """
    report, fixture_set = knowledge_closure_audit.build_report()
    blockers = {
        key: value for key, value in report["strict_blockers"].items()
        if key != "knowledge_phases_not_closed"
    }
    retained_report = load("analysis/phase0_2_knowledge_closure_report.json")
    retained_fixtures = load("analysis/phase0_2_external_fixture_set.json")

    def without_generated(doc):
        result = dict(doc)
        result.pop("generated", None)
        return result

    report_fresh = without_generated(retained_report) == without_generated(report)
    fixtures_fresh = without_generated(retained_fixtures) == without_generated(fixture_set)
    blockers["retained_knowledge_report_stale"] = [] if report_fresh else [
        "analysis/phase0_2_knowledge_closure_report.json differs from low-level recomputation"
    ]
    blockers["retained_external_fixture_set_stale"] = [] if fixtures_fresh else [
        "analysis/phase0_2_external_fixture_set.json differs from low-level recomputation"
    ]
    met = not any(bool(value) for value in blockers.values())
    return met, {
        "computed_from_low_level_predicates": True,
        "retained_knowledge_report_fresh": report_fresh,
        "retained_external_fixture_set_fresh": fixtures_fresh,
        "blockers": blockers,
        "historical_phase_labels": report["phase_status"],
    }


LIVE_PROVENANCE_FIELDS = (
    "command", "generator_sha256", "provenance_helper_sha256", "repository_head",
    "duckstation", "debugger", "anchor", "timing", "cleanup",
)


def live_provenance_gaps(doc, *, generator=None):
    run = doc.get("run_provenance")
    if not isinstance(run, dict):
        return ["run_provenance absent"]
    gaps = [key for key in LIVE_PROVENANCE_FIELDS if not run.get(key)]
    if run.get("provenance_helper_sha256") != \
            evidence_inventory.current_provenance_helper_sha256():
        gaps.append("provenance_helper_sha256 is stale")
    if generator != "tools/phase3_transition_reset.py" and \
            run.get("launcher_helper_sha256") != \
            evidence_inventory.current_launcher_helper_sha256():
        gaps.append("launcher_helper_sha256 is stale")
    if generator is not None and run.get("generator_sha256") != \
            evidence_inventory.sha256(ROOT / generator):
        gaps.append("generator_sha256 is stale")
    duck = run.get("duckstation") or {}
    for key in ("revision", "status", "binary_path", "binary_sha256"):
        if not duck.get(key):
            gaps.append(f"duckstation.{key}")
    dbg = run.get("debugger") or {}
    for key in ("config_dir", "port", "transport", "token_sha256", "recreated"):
        if key not in dbg or dbg.get(key) in (None, ""):
            gaps.append(f"debugger.{key}")
    config_dir = str(dbg.get("config_dir") or "")
    if config_dir and (not Path(config_dir).is_absolute() or not config_dir.startswith("/tmp/")):
        gaps.append("debugger.config_dir is not an absolute /tmp isolation directory")
    cleanup = run.get("cleanup") or {}
    if cleanup.get("owned_pid_stopped") is not True:
        gaps.append("cleanup.owned_pid_stopped")
    anchor = run.get("anchor") or {}
    save_count = int(bool(anchor.get("save"))) + len(anchor.get("saves") or [])
    inspections = anchor.get("state_inspections") or []
    if save_count and len(inspections) < save_count:
        gaps.append(
            f"anchor.state_inspections has {len(inspections)} for {save_count} save anchors")
    return gaps


def decisive_evidence_status():
    spin = load("analysis/phase3_spin_functional.json")
    thud = load("analysis/phase3_thud.json")
    life = load("analysis/phase3_semantic_lifetime.json")
    hook = load("analysis/phase3_hook_contracts.json")
    transition = load("analysis/phase3_transition_reset.json")
    rpc = load("analysis/phase3_duckstation_rpc_manifest.json")
    aggregate_artifacts = {
        rel: load(rel) for rel in (
            "analysis/phase3_record_probe.json",
            "analysis/phase3_render_descriptors.json",
            "analysis/phase3_fn_ptr_fields.json",
        )
    }

    spin_log = spin.get("access_log_accounting", {})
    spin_observation_ok = (
        spin.get("classification") == "bounded_negative"
        and spin.get("disproven") is False
        and not spin.get("undocumented_values")
        and len(spin.get("state_word_owning_function_starts") or []) == 1
        and bool(spin.get("state_word_writer_pcs"))
        and not spin.get("unnamed_block_writer_pcs")
        and spin_log.get("truncated_batches") == 0
        and spin_log.get("unstable_total_batches") == 0
        and spin_log.get("watch_cap_saturated_batches") == 0
        and spin_log.get("incomplete_batches") == 0
        and spin_log.get("events_returned") == spin_log.get("events_total")
        and spin.get("media_identity_after_connect", {}).get("hash_verification", {}).get("pristine_verified") is True
    )
    thud_log = thud.get("retire_handler", {}).get("access_log", {})
    boss = thud.get("boss_identity", {})
    threshold = thud.get("defeat_threshold", {})
    thud_observation_ok = (
        boss.get("id") == 0x24
        and boss.get("hp_at_0x6e") == 50
        and threshold.get("hp1_survives", {}).get("boss_still_live") is True
        and threshold.get("hp0_retires", {}).get("boss_removed") is True
        and thud_log.get("returned") == thud_log.get("total")
        and thud_log.get("truncated") is False
        and thud_log.get("totals_stable") is True
        and thud_log.get("watch_cap_saturated") is False
        and thud.get("media_identity_after_connect", {}).get("hash_verification", {}).get("pristine_verified") is True
    )
    life_entries = life.get("entries", {})
    unchanged_zero_without_blocker = sorted(
        eid for eid, row in life_entries.items()
        if row.get("reset") == "unchanged_zero"
        and not isinstance(row.get("blocker"), dict)
    )
    life_observation_ok = (
        life.get("media_identity_before_playback", {}).get("hash_verification", {}).get("pristine_verified") is True
        and bool(life.get("playback_provenance", {}).get("movie"))
        and not unchanged_zero_without_blocker
    )
    hook_summary = hook["summary"]
    hook_ok = (
        bool(hook_summary.get("patched_image_matches_pin"))
        and hook_summary.get("hard_violations") == 0
        and hook_summary.get("module_not_in_this_image_obligation_owed", 0) == 0
    )
    transition_snapshot = (transition.get("run_provenance") or {}).get(
        "toolchain_snapshot") or {}
    transition_dependencies = (transition.get("run_provenance") or {}).get(
        "source_dependencies") or {}
    required_transition_dependencies = {
        rel: evidence_inventory.sha256(ROOT / rel)
        for rel in (
            "tools/live_toolchain_snapshot.py",
            "tools/launch_repro_playback.sh",
        )
    }
    current_release = rpc.get("binaries", {}).get(
        "build-release/bin/duckstation-qt", {})
    rpc_source = rpc.get("source") or {}
    rpc_runtime = rpc.get("runtime_trees", {}).get("build-release/bin")
    snapshot_files = transition_snapshot.get("files") or {}
    required_snapshot_files = {
        rel: rpc_source.get("files", {}).get(rel)
        for rel in (
            "scripts/debugger-client/launch_debugger_instance.sh",
            "scripts/debugger-client/duckstation_debug_client.py",
        )
    }
    transition_cleanup = (transition.get("run_provenance") or {}).get("cleanup") or {}
    private_cleanup_path = Path(transition_cleanup.get("private_binary_path") or "")
    transition_snapshot_ok = (
        transition.get("stages_measured") == 16
        and not transition.get("skipped")
        and transition_snapshot.get("verified") is True
        and transition_snapshot.get("binary_sha256") == current_release.get("sha256")
        and transition_snapshot.get("source_binary_path") ==
            str(Path.home() / "duckstation/build-release/bin/duckstation-qt")
        and transition_snapshot.get("source", {}).get("revision") ==
            rpc_source.get("revision")
        and transition_snapshot.get("source", {}).get("status_sha256") ==
            rpc_source.get("status_sha256")
        and transition_snapshot.get("source", {}).get("dispatcher_sha256") ==
            rpc_source.get("dispatcher_sha256")
        and transition_snapshot.get("source", {}).get("method_count") ==
            rpc.get("methods", {}).get("counts", {}).get("current")
        and transition_snapshot.get("retained_rpc_manifest_sha256") ==
            evidence_inventory.sha256(
                ROOT / "analysis/phase3_duckstation_rpc_manifest.json")
        and transition_snapshot.get("runtime_tree") == rpc_runtime
        and snapshot_files == required_snapshot_files
        and transition_dependencies == required_transition_dependencies
        and transition.get("run_provenance", {}).get("duckstation", {}).get(
            "binary_sha256") == current_release.get("sha256")
        and transition.get("run_provenance", {}).get("anchor", {}).get(
            "media_identity", {}).get("hash_verification", {}).get(
                "pristine_verified") is True
        and transition_cleanup.get("owned_pid_stopped") is True
        and transition_cleanup.get("private_binary_removed") is True
        and transition_cleanup.get("private_binary_sha256") ==
            current_release.get("sha256")
        and private_cleanup_path.parent ==
            Path.home() / "duckstation/build-release/bin"
        and private_cleanup_path.name.startswith("duckstation-qt.phase3-verifier-")
    )
    provenance_gaps = {
        "spin": live_provenance_gaps(
            spin, generator="tools/phase3_spin_functional.py"),
        "thud": live_provenance_gaps(
            thud, generator="tools/phase3_thud_trace.py"),
        "semantic_lifetime": live_provenance_gaps(
            life, generator="tools/phase3_semantic_lifetime.py"),
        "transition": live_provenance_gaps(
            transition, generator="tools/phase3_transition_reset.py"),
    }
    provenance_ok = not any(provenance_gaps.values())
    aggregate_origin_gaps = {
        rel: evidence_inventory.required_state_media_provenance_gaps(
            doc, require_selection=True)
        for rel, doc in aggregate_artifacts.items()
    }
    aggregate_origins_ok = not any(aggregate_origin_gaps.values())
    met = (spin_observation_ok and thud_observation_ok and life_observation_ok
           and hook_ok and transition_snapshot_ok and provenance_ok
           and aggregate_origins_ok)
    return met, {
        "spin_low_level_predicates_met": spin_observation_ok,
        "thud_low_level_predicates_met": thud_observation_ok,
        "semantic_lifetime_low_level_predicates_met": life_observation_ok,
        "hook_contract_fresh": hook_ok,
        "transition_immutable_toolchain_replay_met": transition_snapshot_ok,
        "transition_snapshot": transition_snapshot,
        "transition_cleanup": transition_cleanup,
        "transition_required_source_dependencies": required_transition_dependencies,
        "live_run_provenance_complete": provenance_ok,
        "live_run_provenance_gaps": provenance_gaps,
        "aggregate_pristine_save_origins_met": aggregate_origins_ok,
        "aggregate_pristine_save_origin_gaps": aggregate_origin_gaps,
        "unchanged_zero_without_blocker": unchanged_zero_without_blocker,
    }


BULLETS = [
    ("1_mechanic_frontier", bullet_1_frontier),
    ("2_state_ownership", bullet_2_state_owned),
    ("3_dispatch_and_overlays", bullet_3_dispatch_and_overlays),
    ("4_hook_contracts", bullet_4_hook_contracts),
    ("5_unknowns_visible", bullet_5_unknowns_visible),
]


def main() -> int:
    results, all_met = {}, True
    for name, fn in BULLETS:
        met, detail = fn()
        results[name] = {"met": met, **detail}
        all_met = all_met and met
    coverage_met, coverage = coverage_matrix_status()
    inventory_met, inventory = evidence_inventory_status()
    rpc_met, rpc = debugger_api_documentation_status()
    decisive_met, decisive = decisive_evidence_status()
    upstream_met, upstream = upstream_durability_status()
    all_met = (all_met and coverage_met and inventory_met and rpc_met
               and decisive_met and upstream_met)

    doc = {
        "_comment": "Phase-3 EXIT-GATE audit: the five gate bullets themselves, each "
                    "COMPUTED from committed evidence (never a hand-set flag), so "
                    "phase closure is SHOWN not asserted. Exit 1 while any bullet is "
                    "open. Regenerate: python3 tools/phase3_gate_audit.py",
        "generated": date.today().isoformat(),
        "gate_met": all_met,
        "coverage_matrix": {"met": coverage_met, **coverage},
        "evidence_inventory": {"met": inventory_met, **inventory},
        "debugger_api_documentation": {"met": rpc_met, **rpc},
        "upstream_durability": {"met": upstream_met, **upstream},
        "decisive_evidence": {"met": decisive_met, **decisive},
        "bullets": results,
    }
    path = ROOT / "analysis" / "phase3_gate_audit.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[gate] Phase-3 exit gate: {'MET' if all_met else 'OPEN'}")
    print(f"  {'MET ' if coverage_met else 'OPEN'} coverage matrix: {coverage}")
    print(f"  {'MET ' if inventory_met else 'OPEN'} evidence inventory: {inventory}")
    print(f"  {'MET ' if upstream_met else 'OPEN'} upstream durability: {upstream}")
    print(f"  {'MET ' if decisive_met else 'OPEN'} decisive evidence: {decisive}")
    for name, r in results.items():
        mark = "MET " if r["met"] else "OPEN"
        extra = {k: v for k, v in r.items() if k != "met"}
        print(f"  {mark} bullet {name}: {extra}")
    return 0 if all_met else 1


if __name__ == "__main__":
    raise SystemExit(main())
