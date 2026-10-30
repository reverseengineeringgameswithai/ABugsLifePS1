#!/usr/bin/env python3
"""Phase-3 WP9 contradiction ledger, recomputed from authoritative surfaces.

The ledger does not declare prose to be correct because it sounds plausible.  Each
row compares at least two independent representations and reports ``open`` unless
the low-level predicates below agree.  ``bounded`` means the disagreement has an
explicit authority boundary and residual; it does not mean the unknown was solved.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import yaml

import phase3_duckstation_rpc_manifest as rpc_manifest
import phase3_evidence_inventory as evidence_inventory

ROOT = Path(__file__).resolve().parents[1]
HUB = "ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md"
PHASE = "ObsidianVault/Playbooks/Game Solving Roadmap/Phase 3 - Reconstruct Semantic Architecture and State Ownership.md"
ACTION_CANON = "ObsidianVault/Canon/Systems/SYS_player_action_state_laws.md"
SCENE_CANON = "ObsidianVault/Canon/Systems/SYS_scene_asset_load_graph.md"
RECORD_CANON = "ObsidianVault/Canon/Systems/SYS_record_layouts_and_lifetimes.md"
A07_EXPERIMENT = "ObsidianVault/Experiments/Runtime Tests/EXP_2026-07-13_a07_spin_move_disproof.md"
RPC_CANON = "ObsidianVault/Canon/Indexes/DuckStation_API_Index.md"
RPC_MANIFEST = "analysis/phase3_duckstation_rpc_manifest.json"
RPC_MARKDOWN = "tools/duckstation_rpc_method_manifest.md"


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def load_yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text())


def sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def checked(category: str, *paths: str) -> dict:
    return {
        "category": category,
        "files": [{"path": path, "sha256": sha256(path)} for path in paths],
    }


def row(rid: str, *, surfaces: list[str], predicate: bool, observation: str,
        resolution: str, evidence: list[str], bounded: bool = False,
        residual: str = "") -> dict:
    return {
        "id": rid,
        "status": ("bounded" if bounded else "reconciled") if predicate else "open",
        "surfaces": surfaces,
        "predicate_met": predicate,
        "observation": observation,
        "resolution": resolution,
        "evidence": evidence,
        "residual": residual,
    }


def build_ledger() -> dict:
    mechanics = {r["id"]: r for r in load_yaml("analysis/mechanics_baseline.yaml")["rows"]}
    findings = {r["id"]: r for r in load_yaml("config/phase3_findings.yaml")["findings"]}
    sem = {r["id"]: r for r in load_yaml("config/semantic_state.yaml")["entries"]
           if isinstance(r.get("address"), int)}
    records_cfg = {r["id"]: r for r in load_yaml("config/record_types.yaml")["records"]}
    records = load_json("analysis/phase3_record_types.json")
    xrefs = load_json("analysis/phase3_xrefs.json")
    lifetime = load_json("analysis/phase3_semantic_lifetime.json")
    scene = load_json("analysis/phase3_scene_asset_graph.json")
    assets = load_json("analysis/phase3_asset_provenance.json")
    hook = load_json("analysis/phase3_hook_contracts.json")
    spin = load_json("analysis/phase3_spin_functional.json")
    thud = load_json("analysis/phase3_thud.json")
    render = load_json("analysis/phase3_render_descriptors.json")
    training = load_json("analysis/phase3_training_anchor_fixture.json")
    hub = (ROOT / HUB).read_text()
    phase = (ROOT / PHASE).read_text()
    action_canon = (ROOT / ACTION_CANON).read_text()
    scene_canon = (ROOT / SCENE_CANON).read_text()
    record_canon = (ROOT / RECORD_CANON).read_text()
    record_canon_normalized = " ".join(record_canon.split())
    experiment = (ROOT / A07_EXPERIMENT).read_text()
    rpc_doc = load_json(RPC_MANIFEST)
    rpc_markdown = (ROOT / RPC_MARKDOWN).read_text()
    rpc_canon = (ROOT / RPC_CANON).read_text()
    rpc_gaps = rpc_manifest.retained_gaps(rpc_doc, rpc_markdown, rpc_canon)
    training_run = training.get("run_provenance") or {}
    training_ok = (
        not evidence_inventory.training_regeneration_gaps(training)
        and training_run.get("generator_sha256") ==
            sha256("tools/phase3_training_anchor_fixture.py")
        and training_run.get("provenance_helper_sha256") ==
            evidence_inventory.current_provenance_helper_sha256()
        and training_run.get("launcher_helper_sha256") ==
            evidence_inventory.current_launcher_helper_sha256()
        and (training_run.get("cleanup") or {}).get("owned_pid_stopped") is True
    )

    a07_docs_ok = all("A07 spin DISPROVEN" not in text and
                      "A07_spin — DISPROVEN" not in text
                      for text in (hub, phase, action_canon, experiment))
    a07_ok = (
        mechanics["A07_spin"]["status"] == "external_lead"
        and findings["spin_move_bounded_negative"]["confidence"] == "partial"
        and spin.get("classification") == "bounded_negative"
        and spin.get("disproven") is False
        and a07_docs_ok
    )
    thud_ok = (
        mechanics["F09_bug_bar"]["status"] == "partial"
        and mechanics["D18_thud"]["status"] == "partial"
        and thud.get("bound") is True
        and thud.get("boss_identity", {}).get("id") == 0x24
    )
    unchanged_zero = {
        eid: state for eid, state in lifetime["entries"].items()
        if state.get("reset") == "unchanged_zero"
    }
    lifetime_ids_ok = set(lifetime["entries"]) == set(sem)
    zero_blockers_ok = all(
        state.get("before") == state.get("after") == 0
        and state.get("init") == "unknown"
        and (state.get("blocker") or {}).get("kind") == "insufficient_transition_evidence"
        for state in unchanged_zero.values()
    )
    writable_rom = []
    for eid, state in lifetime["entries"].items():
        entry = sem[eid]
        xe = xrefs["entries"].get(eid, {})
        if state.get("overlay_lifetime") == "resident_rom" and (
                entry.get("writers") or xe.get("writer_count") or entry["address"] >= 0x80082800):
            writable_rom.append(eid)
    lifetime_ok = lifetime_ids_ok and zero_blockers_ok and not writable_rom

    scene17 = [r for r in scene.get("exceptional_routes", []) if r.get("scene") == 17]
    scene_ok = (
        len(scene17) == 1 and not scene.get("gaps")
        and scene17[0].get("route", {}).get("resource_dispatch_target") == "0x8003CFC4"
        and "0x8003CFC4" in scene_canon and "LEVEL00" in scene_canon
        and "computed gap" not in scene_canon
    )
    schema_ok = (
        set(records_cfg) == set(records.get("records", {}))
        and all(r["unknown_bytes"] == 0 or r.get("unknown_spans")
                for r in records["records"].values())
        and "181/524" in record_canon
    )
    asset_ok = (
        assets.get("exhaustive") is True
        and not assets.get("summary", {}).get("missing_required_roles")
        and not assets.get("summary", {}).get("hash_mismatches_or_missing")
    )
    asm_c_ok = (
        hook["summary"].get("patched_image_matches_pin") is True
        and hook["summary"].get("hard_violations") == 0
        and hook["summary"].get("cave_UNVERIFIED_analysis_too_coarse") == 0
        and "documentation-grade pseudocode" in
        (ROOT / "src_re/player_update_80048138.c").read_text()
    )
    xref_ok = not xrefs.get("declared_writer_contradictions")
    render_expected = [
        "+0x04", "+0x06", "+0x07", "+0x08", "+0x0A",
    ]
    render_owner = sem["original.object_pointer_list"]
    render_record = records_cfg["render_descriptor_pointer_entry"]
    render_ok = (
        render.get("pointer_table_is_scene_invariant") is True
        and render.get("scene_dependent_bytes") == render_expected
        and render.get("invariant_bytes") == [
            "+0x00", "+0x01", "+0x02", "+0x03", "+0x05", "+0x09", "+0x0B"]
        and render.get("writer_attribution", {}).get("status") == "unresolved"
        and render_owner.get("confidence") == "runtime_seen"
        and render_owner.get("writers", [{}])[0].get("name") ==
            "unresolved_scene_initialization_path"
        and render_record["ownership_model"]["reset"].get("confidence") == "partial"
        and "does not identify their writer" in record_canon_normalized
    )
    actor_unknown = load_json("analysis/phase3_unknown_fields.json")["subjects"]["actor_record"]
    actor_finding = findings["actor_motion_and_y_disproof"]
    actor_record = records_cfg["actor_record"]
    actor_ok = (
        actor_unknown.get("anchor") == "level01.sav"
        and actor_unknown.get("actor_id") == 14
        and actor_unknown.get("frames") == 40
        and len(actor_unknown.get("findings", [])) == 2
        and [field.get("offset") for field in actor_unknown["findings"]] ==
            ["0x1C", "0x24"]
        and actor_finding.get("confidence") == "partial"
        and "42-anchor/92-tick" in actor_finding.get("supersedes", [""])[0]
        and "+0x20 remains unknown" in actor_record["lifetime"]
        and "one actor/anchor" in record_canon_normalized
        and "bounded residual" in record_canon_normalized
        and "one Level01 actor" in phase
    )
    terrain_hook = hook["contracts"].get("blackberry:terrain_emitter_color", {})
    hook_summary = hook.get("summary") or {}
    hook_docs_ok = (
        terrain_hook.get("status") == "degraded"
        and terrain_hook.get("liveness", {}).get("confidence") == "degraded"
        and terrain_hook.get("liveness", {}).get("degraded_reason") ==
            "recovered_extent"
        and terrain_hook.get("post_build", {}).get("discharged") is True
        and terrain_hook.get("post_build", {}).get("confidence") == "degraded"
        and hook_summary.get("proven_outright") == 5
        and hook_summary.get(
            "obligations_DISCHARGED_against_the_built_cave") == 9
        and hook_summary.get("degraded_recovered_or_undecoded") == 1
        and "claimed clobbers are now automatically checked" in hub
        and "9 exact-confidence discharged + 1 degraded" in phase
        and "9 exact-confidence DISCHARGED + 1 DEGRADED" in
            findings["hook_continuation_contracts_machine_checked"]["mod_contract"]
    )

    rows = [
        row(
            "a07_absolute_disproof_vs_bounded_negative",
            surfaces=["runtime", "mechanic_registry", "finding_registry", "Canon", "roadmap"],
            predicate=a07_ok,
            observation="The retained battery found no distinct state/writer but cannot exclude a branch inside a named function or an untested trigger.",
            resolution="A07 is an external lead; the runtime result is a bounded negative, never an absolute disproof.",
            evidence=["analysis/phase3_spin_functional.json", "analysis/mechanics_baseline.yaml", ACTION_CANON, A07_EXPERIMENT],
            bounded=True,
            residual="Obtain the external source's exact input sequence, context, and expected effect, then replay it on pristine media.",
        ),
        row(
            "thud_identity_vs_unsolved_encounter",
            surfaces=["runtime", "mechanic_registry", "Canon"],
            predicate=thud_ok,
            observation="Poke-falsification binds enemy id 0x24 and the HP=0 retirement edge; it does not solve the arena or every phase.",
            resolution="Keep F09 and D18 partial while treating the boss identity/retirement boundary as confirmed.",
            evidence=["analysis/phase3_thud.json", "analysis/mechanics_baseline.yaml"],
            bounded=True,
            residual="Phase 4 must map the full encounter state machine and arena semantics.",
        ),
        row(
            "zero_to_zero_vs_initialization_claim",
            surfaces=["runtime", "semantic_registry", "generated_lifetime"],
            predicate=lifetime_ok,
            observation=f"{len(unchanged_zero)} scalar observations are unchanged 0->0 and therefore establish neither initialization nor reset.",
            resolution="Retain init=unknown and an insufficient-transition-evidence blocker for every unchanged-zero field; reject writable/BSS ROM classifications.",
            evidence=["analysis/phase3_semantic_lifetime.json", "config/semantic_state.yaml", "analysis/phase3_xrefs.json"],
            bounded=bool(unchanged_zero),
            residual="Each unchanged-zero field needs a deterministic nonzero->reset experiment before its reset law can be promoted.",
        ),
        row(
            "declared_writers_vs_static_store_scan",
            surfaces=["disassembly", "C", "semantic_registry", "generated_xrefs"],
            predicate=xref_ok,
            observation="Direct EXE scans cannot resolve pointer-based stores or overlay writers and must not contradict declared writers solely because no absolute store was found.",
            resolution="The xref report separates real contradictions from pointer/overlay method limits; no declared direct writer is contradicted.",
            evidence=["analysis/phase3_xrefs.json", "config/semantic_state.yaml", "analysis/functions.json"],
        ),
        row(
            "training_off_table_vs_silent_omission",
            surfaces=["disassembly", "runtime", "asset_observation", "Canon"],
            predicate=scene_ok,
            observation="Scene 17 lies outside the 15-row campaign table but dispatches through table 0x8001AFB0 index 16 to 0x8003CFC4 and owns pinned LEVEL00 assets.",
            resolution="Model Training as an explicit exceptional resident/shared route, not as a gap or a fabricated Region-A code overlay.",
            evidence=["analysis/phase3_scene_asset_graph.json", "analysis/phase3_jr_tables.json", SCENE_CANON],
        ),
        row(
            "training_fixture_pin_vs_actual_cold_boot_regeneration",
            surfaces=["runtime", "fixture_registry", "generator", "debugger_lifecycle"],
            predicate=training_ok,
            observation="The old generator accepted an existing pinned save without replaying its from-boot movie; the nominal frame-6900 RPC also raced while the guest was running.",
            resolution="Pause before playback, advance from index 0 to 6904, require emulator frame 6905/cycle 3909055795, byte-compare the transient save with the central pin, and stop only the exact config-owned PID.",
            evidence=["analysis/phase3_training_anchor_fixture.json",
                      "analysis/phase0_2_external_fixture_set.json",
                      "tools/phase3_training_anchor_fixture.py",
                      "tools/launch_phase3_debugger.py"],
        ),
        row(
            "asset_roles_vs_staged_hash_registry",
            surfaces=["asset_observation", "build_schema", "generated_artifact"],
            predicate=asset_ok,
            observation="Asset role claims are meaningful only for the exact centrally pinned staged inputs.",
            resolution="Enumerate every pinned staged input, verify its hash, and retain load-owner evidence for every required Phase-3 role.",
            evidence=["analysis/phase3_asset_provenance.json", "tools/build_baselines.json"],
        ),
        row(
            "record_schema_vs_generated_byte_accounting",
            surfaces=["C", "record_schema", "generated_artifact", "Canon"],
            predicate=schema_ok,
            observation="Family labels must not erase unknown bytes or outrun the generated record census.",
            resolution="Require identical record IDs, explicit unknown spans, family evidence, and the current 181/524-byte accounting in Canon.",
            evidence=["config/record_types.yaml", "analysis/phase3_record_types.json", "src_re/re_types.h", RECORD_CANON],
        ),
        row(
            "actor_y_absence_claim_vs_retained_evidence",
            surfaces=["runtime", "record_schema", "finding_registry", "Canon", "roadmap"],
            predicate=actor_ok,
            observation="The retained drainer artifact contains one Level01 actor, 40 frames, two promoted horizontal fields, and no rejected Y-candidate table; it cannot establish the former 42-anchor/92-tick absence claim.",
            resolution="Supersede the campaign-wide Y-field absence claim, retain the exact X/Z sample, and leave +0x20 and vertical ownership unknown.",
            evidence=["analysis/phase3_unknown_fields.json", "config/record_types.yaml", "config/phase3_findings.yaml", RECORD_CANON, PHASE],
            bounded=True,
            residual="Capture multiple vertically moving actor families and retain every aligned field candidate and mismatch count before promoting any Y-field identity or absence claim.",
        ),
        row(
            "render_snapshot_variance_vs_loader_causality",
            surfaces=["runtime_snapshot", "semantic_registry", "record_schema", "Canon"],
            predicate=render_ok,
            observation="Strict-pristine post-load anchors prove five scene-dependent target-byte offsets and seven invariant offsets; the former four extra changes came from an ALLMODS-origin save. Snapshots do not observe the writes.",
            resolution="Retain stable pointer identity and exact byte variance, but keep writer, ownership-transfer, and reset attribution partial.",
            evidence=["analysis/phase3_render_descriptors.json", "config/semantic_state.yaml", "config/record_types.yaml", RECORD_CANON],
            bounded=True,
            residual="Cold-boot or transition with write watches over the descriptor targets must attribute exact writer PCs before loader causality is promoted.",
        ),
        row(
            "documentation_c_vs_byte_authority",
            surfaces=["disassembly", "C", "hook_schema", "built_diagnostic_image"],
            predicate=asm_c_ok,
            observation="Documentation-grade src_re C expresses semantics but is not automatically a byte-exact substitute for original instructions or continuation state.",
            resolution="Keep the function census/original bytes authoritative and discharge diagnostic continuation contracts against the pinned independent build.",
            evidence=["analysis/functions.json", "src_re/player_update_80048138.c", "analysis/phase3_hook_contracts.json"],
            bounded=True,
            residual="Non-matching documentation C remains semantic reference only until a byte-exact build proves equivalence.",
        ),
        row(
            "hook_discharge_vs_degraded_recovered_extent",
            surfaces=["disassembly", "hook_schema", "built_diagnostic_image",
                      "finding_registry", "roadmap"],
            predicate=hook_docs_ok,
            observation="terrain_emitter_color is post-build clobber-clean, but both its recovered liveness extent and its discharge confidence are degraded.",
            resolution="Count it as one degraded accounted row, not as an exact-confidence discharge; retain 5 proven + 9 exact discharges + 1 degraded row in every authoritative summary.",
            evidence=["analysis/phase3_hook_contracts.json",
                      "config/phase3_findings.yaml", HUB, PHASE],
            bounded=True,
            residual="Recover the original containing function boundary from independent code identity before promoting this row from degraded to exact confidence.",
        ),
        row(
            "duckstation_api_prose_vs_exact_phase3_fork",
            surfaces=["debugger_source", "debugger_binary", "generated_artifact", "Canon"],
            predicate=not rpc_gaps,
            observation=("Earlier Canon/Markdown surfaces described obsolete 141/143 and "
                         "191-method snapshots; the current fe0cca16 dirty fork exposes "
                         f"{rpc_doc['methods']['counts']['current']} dispatched methods."),
            resolution="Extract the balanced KnownMethods/IsKnownMethod table, retain committed/dirty set differences plus exact source/docs/client/binary hashes, deterministically render Markdown, and reject Canon or current-fork drift.",
            evidence=[RPC_MANIFEST, RPC_MARKDOWN, RPC_CANON,
                      "tools/phase3_duckstation_rpc_manifest.py"],
        ),
    ]

    sources = [
        checked("disassembly", "analysis/functions.json", "symbols/re_symbols.sym"),
        checked("C", "src_re/player_update_80048138.c", "src_re/re_types.h"),
        checked("runtime_evidence", "analysis/phase3_spin_functional.json", "analysis/phase3_thud.json", "analysis/phase3_semantic_lifetime.json", "analysis/phase3_unknown_fields.json", "analysis/phase3_render_descriptors.json", "analysis/phase3_training_anchor_fixture.json"),
        checked("asset_observations", "analysis/phase3_scene_asset_graph.json", "analysis/phase3_asset_provenance.json"),
        checked("schemas", "config/semantic_state.yaml", "config/record_types.yaml", "mod/hook_caves.yaml"),
        checked("registries", "analysis/mechanics_baseline.yaml", "config/phase3_findings.yaml"),
        checked("generated_artifacts", "analysis/phase3_xrefs.json", "analysis/phase3_record_types.json", "analysis/phase3_hook_contracts.json", "analysis/phase3_evidence_inventory.json"),
        checked("debugger_toolchain", RPC_MANIFEST, RPC_MARKDOWN,
                "tools/phase3_duckstation_rpc_manifest.py"),
        checked("Canon", ACTION_CANON, SCENE_CANON, RECORD_CANON, RPC_CANON),
        checked("roadmap", HUB, PHASE),
    ]
    open_rows = [r["id"] for r in rows if r["status"] == "open"]
    return {
        "_comment": "Phase-3 WP9 contradiction ledger. Each status is recomputed from the cited low-level surfaces; reconciled/bounded are the only closure states. Regenerate: python3 tools/phase3_contradictions.py",
        "generated": date.today().isoformat(),
        "sources_checked": sources,
        "contradictions": rows,
        "summary": {
            "rows": len(rows),
            "reconciled": sum(r["status"] == "reconciled" for r in rows),
            "bounded": sum(r["status"] == "bounded" for r in rows),
            "open": open_rows,
        },
    }


def main() -> int:
    doc = build_ledger()
    out = ROOT / "analysis" / "phase3_contradictions.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[phase3-contradictions] {doc['summary']['reconciled']} reconciled; "
          f"{doc['summary']['bounded']} bounded; {len(doc['summary']['open'])} open")
    for rid in doc["summary"]["open"]:
        print(f"  OPEN {rid}")
    return 1 if doc["summary"]["open"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
