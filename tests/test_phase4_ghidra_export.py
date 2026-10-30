"""Contract tests for external Ghidra export orchestration and receipt."""

import copy
from collections import Counter
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_ghidra_export as exporter  # noqa: E402


def write_forged_content_run(root: Path, run_id: str, *, census_perfect: bool = False) -> None:
    index = json.loads(exporter.INDEX_PATH.read_text())
    grouped = exporter.image_rows(index)
    metadata = {row["image_id"]: row for row in index["images"]}
    images = []
    fallback_remaining = 4
    total_statuses = Counter()
    for image_id, specs in grouped.items():
        directory = root / run_id / image_id
        directory.mkdir(parents=True)
        functions = []
        image_statuses = Counter()
        for row in specs:
            if not census_perfect:
                function = {
                    "entry": row["entry"], "end": row["end"],
                    "range_type": row["range_type"], "status": "not_applicable",
                }
            else:
                if row["range_type"] == "data":
                    status = "not_applicable"
                elif row["range_type"] == "code" and fallback_remaining:
                    status = "instruction_fallback_required"
                    fallback_remaining -= 1
                else:
                    status = "high_pcode"
                pcode_ops = ["COPY|null"] if status == "high_pcode" else []
                function = {
                    "entry": row["entry"], "end": row["end"],
                    "range_type": row["range_type"], "name": str(row.get("name") or ""),
                    "status": status, "pcode_op_count": len(pcode_ops),
                    "pcode_fingerprint": (exporter.pcode_fingerprint(pcode_ops)
                                          if pcode_ops else None),
                    "pcode_ops": pcode_ops, "calls": [], "memory_ops": [],
                }
                if status == "instruction_fallback_required":
                    function["error"] = "fabricated fallback"
            functions.append(function)
            image_statuses[function["status"]] += 1
            total_statuses[function["status"]] += 1
        raw = {
            "schema": "abl-phase4-ghidra-raw/1",
            "image_id": image_id,
            "gp": metadata[image_id]["runtime_gp"],
            "functions": functions,
        }
        raw_path = directory / "raw.json"
        raw_path.write_text(exporter.render(raw))
        images.append({
            "image_id": image_id,
            "input_sha256": metadata[image_id]["sha256"],
            "file_va_base": metadata[image_id]["file_va_base"],
            "rows": len(specs), "raw_sha256": exporter.sha256(raw_path),
            "raw_size": raw_path.stat().st_size,
            "statuses": dict(sorted(image_statuses.items())),
        })
    tool = exporter.frontier.load_yaml(exporter.frontier.CONFIG_PATH)["toolchain"]
    manifest = {
        "schema": "abl-phase4-ghidra-external-run/1", "run_id": run_id,
        "source_index_sha256": exporter.sha256(exporter.INDEX_PATH),
        "exporter_sha256": exporter.sha256(exporter.EXPORTER_PATH),
        "toolchain": {"app_id": tool["app_id"], "version": str(tool["version"]),
                      "commit": tool["flatpak_commit"]},
        "images": images,
        "summary": {"images": len(images), "records": len(index["records"]),
                    "statuses": dict(sorted(total_statuses.items()))},
        "raw_output_policy": "external_only", "complete": True,
    }
    (root / run_id / "manifest.json").write_text(exporter.render(manifest))


def test_retained_receipt_proves_two_full_byte_identical_regenerations():
    receipt = json.loads(exporter.RECEIPT_PATH.read_text())
    assert receipt["schema"] == "abl-phase4-ghidra-regeneration-receipt/1"
    assert receipt["valid"] is True
    assert receipt["full_corpus"] is True
    assert receipt["image_identities_match"] is True
    assert receipt["raw_exports_byte_identical"] is True
    assert receipt["summary"] == {
        "images": 21,
        "records": 1190,
        "statuses": {
            "high_pcode": 1108,
            "instruction_fallback_required": 4,
            "not_applicable": 78,
        },
    }
    assert receipt["raw_output_policy"] == "external_only"
    assert receipt["raw_record_contract_sha256"] == \
        exporter.EXPECTED_RAW_RECORD_CONTRACT_SHA256
    assert "/" + "home" + "/" not in exporter.RECEIPT_PATH.read_text()


def test_every_index_record_is_assigned_to_one_ghidra_image():
    index = json.loads(exporter.INDEX_PATH.read_text())
    grouped = exporter.image_rows(index)
    assert len(grouped) == 21
    assert sum(map(len, grouped.values())) == 1190
    assert len(grouped["SCUS_942_88"]) == 998
    assert len(grouped["MEMORY"]) == 69


def test_external_root_must_be_absolute_and_outside_repository(tmp_path):
    with pytest.raises(ValueError, match="absolute"):
        exporter.checked_external_root(Path("relative"))
    with pytest.raises(ValueError, match="outside"):
        exporter.checked_external_root(ROOT / "analysis")
    assert exporter.checked_external_root(tmp_path) == tmp_path.resolve()


def test_comparison_rejects_forged_full_manifests_without_raw_exports(tmp_path):
    receipt = json.loads(exporter.RECEIPT_PATH.read_text())
    manifest = {
        "schema": "abl-phase4-ghidra-external-run/1",
        "source_index_sha256": receipt["source_index_sha256"],
        "exporter_sha256": receipt["exporter_sha256"],
        "toolchain": receipt["toolchain"],
        "summary": {"images": 21, "records": 1190, "statuses": {}},
        "images": [{"image_id": f"image-{index}", "raw_sha256": "a" * 64}
                   for index in range(21)],
    }
    for run_id in ("a", "b"):
        directory = tmp_path / run_id
        directory.mkdir()
        (directory / "manifest.json").write_text(exporter.render(manifest))
    document = exporter.comparison(tmp_path, "a", "b")
    assert document["valid"] is False
    assert document["raw_exports_byte_identical"] is False
    assert any(error.startswith("MANIFEST_") or error.startswith("RAW_MISSING")
               for errors in document["run_validation_errors"].values()
               for error in errors)

    changed = copy.deepcopy(manifest)
    changed["images"][0]["raw_sha256"] = "b" * 64
    (tmp_path / "b" / "manifest.json").write_text(exporter.render(changed))
    document = exporter.comparison(tmp_path, "a", "b")
    assert document["raw_exports_byte_identical"] is False
    assert document["valid"] is False


def test_comparison_rejects_unsafe_run_ids(tmp_path):
    document = exporter.comparison(tmp_path, "../escape", "also/escape")
    assert document["valid"] is False
    assert document["run_validation_errors"]["../escape"] == ["RUN_ID_INVALID"]


def test_comparison_rejects_rehashed_raw_content_forgery(tmp_path):
    for run_id in ("forged-a", "forged-b"):
        write_forged_content_run(tmp_path, run_id)
    document = exporter.comparison(tmp_path, "forged-a", "forged-b")
    assert document["valid"] is False
    assert document["full_corpus"] is True
    assert document["raw_exports_byte_identical"] is True
    errors = document["run_validation_errors"]["forged-a"]
    assert any(error.startswith("RAW_FIELDS_MISSING:") for error in errors)
    assert any(error.startswith("RAW_STATUS_RANGE_MISMATCH:") for error in errors)
    assert "RAW_EXPECTED_STATUS_CENSUS_DRIFT" in errors
    assert "RAW_EXPECTED_RANGE_STATUS_CENSUS_DRIFT" in errors


def test_comparison_rejects_census_perfect_rehashed_content_forgery(tmp_path):
    for run_id in ("plausible-a", "plausible-b"):
        write_forged_content_run(tmp_path, run_id, census_perfect=True)
    document = exporter.comparison(tmp_path, "plausible-a", "plausible-b")
    assert document["valid"] is False
    assert document["full_corpus"] is True
    assert document["raw_exports_byte_identical"] is True
    errors = document["run_validation_errors"]["plausible-a"]
    assert "RAW_RECORD_CONTRACT_DRIFT" in errors
    assert "RAW_EXPECTED_STATUS_CENSUS_DRIFT" not in errors
    assert "RAW_EXPECTED_RANGE_STATUS_CENSUS_DRIFT" not in errors
    assert not any(error.startswith("RAW_FIELDS_MISSING:") for error in errors)
    assert not any(error.startswith("RAW_STATUS_RANGE_MISMATCH:") for error in errors)
