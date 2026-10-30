#!/usr/bin/env python3
"""Round-trip the ABL symbol baseline through documented consumer formats."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

from validate_symbol_map import DEFAULT_MAP, parse_symbols


Symbol = tuple[int, str]
R2_RE = re.compile(r"^f ([A-Za-z_][A-Za-z0-9_]*) = 0x([0-9A-F]{8})$")


def write_duckstation_csv(symbols: tuple[Symbol, ...], path: Path) -> None:
    rows = ["address,name,comment"]
    rows.extend(f"0x{address:08X},{name}," for address, name in symbols)
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


def read_duckstation_csv(path: Path) -> tuple[Symbol, ...]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "address,name,comment":
        raise ValueError(f"{path}: missing DuckStation CSV header")
    symbols: list[Symbol] = []
    for line_number, line in enumerate(lines[1:], 2):
        fields = line.split(",", 2)
        if len(fields) != 3 or fields[2]:
            raise ValueError(f"{path}:{line_number}: expected address,name,<empty comment>")
        address_text, name, _comment = fields
        if not re.fullmatch(r"0x[0-9A-F]{8}", address_text):
            raise ValueError(f"{path}:{line_number}: invalid address")
        symbols.append((int(address_text, 16), name))
    return tuple(symbols)


def write_r2_script(symbols: tuple[Symbol, ...], path: Path) -> None:
    rows = [f"f {name} = 0x{address:08X}" for address, name in symbols]
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


def read_r2_script(path: Path) -> tuple[Symbol, ...]:
    symbols: list[Symbol] = []
    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        match = R2_RE.fullmatch(line)
        if not match:
            raise ValueError(f"{path}:{line_number}: invalid radare2 flag command")
        symbols.append((int(match.group(2), 16), match.group(1)))
    return tuple(symbols)


FORMATS = {
    "duckstation-csv": (write_duckstation_csv, read_duckstation_csv),
    "r2": (write_r2_script, read_r2_script),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--format", choices=FORMATS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = parse_symbols(args.input)
    writer, reader = FORMATS[args.format]
    writer(source, args.output)
    round_tripped = reader(args.output)
    if round_tripped != source:
        raise ValueError(f"{args.format} round-trip changed address/name pairs")
    print(f"OK: {len(source)} symbols round-tripped via {args.format}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
