"""Safe, asset-free guards for the inbound PC-to-PS1 semantic bridge."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cross_port_semantic_bridge as bridge  # noqa: E402


LEAD = ROOT / "analysis" / "cross_port" / "pc_to_ps1_berry_accumulator_calibration.json"
CATALOG = ROOT / "analysis" / "cross_port" / "ps1_semantic_candidate_calibration.json"
LEAD_SCHEMA = ROOT / "config" / "cross_port_semantic_lead.schema.json"
CATALOG_SCHEMA = ROOT / "config" / "cross_port_semantic_candidate_catalog.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_versioned_contract_files_are_valid_json():
    lead_schema = _load(LEAD_SCHEMA)
    catalog_schema = _load(CATALOG_SCHEMA)
    assert lead_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert lead_schema["properties"]["schema"]["const"] == bridge.LEAD_SCHEMA
    assert catalog_schema["properties"]["schema"]["const"] == bridge.CATALOG_SCHEMA


def test_calibration_packet_and_catalog_validate_against_pristine_target():
    lead = bridge.validate_lead(_load(LEAD))
    catalog = bridge.validate_catalog(_load(CATALOG))
    assert lead["status"] == "external_lead"
    assert lead["purpose"] == "calibration"
    assert lead["target"] == catalog["target"]
    assert lead["target"]["binary"]["sha256"] == bridge.PS1_BINARY_SHA256
    assert catalog["status"] == "curated_calibration_catalog"


def test_calibration_ranks_known_ps1_window_first_without_promotion():
    lead_doc, lead_hash = bridge.load_json_strict(LEAD)
    catalog_doc, catalog_hash = bridge.load_json_strict(CATALOG)
    result = bridge.rank_candidates(
        bridge.validate_lead(lead_doc),
        bridge.validate_catalog(catalog_doc),
        lead_sha256=lead_hash,
        catalog_sha256=catalog_hash,
    )
    assert result["status"] == "ranked_external_leads_only"
    assert result["promotion_allowed"] is False
    assert result["candidate_count"] == 4
    top = result["candidates"][0]
    assert top["candidate_id"] == "PS1-CAND-BERRY-ACCUMULATOR-INCREMENT"
    assert top["locator"]["value"] == "0x8004B4C0-0x8004B53C"
    assert top["eligible"] is True
    assert top["score_basis_points"] == 10_000
    assert all(row["claim_status"] == "ps1_candidate_only" for row in result["candidates"])
    assert result["candidates"][1]["candidate_id"] == "PS1-CAND-BERRY-ACCUMULATOR-DECAY"
    assert result["candidates"][1]["eligible"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "confirmed"),
        (("direction",), "ps1-to-pc"),
        (("target", "binary", "sha256"), "0" * 64),
        (("source", "binary", "architecture"), "x86-64-le"),
    ],
)
def test_inbound_lead_fails_closed_on_authority_or_identity_drift(path, value):
    doc = copy.deepcopy(_load(LEAD))
    cursor = doc
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(bridge.BridgeError):
        bridge.validate_lead(doc)


def test_feature_width_and_signedness_are_part_of_identity():
    lead = bridge.validate_lead(_load(LEAD))
    catalog_doc = copy.deepcopy(_load(CATALOG))
    top = catalog_doc["candidates"][0]
    threshold = next(feature for feature in top["features"] if feature["kind"] == "threshold")
    threshold["attributes"]["operand_bits"] = 16
    result = bridge.rank_candidates(
        lead,
        bridge.validate_catalog(catalog_doc),
        lead_sha256="1" * 64,
        catalog_sha256="2" * 64,
    )
    changed = next(row for row in result["candidates"] if row["candidate_id"] == top["candidate_id"])
    assert changed["eligible"] is False
    assert changed["raw_coverage_basis_points"] < 10_000


def test_duplicate_json_keys_are_rejected(tmp_path):
    packet = tmp_path / "duplicate.json"
    packet.write_text('{"schema":"one","schema":"two"}\n')
    with pytest.raises(bridge.BridgeError, match="duplicate JSON key"):
        bridge.load_json_strict(packet)


def test_cli_is_read_only_by_default_and_refuses_overwrite(tmp_path):
    before_lead = LEAD.read_bytes()
    before_catalog = CATALOG.read_bytes()
    command = [
        sys.executable,
        "tools/cross_port_semantic_bridge.py",
        "rank",
        str(LEAD),
        str(CATALOG),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["promotion_allowed"] is False
    assert LEAD.read_bytes() == before_lead
    assert CATALOG.read_bytes() == before_catalog

    output = tmp_path / "ranking.json"
    first = subprocess.run(command + ["--output", str(output)], cwd=ROOT, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command + ["--output", str(output)], cwd=ROOT, capture_output=True, text=True)
    assert second.returncode == 2
    assert "refusing to overwrite" in second.stderr


def test_committed_evidence_verifier_ignores_working_tree(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.invalid"], check=True)
    evidence = repository / "evidence.txt"
    evidence.write_text("committed\n")
    subprocess.run(["git", "-C", str(repository), "add", "evidence.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "fixture"], check=True)
    commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    digest = __import__("hashlib").sha256(b"committed\n").hexdigest()
    evidence.write_text("dirty working tree must be ignored\n")
    bridge.verify_committed_evidence(
        repository,
        commit,
        [{"path": "evidence.txt", "blob_sha256": digest}],
    )
