#!/usr/bin/env python3
"""Declarative type-0x3f placement spec runner.

Phase: Option C Phase 4. This tool composes fixed-size moves and relocation-aware
appends in memory. It writes a DAT only when both --write and --out are provided.
It does not build ISOs or stage rebuild files.
"""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import catalog_type3f
import insert_type3f_entries
import move_type3f_entry


ENTRY_SIZE = 0x10


@dataclass(frozen=True)
class OperationResult:
    ordinal: int
    op: str
    summary: str
    old_size: int
    new_size: int
    old_count: int
    new_count: int


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    try:
        return int(value, 0)
    except ValueError:
        return value


def parse_spec(path: Path) -> dict[str, Any]:
    text = path.read_text()
    stripped = text.lstrip()
    if stripped.startswith("{"):
        spec = json.loads(text)
        if not isinstance(spec, dict):
            raise SystemExit("spec JSON must be an object")
        return spec

    spec: dict[str, Any] = {}
    operations: list[dict[str, Any]] = []
    current_op: dict[str, Any] | None = None
    in_operations = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped_line = line.strip()
        if stripped_line == "operations:":
            in_operations = True
            spec["operations"] = operations
            continue
        if in_operations:
            if stripped_line.startswith("- "):
                current_op = {}
                operations.append(current_op)
                rest = stripped_line[2:].strip()
                if rest:
                    if ":" not in rest:
                        raise SystemExit(f"invalid operation line: {raw_line}")
                    key, value = rest.split(":", 1)
                    current_op[key.strip()] = parse_scalar(value)
                continue
            if current_op is None:
                raise SystemExit(f"operation property before list item: {raw_line}")
            if ":" not in stripped_line:
                raise SystemExit(f"invalid operation property: {raw_line}")
            key, value = stripped_line.split(":", 1)
            current_op[key.strip()] = parse_scalar(value)
            continue

        if ":" not in stripped_line:
            raise SystemExit(f"invalid top-level spec line: {raw_line}")
        key, value = stripped_line.split(":", 1)
        spec[key.strip()] = parse_scalar(value)

    if "operations" not in spec:
        spec["operations"] = operations
    return spec


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def s32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def type3f_rows_from_bytes(data: bytes, source_path: Path) -> tuple[int, int, list[catalog_type3f.Type3FRow]]:
    matches: list[tuple[int, int]] = []
    for _ordinal, off, count, rec_type, _size in catalog_type3f.iter_dat_records(data):
        if rec_type == catalog_type3f.TYPE3F:
            matches.append((off, count))
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one type-0x3f record, found {len(matches)}")

    rec_off, count = matches[0]
    rows: list[catalog_type3f.Type3FRow] = []
    for index in range(count):
        entry_off = rec_off + 4 + index * ENTRY_SIZE
        x = s32(data, entry_off)
        y = s32(data, entry_off + 4)
        z = s32(data, entry_off + 8)
        kind = data[entry_off + 0x0C]
        identity, movement, warnings, notes = catalog_type3f.decode_entry(source_path, index, kind)
        rows.append(
            catalog_type3f.Type3FRow(
                file=str(source_path),
                top_level_dat_record_offset=rec_off,
                raw_entry_index=index,
                entry_offset=entry_off,
                x=x,
                y=y,
                z=z,
                source_kind=kind,
                decoded_identity=identity,
                movement_safe_status=movement,
                known_warnings="; ".join(warnings),
                runtime_x=x << 5,
                runtime_y=y << 5,
                runtime_z=z << 5,
                notes=notes,
            )
        )
    return rec_off, count, rows


def bool_from_op(op: dict[str, Any], args: argparse.Namespace, name: str) -> bool:
    return bool(op.get(name, getattr(args, name)))


def risk_args_for_op(op: dict[str, Any], args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        allow_telescope=bool(op.get("allow_telescope",
                                    op.get("allow_checkpoint", args.allow_telescope))),
        allow_token_like=bool_from_op(op, args, "allow_token_like"),
        allow_unknown=bool_from_op(op, args, "allow_unknown"),
    )


def int_field(op: dict[str, Any], name: str, default: int | None = None) -> int:
    if name not in op:
        if default is None:
            raise SystemExit(f"operation missing required field: {name}")
        return default
    value = op[name]
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise SystemExit(f"operation field {name} must be an integer")


def apply_move(data: bytes, source_path: Path, op: dict[str, Any], args: argparse.Namespace) -> tuple[bytes, str]:
    rec_off, count, rows = type3f_rows_from_bytes(data, source_path)
    entries_value = op.get("entries", op.get("entry"))
    if entries_value is None and "identity" not in op:
        raise SystemExit("move operation requires entry/entries or identity")
    if isinstance(entries_value, list):
        entry_args = [str(value) for value in entries_value]
    elif entries_value is None:
        entry_args = []
    else:
        entry_args = [str(entries_value)]
    selected = move_type3f_entry.select_rows(rows, move_type3f_entry.parse_index_list(entry_args), op.get("identity"))
    if not selected:
        raise SystemExit("move operation selected no entries")
    risk_args = risk_args_for_op(op, args)
    for row in selected:
        move_type3f_entry.check_risk(row, risk_args)

    dx = int_field(op, "dx", 0)
    dy = int_field(op, "dy", 0)
    dz = int_field(op, "dz", 0)
    if dx == 0 and dy == 0 and dz == 0:
        raise SystemExit("move operation refuses zero dx/dy/dz")

    patched, moves = move_type3f_entry.build_moves(data, selected, dx, dy, dz)
    changed_axis_offsets = {
        axis_off
        for delta, (_axis, axis_off) in zip((dx, dy, dz), move_type3f_entry.AXES)
        if delta != 0
    }
    move_type3f_entry.verify_patch(data, patched, moves, changed_axis_offsets)
    if len(patched) != len(data):
        raise SystemExit("move operation changed file size")
    if u16(patched, rec_off) != count:
        raise SystemExit("move operation changed type-0x3f count")

    summary = ", ".join(f"{move.row.raw_entry_index}:{move.old_xyz}->{move.new_xyz}" for move in moves)
    return patched, summary


def apply_set_entry(data: bytes, source_path: Path, op: dict[str, Any], args: argparse.Namespace) -> tuple[bytes, str]:
    """Edit an EXISTING type-0x3f entry in place (kind and/or absolute X/Y/Z). No append,
    so the loader still initialises the record's runtime fields -> no corruption."""
    rec_off, count, rows = type3f_rows_from_bytes(data, source_path)
    idx = int_field(op, "entry")
    row = next((r for r in rows if r.raw_entry_index == idx), None)
    if row is None:
        raise SystemExit(f"set_entry: no entry index {idx}")
    eo = row.entry_offset
    x, y, z, kw = struct.unpack_from("<iiiI", data, eo)
    if "x" in op: x = int_field(op, "x")
    if "y" in op: y = int_field(op, "y")
    if "z" in op: z = int_field(op, "z")
    if "kind" in op: kw = (kw & ~0xFF) | (int_field(op, "kind") & 0xFF)
    patched = bytearray(data)
    struct.pack_into("<iiiI", patched, eo, x, y, z, kw)
    if len(patched) != len(data) or u16(bytes(patched), rec_off) != count:
        raise SystemExit("set_entry changed size/count (should not happen)")
    return bytes(patched), f"entry {idx} @ {eo:#x} -> kind=0x{kw & 0xFF:02x} XYZ=({x},{y},{z})"


def append_entry_for_op(data: bytes, rec_off: int, count: int, op: dict[str, Any]) -> insert_type3f_entries.NewEntry:
    op_name = op.get("op")
    if op_name == "append_clone":
        clone_entry = int_field(op, "clone_entry", int_field(op, "entry") if "entry" in op else None)
        spec = f"{clone_entry}:{int_field(op, 'dx', 0)}:{int_field(op, 'dy', 0)}:{int_field(op, 'dz', 0)}"
        return insert_type3f_entries.parse_append_clone(spec, data, rec_off, count)
    if op_name == "append_new":
        for field in ("kind", "x", "y", "z"):
            if field not in op:
                raise SystemExit(f"append_new operation missing {field}")
        spec = (
            f"{op['kind']}:{op['x']}:{op['y']}:{op['z']}:"
            f"{op.get('unk0d', 0)}:{op.get('unk0e', 0)}:{op.get('unk0f', 0)}"
        )
        return insert_type3f_entries.parse_append_new(spec)
    if op_name == "entry_bytes":
        value = op.get("entry_bytes", op.get("bytes", op.get("hex")))
        if value is None:
            raise SystemExit("entry_bytes operation requires entry_bytes, bytes, or hex")
        return insert_type3f_entries.parse_entry_hex(str(value))
    raise SystemExit(f"unsupported append operation: {op_name}")


def apply_append(data: bytes, source_path: Path, op: dict[str, Any], args: argparse.Namespace) -> tuple[bytes, str]:
    rec_off, count, _insert_off = insert_type3f_entries.type3f_info_from_bytes(data)
    entry = append_entry_for_op(data, rec_off, count, op)
    insert_type3f_entries.check_entry_risk(entry, risk_args_for_op(op, args))
    final, steps, _reloc_report = insert_type3f_entries.apply_appends(data, rec_off, [entry])
    insert_type3f_entries.verify_result(data, final, rec_off, count, [entry], steps)
    step = steps[0]
    summary = (
        f"new index {count} kind=0x{entry.kind:02x} XYZ=({entry.x},{entry.y},{entry.z}) "
        f"bytes={entry.data.hex()} reloc={step.relocation_total}/{step.relocation_bumped}"
    )
    return final, summary


def write_report(path: Path, spec_path: Path, source_dat: Path, out: Path | None, wrote: bool, results: list[OperationResult], final_size: int) -> None:
    lines = [
        "# Type-0x3f Placement Spec Report",
        "",
        f"- spec: `{spec_path}`",
        f"- source DAT: `{source_dat}`",
        f"- output: `{out}`" if out else "- output: dry-run only",
        f"- wrote file: {'yes' if wrote else 'no'}",
        f"- operations: {len(results)}",
        f"- final size: {final_size}",
        "",
        "| op # | op | size | count | summary |",
        "|---:|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result.ordinal} | `{result.op}` | {result.old_size} -> {result.new_size} | "
            f"{result.old_count} -> {result.new_count} | {result.summary} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a declarative type-0x3f placement spec.")
    parser.add_argument("spec", type=Path, help="YAML-like or JSON placement spec")
    parser.add_argument("--source-dat", type=Path, help="override source_dat in spec")
    parser.add_argument("--write", action="store_true", help="write --out; default is dry-run")
    parser.add_argument("--out", type=Path, help="output DAT path; required with --write")
    parser.add_argument("--report", type=Path, help="optional Markdown placement report path")
    parser.add_argument("--allow-telescope", action="store_true", help="allow move/append kind 0x30 telescope")
    parser.add_argument("--allow-checkpoint", dest="allow_telescope", action="store_true",
                        help=argparse.SUPPRESS)  # compatibility with pre-correction scripts
    parser.add_argument("--allow-token-like", action="store_true", help="allow move/append kinds 0x2c/0x2d")
    parser.add_argument("--allow-unknown", action="store_true", help="allow move/append unknown/unsupported kinds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")

    spec = parse_spec(args.spec)
    source_dat_value = args.source_dat or spec.get("source_dat")
    if source_dat_value is None or str(source_dat_value).strip() == "":
        raise SystemExit("spec must provide source_dat or use --source-dat")
    source_dat = Path(str(source_dat_value))
    if not source_dat.exists():
        raise SystemExit(f"source DAT not found: {source_dat}")
    if args.out is not None and args.out.resolve() == source_dat.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    operations = spec.get("operations")
    if not isinstance(operations, list) or not operations:
        raise SystemExit("spec must contain a non-empty operations list")

    data = source_dat.read_bytes()
    results: list[OperationResult] = []

    print(f"source DAT: {source_dat}")
    print(f"mode: {'write' if args.write else 'dry-run'}")
    for ordinal, op in enumerate(operations):
        if not isinstance(op, dict):
            raise SystemExit(f"operation {ordinal} must be an object")
        op_name = str(op.get("op", ""))
        if not op_name:
            raise SystemExit(f"operation {ordinal} missing op")
        old_size = len(data)
        _old_rec_off, old_count, _old_rows = type3f_rows_from_bytes(data, source_dat)

        if op_name == "move":
            data, summary = apply_move(data, source_dat, op, args)
        elif op_name == "set_entry":
            data, summary = apply_set_entry(data, source_dat, op, args)
        elif op_name in {"append_clone", "append_new", "entry_bytes"}:
            data, summary = apply_append(data, source_dat, op, args)
        else:
            raise SystemExit(f"operation {ordinal} has unsupported op {op_name!r}")

        _new_rec_off, new_count, _new_rows = type3f_rows_from_bytes(data, source_dat)
        result = OperationResult(
            ordinal=ordinal,
            op=op_name,
            summary=summary,
            old_size=old_size,
            new_size=len(data),
            old_count=old_count,
            new_count=new_count,
        )
        results.append(result)
        print(
            f"op {ordinal} {op_name}: size {result.old_size}->{result.new_size}, "
            f"count {result.old_count}->{result.new_count}, {summary}"
        )

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(data)
        if args.out.read_bytes() != data:
            raise SystemExit("verification failed: written output differs from verified buffer")
        print(f"wrote {args.out} ({len(data)} bytes)")
    else:
        print("dry-run only; no DAT written")

    if args.report:
        write_report(args.report, args.spec, source_dat, args.out, args.write, results, len(data))
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
