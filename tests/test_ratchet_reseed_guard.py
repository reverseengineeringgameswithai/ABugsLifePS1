import json
from pathlib import Path

from tools import ratchet_reseed_guard


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _build(
    tmp_path: Path,
    *,
    summary: str = "advanced boundary",
    complete_rows: int = 16,
    previous_signature: str = "",
    previous_repeat_count: int = 0,
) -> dict:
    decision = _write(tmp_path / "decision.json", {
        "phase": 4,
        "status": "open_autonomous",
        "summary": summary,
        "gaps": ["next bounded experiment"],
        "gap_codes": ["NEXT_EXPERIMENT"],
        "required_input": "",
        "candidate_commit": "a" * 40,
    })
    debt = _write(tmp_path / "debt.json", {
        "valid": True,
        "counts": {"complete_rows": complete_rows, "open_rows": 107 - complete_rows},
        "campaigns": [{
            "campaign_id": "fmv_playback",
            "counts": {"met": 3, "remaining": 6},
            "dimensions": {"source_closure": "partial"},
            "next_lane": "live",
            "rows": ["E15_fmv_playback"],
        }],
        "scheduler": {"selected_campaigns": ["fmv_playback"], "wip_limits": {}},
    })
    return ratchet_reseed_guard.build(
        reason="TRIAL_CRITICAL_CHANGE",
        decision=decision,
        debt=debt,
        details=None,
        previous_signature=previous_signature,
        previous_repeat_count=previous_repeat_count,
        max_identical_reseeds=3,
    )


def test_identical_no_progress_signature_opens_on_third_occurrence(tmp_path):
    first = _build(tmp_path)
    assert first["repeat_count"] == 1
    assert not first["circuit_open"]
    second = _build(
        tmp_path,
        previous_signature=first["semantic_signature"],
        previous_repeat_count=first["repeat_count"],
    )
    assert second["same_as_previous"]
    assert second["repeat_count"] == 2
    assert not second["circuit_open"]
    third = _build(
        tmp_path,
        previous_signature=second["semantic_signature"],
        previous_repeat_count=second["repeat_count"],
    )
    assert third["same_as_previous"]
    assert third["repeat_count"] == 3
    assert third["circuit_open"]


def test_semantic_or_debt_progress_resets_repeat_count(tmp_path):
    first = _build(tmp_path)
    semantic = _build(
        tmp_path,
        summary="different bounded finding",
        previous_signature=first["semantic_signature"],
        previous_repeat_count=2,
    )
    assert not semantic["same_as_previous"]
    assert semantic["repeat_count"] == 1
    assert not semantic["circuit_open"]

    debt = _build(
        tmp_path,
        complete_rows=17,
        previous_signature=semantic["semantic_signature"],
        previous_repeat_count=2,
    )
    assert not debt["same_as_previous"]
    assert debt["repeat_count"] == 1
    assert not debt["circuit_open"]


def test_candidate_hash_does_not_fake_progress(tmp_path):
    first = _build(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision = json.loads(decision_path.read_text())
    decision["candidate_commit"] = "b" * 40
    decision_path.write_text(json.dumps(decision))
    second = ratchet_reseed_guard.build(
        reason="TRIAL_CRITICAL_CHANGE",
        decision=decision_path,
        debt=tmp_path / "debt.json",
        details=None,
        previous_signature=first["semantic_signature"],
        previous_repeat_count=1,
        max_identical_reseeds=3,
    )
    assert second["same_as_previous"]
    assert second["repeat_count"] == 2
