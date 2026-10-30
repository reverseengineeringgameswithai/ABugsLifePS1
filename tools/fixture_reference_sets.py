#!/usr/bin/env python3
"""Resolve frozen mechanics-registry fixture shorthand to literal paths.

``analysis/mechanics_baseline.yaml`` is a historical baseline and is not edited
by Phase 4. Two of its ``fixture_have`` values predate the rule that every
fixture reference must be a repository-relative path: one is a six-save prose
summary and one is a bare movie basename. This module applies the explicit,
evidence-linked source corrections in ``config/fixture_reference_sets.yaml`` to
every generator that consumes that baseline.

This is deliberately not a closure-gate exception. A correction must replace
an exact value still present in its named row, must expand to one or more literal
fixture paths, and the downstream audit still requires every expanded path to
exist in the central fixture manifest.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/fixture_reference_sets.yaml"
SCHEMA = "abl-fixture-reference-sets/1"


def load() -> dict:
    doc = yaml.safe_load(CONFIG.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"{CONFIG.relative_to(ROOT)} has an invalid schema")
    rows = doc.get("rows")
    if not isinstance(rows, dict):
        raise ValueError(f"{CONFIG.relative_to(ROOT)} rows must be a mapping")
    return doc


def _literal_fixture_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        return False
    return value.endswith(".sav") or (".movie" in path.name and value.endswith(".json"))


def resolve_row(row: dict, document: dict | None = None) -> list[str]:
    """Return one row's literal fixture references after strict correction."""
    values = [str(value) for value in (row.get("fixture_have") or [])]
    correction = (document or load())["rows"].get(row.get("id"))
    if correction is None:
        return values

    legacy = correction.get("replaces")
    if values.count(legacy) != 1:
        raise ValueError(
            f"{row.get('id')}: configured fixture correction must replace exactly "
            f"one current value, found {values.count(legacy)}")
    fixtures = correction.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError(f"{row.get('id')}: fixture correction is empty")
    if len(set(fixtures)) != len(fixtures):
        raise ValueError(f"{row.get('id')}: fixture correction contains duplicates")
    bad = [value for value in fixtures if not _literal_fixture_path(value)]
    if bad:
        raise ValueError(f"{row.get('id')}: non-literal fixture paths: {bad}")
    evidence = correction.get("evidence")
    if not isinstance(evidence, str) or not (ROOT / evidence).is_file():
        raise ValueError(f"{row.get('id')}: correction evidence is absent: {evidence}")

    result: list[str] = []
    for value in values:
        result.extend(fixtures if value == legacy else [value])
    return result


def validate_rows(rows: list[dict], document: dict | None = None) -> None:
    """Fail on stale/orphan corrections as well as malformed expansions."""
    doc = document or load()
    by_id = {row.get("id"): row for row in rows}
    unknown = sorted(set(doc["rows"]) - set(by_id))
    if unknown:
        raise ValueError(f"fixture corrections name unknown mechanics rows: {unknown}")
    for row_id in doc["rows"]:
        resolve_row(by_id[row_id], doc)
