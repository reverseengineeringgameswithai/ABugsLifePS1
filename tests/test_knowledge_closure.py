import json
import subprocess
import sys
from pathlib import Path

import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import knowledge_closure_audit as closure_audit  # noqa: E402
import fixture_reference_sets  # noqa: E402
import provision_clean_checkout_inputs as clean_inputs  # noqa: E402
import function_census as census  # noqa: E402


def test_knowledge_closure_artifacts_are_fresh_and_honest():
    paths = [ROOT / "analysis/phase0_2_knowledge_closure_report.json",
             ROOT / "analysis/phase0_2_external_fixture_set.json"]
    before = [p.read_bytes() for p in paths]
    proc = subprocess.run([sys.executable, "tools/knowledge_closure_audit.py", "--write"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert before == [p.read_bytes() for p in paths]


def test_matrix_has_all_eight_requirements_and_does_not_claim_closure():
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    reqs = set(matrix["requirements"])
    assert len(reqs) == 8
    for item in matrix["deliverables"]:
        assert set(item["requirements"]) == reqs, item["id"]
    # The audit intentionally records real blockers. A future closure change must
    # update the evidence and regenerated report, not just flip prose.
    report = json.loads((ROOT / "analysis/phase0_2_knowledge_closure_report.json").read_text())
    assert report["phase_status"] == {"phase0": "partial", "phase1": "partial", "phase2": "partial"}
    assert report["strict_blockers"]["knowledge_phases_not_closed"] == ["phase0", "phase1", "phase2"]


def test_external_fixture_set_is_central_and_classified():
    doc = json.loads((ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())
    assert not doc["missing_central_pins"], doc["missing_central_pins"]
    for rel, entry in doc["entries"].items():
        assert len(entry["sha256"]) == 64, rel
        assert entry["media_class"] in {"pristine", "non_pristine", "pristine_serial",
                                        "unknown_serial", "unknown", "unreadable",
                                        "derived_retail_metadata",
                                        "derived_retail_assembly",
                                        "derived_retail_disassembly"}, rel
        assert entry["consumers"] and entry["preservation_required"] is True, rel
        assert entry["capture_origin"] in {
            "repo_generator_or_replay_tool", "operator_owned_external_capture"}, rel


def test_indirect_phase3_fixture_consumers_and_generators_are_central():
    entries = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())["entries"]
    rejected = entries["collecting_FLIK_LEVELTRAINING.movie.sav"]
    assert rejected["media_class"] == "non_pristine"
    aggregate_artifacts = {
        "analysis/phase3_record_probe.json",
        "analysis/phase3_render_descriptors.json",
        "analysis/phase3_fn_ptr_fields.json",
    }
    aggregate_generators = {
        "tools/phase3_record_types.py",
        "tools/phase3_render_descriptors.py",
        "tools/phase3_fn_ptr_fields.py",
    }
    assert aggregate_artifacts.isdisjoint(rejected["consumers"])
    assert aggregate_generators.isdisjoint(rejected["generator_references"])
    row = entries["phase3_pristine_training_gameplay_i5.sav"]
    assert row["media_class"] == "pristine"
    assert aggregate_artifacts <= set(row["consumers"])
    assert aggregate_generators <= set(row["generator_references"])


def test_every_mechanics_recording_is_in_the_central_fixture_set():
    """Movie variants such as *.movie_1.json must not fall through a suffix list."""
    mechanics = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text())
    reference_sets = fixture_reference_sets.load()
    fixture_reference_sets.validate_rows(mechanics["rows"], reference_sets)
    declared = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())["entries"]
    recordings = {
        value.split(" @f", 1)[0]
        for row in mechanics["rows"]
        for value in fixture_reference_sets.resolve_row(row, reference_sets)
        if value.endswith(".sav") or ".movie" in value and value.endswith(".json")
    }
    assert recordings <= set(declared), sorted(recordings - set(declared))


def test_known_glyph_dependency_is_in_clean_checkout_source():
    report = json.loads((ROOT / "analysis/phase0_2_knowledge_closure_report.json").read_text())
    glyph = report["known_dependency_checks"]["tools/glyph_spin_native.py"]
    assert glyph["tracked"] is True
    assert set(glyph["consumers"]) == {
        "tools/generate_training_pickup_letters.py", "tools/training_word_pickups.py"}


def test_provisioned_operator_source_is_hash_pinned_and_tracked():
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    rows = matrix["provisioned_external_source_inputs"]
    assert {row["path"] for row in rows} == {
        "tools/native_collision_from_heightfield.py",
        "tools/tier3_native_object_inventory.py",
        "tools/patch_training_overlay.py",
        "tools/training_board_edit.py",
        "tests/test_training_board_edit.py",
    }
    tracked, _ = closure_audit.tracked_paths()
    assert closure_audit.validate_provisioned_sources(matrix, tracked) == []
    assert closure_audit.local_import_gaps(tracked) == []


def test_derived_retail_inputs_are_centrally_pinned_and_required():
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    rows = matrix["external_local_media_inputs"]
    assert {row["path"] for row in rows} == {
        "extracted/re_baseline/functions.json",
        "extracted/re_baseline/strings.json",
        "asm/nonmatchings/resident/800563d4.s",
        "asm/nonmatchings/resident/8005905c_berry_tough_damage_dispatch.s",
        "asm/nonmatchings/resident/8005921c.s",
    }
    tracked, _ = closure_audit.tracked_paths()
    assert closure_audit.validate_external_local_media_inputs(matrix, tracked) == []
    central = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())["entries"]
    for row in rows:
        assert central[row["path"]]["sha256"] == row["sha256"]
        assert central[row["path"]]["regeneration_command"] == row["generator"]


def test_every_substrate_source_is_manifested_and_hash_verified():
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    tracked, _ = closure_audit.tracked_paths()
    assert closure_audit.validate_external_local_media_manifests(matrix, tracked) == []
    rows = closure_audit.external_manifest_rows(matrix)
    assert len(rows) >= 600
    assert len({row["path"] for row in rows}) == len(rows)
    central = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())["entries"]
    assert all(row["path"] in central for row in rows)


def test_whole_image_census_inputs_are_manifested_and_use_pristine_staging():
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    rows = [row for row in closure_audit.external_manifest_rows(matrix)
            if row["manifest"] == "tools/re_baseline_inputs.sha256"]
    baselines = json.loads((ROOT / "tools/build_baselines.json").read_text())
    targets = census.staged_overlay_targets(baselines)
    required = {
        str(path.relative_to(ROOT)) for path in census.required_external_metadata(targets)
    } | {"extracted/re_baseline/code_data_map.json"}
    assert len(targets) == 20
    assert {row["path"] for row in rows} == required
    assert len(rows) == 23
    assert 'ROOT / "OVL"' not in (ROOT / "tools/function_census.py").read_text()


def test_clean_checkout_provision_plan_is_exactly_the_central_manifests():
    plan = clean_inputs.build_plan(clean_inputs.DEFAULT_OPERATOR_ROOT)
    baselines = json.loads((ROOT / "tools/build_baselines.json").read_text())
    fixtures = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())["entries"]
    matrix = yaml.safe_load(
        (ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    fixture_paths = set(fixtures) | {
        row["path"] for row in matrix["external_local_media_inputs"]}
    expected = (len(baselines["pristine_media"]) +
                len(baselines["staged_inputs"]) + len(fixture_paths))
    assert len(plan) == expected
    assert len({row["target"] for row in plan}) == expected
    assert {row["class"] for row in plan} >= {
        "pristine_media", "pristine_staged_input", "derived_retail_metadata",
        "derived_retail_assembly", "derived_retail_disassembly",
    }


def test_clean_checkout_provisioner_refuses_mismatched_existing_target(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_bytes(b"pinned bytes")
    target.write_bytes(b"operator work")
    row = {"source": source, "target": target, "algorithm": "sha256",
           "digest": __import__("hashlib").sha256(b"pinned bytes").hexdigest(),
           "size": len(b"pinned bytes")}
    with pytest.raises(SystemExit, match="checkout target size mismatch"):
        clean_inputs.provision(row, verify_only=False)
    assert target.read_bytes() == b"operator work"


def test_missing_derived_retail_input_is_a_durability_failure(tmp_path):
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    matrix["external_local_media_inputs"][0]["path"] = str(
        tmp_path / "missing-functions.json")
    tracked, _ = closure_audit.tracked_paths()
    errors = closure_audit.validate_external_local_media_inputs(matrix, tracked)
    assert errors and "workspace path is absent" in errors[0]["reasons"]


def test_provisioned_source_pin_falsification_is_detected():
    matrix = yaml.safe_load((ROOT / "analysis/phase0_2_knowledge_closure.yaml").read_text())
    matrix["provisioned_external_source_inputs"][0]["sha256"] = "0" * 64
    tracked, _ = closure_audit.tracked_paths()
    errors = closure_audit.validate_provisioned_sources(matrix, tracked)
    assert errors and errors[0]["path"] == "tools/native_collision_from_heightfield.py"


@pytest.mark.local_media
def test_declared_external_fixture_bytes_match_pins():
    doc = json.loads((ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())
    import hashlib
    for rel, entry in doc["entries"].items():
        path = ROOT / rel
        assert path.exists(), rel
        assert path.stat().st_size == entry["size"], rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], rel


def test_strict_mode_fails_while_declared_blockers_remain():
    proc = subprocess.run([sys.executable, "tools/knowledge_closure_audit.py", "--strict"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 1
