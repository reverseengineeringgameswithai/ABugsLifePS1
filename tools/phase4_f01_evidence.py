#!/usr/bin/env python3
"""Shared fail-closed identity helpers for the F01 oracle/breadth repair.

This module owns filesystem/media identity only.  It deliberately does not decode MIPS
instructions; the compiled-C probes remain the instruction-decoding authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SET = ROOT / "analysis/phase0_2_external_fixture_set.json"

PRISTINE_SERIAL = "SCUS-94288"
PRISTINE_TITLE = "Disney-Pixar A Bug's Life"
PRISTINE_CUE_NAME = "Disney-Pixar A Bug's Life (v1.0).cue"
PRISTINE_CUE_SHA256 = "463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644"
PRISTINE_BIN_NAME = "Disney-Pixar A Bug's Life (v1.0).bin"
PRISTINE_BIN_SHA256 = "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566"
PRISTINE_EXE_NAME = "SCUS_942.88"
PRISTINE_EXE_IDENTITY = "REBUILD/files/SCUS_942.88"
PRISTINE_EXE_SHA256 = "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fixture_entries(path: Path = FIXTURE_SET) -> dict[str, dict[str, Any]]:
    return json.loads(path.read_text())["entries"]


def external_identity(
    path_value: str | Path,
    allowed_identities: set[str],
    *,
    root: Path = ROOT,
) -> str:
    """Map a local/old-checkout path to exactly one centrally declared identity."""
    path = Path(path_value)
    if path.is_absolute():
        try:
            identity = path.relative_to(root).as_posix()
        except ValueError:
            matches = sorted(
                item for item in allowed_identities
                if path.as_posix().endswith(f"/{item}")
            )
            if len(matches) != 1:
                raise ValueError(
                    f"cannot map absolute path to exactly one declared identity: {path}"
                )
            identity = matches[0]
    else:
        identity = path.as_posix()

    if identity.startswith("../") or identity.startswith("/"):
        raise ValueError(f"identity escapes repository root: {identity}")
    if identity not in allowed_identities:
        raise ValueError(f"identity is not centrally declared: {identity}")
    return identity


def provisioned_path(identity: str, *, root: Path = ROOT) -> Path:
    path = root / identity
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"identity escapes provisioned root: {identity}") from exc
    return path


def pristine_executable_path(*, root: Path = ROOT) -> Path:
    """Return the project-declared pristine EXE path, never a convenience copy."""
    return root / PRISTINE_EXE_IDENTITY


def observed_media_identity(media: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    """Hash the mounted descriptor, its track, and the executing retail EXE.

    `emulator.getMediaInfo` exposes the mounted path but does not hash every CUE track.
    The descriptor and its one referenced BIN are therefore measured separately.
    Checkout-local absolute paths are intentionally absent from the returned identity.
    """
    cue_path = Path(str(media.get("path") or ""))
    if not cue_path.is_absolute() or not cue_path.is_file():
        raise ValueError(f"mounted media path is not an absolute existing file: {cue_path}")
    track_path = cue_path.with_name(PRISTINE_BIN_NAME)
    executable_path = pristine_executable_path(root=root)
    if not track_path.is_file():
        raise ValueError(f"pristine track is absent beside mounted CUE: {track_path}")
    if not executable_path.is_file():
        raise ValueError(f"pristine executable is absent: {executable_path}")
    return {
        "has_media": media.get("has_media"),
        "serial": media.get("game_serial"),
        "title": media.get("game_title"),
        "cue": {
            "identity": PRISTINE_CUE_NAME,
            "sha256": sha256_file(cue_path),
        },
        "track": {
            "identity": PRISTINE_BIN_NAME,
            "sha256": sha256_file(track_path),
        },
        "executable": {
            "identity": PRISTINE_EXE_NAME,
            "sha256": sha256_file(executable_path),
        },
    }


def pristine_media_checks(identity: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {
        "has_media": True,
        "serial": PRISTINE_SERIAL,
        "title": PRISTINE_TITLE,
        "cue_identity": PRISTINE_CUE_NAME,
        "cue_sha256": PRISTINE_CUE_SHA256,
        "track_identity": PRISTINE_BIN_NAME,
        "track_sha256": PRISTINE_BIN_SHA256,
        "executable_identity": PRISTINE_EXE_NAME,
        "executable_sha256": PRISTINE_EXE_SHA256,
    }
    actual = {
        "has_media": identity.get("has_media"),
        "serial": identity.get("serial"),
        "title": identity.get("title"),
        "cue_identity": (identity.get("cue") or {}).get("identity"),
        "cue_sha256": (identity.get("cue") or {}).get("sha256"),
        "track_identity": (identity.get("track") or {}).get("identity"),
        "track_sha256": (identity.get("track") or {}).get("sha256"),
        "executable_identity": (identity.get("executable") or {}).get("identity"),
        "executable_sha256": (identity.get("executable") or {}).get("sha256"),
    }
    return [
        {
            "id": f"pristine_media_{key}",
            "expected": value,
            "actual": actual[key],
            "passed": actual[key] == value,
        }
        for key, value in expected.items()
    ]


def oracle_provenance_checks(
    *,
    movie_identity: str,
    movie_doc: dict[str, Any],
    movie_sha256: str,
    movie_size: int,
    central_pin: dict[str, Any] | None,
    media_identity: dict[str, Any],
    trace_truncated: Any,
    playback_reproducible: Any,
    playback_completed: Any,
    declared_identities: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return every provenance predicate as a mutation-friendly assertion row."""
    start = movie_doc.get("start_state")
    start = start if isinstance(start, dict) else {}
    actual_pin = central_pin or {}
    declared = declared_identities if declared_identities is not None else set(fixture_entries())
    checks = [
        ("movie_identity_declared", movie_identity in declared, True),
        ("movie_hash_matches_central_pin", actual_pin.get("sha256") == movie_sha256, True),
        ("movie_size_matches_central_pin", actual_pin.get("size") == movie_size, True),
        ("movie_media_class_is_pristine", actual_pin.get("media_class"), "pristine_serial"),
        ("movie_preservation_required", actual_pin.get("preservation_required"), True),
        ("movie_metadata_from_boot", start.get("from_boot"), True),
        ("movie_metadata_start_path_empty", start.get("path"), ""),
        ("movie_metadata_start_size_zero", start.get("file_size"), 0),
        ("movie_metadata_start_hash_absent", start.get("sha256"), None),
        ("movie_metadata_not_loaded_before_recording",
         start.get("loaded_before_recording"), False),
        ("movie_metadata_not_state_only",
         start.get("reproducible_only_from_state"), False),
        ("movie_metadata_serial", start.get("game_serial"), PRISTINE_SERIAL),
        ("movie_top_level_serial", movie_doc.get("game_serial"), PRISTINE_SERIAL),
        ("playback_reproducible", playback_reproducible, True),
        ("playback_completed", playback_completed, True),
        ("exec_trace_not_truncated", trace_truncated, False),
    ]
    rows = [
        {"id": key, "expected": expected, "actual": actual,
         "passed": actual == expected}
        for key, actual, expected in checks
    ]
    rows.extend(pristine_media_checks(media_identity))
    return rows


def require_checks(checks: list[dict[str, Any]], label: str) -> None:
    failed = [row for row in checks if not row.get("passed")]
    if failed:
        details = "; ".join(
            f"{row['id']}={row.get('actual')!r} expected {row.get('expected')!r}"
            for row in failed
        )
        raise ValueError(f"{label} failed closed: {details}")
