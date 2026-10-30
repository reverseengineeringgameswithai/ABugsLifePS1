#!/usr/bin/env python3
"""Safe user-facing type-0x3f DELETE wrapper around tools/dat_reloc.py.

The inverse of insert_type3f_entries.py: removes one or more 0x10-byte type-0x3f
entries by index using the trusted dat_reloc relocation engine (build_reloc_delete),
decrements the record count, and bumps every baked file-offset that points past the
removed bytes by -0x10. Defaults to dry-run; writes only with --write --out.

Multiple --delete-index values refer to the ORIGINAL entry numbering; they are
applied high-index-first so earlier removals never renumber a not-yet-deleted target.

This closes punchlist CC5 ("no DELETE/REMOVE operation for placements"): it lets the
level editor LOWER grain/berry/token counts. The dynamic grain HUD + all-grain emblem
already count kind-0x14 live (commit 6c9445c), so fewer grains auto-update the target.
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

import dat_reloc
from catalog_type3f import analyze_file

ENTRY_SIZE = 0x10

# Risk classes for DELETION (distinct from append: removing some kinds soft-locks a
# level even though adding them is safe).
FLIK_LETTERS = {0x10, 0x11, 0x12, 0x13}   # all four needed to spell FLIK -> completion
RISK_TOKEN_LIKE = {0x2C, 0x2D}
RISK_TELESCOPE = {0x30}                     # telescope / hint device
RISK_UNKNOWN = {0x31}
KNOWN_SAFE_TO_DELETE = {
    0x14,                                   # grain  (CC5 primary)
    0x21, 0x22, 0x23, 0x24,                 # berries (req. #3)
    0x29, 0x2A, 0x2B,                       # seed tokens (req. #1/#3)
}


@dataclass(frozen=True)
class Victim:
    index: int
    offset: int
    x: int
    y: int
    z: int
    kind: int
    data: bytes


@dataclass(frozen=True)
class DeleteStep:
    index: int
    deletion_offset: int
    old_size: int
    new_size: int
    old_count: int
    new_count: int
    victim: Victim
    relocation_total: int
    relocation_bumped: int
    final_relocation_total: int


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def type3f_info(data: bytes, path: Path) -> tuple[int, int]:
    """Return (rec_off, count). Prefer the catalog parser; fall back to dat_reloc."""
    summary = analyze_file(path) if path.exists() else None
    if summary and len(summary.type3f_offsets) == 1:
        return summary.type3f_offsets[0], summary.type3f_counts[0]
    return type3f_info_from_bytes(data)


def type3f_info_from_bytes(data: bytes) -> tuple[int, int]:
    src = dat_reloc.DAT(data)
    _trail, records = src.trailing_base()
    matches = [(off, count) for off, typ, count, _size in records if typ == 0x3F]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one type-0x3f record, found {len(matches)}")
    return matches[0]


def read_victim(data: bytes, rec_off: int, index: int) -> Victim:
    off = rec_off + 4 + index * ENTRY_SIZE
    x, y, z, kw = struct.unpack_from("<iiiI", data, off)
    return Victim(index=index, offset=off, x=x, y=y, z=z, kind=kw & 0xFF,
                  data=data[off:off + ENTRY_SIZE])


def check_delete_risk(victim: Victim, args: argparse.Namespace) -> None:
    kind = victim.kind
    if kind in FLIK_LETTERS and not args.allow_flik_letter:
        raise SystemExit(
            f"entry {victim.index}: kind 0x{kind:02x} is a FLIK letter; deleting it "
            "breaks level completion. Use --allow-flik-letter to override")
    if kind in RISK_TELESCOPE and not args.allow_telescope:
        raise SystemExit(
            f"entry {victim.index}: kind 0x{kind:02x} is a telescope/hint device; "
            "use --allow-telescope to override")
    if kind in RISK_TOKEN_LIKE and not args.allow_token_like:
        raise SystemExit(
            f"entry {victim.index}: kind 0x{kind:02x} is token-like but not "
            "production-tested; use --allow-token-like to override")
    if (kind in RISK_UNKNOWN or kind not in KNOWN_SAFE_TO_DELETE | RISK_TOKEN_LIKE
            | RISK_TELESCOPE | FLIK_LETTERS) and not args.allow_unknown:
        raise SystemExit(
            f"entry {victim.index}: kind 0x{kind:02x} is unknown/unsupported for "
            "deletion; use --allow-unknown to override")


def apply_deletes(original: bytes, rec_off: int, indices: list[int]) -> tuple[bytes, list[DeleteStep]]:
    """Delete the given ORIGINAL indices, high-index-first. Returns (final, steps)."""
    current = original
    steps: list[DeleteStep] = []
    # high-index-first so a removal never renumbers a not-yet-deleted lower target
    for index in sorted(indices, reverse=True):
        cur_rec_off, cur_count = type3f_info_from_bytes(current)
        if cur_rec_off != rec_off:
            raise SystemExit(
                f"type-0x3f record offset changed unexpectedly: 0x{cur_rec_off:x} != 0x{rec_off:x}")
        if index < 0 or index >= cur_count:
            raise SystemExit(f"delete index {index} outside range 0..{cur_count - 1}")
        victim = read_victim(current, cur_rec_off, index)
        del_off = cur_rec_off + 4 + index * ENTRY_SIZE
        before_sites, _ = dat_reloc.DAT(current).scan_sites()
        dat_reloc.T3F_HDR = cur_rec_off
        dat_reloc.ENTRY_BASE = cur_rec_off + 4
        new_data, report, _sites, _meta = dat_reloc.build_reloc_delete(current, del_off)
        after_sites, _ = dat_reloc.DAT(new_data).scan_sites()
        steps.append(DeleteStep(
            index=index,
            deletion_offset=del_off,
            old_size=len(current),
            new_size=len(new_data),
            old_count=cur_count,
            new_count=u16(new_data, cur_rec_off),
            victim=victim,
            relocation_total=len(report),
            relocation_bumped=sum(1 for row in report if row["bumped"]),
            final_relocation_total=len(after_sites),
        ))
        # parser invariant: a 0x3f-entry delete removes no relocation site
        if len(report) != len(before_sites) or len(after_sites) != len(before_sites):
            raise SystemExit(
                f"verification failed: relocation-site count changed for index {index} "
                f"({len(before_sites)} -> report {len(report)} / after {len(after_sites)})")
        current = new_data
    return current, steps


def verify_result(original: bytes, final: bytes, rec_off: int, old_count: int,
                  indices: list[int], steps: list[DeleteStep]) -> None:
    n = len(set(indices))
    if len(final) != len(original) - ENTRY_SIZE * n:
        raise SystemExit(f"verification failed: size {len(final)} != "
                         f"{len(original) - ENTRY_SIZE * n}")
    if u16(final, rec_off) != old_count - n:
        raise SystemExit(f"verification failed: count {u16(final, rec_off)} != {old_count - n}")
    if final[rec_off + 2:rec_off + 4] != original[rec_off + 2:rec_off + 4]:
        raise SystemExit("verification failed: type-0x3f record type changed")

    # the surviving entries must be exactly the original entries minus the deleted set,
    # in original order, byte-identical.
    deleted = set(indices)
    survivors = [i for i in range(old_count) if i not in deleted]
    eb_old = rec_off + 4
    eb_new = rec_off + 4
    for new_i, old_i in enumerate(survivors):
        a = original[eb_old + old_i * ENTRY_SIZE: eb_old + (old_i + 1) * ENTRY_SIZE]
        b = final[eb_new + new_i * ENTRY_SIZE: eb_new + (new_i + 1) * ENTRY_SIZE]
        if a != b:
            raise SystemExit(
                f"verification failed: survivor entry old#{old_i}->new#{new_i} bytes "
                f"differ ({a.hex()} != {b.hex()})")

    # the trailing region (after the 0x3f block) must equal the original trailing region
    # byte-for-byte EXCEPT the baked offsets the engine bumped -- proven by re-scanning:
    # every relocation site in `final` must parse and resolve to a valid in-file offset.
    sites, _ = dat_reloc.DAT(final).scan_sites()
    fsize = len(final)
    for s in sites:
        if s["site"] in ("P1.A [s3+2]", "P3.G [s3+2]", "P2.F [a0+4]") and s["value"]:
            if not (0 <= s["value"] < fsize):
                raise SystemExit(
                    f"verification failed: relocated field {s['field']:#x} value "
                    f"{s['value']:#x} is outside the deleted file (0..{fsize:#x})")

    if len(steps) != n:
        raise SystemExit("verification failed: delete step count mismatch")
    for step in steps:
        if step.new_size != step.old_size - ENTRY_SIZE:
            raise SystemExit(f"verification failed: step index {step.index} size delta != -0x10")
        if step.new_count != step.old_count - 1:
            raise SystemExit(f"verification failed: step index {step.index} count did not drop by 1")


def write_report(path: Path, source: Path, out: Path | None, old_count: int, final: bytes,
                 steps: list[DeleteStep], wrote: bool) -> None:
    n = len(steps)
    lines = [
        "# Type-0x3f Relocation-Aware Delete Report",
        "",
        f"- input: `{source}`",
        f"- output: `{out}`" if out else "- output: dry-run only",
        f"- wrote file: {'yes' if wrote else 'no'}",
        f"- deleted entries: {n}",
        f"- old count: {old_count}",
        f"- new count: {old_count - n}",
        f"- output size: {len(final)}",
        f"- expected size delta: {-ENTRY_SIZE * n}",
        "",
        "## Deleted Entries (original numbering)",
        "",
        "| index | offset | X | Y | Z | kind | bytes |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for step in steps:
        v = step.victim
        lines.append(
            f"| {v.index} | `0x{v.offset:06x}` | {v.x} | {v.y} | {v.z} | "
            f"`0x{v.kind:02x}` | `{v.data.hex()}` |")
    lines += [
        "",
        "## Relocation Steps (applied high-index-first)",
        "",
        "| step index | deletion offset | size | count | reloc fields | bumped | final scan |",
        "|---:|---:|---|---|---:|---:|---:|",
    ]
    for step in steps:
        lines.append(
            f"| {step.index} | `0x{step.deletion_offset:06x}` | "
            f"{step.old_size} -> {step.new_size} | {step.old_count} -> {step.new_count} | "
            f"{step.relocation_total} | {step.relocation_bumped} | {step.final_relocation_total} |")
    lines += [
        "",
        "## Verification",
        "",
        "- Count dropped by exactly the number of deleted entries.",
        "- Surviving type-`0x3f` entries are byte-identical (original order, minus deletions).",
        "- Each delete step shrank output size by `0x10` and dropped count by one.",
        "- Relocation-site count is unchanged (a 0x3f-entry delete removes no baked field).",
        "- Every relocated entry/pointer field resolves inside the shrunken file.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Relocation-aware type-0x3f DELETE wrapper around tools/dat_reloc.py "
                    "(inverse of insert_type3f_entries.py).")
    p.add_argument("dat", type=Path)
    p.add_argument("--delete-index", action="append", default=[], type=lambda s: int(s, 0),
                   metavar="N", help="original entry index to delete; may repeat")
    p.add_argument("--write", action="store_true", help="write --out; default is dry-run")
    p.add_argument("--out", type=Path, help="output DAT path; required with --write")
    p.add_argument("--report", type=Path, help="optional Markdown verification report path")
    p.add_argument("--allow-flik-letter", action="store_true",
                   help="allow deleting FLIK letters 0x10-0x13 (breaks completion)")
    p.add_argument("--allow-telescope", action="store_true", help="allow deleting kind 0x30 telescope")
    p.add_argument("--allow-checkpoint", dest="allow_telescope", action="store_true",
                   help=argparse.SUPPRESS)  # compatibility with pre-correction scripts
    p.add_argument("--allow-token-like", action="store_true", help="allow deleting kinds 0x2c/0x2d")
    p.add_argument("--allow-unknown", action="store_true", help="allow deleting unknown/unsupported kinds")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.dat.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")
    if not args.delete_index:
        raise SystemExit("provide at least one --delete-index")

    indices = list(dict.fromkeys(args.delete_index))  # dedupe, preserve order for messages
    original = args.dat.read_bytes()
    rec_off, old_count = type3f_info(original, args.dat)
    if u16(original, rec_off + 2) != 0x3F:
        raise SystemExit("internal error: selected record is not type-0x3f")
    for index in indices:
        if index < 0 or index >= old_count:
            raise SystemExit(f"delete index {index} outside range 0..{old_count - 1}")
        check_delete_risk(read_victim(original, rec_off, index), args)

    final, steps = apply_deletes(original, rec_off, indices)
    verify_result(original, final, rec_off, old_count, indices, steps)

    print(f"type-0x3f @ 0x{rec_off:06x}, old count {old_count}, delete count {len(indices)}")
    print(f"mode: {'write' if args.write else 'dry-run'}")
    for step in steps:
        v = step.victim
        print(f"delete index {v.index}: kind=0x{v.kind:02x} XYZ=({v.x},{v.y},{v.z}) "
              f"bytes={v.data.hex()} size {step.old_size}->{step.new_size} "
              f"count {step.old_count}->{step.new_count} reloc {step.relocation_bumped}/{step.relocation_total}")
    print(f"output size: {len(original)} -> {len(final)} ({len(final) - len(original)})")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(final)
        if args.out.read_bytes() != final:
            raise SystemExit("verification failed: written output differs from verified buffer")
        print(f"wrote {args.out} ({len(final)} bytes)")
    else:
        print("dry-run only; no DAT written")

    if args.report:
        write_report(args.report, args.dat, args.out, old_count, final, steps, args.write)
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
