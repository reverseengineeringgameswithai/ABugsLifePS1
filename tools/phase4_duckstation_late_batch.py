#!/usr/bin/env python3
"""Execute typed late-arm boot batches without changing the legacy adapter.

The closed iteration-1 E15 receipt hash-pins
``tools/phase4_duckstation_batch.py``.  This narrow adapter preserves those
historical bytes while admitting one additional recipe shape:
``scenario.bootAndRun`` with a typed emulator-frame staged prelude.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import phase4_common as common
import phase4_duckstation_batch as legacy

_ORIGINAL_VALIDATE = legacy.validate_plan
_ORIGINAL_RAW_RESULT = legacy._raw_result_document
_ORIGINAL_EMIT = legacy.emit_v2_receipt
_ORIGINAL_RUN_LIVE = legacy.run_live


def __getattr__(name: str):
    """Expose unchanged constants/helpers from the preserved adapter."""
    return getattr(legacy, name)


def _staged_prelude(operation: object) -> dict[str, int | str]:
    if not isinstance(operation, dict) or set(operation) != {
            "kind", "target_frame", "max_frames"}:
        raise ValueError(
            "staged_prelude must contain exactly kind, target_frame, and "
            "max_frames")
    if operation["kind"] != "emulator_advance":
        raise ValueError("staged_prelude kind must be emulator_advance")
    normalized: dict[str, int | str] = {"kind": "emulator_advance"}
    for key in ("target_frame", "max_frames"):
        value = operation[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"staged_prelude {key} must be a positive integer")
        if value > legacy.MAX_STAGED_PRELUDE_FRAMES:
            raise ValueError(
                f"staged_prelude {key} exceeds the debugger recipe limit")
        normalized[key] = value
    if normalized["max_frames"] < normalized["target_frame"]:
        raise ValueError(
            "staged_prelude max_frames must cover its absolute target")
    return normalized


def _central_fixture(
        path_text: str, entries: dict, operator_root: Path
) -> tuple[str | None, dict | None]:
    raw = Path(path_text)
    path = (
        raw.resolve()
        if raw.is_absolute()
        else (common.ROOT / raw).resolve()
    )
    try:
        rel = str(path.relative_to(common.ROOT))
    except ValueError:
        return None, None
    if rel in entries:
        return rel, entries[rel]
    return None, None


def _legacy_validation_view(
        plan: dict, operator_root: Path
) -> dict:
    """Remove the new prelude only for the legacy validation predicates."""
    translated = copy.deepcopy(plan)
    for job in translated.get("jobs") or []:
        job.pop("staged_prelude", None)
        movie = job.get("movie") or {}
        movie_path = Path(str(movie.get("path") or ""))
        resolved_movie = (
            movie_path.resolve()
            if movie_path.is_absolute()
            else (common.ROOT / movie_path).resolve()
        )
        try:
            relative = resolved_movie.relative_to(common.ROOT)
        except (ValueError, OSError):
            continue
        operator_path = (operator_root / relative).resolve()
        if operator_path.is_file():
            movie["path"] = str(operator_path)
    receipt = translated.get("v2_receipt") or {}
    execution = receipt.get("execution") or {}
    bound = execution.get("bound") or {}
    capture = execution.get("capture_window") or {}
    if bound.get("clock") == "emulator_frame" and \
            capture.get("clock") == "emulator_frame":
        capture["start"] = bound.get("start")
    return translated


def validate_plan(
        plan: dict, operator_root: Path | None = None,
        debt_doc: dict | None = None, escalation_doc: dict | None = None,
        capsule_doc: dict | None = None,
        allow_executed: bool = False) -> list[str]:
    operator_root = (
        operator_root
        or Path.home() / "Downloads" / "ABL"
    ).resolve()
    jobs = plan.get("jobs") or []
    staged = [
        (job.get("id", "<missing>"), job.get("staged_prelude"))
        for job in jobs if job.get("staged_prelude") is not None
    ]
    if not staged:
        return _ORIGINAL_VALIDATE(
            plan, operator_root=operator_root, debt_doc=debt_doc,
            escalation_doc=escalation_doc, capsule_doc=capsule_doc,
            allow_executed=allow_executed,
        )

    errors = _ORIGINAL_VALIDATE(
        _legacy_validation_view(plan, operator_root),
        operator_root=operator_root, debt_doc=debt_doc,
        escalation_doc=escalation_doc, capsule_doc=capsule_doc,
        allow_executed=allow_executed,
    )
    receipt = plan.get("v2_receipt") or {}
    execution = receipt.get("execution") or {}
    bound = execution.get("bound") or {}
    capture = execution.get("capture_window") or {}
    capture_start = capture.get("start")
    capture_stop = capture.get("stop")
    if len(staged) != len(jobs):
        errors.append(
            "v2_receipt nonzero cold-boot capture requires one "
            "emulator_advance staged_prelude in every job")
    entries = common.load_json(common.FIXTURE_SET_PATH).get("entries") or {}
    for job in jobs:
        job_id = job.get("id", "<missing>")
        operation = job.get("staged_prelude")
        if operation is None:
            continue
        try:
            prelude = _staged_prelude(operation)
        except ValueError as exc:
            errors.append(f"{job_id}: {exc}")
            if isinstance(operation, dict) and \
                    operation.get("kind") == "movie_advance":
                errors.append(
                    f"{job_id}: movie_advance staged_prelude is valid only "
                    "for loadStateAndRun")
            continue
        if job.get("recipe") != "bootAndRun":
            errors.append(
                f"{job_id}: emulator_advance staged_prelude is valid only "
                "for bootAndRun")
        if set(job.get("run") or {}) != {"frames"}:
            errors.append(
                f"{job_id}: emulator_advance staged_prelude requires one "
                "post-prelude frames bound")
        if prelude["target_frame"] != capture_start:
            errors.append(
                "v2_receipt emulator-frame capture start differs from the "
                "staged_prelude target")
        if prelude["max_frames"] != prelude["target_frame"]:
            errors.append(
                f"{job_id}: emulator_advance max_frames must equal the "
                "absolute target for this cold-boot plan")
        movie_path = str((job.get("movie") or {}).get("path") or "")
        rel, pin = _central_fixture(movie_path, entries, operator_root)
        path = Path(movie_path)
        if not path.is_absolute():
            path = (common.ROOT / path).resolve()
        if not rel or not pin:
            errors.append(
                f"{job_id}: external fixture is not centrally declared: "
                f"{movie_path}")
        elif pin.get("media_class") not in {"pristine", "pristine_serial"}:
            errors.append(f"{job_id}: fixture is not pristine eligible: {rel}")
        elif not path.is_absolute() or not path.is_file() or \
                common.sha256(path) != pin.get("sha256") or \
                path.stat().st_size != pin.get("size"):
            errors.append(
                f"{job_id}: fixture hash/size differs from central pin: {rel}")
    if bound.get("clock") != "emulator_frame" or bound.get("start") != 0:
        errors.append(
            "v2_receipt staged_prelude execution bound must retain the "
            "cold-boot frame-zero anchor")
    if capture.get("clock") != "emulator_frame" or \
            not isinstance(capture_start, int) or \
            not isinstance(capture_stop, int) or \
            capture_start <= 0 or capture_stop <= capture_start:
        errors.append(
            "v2_receipt emulator-frame capture window is invalid")
    elif any(
            (job.get("run") or {}).get("frames")
            != capture_stop - capture_start
            for job in jobs):
        errors.append(
            "v2_receipt post-prelude frames do not exactly cover the "
            "emulator-frame capture window")
    assertion_prelude = (
        (receipt.get("assertion_plan") or {}).get(
            "required_staged_prelude")
        or {}
    )
    if assertion_prelude != {
            "kind": "emulator_advance",
            "start": 1,
            "stop": capture_start}:
        errors.append(
            "v2_receipt assertion does not bind the returned emulator "
            "staged-prelude counters")
    return sorted(set(errors))


def _execution_plan(plan: dict) -> dict:
    """Resolve provisioned movie aliases only at the RPC execution boundary."""
    normalized = copy.deepcopy(plan)
    for job in normalized.get("jobs") or []:
        movie = job.get("movie") or {}
        path_text = str(movie.get("path") or "")
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_absolute():
            movie["path"] = str((common.ROOT / path).resolve())
    return normalized


def run_live(*args, **kwargs):
    plan = args[0] if args else kwargs["plan"]
    normalized = _execution_plan(plan)
    if args:
        args = (normalized, *args[1:])
    else:
        kwargs["plan"] = normalized
    return _ORIGINAL_RUN_LIVE(*args, **kwargs)


def _raw_result_document(
        document: dict, session_id: str, execution: dict
) -> dict:
    raw = _ORIGINAL_RAW_RESULT(document, session_id, execution)
    jobs = {
        row.get("id"): row
        for row in (document.get("result") or {}).get("jobs") or []
    }
    added_replay_frames = 0
    for row in raw["results"]:
        result = (jobs.get(row["job_id"]) or {}).get("result") or {}
        staged = result.get("staged_prelude")
        if not isinstance(staged, dict):
            raise RuntimeError(
                f"{row['job_id']}: staged prelude lacks emulator counters")
        values = {
            "advanced": staged.get("frames_advanced"),
            "start": staged.get("start_frame"),
            "stop": staged.get("target_frame"),
            "status_stop": (staged.get("status") or {}).get("frame"),
        }
        if not all(isinstance(value, int) for value in values.values()) or \
                values["start"] < 0 or \
                values["stop"] <= values["start"] or \
                values["stop"] - values["start"] != values["advanced"] or \
                values["status_stop"] != values["stop"] or \
                values["stop"] != row["observer_start"]:
            raise RuntimeError(
                f"{row['job_id']}: staged prelude is not contiguous with "
                "the observed emulator-frame run")
        row["replay_start"] = values["start"]
        added_replay_frames += values["advanced"]
    raw["counters"]["replay_frames"] += added_replay_frames
    return raw


def emit_v2_receipt(*args, **kwargs) -> Path:
    """Retain this adapter's source identity in the otherwise shared writer."""
    original_file = legacy.__file__
    try:
        legacy.__file__ = __file__
        receipt_path = _ORIGINAL_EMIT(*args, **kwargs)
    finally:
        legacy.__file__ = original_file
    receipt = json.loads(receipt_path.read_text())
    receipt["evidence"]["adapter_source"]["path"] = (
        "tools/phase4_duckstation_late_batch.py"
    )
    legacy.write_json(receipt_path, receipt)
    return receipt_path


def main() -> int:
    legacy.validate_plan = validate_plan
    legacy._raw_result_document = _raw_result_document
    legacy.emit_v2_receipt = emit_v2_receipt
    legacy.run_live = run_live
    return legacy.main()


if __name__ == "__main__":
    raise SystemExit(main())
