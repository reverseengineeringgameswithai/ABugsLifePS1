#!/usr/bin/env python3
"""Validate the import-safe DuckStation ``AAAAAAAA label`` symbol baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "symbols" / "re_symbols.sym"
LINE_RE = re.compile(r"^([0-9A-F]{8}) ([A-Za-z_][A-Za-z0-9_]*)$")


def parse_symbols(path: Path) -> tuple[tuple[int, str], ...]:
    addresses: set[int] = set()
    labels: set[str] = set()
    previous = -1
    symbols: list[tuple[int, str]] = []

    for line_number, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        match = LINE_RE.fullmatch(raw)
        if not match:
            raise ValueError(f"{path}:{line_number}: expected 'AAAAAAAA label'")
        address = int(match.group(1), 16)
        label = match.group(2)
        if address in addresses:
            raise ValueError(f"{path}:{line_number}: duplicate address {address:08X}")
        if label in labels:
            raise ValueError(f"{path}:{line_number}: duplicate label {label}")
        if address <= previous:
            raise ValueError(f"{path}:{line_number}: addresses are not strictly increasing")
        addresses.add(address)
        labels.add(label)
        previous = address
        symbols.append((address, label))

    if not symbols:
        raise ValueError(f"{path}: symbol map is empty")
    return tuple(symbols)


def validate(path: Path) -> int:
    return len(parse_symbols(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_MAP)
    args = parser.parse_args()
    count = validate(args.path)
    print(f"OK: {count} unique, sorted symbols in {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
