import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_f01_request2_probe.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PROBE = load_module(
    ROOT / "tools/phase4_f01_request2_probe.py",
    "phase4_f01_request2_probe",
)


def retained_receipts():
    return list(json.loads(ARTIFACT.read_text())["results"].values())


def consolidate(tmp_path: Path, receipts: list[dict]):
    inputs = []
    for index, receipt in enumerate(receipts):
        path = tmp_path / f"receipt-{index}.json"
        path.write_text(json.dumps(receipt))
        inputs.append(str(path))
    out = tmp_path / "out.json"
    rc = PROBE.consolidate(SimpleNamespace(inputs=inputs, out=str(out)))
    return rc, json.loads(out.read_text())


# 2026-08-10 fresh-verifier replacement. The predecessor test asserted
# element_outcome == "BLOCKED" over the two-receipt pair; its expectation was
# legitimately overtaken when the BLOCKED element's own named dependency (a
# centrally pinned pristine cold-boot natural-death movie) was delivered and
# independently replayed byte-identically. The premature-DONE guard it existed
# for lives on in test_missing_control_consolidates_blocked_not_done below.
def test_retained_set_is_valid_and_honestly_done(tmp_path):
    receipts = retained_receipts()
    validations = [PROBE.validate_receipt(receipt) for receipt in receipts]
    assert [errors for errors, _ in validations] == [[], [], []]
    controls = [control for _, found in validations for control in found]
    assert len(controls) == 1
    control = controls[0]
    assert control["request"] == 2
    assert control["gp4c4"] == 0
    assert control["consumer_proceeded"] is True
    assert control["finalizer_observed"] is False
    writer = control["last_request_writer"]
    assert writer["instruction_pc"] == "0x8004A8B4"
    assert writer["instruction_word"] == "0xA42223A0"
    assert writer["stored_u16"] == 2
    assert writer["resident_pristine_certificate"]["passed"] is True
    rc, result = consolidate(tmp_path, receipts)
    assert rc == 0
    assert result["exact_set_replayed"] is True
    assert result["captures_accepted"] == result["captures_required"] == 3
    assert len(result["natural_request2_skip_controls"]) == 1
    assert result["natural_request2_skip_controls"][0]["movie"] == (
        "movies/Phase4/Interpreter/F01_natural_death_FromBoot.movie.json"
    )
    assert result["element_outcome"] == "DONE"
    assert result["dependency"] is None


def natural_death_receipt_without_its_control() -> list[dict]:
    """A coherently control-free exact set: the natural-death receipt with the
    death decision and its resident death store removed, all envelope counts
    reconciled so validate_receipt still accepts it."""
    receipts = retained_receipts()
    receipt = next(
        row for row in receipts
        if row["fixture"]["movie"].endswith("F01_natural_death_FromBoot.movie.json")
    )
    receipt["decisions"] = []
    receipt["request_values"] = []
    receipt["natural_request2_skip_controls"] = []
    receipt["natural_request2_skip_control_observed"] = False
    receipt["watch_certification"]["decision"]["retained_events"] = 0
    receipt["request_writes"] = [
        write for write in receipt["request_writes"]
        if not write["resident_death_store"]
    ]
    kept = len(receipt["request_writes"])
    receipt["request_write_watch"]["retained_events"] = kept
    receipt["access_log"]["total"] = receipt["access_log"]["returned"] = kept
    # 1 consumer + 0 decision + 0 finalizer retained + 326 rejected pre-load
    receipt["exec_trace"]["total"] = receipt["exec_trace"]["returned"] = 327
    return receipts


def test_missing_control_consolidates_blocked_not_done(tmp_path):
    receipts = natural_death_receipt_without_its_control()
    rc, result = consolidate(tmp_path, receipts)
    assert rc == 0
    assert result["exact_set_replayed"] is True
    assert result["captures_accepted"] == 3
    assert result["natural_request2_skip_controls"] == []
    assert result["element_outcome"] == "BLOCKED"
    assert result["dependency"]


def test_invalid_receipt_is_not_misreported_as_blocked(tmp_path):
    receipts = retained_receipts()
    receipts[0]["exec_trace"]["truncated"] = True
    rc, result = consolidate(tmp_path, receipts)
    assert rc == 1
    assert result["captures_accepted"] == 2
    assert result["element_outcome"] == "NOT DONE"
    assert result["receipt_validation_errors"]


def test_consolidation_rejects_missing_duplicate_and_extra_receipts(tmp_path):
    receipts = retained_receipts()
    extra = copy.deepcopy(receipts[0])
    extra["fixture"]["movie"] = "movies/Phase4/Interpreter/UNDECLARED.movie.json"
    cases = {
        "missing": receipts[:2],
        "duplicate": [receipts[0], receipts[0], receipts[2]],
        "extra": receipts + [extra],
    }
    for name, rows in cases.items():
        case_path = tmp_path / name
        case_path.mkdir()
        rc, result = consolidate(case_path, rows)
        assert rc == 1, name
        assert result["exact_set_replayed"] is False, name
        assert result["element_outcome"] == "NOT DONE", name


def test_validator_rejects_deleted_access_event_with_retained_total():
    receipt = copy.deepcopy(retained_receipts()[0])
    receipt["request_writes"].pop()
    receipt["request_write_watch"]["retained_events"] -= 1
    errors, controls = PROBE.validate_receipt(receipt)
    assert controls == []
    assert "request write-watch page/count envelope is invalid" in errors


# 2026-08-10 fresh-verifier replacement: the blanket `stored_u16 is None` held
# only while no retained receipt legitimately contained a resident death store.
# The natural-death receipt now carries exactly one, and it must be the ONLY one.
def test_access_events_preserve_aliases_and_do_not_infer_overlay_images():
    writes = [write for receipt in retained_receipts()
              for write in receipt["request_writes"]]
    assert len(writes) == 24
    assert any(write["address"] == "0xA00823A0" and write["width"] == 4
               for write in writes)
    assert any(write["address"] == "0x800823A1" and write["width"] == 1
               for write in writes)
    assert all(write["overlaps_request_word"] is True for write in writes)
    assert all("image" not in write for write in writes)
    death_stores = [write for write in writes if write["resident_death_store"]]
    assert len(death_stores) == 1
    assert death_stores[0]["instruction_pc"] == "0x8004A8B4"
    assert death_stores[0]["stored_u16"] == 2
    assert death_stores[0]["resident_pristine_certificate"]["passed"] is True
    assert all(write["stored_u16"] is None for write in writes
               if not write["resident_death_store"])

    receipt = copy.deepcopy(retained_receipts()[0])
    receipt["request_writes"][-1]["image"] = "unproved-overlay.bin"
    errors, controls = PROBE.validate_receipt(receipt)
    assert controls == []
    assert any("effective-writer provenance" in error for error in errors)


def test_validator_rejects_reordered_writes_and_stale_attribution():
    receipt = copy.deepcopy(retained_receipts()[0])
    receipt["request_writes"].reverse()
    decision = receipt["decisions"][0]
    decision["request"] = 2
    decision["gp4c4"] = 0
    decision["finalizer_observed"] = False
    decision["last_request_writer"] = receipt["request_writes"][-1]
    errors, controls = PROBE.validate_receipt(receipt)
    assert controls == []
    assert any("cycle order" in error for error in errors)
    assert any("inconsistent" in error for error in errors)


def test_validator_rejects_missing_captured_decision_values():
    for field in ("request", "gp4c4", "frame", "cycle"):
        receipt = copy.deepcopy(retained_receipts()[0])
        receipt["decisions"][0].pop(field)
        errors, controls = PROBE.validate_receipt(receipt)
        assert controls == []
        assert "decision certificate invalid" in errors


def test_validator_rejects_forged_capture_acceptance():
    receipt = copy.deepcopy(retained_receipts()[0])
    receipt["capture_accepted"] = False
    receipt["capture_assertions"][0]["passed"] = False
    errors, controls = PROBE.validate_receipt(receipt)
    assert controls == []
    assert "receipt does not declare an accepted capture" in errors
    assert "capture assertions are missing or failed" in errors


def test_validator_rejects_boolean_access_width():
    receipt = copy.deepcopy(retained_receipts()[0])
    receipt["request_writes"][0]["width"] = True
    errors, controls = PROBE.validate_receipt(receipt)
    assert controls == []
    assert any("effective-writer provenance" in error for error in errors)


def test_validator_rejects_forged_retained_summaries():
    receipt = copy.deepcopy(retained_receipts()[0])
    receipt["request_values"] = [2]
    receipt["natural_request2_skip_control_observed"] = True
    receipt["natural_request2_skip_controls"] = [{"forged": True}]
    receipt["receipt_self_validation_errors"] = ["forged but ignored"]
    errors, controls = PROBE.validate_receipt(receipt)
    assert controls == []
    assert {
        "stored request-value summary is inconsistent",
        "stored request-2 control rows are inconsistent",
        "stored request-2 control observation is inconsistent",
        "receipt retains self-validation errors",
    } <= set(errors)
