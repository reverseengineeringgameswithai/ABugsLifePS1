#!/usr/bin/env python3
"""Validate and emit review-only derivatives of config/semantic_state.yaml."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "semantic_state.yaml"
NAMESPACES = {"original", "mod_private", "hypothesis"}
CONFIDENCE = {"hypothesized", "static_seen", "runtime_seen", "confirmed"}
WIDTHS = {"u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4}


class RegistryError(ValueError):
    pass


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"cannot load registry {path}: {exc}") from exc
    validate_registry(doc)
    return doc


def known_overlay_images() -> set[str]:
    """Overlay image names, DERIVED from the committed registries -- never hardcoded.

    Union of the overlay decompilation track (config/overlays.yml, the 12 with attempted
    matches) and the function census's own per-image tags (analysis/functions.json,
    all 20). Either file may be absent in a stripped checkout; the caller then skips
    name validation rather than inventing a set.
    """
    names: set[str] = set()
    ovl = ROOT / "config" / "overlays.yml"
    if ovl.exists():
        try:
            doc = yaml.safe_load(ovl.read_text(encoding="utf-8")) or {}
            names |= set((doc.get("overlays") or {}).keys())
        except yaml.YAMLError:
            pass
    fns = ROOT / "analysis" / "functions.json"
    if fns.exists():
        try:
            for f in json.loads(fns.read_text(encoding="utf-8")).get("functions", []):
                if f.get("space") != "resident" and isinstance(f.get("overlay"), str):
                    names.add(f["overlay"])
        except (OSError, json.JSONDecodeError):
            pass
    return names


def validate_registry(doc: Any) -> None:
    known_images = known_overlay_images()
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise RegistryError("registry must be a mapping with schema_version: 1")
    if set((doc.get("namespaces") or {}).keys()) != NAMESPACES:
        raise RegistryError(f"registry must define exactly these namespaces: {sorted(NAMESPACES)}")
    entries = doc.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RegistryError("registry entries must be a non-empty list")
    ids: set[str] = set()
    occupied: dict[tuple[str, int], str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RegistryError("every registry entry must be a mapping")
        eid = entry.get("id")
        namespace = entry.get("namespace")
        if not isinstance(eid, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]*", eid):
            raise RegistryError(f"invalid entry id: {eid!r}")
        if eid in ids:
            raise RegistryError(f"duplicate entry id: {eid}")
        ids.add(eid)
        if namespace not in NAMESPACES or not eid.startswith(namespace + "."):
            raise RegistryError(f"{eid}: namespace/id mismatch")
        if entry.get("confidence") not in CONFIDENCE:
            raise RegistryError(f"{eid}: invalid confidence")
        address = entry.get("address")
        width = entry.get("width")
        if namespace == "hypothesis":
            if entry.get("confidence") != "hypothesized":
                raise RegistryError(f"{eid}: hypotheses must remain hypothesized")
        elif not isinstance(address, int):
            raise RegistryError(f"{eid}: confirmed namespaces require an integer address")
        if entry.get("kind") in {"field", "overlay_field"} and width not in WIDTHS:
            raise RegistryError(f"{eid}: fields need a supported width")
        if width is not None and width not in WIDTHS:
            raise RegistryError(f"{eid}: invalid width {width!r}")
        # OVERLAY KEYING. Every overlay is CdRead-loaded at the same VA, so an overlay
        # address is NOT an identity: 0x800B4A3C is `training_step` (range 0..13) in
        # LEVEL07/LEVEL1.BIN and a different, independently measured field (0..320 over
        # 1,896 writes) in LEVEL02/LEVEL1.BIN. Keying on (namespace, address) alone made
        # the second field UNRECORDABLE -- the gate rejected it as a duplicate of the
        # first, so the registry could hold at most one overlay's view of any VA.
        # The key is therefore (namespace, image, address); `image` is required for
        # overlay_field and must be absent for resident state, where the VA IS the key.
        image = entry.get("image")
        if entry.get("kind") == "overlay_field":
            if not isinstance(image, str) or not image:
                raise RegistryError(
                    f"{eid}: overlay_field requires `image` (which blob owns this VA) -- "
                    "an overlay address alone is ambiguous by construction")
            if known_images and image not in known_images:
                raise RegistryError(f"{eid}: unknown image {image!r}; "
                                    f"expected one of {sorted(known_images)}")
        elif image is not None:
            raise RegistryError(f"{eid}: `image` is only meaningful for overlay_field "
                                f"(kind={entry.get('kind')!r}); resident VAs are unique")
        if isinstance(address, int) and width in WIDTHS:
            align = WIDTHS[width]
            if align > 1 and address % align:
                raise RegistryError(f"{eid}: {width} address {address:#x} is misaligned")
            key = (namespace, image, address)
            if key in occupied:
                where = f" in {image}" if image else ""
                raise RegistryError(f"{eid}: duplicates {occupied[key]} at {address:#x}{where}")
            occupied[key] = eid
        if not isinstance(entry.get("owner"), str) or not entry["owner"]:
            raise RegistryError(f"{eid}: owner is required")
        if not isinstance(entry.get("writers"), list):
            raise RegistryError(f"{eid}: writers must be a list")
        if not isinstance(entry.get("invariants"), list):
            raise RegistryError(f"{eid}: invariants must be a list")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise RegistryError(f"{eid}: at least one evidence path is required")


def symbol_name(eid: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", eid).upper()


def confirmed_entries(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in doc["entries"] if e["namespace"] != "hypothesis" and isinstance(e.get("address"), int)]


def emit_asm(doc: dict[str, Any]) -> str:
    lines = ["; GENERATED REVIEW SNIPPET -- do not overwrite hand-authored labels automatically."]
    lines += [f".definelabel {symbol_name(e['id'])}, 0x{e['address']:08X}" for e in confirmed_entries(doc)]
    return "\n".join(lines) + "\n"


def emit_c(doc: dict[str, Any]) -> str:
    lines = ["/* GENERATED REVIEW SNIPPET -- copy intentionally; do not overwrite authored headers. */"]
    lines += [f"#define {symbol_name(e['id'])} 0x{e['address']:08X}u" for e in confirmed_entries(doc)]
    return "\n".join(lines) + "\n"


def emit_scenario(doc: dict[str, Any]) -> str:
    assertions = []
    for entry in confirmed_entries(doc):
        if entry.get("width") not in WIDTHS:
            continue
        for invariant in entry.get("invariants", []):
            if invariant.get("kind") == "range":
                assertions.append({
                    "id": entry["id"].replace(".", "_") + "_range",
                    "type": "memory", "address": f"0x{entry['address']:08x}",
                    "width": entry["width"], "op": "between",
                    "expected": [invariant["min"], invariant["max"]],
                    "semantic_id": entry["id"],
                })
    return yaml.safe_dump({"assertions": assertions}, sort_keys=False)


def emit_obsidian(doc: dict[str, Any]) -> str:
    lines = ["| ID | Namespace | Kind | Address | Width | Owner | Confidence |",
             "|---|---|---|---:|---|---|---|"]
    for e in doc["entries"]:
        address = f"`0x{e['address']:08X}`" if isinstance(e.get("address"), int) else "unresolved"
        lines.append(f"| `{e['id']}` | {e['namespace']} | {e['kind']} | {address} | "
                     f"{e.get('width') or '—'} | `{e['owner']}` | {e['confidence']} |")
    return "\n".join(lines) + "\n"


EMITTERS = {"asm": emit_asm, "c": emit_c, "scenario": emit_scenario, "obsidian": emit_obsidian,
            "json": lambda d: json.dumps(d, indent=2) + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--emit", choices=sorted(EMITTERS))
    parser.add_argument("--output", type=Path,
                        help="write a new generated file; existing files are never overwritten")
    args = parser.parse_args()
    try:
        doc = load_registry(args.registry)
        if not args.emit:
            print(f"valid: {args.registry} ({len(doc['entries'])} entries)")
            return 0
        rendered = EMITTERS[args.emit](doc)
        if args.output:
            output = args.output.resolve()
            if output.exists():
                raise RegistryError(f"refusing to overwrite existing file: {output}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
            print(output)
        else:
            print(rendered, end="")
        return 0
    except RegistryError as exc:
        print(f"semantic registry error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
