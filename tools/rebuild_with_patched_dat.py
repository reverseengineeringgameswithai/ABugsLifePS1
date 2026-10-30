#!/usr/bin/env python3
"""Stage a patched DAT, rebuild with mkpsxiso, verify embedded bytes, restore.

Phase: Option C Phase 5. This tool does not patch DAT contents. It stages an
already-built DAT into REBUILD/files, runs mkpsxiso only with --write, verifies
that the rebuilt image embeds the exact patched bytes, and restores the staged
workspace file before exiting.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


SECTOR_SIZE = 2352
USER_DATA_OFFSET = 24
USER_DATA_SIZE = 2048
DEFAULT_XML = Path("REBUILD/abl.xml")
DEFAULT_REBUILD_ROOT = Path("REBUILD")
DEFAULT_MKPSXISO = Path("/usr/local/bin/mkpsxiso")


@dataclass(frozen=True)
class TargetFile:
    source_attr: str
    stage_path: Path
    lba: int


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_source(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def find_target(xml_path: Path, rebuild_root: Path, target: str) -> TargetFile:
    xml_root = ElementTree.parse(xml_path).getroot()
    target_norm = normalize_source(target)
    matches: list[TargetFile] = []
    for elem in xml_root.iter("file"):
        source = elem.get("source")
        offs = elem.get("offs")
        if not source or offs is None:
            continue
        source_norm = normalize_source(source)
        if source_norm == target_norm or source_norm == f"files/{target_norm}":
            matches.append(
                TargetFile(
                    source_attr=source,
                    stage_path=rebuild_root / source_norm,
                    lba=int(offs, 0),
                )
            )
    if not matches:
        raise SystemExit(f"target source not found in {xml_path}: {target}")
    if len(matches) != 1:
        raise SystemExit(f"target source matched multiple files in {xml_path}: {target}")
    return matches[0]


def extract_mode2_user_data(bin_path: Path, lba: int, size: int) -> bytes:
    pieces: list[bytes] = []
    remaining = size
    sector = lba
    with bin_path.open("rb") as f:
        while remaining > 0:
            f.seek(sector * SECTOR_SIZE + USER_DATA_OFFSET)
            chunk = f.read(USER_DATA_SIZE)
            if len(chunk) != USER_DATA_SIZE:
                raise SystemExit(f"short read extracting sector {sector} from {bin_path}")
            take = min(remaining, USER_DATA_SIZE)
            pieces.append(chunk[:take])
            remaining -= take
            sector += 1
    return b"".join(pieces)


def write_report(
    path: Path,
    patched_dat: Path,
    target: TargetFile,
    out_bin: Path,
    out_cue: Path,
    patched_size: int,
    patched_sha1: str,
    embedded_sha1: str | None,
    staged_restored: bool,
    wrote: bool,
) -> None:
    lines = [
        "# Rebuild With Patched DAT Report",
        "",
        f"- patched DAT: `{patched_dat}`",
        f"- staged target: `{target.stage_path}`",
        f"- XML source: `{target.source_attr}`",
        f"- LBA: {target.lba}",
        f"- output BIN: `{out_bin}`",
        f"- output CUE: `{out_cue}`",
        f"- wrote rebuild outputs: {'yes' if wrote else 'no'}",
        f"- patched size: {patched_size}",
        f"- patched sha1: `{patched_sha1}`",
        f"- embedded sha1: `{embedded_sha1}`" if embedded_sha1 else "- embedded sha1: dry-run only",
        f"- staged file restored: {'yes' if staged_restored else 'no'}"
        if wrote
        else "- staged file restored: not staged (dry-run)",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage one patched DAT into REBUILD/files, rebuild, verify embedded bytes, then restore."
    )
    parser.add_argument("--patched-dat", type=Path, required=True, help="already patched DAT to stage")
    parser.add_argument(
        "--target",
        default="files/LEVEL01/LEVEL.DAT",
        help="REBUILD/abl.xml source target to replace temporarily",
    )
    parser.add_argument("--xml", type=Path, default=DEFAULT_XML, help="mkpsxiso XML manifest")
    parser.add_argument("--rebuild-root", type=Path, default=DEFAULT_REBUILD_ROOT)
    parser.add_argument("--mkpsxiso", type=Path, default=DEFAULT_MKPSXISO)
    parser.add_argument("--out-bin", type=Path, required=True, help="rebuilt BIN output path")
    parser.add_argument("--out-cue", type=Path, required=True, help="rebuilt CUE output path")
    parser.add_argument("--expected-sha1", help="optional expected sha1 for --patched-dat")
    parser.add_argument("--write", action="store_true", help="stage, rebuild, and verify; default is dry-run")
    parser.add_argument("--force-output", action="store_true", help="allow overwriting output BIN/CUE")
    parser.add_argument("--report", type=Path, help="optional Markdown report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.patched_dat.exists():
        raise SystemExit(f"patched DAT not found: {args.patched_dat}")
    if not args.xml.exists():
        raise SystemExit(f"XML manifest not found: {args.xml}")
    if not args.mkpsxiso.exists():
        raise SystemExit(f"mkpsxiso not found: {args.mkpsxiso}")
    if args.out_bin.resolve() == args.patched_dat.resolve() or args.out_cue.resolve() == args.patched_dat.resolve():
        raise SystemExit("output image paths must differ from --patched-dat")
    if args.write and not args.force_output:
        for out in (args.out_bin, args.out_cue):
            if out.exists():
                raise SystemExit(f"refusing to overwrite existing output without --force-output: {out}")

    target = find_target(args.xml, args.rebuild_root, args.target)
    if not target.stage_path.exists():
        raise SystemExit(f"staged target does not exist: {target.stage_path}")

    patched = args.patched_dat.read_bytes()
    patched_sha1 = sha1_bytes(patched)
    if args.expected_sha1 and patched_sha1.lower() != args.expected_sha1.lower():
        raise SystemExit(
            f"patched DAT sha1 {patched_sha1} does not match expected {args.expected_sha1.lower()}"
        )

    original_stage = target.stage_path.read_bytes()
    original_stage_sha1 = sha1_bytes(original_stage)
    print(f"patched DAT: {args.patched_dat} size={len(patched)} sha1={patched_sha1}")
    print(f"stage target: {target.stage_path} lba={target.lba} current_sha1={original_stage_sha1}")
    print(f"mode: {'write' if args.write else 'dry-run'}")

    embedded_sha1: str | None = None
    restored = False
    wrote = False
    try:
        if args.write:
            args.out_bin.parent.mkdir(parents=True, exist_ok=True)
            args.out_cue.parent.mkdir(parents=True, exist_ok=True)
            target.stage_path.write_bytes(patched)
            if target.stage_path.read_bytes() != patched:
                raise SystemExit("verification failed: staged file differs from patched DAT")

            cmd = [
                str(args.mkpsxiso),
                "-y",
                "-o",
                str(args.out_bin),
                "-c",
                str(args.out_cue),
                str(args.xml),
            ]
            proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            print(proc.stdout, end="")
            if proc.returncode != 0:
                raise SystemExit(f"mkpsxiso exited {proc.returncode}")
            wrote = True
            if not args.out_bin.exists() or not args.out_cue.exists():
                raise SystemExit("mkpsxiso did not produce both BIN and CUE outputs")

            embedded = extract_mode2_user_data(args.out_bin, target.lba, len(patched))
            embedded_sha1 = sha1_bytes(embedded)
            if embedded != patched:
                raise SystemExit(
                    f"verification failed: embedded bytes sha1 {embedded_sha1} != patched {patched_sha1}"
                )
            print(f"embedded verification passed: lba={target.lba} size={len(patched)} sha1={embedded_sha1}")
        else:
            print("dry-run only; no staging, rebuild, or output files written")
    finally:
        if args.write:
            target.stage_path.write_bytes(original_stage)
            restored = target.stage_path.read_bytes() == original_stage
            if not restored:
                raise SystemExit(f"restore failed: {target.stage_path} differs from original staged bytes")
            print(f"restored staged target: {target.stage_path} sha1={sha1_file(target.stage_path)}")

    if args.report:
        write_report(
            args.report,
            args.patched_dat,
            target,
            args.out_bin,
            args.out_cue,
            len(patched),
            patched_sha1,
            embedded_sha1,
            restored if args.write else False,
            wrote,
        )
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
