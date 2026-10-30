#!/usr/bin/env python3
"""Validate the typed registry of confirmed non-function-start sites."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/confirmed_sites.yaml"


def validate(doc: dict) -> list[str]:
    errors, ids, addresses = [], set(), set()
    for entry in doc.get("entries", []):
        ident, addr = entry.get("id"), entry.get("address")
        if ident in ids:
            errors.append(f"duplicate id: {ident}")
        if addr in addresses:
            errors.append(f"duplicate address: 0x{addr:08X}")
        ids.add(ident)
        addresses.add(addr)
        if entry.get("kind") not in {"code_site", "data_base"}:
            errors.append(f"{ident}: invalid kind")
        if not isinstance(addr, int) or not 0x80010000 <= addr < 0x80200000:
            errors.append(f"{ident}: invalid address")
        for field in ("owner", "lifecycle", "confidence", "mod_contract"):
            if not str(entry.get(field, "")).strip():
                errors.append(f"{ident}: missing {field}")
        if entry.get("confidence") not in {"confirmed", "partial", "inferred"}:
            errors.append(f"{ident}: invalid confidence")
        for rel in entry.get("evidence") or []:
            if not (ROOT / rel).exists():
                errors.append(f"{ident}: missing evidence {rel}")
    return errors


def main() -> int:
    argparse.ArgumentParser().parse_args()
    errors = validate(yaml.safe_load(REGISTRY.read_text()))
    for error in errors:
        print(f"ERROR: {error}")
    print(f"[confirmed_sites] {'PASS' if not errors else 'FAIL'}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
