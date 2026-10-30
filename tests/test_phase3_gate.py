"""Phase-3 EXIT-GATE guard — computed, semantic, and falsifiable."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "analysis" / "phase3_gate_audit.json"


def _run():
    return subprocess.run([sys.executable, "tools/phase3_gate_audit.py"],
                          cwd=ROOT, capture_output=True, text=True)


def test_gate_is_met_only_with_all_binding_packages_and_live_provenance():
    """The retained verdict is reproduced from its low-level package predicates."""
    proc = _run()
    doc = json.loads(G.read_text())
    assert proc.returncode == 0
    assert doc["gate_met"] is True
    assert doc["coverage_matrix"]["overall_met"] is True
    assert doc["coverage_matrix"]["unmet_packages"] == []
    assert doc["coverage_matrix"]["retained_artifact_fresh"] is True
    assert doc["upstream_durability"]["met"] is True
    assert doc["upstream_durability"]["retained_knowledge_report_fresh"] is True
    assert doc["upstream_durability"]["retained_external_fixture_set_fresh"] is True
    assert not any(doc["upstream_durability"]["blockers"].values())
    assert doc["evidence_inventory"]["closure_ready"] is True
    assert doc["evidence_inventory"]["retained_artifact_fresh"] is True
    assert doc["debugger_api_documentation"]["met"] is True
    assert doc["debugger_api_documentation"]["current_fork_compared_by_gate"] is True
    assert doc["debugger_api_documentation"]["current_fork_fresh"] is True
    assert doc["debugger_api_documentation"]["counts"]["current"] == 203
    assert doc["debugger_api_documentation"]["gaps"] == []
    assert doc["bullets"]["1_mechanic_frontier"]["residuals"] == []
    assert doc["bullets"]["1_mechanic_frontier"]["met"] is True
    assert doc["bullets"]["4_hook_contracts"]["met"] is True
    assert doc["decisive_evidence"]["live_run_provenance_complete"] is True
    assert doc["decisive_evidence"][
        "transition_immutable_toolchain_replay_met"] is True
    assert doc["decisive_evidence"]["transition_cleanup"][
        "owned_pid_stopped"] is True
    assert doc["decisive_evidence"]["transition_cleanup"][
        "private_binary_removed"] is True
    assert doc["decisive_evidence"]["aggregate_pristine_save_origins_met"] is True
    assert not any(doc["decisive_evidence"]
                   ["aggregate_pristine_save_origin_gaps"].values())


def test_gate_rejects_a_same_serial_non_pristine_aggregate_anchor():
    """A MOD save cannot become original authority merely by retaining the serial."""
    artifact = ROOT / "analysis/phase3_record_probe.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        rel = "collecting_FLIK_LEVELTRAINING.movie.sav"
        fixture = json.loads(
            (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text()
        )["entries"][rel]
        doc["run_provenance"]["anchor"]["saves"][0] = rel
        doc["run_provenance"]["anchor"]["fixture_sha256"][rel] = fixture["sha256"]
        inspection = doc["run_provenance"]["anchor"]["state_inspections"][0]
        inspection["path"] = str(ROOT / rel)
        inspection["media_path"] = "/operator/build/ABL_ALLMODS.cue"
        inspection["fixture_declaration"] = {
            "path": rel, "sha256": fixture["sha256"],
            "size": fixture["size"], "media_class": "non_pristine",
        }
        inspection["state_media_hash_verification"] = {"pristine_verified": False}
        doc["fixture_sha256"][rel] = fixture["sha256"]
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["decisive_evidence"]["aggregate_pristine_save_origins_met"] is False
        assert changed["decisive_evidence"]["aggregate_pristine_save_origin_gaps"][
            "analysis/phase3_record_probe.json"]
    finally:
        artifact.write_text(original)
        _run()


def test_gate_rejects_stale_shared_live_provenance_helper():
    """The gate consumes helper freshness instead of trusting retained observations."""
    artifact = ROOT / "analysis/phase3_spin_functional.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["run_provenance"]["provenance_helper_sha256"] = "0" * 64
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["evidence_inventory"]["met"] is False
        assert changed["evidence_inventory"]["closure_ready"] is False
        assert changed["evidence_inventory"]["summary"][
            "live_artifact_source_dependency_mismatches"]
        assert changed["decisive_evidence"]["live_run_provenance_complete"] is False
        assert "provenance_helper_sha256 is stale" in changed["decisive_evidence"][
            "live_run_provenance_gaps"]["spin"]
    finally:
        artifact.write_text(original)
        _run()


def test_gate_rejects_an_existence_only_training_fixture_claim():
    """A pinned save is not enough; its cold-boot recipe must reproduce exactly."""
    artifact = ROOT / "analysis/phase3_training_anchor_fixture.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["playback_generation"] = None
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["gate_met"] is False
        assert changed["evidence_inventory"]["met"] is False
        failures = changed["evidence_inventory"]["summary"][
            "live_artifact_reproduction_guard_failures"]
        assert any("playback_generation is absent" in gap for gap in failures)
    finally:
        artifact.write_text(original)
        _run()


def test_gate_rejects_transition_evidence_without_a_verified_private_toolchain():
    artifact = ROOT / "analysis/phase3_transition_reset.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["run_provenance"]["toolchain_snapshot"]["verified"] = False
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["decisive_evidence"][
            "transition_immutable_toolchain_replay_met"] is False
    finally:
        artifact.write_text(original)
        _run()


def test_gate_rejects_a_stale_duckstation_rpc_manifest():
    """The exact current-fork method census is a closure predicate, not prose."""
    artifact = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["methods"]["counts"]["current"] -= 1
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["debugger_api_documentation"]["met"] is False
        assert any("method counts are stale" in gap
                   for gap in changed["debugger_api_documentation"]["gaps"])
    finally:
        artifact.write_text(original)
        restored = _run()
        assert restored.returncode == 0, restored.stdout + restored.stderr


def test_gate_rejects_transition_evidence_without_owned_sibling_cleanup():
    artifact = ROOT / "analysis/phase3_transition_reset.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["run_provenance"]["cleanup"]["private_binary_removed"] = False
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["decisive_evidence"][
            "transition_immutable_toolchain_replay_met"] is False
    finally:
        artifact.write_text(original)
        restored = _run()
        assert restored.returncode == 0, restored.stdout + restored.stderr


def test_gate_reopens_when_a_clean_checkout_regeneration_product_drifts():
    """The gate must consume low-level durability freshness, not just phase labels."""
    product = ROOT / "analysis" / "decomp_candidates.json"
    original = product.read_text()
    try:
        doc = json.loads(original)
        doc["total_candidates"] += 1
        product.write_text(json.dumps(doc, indent=1) + "\n")
        proc = _run()
        changed = json.loads(G.read_text())
        assert proc.returncode == 1
        assert changed["upstream_durability"]["met"] is False
        assert changed["upstream_durability"]["retained_knowledge_report_fresh"] is False
    finally:
        product.write_text(original)
        _run()


def test_inventory_and_gate_reject_a_tracked_render_evidence_mutation():
    """A semantic replay rewrite must keep both closure layers open."""
    artifact = ROOT / "analysis/phase3_render_descriptors.json"
    inventory_path = ROOT / "analysis/phase3_evidence_inventory.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["adversarial_tracked_mutation"] = True
        artifact.write_text(json.dumps(doc, indent=1) + "\n")

        inventory_proc = subprocess.run(
            [sys.executable, "tools/phase3_evidence_inventory.py"],
            cwd=ROOT, capture_output=True, text=True,
        )
        inventory_doc = json.loads(inventory_path.read_text())
        assert inventory_proc.returncode == 1
        assert inventory_doc["closure_ready"] is False
        assert "analysis/phase3_render_descriptors.json" in \
            inventory_doc["summary"]["tracked_input_mutations"]

        gate_proc = _run()
        changed = json.loads(G.read_text())
        assert gate_proc.returncode == 1
        assert changed["gate_met"] is False
        assert changed["evidence_inventory"]["met"] is False
        assert "analysis/phase3_render_descriptors.json" in \
            changed["evidence_inventory"]["summary"]["tracked_input_mutations"]
    finally:
        artifact.write_text(original)
        subprocess.run(
            [sys.executable, "tools/phase3_evidence_inventory.py"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        restored = _run()
        assert restored.returncode == 0, restored.stdout + restored.stderr


def test_bullet_1_separates_address_gaps_from_missing_semantic_facets():
    """A07's open behavioral question is not waived: its known function/state frontier
    is mapped and its residual is explicit. Strip a binding and a real ownership gap
    must reappear."""
    b = json.loads(G.read_text())["bullets"]["1_mechanic_frontier"]
    assert b["met"] is True
    assert b["ownership_graph_gap_free"] is True
    assert b["work_package_met"] is True
    assert b["residuals"] == []
    assert "A07" in b["note"] and "external lead" in b["note"]
    # falsify: corrupt the ownership graph so a mechanic loses its binding
    graph = ROOT / "analysis" / "phase3_ownership_graph.json"
    orig = graph.read_text()
    try:
        g = json.loads(orig)
        g["rows"]["F09_bug_bar"]["gaps"] = ["state 0xDEAD cited with no owner"]
        graph.write_text(json.dumps(g))
        _run()
        changed = json.loads(G.read_text())["bullets"]["1_mechanic_frontier"]
        assert changed["met"] is False
        assert changed["ownership_graph_gap_free"] is False
    finally:
        graph.write_text(orig)
        _run()
    restored = json.loads(G.read_text())["bullets"]["1_mechanic_frontier"]
    assert restored["ownership_graph_gap_free"] is True
    assert restored["met"] is True


def test_bullet_4_is_met_but_not_vacuously():
    """The audit's finding was that bullet 4 passed on hard_violations==0 even with
    0 discharges against an untracked image. It is now MET the HONEST way: the
    on-disk image matches the manifest hash pin, ZERO modules are owed, and every
    obligated hook is discharged against its built cave (0 cave-unverified). None of
    that can be faked by an absent or stale image."""
    b = json.loads(G.read_text())["bullets"]["4_hook_contracts"]
    assert b["patched_image_pinned"] is True
    assert b["patched_image_matches_pin"] is True
    assert b["module_owed"] == 0
    assert b["cave_unverified_remaining"] == 0
    assert b["hard_violations"] == 0
    assert (b["discharged_against_cave"] + b["degraded_with_reason"]
            == b["obligated_hooks"])
    assert b["degraded_with_reason"] == 1
    assert b["met"] is True


def test_bullet_4_goes_open_if_the_image_does_not_match_the_pin():
    """Falsification for bullet 4: if the discharge image is absent or does not
    match the pinned hash, the tool must NOT trust it and the bullet must reopen —
    the stale-image hole cannot silently pass."""
    contracts = ROOT / "analysis" / "phase3_hook_contracts.json"
    orig = contracts.read_text()
    try:
        doc = json.loads(orig)
        doc["summary"]["patched_image_matches_pin"] = False
        contracts.write_text(json.dumps(doc))
        _run()
        b = json.loads(G.read_text())["bullets"]["4_hook_contracts"]
        assert b["met"] is False
    finally:
        contracts.write_text(orig)
        _run()
    assert json.loads(G.read_text())["bullets"]["4_hook_contracts"]["met"] is True


def test_bullet_2_rejects_semantically_false_lifetime_answers():
    """Non-empty strings are not enough: declared-writer MOD state cannot be ROM,
    and a 0->0 observation cannot become zeroed-at-load evidence."""
    lifetime = ROOT / "analysis" / "phase3_semantic_lifetime.json"
    orig = lifetime.read_text()
    try:
        doc = json.loads(orig)
        mod_id = "mod_private.blackberry_equipped"
        doc["entries"][mod_id]["overlay_lifetime"] = "resident_rom"
        doc["entries"][mod_id]["init"] = "load_time (const in the EXE/ROM image)"
        doc["entries"][mod_id]["reset"] = "never (immutable const in ROM)"
        zero_id = "original.player_equipped_berry"
        assert doc["entries"][zero_id]["reset"] == "unchanged_zero"
        doc["entries"][zero_id]["init"] = "zeroed_at_load"
        doc["entries"][zero_id].pop("blocker", None)
        lifetime.write_text(json.dumps(doc))
        _run()
        b = json.loads(G.read_text())["bullets"]["2_state_ownership"]
        assert b["met"] is False
        assert b["semantic_registry_met"] is False
        assert mod_id in b["semantically_invalid"]
        assert zero_id in b["semantically_invalid"]
    finally:
        lifetime.write_text(orig)
        _run()
    restored = json.loads(G.read_text())["bullets"]["2_state_ownership"]
    assert restored["semantic_registry_met"] is True
    assert restored["met"] is True


def test_met_bullets_reopen_when_their_low_level_evidence_is_corrupted():
    """Falsify two independent bullets, then prove restoration closes them."""
    # bullet 3: overlays mapped -> 0
    ov = ROOT / "analysis" / "phase3_overlay_map.json"
    b_ov = ov.read_text()
    # bullet 5: strip a finding's residuals
    fnd = ROOT / "config" / "phase3_findings.yaml"
    b_fnd = fnd.read_text()
    try:
        d = json.loads(b_ov)
        d["overlays"] = 0
        ov.write_text(json.dumps(d))
        _run()
        changed = json.loads(G.read_text())["bullets"]["3_dispatch_and_overlays"]
        assert changed["met"] is False
        assert changed["enumeration_met"] is False
    finally:
        ov.write_text(b_ov)
        _run()
    # and confirm the restored gate is exactly as committed
    restored = json.loads(G.read_text())["bullets"]["3_dispatch_and_overlays"]
    assert restored["enumeration_met"] is True
    assert restored["met"] is True

    try:
        doc = yaml.safe_load(b_fnd)
        doc["findings"][0]["residuals"] = ""
        fnd.write_text(yaml.safe_dump(doc, sort_keys=False))
        _run()
        changed = json.loads(G.read_text())["bullets"]["5_unknowns_visible"]
        assert changed["met"] is False
        assert changed["all_findings_have_confidence_and_residuals"] is False
    finally:
        fnd.write_text(b_fnd)
        _run()
    assert json.loads(G.read_text())["bullets"]["5_unknowns_visible"]["met"] is True
