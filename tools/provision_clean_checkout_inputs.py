#!/usr/bin/env python3
"""Provision only centrally declared external inputs into a clean checkout.

The source root is operator-owned and defaults to ``~/Downloads/ABL``. Every
source is hash-verified before it is copied, an existing mismatched target is
never overwritten, and the copied bytes are verified again. No media bytes are
added to Git; the authoritative declarations are:

* ``tools/build_baselines.json`` for pristine media and ``REBUILD/files``;
* ``analysis/phase0_2_external_fixture_set.json`` for saves, movies, derived
  retail metadata, and derived assembly.

Usage:
    python3 tools/provision_clean_checkout_inputs.py
    python3 tools/provision_clean_checkout_inputs.py --verify-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "tools/build_baselines.json"
FIXTURES = ROOT / "analysis/phase0_2_external_fixture_set.json"
KNOWLEDGE_MATRIX = ROOT / "analysis/phase0_2_knowledge_closure.yaml"
DEFAULT_OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads/ABL")))


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def safe_relative(value: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise SystemExit(f"unsafe centrally declared relative path: {value!r}")
    return Path(*pure.parts)


def build_plan(operator_root: Path) -> list[dict]:
    """Return the exact, de-duplicated plan represented by the two manifests."""
    operator_root = operator_root.expanduser().resolve()
    baselines = json.loads(BASELINES.read_text())
    fixture_set = json.loads(FIXTURES.read_text())
    fixtures = dict(fixture_set["entries"])
    # Bootstrap newly declared derived inputs before the generated fixture-set
    # consumer has been refreshed. Once refreshed, these merges are no-ops.
    matrix = yaml.safe_load(KNOWLEDGE_MATRIX.read_text())

    def merge_fixture(rel: str, pin: dict, authority: str) -> None:
        existing = fixtures.get(rel)
        if existing and any(existing.get(key) != pin.get(key)
                            for key in ("sha256", "size", "media_class")):
            raise SystemExit(
                f"conflicting central declarations for {rel}: fixture set vs {authority}")
        fixtures.setdefault(rel, pin)

    for row in matrix.get("external_local_media_inputs", []):
        merge_fixture(row["path"], row, "knowledge matrix")
    for spec in matrix.get("external_local_media_manifests", []):
        manifest = ROOT / spec["path"]
        for line in manifest.read_text().splitlines():
            parts = line.split()
            if len(parts) != 2 or len(parts[0]) != 64 or not parts[1].startswith(
                    spec["prefix"]):
                continue
            source = operator_root / safe_relative(parts[1])
            merge_fixture(parts[1], {
                "sha256": parts[0],
                "size": source.stat().st_size if source.is_file() else None,
                "media_class": spec["media_class"],
            }, spec["path"])
    plan = []
    for name, pin in sorted(baselines["pristine_media"].items()):
        plan.append({
            "class": "pristine_media",
            "source": operator_root / safe_relative(name),
            "target": ROOT / safe_relative(name),
            "algorithm": "sha1",
            "digest": pin["sha1"],
            "size": pin.get("size"),
        })
    for rel, pin in sorted(baselines["staged_inputs"].items()):
        plan.append({
            "class": "pristine_staged_input",
            "source": operator_root / "REBUILD/files" / safe_relative(rel),
            "target": ROOT / "REBUILD/files" / safe_relative(rel),
            "algorithm": "sha256",
            "digest": pin["sha256"],
            "size": pin["size"],
        })
    for rel, pin in sorted(fixtures.items()):
        plan.append({
            "class": pin["media_class"],
            "source": operator_root / safe_relative(rel),
            "target": ROOT / safe_relative(rel),
            "algorithm": "sha256",
            "digest": pin["sha256"],
            "size": pin["size"],
        })
    seen = set()
    duplicates = []
    for row in plan:
        key = row["target"].resolve()
        if key in seen:
            duplicates.append(str(key.relative_to(ROOT)))
        seen.add(key)
    if duplicates:
        raise SystemExit(f"duplicate centrally declared targets: {duplicates[:8]}")
    return plan


def verify_path(path: Path, row: dict, label: str) -> None:
    if not path.is_file():
        raise SystemExit(f"{label} absent: {path}")
    expected_size = row.get("size")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise SystemExit(
            f"{label} size mismatch: {path}: {path.stat().st_size} != {expected_size}")
    actual = digest(path, row["algorithm"])
    if actual != row["digest"]:
        raise SystemExit(
            f"{label} {row['algorithm']} mismatch: {path}: "
            f"{actual} != {row['digest']}")


def provision(row: dict, verify_only: bool) -> str:
    source, target = row["source"], row["target"]
    verify_path(source, row, "operator source")
    if target.exists():
        verify_path(target, row, "checkout target")
        return "verified"
    if verify_only:
        raise SystemExit(f"checkout target absent: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.provisioning-", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        verify_path(temporary, row, "provisional copy")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    verify_path(target, row, "checkout target")
    return "copied"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--operator-root", type=Path, default=DEFAULT_OPERATOR_ROOT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    plan = build_plan(args.operator_root)
    counts: dict[str, int] = {"copied": 0, "verified": 0}
    classes: dict[str, int] = {}
    for row in plan:
        counts[provision(row, args.verify_only)] += 1
        classes[row["class"]] = classes.get(row["class"], 0) + 1
    print(
        f"[provision] PASS {len(plan)} centrally declared inputs: "
        f"copied={counts['copied']} verified={counts['verified']} classes={classes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
