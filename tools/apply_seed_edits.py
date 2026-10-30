#!/usr/bin/env python3
"""Declarative LEVEL.RAW chunk-31 seed-placement spec runner.

Mirrors ``apply_level_placements.py`` (type-0x3f pickups) for the seed table,
but uses a DEDICATED schema — per the level-editor roadmap design rule "define
dedicated edit-plan schemas for terrain/collision; do not overload pickup YAML."
It reads a YAML-like or JSON spec of seed moves, decompresses chunk 31, applies
the moves to the typed records (``seed_table``), recompresses ONLY chunk 31 via
the proven codec, splices it back, and writes a new LEVEL.RAW. Dry-run by
default; ``--write --out`` writes the patched image.

Disc rebuild reuses the existing, generic tool::

    python3 tools/apply_seed_edits.py seeds.yaml --write --out /tmp/LEVEL_seeds.RAW
    python3 tools/rebuild_with_patched_dat.py \
        --target files/LEVEL01/LEVEL.RAW \
        --patched-dat /tmp/LEVEL_seeds.RAW \
        --out-bin /tmp/ABL_SEEDS.bin --out-cue /tmp/ABL_SEEDS.cue --write

Spec schema (YAML-like; JSON also accepted)::

    source_raw: REBUILD/files/LEVEL01/LEVEL.RAW
    chunk: 31            # optional; defaults to the seed chunk (31)
    operations:
      - op: move         # translate a seed by a delta (file coordinates)
        seed: 26
        dx: -3184
        dy: 0
        dz: 0
      - op: set          # set a seed to absolute file coordinates
        seed: 19
        x: 1000
        y: -2325
        z: 2813

The LEVEL.RAW it edits is owner-supplied local media; this runner ships no disc
bytes. ``seed_table`` (the schema + codec wrapper) is covered by synthetic tests.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import seed_table
from apply_level_placements import parse_spec   # reuse the pickup spec parser


# Refuse coordinates outside this half-open file-coordinate band. The proven
# LEVEL01 seeds sit within +/-32k file units; this is a soft guard against a
# typo writing a seed into the unstreamed "void" (which can crash the guest).
COORD_LIMIT = 1 << 20


@dataclass(frozen=True)
class SeedEdit:
    ordinal: int
    op: str
    seed: int
    old_xyz: tuple[int, int, int]
    new_xyz: tuple[int, int, int]


def _int(op: dict[str, Any], name: str, default: int | None = None) -> int:
    if name not in op:
        if default is None:
            raise SystemExit(f"seed operation missing required field: {name}")
        return default
    value = op[name]
    if isinstance(value, bool):  # guard: YAML 'true' is not a coordinate
        raise SystemExit(f"seed operation field {name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise SystemExit(f"seed operation field {name} must be an integer")


def _check_coords(seed: int, xyz: tuple[int, int, int]) -> None:
    for axis, value in zip("xyz", xyz):
        if not (-COORD_LIMIT <= value < COORD_LIMIT):
            raise SystemExit(
                f"seed #{seed} {axis}={value} outside the +/-0x{COORD_LIMIT:x} file-coordinate guard"
            )


def apply_operations(
    records: list[seed_table.SeedRecord], operations: list[dict[str, Any]]
) -> tuple[list[seed_table.SeedRecord], list[SeedEdit]]:
    edits: list[SeedEdit] = []
    by_index = {r.index: r for r in records}
    for ordinal, op in enumerate(operations):
        if not isinstance(op, dict):
            raise SystemExit(f"operation {ordinal} must be an object")
        op_name = str(op.get("op", ""))
        seed = _int(op, "seed")
        if seed not in by_index:
            raise SystemExit(f"operation {ordinal}: no seed #{seed} (have 0..{len(records) - 1})")
        old = by_index[seed]
        old_xyz = (old.x, old.y, old.z)

        if op_name == "move":
            dx, dy, dz = _int(op, "dx", 0), _int(op, "dy", 0), _int(op, "dz", 0)
            if dx == 0 and dy == 0 and dz == 0:
                raise SystemExit(f"operation {ordinal}: move refuses zero dx/dy/dz")
            records = seed_table.move_record(records, seed, dx, dy, dz)
        elif op_name == "set":
            x, y, z = _int(op, "x"), _int(op, "y"), _int(op, "z")
            records = seed_table.set_record(records, seed, x, y, z)
        else:
            raise SystemExit(f"operation {ordinal}: unsupported seed op {op_name!r} (move|set)")

        by_index = {r.index: r for r in records}
        new = by_index[seed]
        new_xyz = (new.x, new.y, new.z)
        if new_xyz == old_xyz:
            raise SystemExit(f"operation {ordinal}: seed #{seed} unchanged")
        _check_coords(seed, new_xyz)
        edits.append(SeedEdit(ordinal, op_name, seed, old_xyz, new_xyz))
    return records, edits


def write_report(path: Path, spec_path: Path, source_raw: Path, out: Path | None,
                 wrote: bool, edits: list[SeedEdit]) -> None:
    lines = [
        "# Chunk-31 Seed Placement Spec Report",
        "",
        f"- spec: `{spec_path}`",
        f"- source LEVEL.RAW: `{source_raw}`",
        f"- output: `{out}`" if out else "- output: dry-run only",
        f"- wrote file: {'yes' if wrote else 'no'}",
        f"- operations: {len(edits)}",
        "",
        "| op # | op | seed | old XYZ (file) | new XYZ (file) | runtime delta |",
        "|---:|---|---:|---|---|---|",
    ]
    for e in edits:
        d = tuple((n - o) << seed_table.RUNTIME_SHIFT for o, n in zip(e.old_xyz, e.new_xyz))
        lines.append(f"| {e.ordinal} | `{e.op}` | {e.seed} | {e.old_xyz} | {e.new_xyz} | {d} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a declarative chunk-31 seed placement spec.")
    parser.add_argument("spec", type=Path, help="YAML-like or JSON seed spec")
    parser.add_argument("--source-raw", type=Path, help="override source_raw in spec")
    parser.add_argument("--chunk", type=int, default=None, help="override seed chunk index (default 31)")
    parser.add_argument("--write", action="store_true", help="write --out; default is dry-run")
    parser.add_argument("--out", type=Path, help="output LEVEL.RAW path; required with --write")
    parser.add_argument("--report", type=Path, help="optional Markdown report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")

    spec = parse_spec(args.spec)
    source_value = args.source_raw or spec.get("source_raw")
    if source_value is None or str(source_value).strip() == "":
        raise SystemExit("spec must provide source_raw or use --source-raw")
    source_raw = Path(str(source_value))
    if not source_raw.exists():
        raise SystemExit(f"source LEVEL.RAW not found: {source_raw}")
    if args.out is not None and args.out.resolve() == source_raw.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    chunk_index = args.chunk if args.chunk is not None else int(spec.get("chunk", seed_table.SEED_CHUNK_INDEX))
    operations = spec.get("operations")
    if not isinstance(operations, list) or not operations:
        raise SystemExit("spec must contain a non-empty operations list")

    raw = source_raw.read_bytes()
    span, records = seed_table.read_seed_chunk(raw, chunk_index)
    print(f"source LEVEL.RAW: {source_raw}")
    print(f"chunk {chunk_index}: {len(records)} seed slots ({seed_table.active_count(records)} active), "
          f"comp_off=0x{span.comp_off:x} word0={span.word0}")
    print(f"mode: {'write' if args.write else 'dry-run'}")

    new_records, edits = apply_operations(records, operations)
    for e in edits:
        print(f"op {e.ordinal} {e.op}: seed #{e.seed} {e.old_xyz} -> {e.new_xyz} (file coords)")

    # Re-serialize + splice the edited chunk; verify the patched image re-parses.
    _, decompressed = seed_table.read_chunk_decompressed(raw, chunk_index)
    new_decompressed = seed_table.serialize_seed_table(decompressed, new_records)
    patched = seed_table.splice_chunk(raw, chunk_index, new_decompressed)
    _, reparsed = seed_table.read_seed_chunk(patched, chunk_index)
    for e in edits:
        got = reparsed[e.seed]
        if (got.x, got.y, got.z) != e.new_xyz:
            raise SystemExit(f"verification failed: seed #{e.seed} reparsed as "
                             f"{(got.x, got.y, got.z)} != {e.new_xyz}")
    delta = len(patched) - len(raw)
    print(f"patched LEVEL.RAW: {len(raw)} -> {len(patched)} bytes ({delta:+d}); chunk-31 re-parse OK")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(patched)
        if args.out.read_bytes() != patched:
            raise SystemExit("verification failed: written output differs from verified buffer")
        print(f"wrote {args.out} ({len(patched)} bytes)")
    else:
        print("dry-run only; no LEVEL.RAW written")

    if args.report:
        write_report(args.report, args.spec, source_raw, args.out, args.write, edits)
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
