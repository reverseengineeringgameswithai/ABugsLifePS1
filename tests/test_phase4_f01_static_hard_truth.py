import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_evidence_dag as evidence_dag  # noqa: E402
import phase4_inventory  # noqa: E402

SOURCE = ROOT / "tools/phase4_f01_static_hard_truth.c"
DRIVER = ROOT / "tools/phase4_f01_static_hard_truth.py"
IMAGE = ROOT / "REBUILD/files/SCUS_942.88"
ARTIFACT = ROOT / "analysis/phase4_f01_static_hard_truth.json"
FILE_VA_BASE = 0x8000F800


@pytest.fixture(scope="module")
def receipt():
    return json.loads(ARTIFACT.read_bytes())


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    output = tmp_path_factory.mktemp("f01-hard-truth") / "probe"
    subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(SOURCE), "-lm", "-o", str(output)], check=True, cwd=ROOT)
    return output


def test_retained_receipt_rebuilds_byte_identically():
    proc = subprocess.run([sys.executable, str(DRIVER), "--output", str(ARTIFACT),
                           "--check"], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_task_added_evidence_surfaces_are_declared_without_one_sided_gaps():
    declaration = common.load_yaml(common.INVENTORY_CONFIG_PATH)
    generators = {row["path"]: row for row in declaration["generators"]}
    assert generators["tools/phase4_f01_static_hard_truth.py"][
        "classification"] == "local_media"
    assert generators["tools/phase4_f01_static_hard_truth.py"]["outputs"] == [
        "analysis/phase4_f01_static_hard_truth.json"]
    assert generators["tools/phase4_f01_local_base_recovery.py"][
        "classification"] == "local_media"
    assert generators["tools/phase4_f01_local_base_recovery.py"]["outputs"] == [
        "analysis/phase4_f01_local_base_recovery.json",
        "analysis/phase4_f01_local_base_recovery_1bba2487_outcomes.json",
    ]
    assert {
        "tests/test_phase4_f01_static_hard_truth.py",
        "tests/test_phase4_f01_local_base_recovery.py",
    }.issubset(set(declaration["tests"]))

    gaps = phase4_inventory.build_campaign_inventory()["gaps"]
    assert "tools/phase4_f01_static_hard_truth.py" not in \
        gaps["missing_generator_declarations"]
    assert "tools/phase4_f01_local_base_recovery.py" not in \
        gaps["missing_generator_declarations"]
    assert "analysis/phase4_f01_static_hard_truth.json" not in \
        gaps["orphan_artifacts"]
    assert "analysis/phase4_f01_local_base_recovery.json" not in \
        gaps["orphan_artifacts"]
    assert "analysis/phase4_f01_local_base_recovery_1bba2487_outcomes.json" \
        not in gaps["orphan_artifacts"]
    assert "tests/test_phase4_f01_static_hard_truth.py" not in \
        gaps["missing_test_declarations"]
    assert "tests/test_phase4_f01_local_base_recovery.py" not in \
        gaps["missing_test_declarations"]


def test_inventory_declaration_exact_pin_is_reconciled_in_the_retained_dag():
    retained = json.loads(
        (ROOT / "analysis/phase4_evidence_dag.json").read_bytes())
    retained_node = retained["nodes"]["phase4_gate"]
    rows = [row for row in retained_node["inputs"]
            if row["path"] == "config/phase4_inventory.yaml"]
    assert len(rows) == 1
    expected = evidence_dag.path_identity(ROOT, {
        "path": "config/phase4_inventory.yaml", "kind": "file"})
    assert {key: rows[0][key] for key in
            ("path", "kind", "size", "exact_sha256", "semantic_sha256")} == \
        expected
    assert rows[0]["mode"] == "exact"

    declared_node = next(
        node for node in evidence_dag.validate_config(evidence_dag.load_config())
        if node["id"] == "phase4_gate")
    material = {
        "classification": retained_node["classification"],
        "generator": retained_node["generator"],
        "generator_sha256": retained_node["generator_sha256"],
        "command": retained_node["command"],
        "verify_command": retained_node["verify_command"],
        "accepted_exit_codes": declared_node["accepted_exit_codes"],
        "depends_on": retained_node["depends_on"],
        "inputs": [{
            "path": row["path"], "kind": row["kind"], "mode": row["mode"],
            "sha256": row[f"{row['mode']}_sha256"],
        } for row in retained_node["inputs"]],
        "outputs": declared_node["outputs"],
    }
    assert retained_node["fingerprint"] == evidence_dag.sha256_bytes(
        evidence_dag.canonical_json(material))
    assert (ROOT / "analysis/phase4_gate.json").read_bytes() == \
        subprocess.check_output([
            "git", "show",
            "1bba2487b1b6f3e9d7669947de494ba649b99b70:analysis/phase4_gate.json",
        ], cwd=ROOT)


def test_regenerated_inventory_receipts_are_exactly_repinned_in_the_dag():
    retained = json.loads(
        (ROOT / "analysis/phase4_evidence_dag.json").read_bytes())
    declared = {
        node["id"]: node
        for node in evidence_dag.validate_config(evidence_dag.load_config())
    }
    expected_consumers = {
        "analysis/phase4_campaign_inventory.json": {
            "offline_queue", "closure_debt", "phase4_gate"},
        "analysis/phase4_fixture_audit.json": {
            "offline_queue", "movie_priority", "phase4_gate"},
        "analysis/phase4_knowledge_audit.json": {"phase4_gate"},
    }
    touched = set()
    for path, consumers in expected_consumers.items():
        expected = evidence_dag.path_identity(ROOT, {
            "path": path, "kind": "file"})
        actual_consumers = set()
        for node_id, node in retained["nodes"].items():
            rows = [row for row in node["inputs"] if row["path"] == path]
            if not rows:
                continue
            assert len(rows) == 1
            assert {key: rows[0][key] for key in
                    ("path", "kind", "size", "exact_sha256",
                     "semantic_sha256")} == expected
            assert rows[0]["mode"] == "exact"
            actual_consumers.add(node_id)
            touched.add(node_id)
        assert actual_consumers == consumers

    for node_id in touched:
        retained_node = retained["nodes"][node_id]
        declared_node = declared[node_id]
        material = {
            "classification": retained_node["classification"],
            "generator": retained_node["generator"],
            "generator_sha256": retained_node["generator_sha256"],
            "command": retained_node["command"],
            "verify_command": retained_node["verify_command"],
            "accepted_exit_codes": declared_node["accepted_exit_codes"],
            "depends_on": retained_node["depends_on"],
            "inputs": [{
                "path": row["path"], "kind": row["kind"],
                "mode": row["mode"],
                "sha256": row[f"{row['mode']}_sha256"],
            } for row in retained_node["inputs"]],
            "outputs": declared_node["outputs"],
        }
        assert retained_node["fingerprint"] == evidence_dag.sha256_bytes(
            evidence_dag.canonical_json(material))


def test_complete_content_models_and_reader_sets(receipt):
    tables = {row["id"]: row for row in receipt["c_probe"]["trigonometric_tables"]}
    raw = tables["q14_sine_4096_plus_quadrature_tail"]
    assert (raw["entry_count"], raw["stride_bytes"], raw["amplitude"]) == \
        (5120, 2, 16384)
    assert raw["content_comparison"]["mismatched_entries"] == 0
    assert raw["gap"] == {
        "byte_count": 4216, "end": "0x800769A8", "entry_count": 2108,
        "first_entry": 2016, "first_mismatch": None,
        "mismatched_entries": 0, "start": "0x80075930"}
    assert len(raw["readers"]) == 23

    packed = tables["q12_packed_rotmatrix_sine_phase_pair"]
    assert (packed["entry_count"], packed["stride_bytes"], packed["amplitude"]) == \
        (4096, 4, 4096)
    assert packed["content_comparison"]["mismatched_entries"] == 0
    assert packed["gap"]["byte_count"] == 8068
    assert packed["gap"]["entry_count"] == 2017
    assert len(packed["readers"]) == 6
    assert "((j mod 4096)>>10)&1" in packed["formula"]


def test_claimed_jalrs_fail_closed_and_real_jr_sets_reconcile(receipt):
    claimed = receipt["c_probe"]["requested_dispatch_sites"]
    assert [(row["pc"], row["decoded_kind"], row["direct_target"])
            for row in claimed] == [
                ("0x8005BFE4", "direct_jal", "0x80038E48"),
                ("0x80058EB8", "direct_jal", "0x80060284"),
            ]
    assert all(row["target_set_proved"] is False for row in claimed)
    assert receipt["dispatch_import_delta"]["new_sites"] == []
    reconciled = receipt["registered_actual_jr_reconciliation"]
    assert [(row["pc"], row["entry_count"], row["distinct_target_count"])
            for row in reconciled] == [
                ("0x8005C108", 13, 10), ("0x80058E78", 12, 6)]
    for row in reconciled:
        assert row["verified"] is True
        assert row["c_only_phase3"] == row["phase3_only_c"] == []
        assert row["c_only_gate"] == row["gate_only_c"] == []


def test_instruction_and_content_mutations_both_fail_closed(binary, tmp_path):
    pristine = bytearray(IMAGE.read_bytes())

    instruction = bytearray(pristine)
    instruction[0x800608A4 - FILE_VA_BASE] ^= 1
    instruction_path = tmp_path / "instruction-mutated.exe"
    instruction_path.write_bytes(instruction)
    proc = subprocess.run([str(binary), str(instruction_path)], cwd=ROOT,
                          capture_output=True, text=True)
    assert proc.returncode != 0
    assert "instruction pin failed" in proc.stderr

    content = bytearray(pristine)
    content[0x80075930 - FILE_VA_BASE] ^= 1
    content_path = tmp_path / "content-mutated.exe"
    content_path.write_bytes(content)
    proc = subprocess.run([str(binary), str(content_path)], cwd=ROOT,
                          capture_output=True, text=True)
    assert proc.returncode != 0
    mutated = json.loads(proc.stdout)
    raw = mutated["trigonometric_tables"][0]
    assert raw["content_comparison"]["mismatched_entries"] == 1
    assert raw["gap"]["mismatched_entries"] == 1
    assert mutated["verdicts"]["trig_semantic_disposition_supported"] is False
