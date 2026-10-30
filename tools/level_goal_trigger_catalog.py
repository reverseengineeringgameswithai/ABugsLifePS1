#!/usr/bin/env python3
"""Catalog runtime collision-sector trigger codes from DuckStation save states.

RCG-003 asks for campaign-wide level goal/exit evidence.  LEVEL01 already proved
the mechanism: player update calls FUNC_80038f38, which reads the current
collision sector's region code from runtime table 0x800A7E48+sector*0x30+0x2e.

This tool extracts DuckStation v84 zstd save-state RAM blocks without launching
the emulator, scans the bounded runtime sector table, and reports only plausible
trigger sectors (codes 1..4 with sane origins and collision plane pointers).
It writes metadata only: save names, scene ids, sector ids, codes, origins, and
hashes.  It does not persist RAM or save-state payload bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


HEADER_FMT = "<II128s32s" + "I" * 12
HEADER_SIZE = struct.calcsize(HEADER_FMT)
SAVE_MAGIC = 0x43435544
SAVE_VERSION = 84
COMPRESSION_ZSTD = 2

SECTOR_TABLE = 0x800A7E48
SECTOR_STRIDE = 0x30
SECTOR_REGION_CODE = 0x2E
SECTOR_PLANE_PTR = 0x10
CURRENT_SECTOR = 0x80090560
SCENE_ID = 0x80082504
FLIK_BASE = 0x800A6500
FLIK_GATE = 0x800A6582
TRANSITION_LEVER = 0x800823A0

MAX_SCAN_SECTORS = 700
TRIGGER_CODES = {1, 2, 3, 4}

STAGE_MAP = {
    1: ("LEVEL01", "LEVEL1A"),
    2: ("LEVEL03", "LEVEL1B"),
    3: ("LEVEL02", "LEVEL1C"),
    4: ("LEVEL06", "LEVEL2A"),
    5: ("LEVEL10", "LEVEL2B"),
    6: ("LEVEL01", "LEVEL2C"),
    7: ("LEVEL04", "LEVEL3A"),
    8: ("LEVEL05", "LEVEL3B"),
    9: ("LEVEL04", "LEVEL3C"),
    10: ("LEVEL07", "LEVEL4A"),
    11: ("LEVEL02", "LEVEL4B"),
    12: ("LEVEL03", "LEVEL4C"),
    13: ("LEVEL09", "LEVEL5A"),
    14: ("LEVEL08", "LEVEL5B"),
    15: ("LEVEL05", "LEVEL5C"),
}


@dataclass
class TriggerRow:
    sector: int
    code: int
    origin_x: int
    origin_y: int
    origin_z: int
    plane_ptr: str


@dataclass
class SaveRow:
    save: str
    sha256_16: str
    serial: str
    scene_id: int
    stage_dir: str
    overlay_stem: str
    flik_x: int
    flik_y: int
    flik_z: int
    flik_gate: int
    current_sector: int
    current_sector_code: int | None
    transition_lever: int
    triggers: list[TriggerRow]


def u16(buf: bytes, addr: int) -> int:
    return struct.unpack_from("<H", buf, addr & 0x1FFFFF)[0]


def u32(buf: bytes, addr: int) -> int:
    return struct.unpack_from("<I", buf, addr & 0x1FFFFF)[0]


def s32(buf: bytes, addr: int) -> int:
    return struct.unpack_from("<i", buf, addr & 0x1FFFFF)[0]


def parse_header(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < HEADER_SIZE:
        raise ValueError(f"{path}: too small for DuckStation save-state header")
    fields = struct.unpack_from(HEADER_FMT, data, 0)
    (
        magic,
        version,
        title,
        serial,
        media_path_length,
        offset_to_media_path,
        media_subimage_index,
        screenshot_compression_type,
        screenshot_width,
        screenshot_height,
        screenshot_compressed_size,
        offset_to_screenshot,
        data_compression_type,
        data_compressed_size,
        data_uncompressed_size,
        offset_to_data,
    ) = fields
    if magic != SAVE_MAGIC:
        raise ValueError(f"{path}: not a DuckStation save state")
    return {
        "data": data,
        "version": version,
        "title": title.split(b"\0", 1)[0].decode("ascii", "replace"),
        "serial": serial.split(b"\0", 1)[0].decode("ascii", "replace"),
        "media_path_length": media_path_length,
        "offset_to_media_path": offset_to_media_path,
        "media_subimage_index": media_subimage_index,
        "screenshot_compression_type": screenshot_compression_type,
        "screenshot_width": screenshot_width,
        "screenshot_height": screenshot_height,
        "screenshot_compressed_size": screenshot_compressed_size,
        "offset_to_screenshot": offset_to_screenshot,
        "data_compression_type": data_compression_type,
        "data_compressed_size": data_compressed_size,
        "data_uncompressed_size": data_uncompressed_size,
        "offset_to_data": offset_to_data,
    }


def zstd_decompress(block: bytes) -> bytes:
    zstd = shutil.which("zstd")
    if zstd is None:
        raise RuntimeError("zstd CLI not found; install zstd or load the save through DuckStation RPC")
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(block)
        tmp.flush()
        return subprocess.check_output([zstd, "-dc", tmp.name])


def extract_main_ram(path: Path) -> tuple[dict, bytes]:
    header = parse_header(path)
    if header["version"] != SAVE_VERSION:
        raise ValueError(f"{path}: expected save-state version {SAVE_VERSION}, got {header['version']}")
    if header["data_compression_type"] != COMPRESSION_ZSTD:
        raise ValueError(f"{path}: unsupported state compression {header['data_compression_type']}")
    off = header["offset_to_data"]
    size = header["data_compressed_size"]
    state = zstd_decompress(header["data"][off:off + size])
    if len(state) != header["data_uncompressed_size"]:
        raise ValueError(f"{path}: decompressed length mismatch")

    marker = state.find(b"Bus")
    if marker < 4 or struct.unpack_from("<I", state, marker - 4)[0] != 3:
        raise ValueError(f"{path}: cannot locate StateWrapper Bus marker")
    bus_fields = marker + 3
    ram_size = struct.unpack_from("<I", state, bus_fields)[0]
    if ram_size not in (0x200000, 0x800000):
        raise ValueError(f"{path}: unexpected main RAM size 0x{ram_size:x}")
    ram_start = bus_fields + 4 + 5 * 3 * 4
    ram = state[ram_start:ram_start + ram_size]
    if len(ram) != ram_size:
        raise ValueError(f"{path}: truncated RAM block")
    return header, ram


def is_plausible_sector(ram: bytes, sector: int) -> bool:
    base = SECTOR_TABLE + sector * SECTOR_STRIDE
    ptr = u32(ram, base + SECTOR_PLANE_PTR)
    x, y, z = s32(ram, base + 0), s32(ram, base + 4), s32(ram, base + 8)
    return (
        0x800C0000 <= ptr < 0x80110000
        and abs(x) < 6_000_000
        and abs(y) < 3_000_000
        and abs(z) < 7_000_000
    )


def scan_save(path: Path) -> SaveRow:
    header, ram = extract_main_ram(path)
    scene = u16(ram, SCENE_ID)
    stage_dir, overlay_stem = STAGE_MAP.get(scene, ("?", "?"))
    current = s32(ram, CURRENT_SECTOR)
    current_code = None
    if 0 <= current < MAX_SCAN_SECTORS and is_plausible_sector(ram, current):
        current_code = u16(ram, SECTOR_TABLE + current * SECTOR_STRIDE + SECTOR_REGION_CODE)

    triggers: list[TriggerRow] = []
    for sector in range(MAX_SCAN_SECTORS):
        base = SECTOR_TABLE + sector * SECTOR_STRIDE
        code = u16(ram, base + SECTOR_REGION_CODE)
        if code not in TRIGGER_CODES:
            continue
        if not is_plausible_sector(ram, sector):
            continue
        triggers.append(
            TriggerRow(
                sector=sector,
                code=code,
                origin_x=s32(ram, base + 0),
                origin_y=s32(ram, base + 4),
                origin_z=s32(ram, base + 8),
                plane_ptr=f"0x{u32(ram, base + SECTOR_PLANE_PTR):08x}",
            )
        )

    return SaveRow(
        save=path.name,
        sha256_16=hashlib.sha256(path.read_bytes()).hexdigest()[:16],
        serial=header["serial"],
        scene_id=scene,
        stage_dir=stage_dir,
        overlay_stem=overlay_stem,
        flik_x=s32(ram, FLIK_BASE + 0),
        flik_y=s32(ram, FLIK_BASE + 4),
        flik_z=s32(ram, FLIK_BASE + 8),
        flik_gate=ram[FLIK_GATE & 0x1FFFFF],
        current_sector=current,
        current_sector_code=current_code,
        transition_lever=u16(ram, TRANSITION_LEVER),
        triggers=triggers,
    )


def default_saves(root: Path) -> list[Path]:
    names = sorted(root.glob("level*.sav"))
    return [p for p in names if p.name != "level02_loading.sav"]


def render_markdown(rows: Iterable[SaveRow]) -> str:
    rows = list(rows)
    lines = [
        "---",
        "title: Level Goal and Exit Trigger Matrix",
        "type: system",
        "status: active baseline",
        "updated: 2026-07-02",
        "confidence: RUNTIME-SAVE-STATE",
        "tags: [system, gameplay, exits, collision, rcg-003]",
        "---",
        "",
        "# Level Goal and Exit Trigger Matrix",
        "",
        "> Runtime-save-state catalog for [[Retail Gameplay Completeness Gap Audit]] `RCG-003`. The mechanism is the LEVEL01-proven collision-sector region-code path: `FUNC_80048138` calls `FUNC_80038f38(0,&Flik+0x82)`, which reads `0x800A7E48 + sector*0x30 + 0x2E`. Source anchor: `src_re/level_goal_trigger_catalog.c`; generator: `tools/level_goal_trigger_catalog.py`.",
        "",
        "## Evidence Boundary",
        "",
        "- Uses DuckStation v84 save-state headers and zstd state blocks; extracts only the in-memory `Bus` main-RAM block.",
        "- Scans `0x800A7E48` with stride `0x30` and keeps codes `1..4` only when origin coordinates and plane pointers look like real collision sectors.",
        "- This identifies the native sector-trigger surfaces present at each save-state anchor. It does not prove boss HP, cutscene, harvester, or overlay objective success logic.",
        "- Save states are all `SCUS-94288`; only SHA-256 prefixes are recorded here.",
        "",
        "## Region-Code Semantics",
        "",
        "| Code | Current meaning | Confidence |",
        "|---:|---|---|",
        "| 1 | Calls `FUNC_8004A700` type-2 transition path from `FUNC_80048138` | Resident dispatch decoded; per-level destination semantics still open |",
        "| 2 | Type-1 level exit body: `[0x800823A0]=1`, fade color `23`, `FUNC_80050994(58,0)` | Live-proven on LEVEL01; present again in stage 8 save-state table |",
        "| 3 | Resident dispatch has a nonzero case; appears as terminal/goal-adjacent marker in several stages | Semantics unresolved |",
        "| 4 | Resident dispatch has a nonzero case; appears as a cluster in stage 4 | Semantics unresolved |",
        "",
        "## Save-State Trigger Matrix",
        "",
        "| Save | Scene | Stage dir | Overlay | Current sector/code | Trigger sectors |",
        "|---|---:|---|---|---|---|",
    ]
    for r in rows:
        trig = ", ".join(f"`{t.sector}:code{t.code}` @ ({t.origin_x},{t.origin_y},{t.origin_z})" for t in r.triggers)
        if not trig:
            trig = "none exposed at this anchor"
        cur_code = "?" if r.current_sector_code is None else str(r.current_sector_code)
        lines.append(
            f"| `{r.save}` | {r.scene_id} | `{r.stage_dir}` | `{r.overlay_stem}` | "
            f"{r.current_sector}/`{cur_code}` | {trig} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "- `level01*.sav` confirms the already-solved stage-1 exit sector `177:code2`.",
        "- `level02.sav` (scene 3 / `LEVEL02`, stage `LEVEL1C`) exposes a large code-1 cluster at sectors `570..578` and a code-3 sector `579`; this matches the prior deep collision-map note that this scene has hundreds of sectors.",
        "- `level04.sav` and `level05.sav` expose single/clustered code-3 endpoints; `level_07.sav` exposes code-1 plus code-4 cluster; `level_14.sav` exposes a code-2 exit-like sector.",
        "- Many stage-start saves expose no nonzero sector triggers at the start anchor. That means the sector mechanism is absent from the loaded table at that anchor or is elsewhere in the level; it does not prove the level lacks a goal.",
        "",
        "## Residual RCG-003 Work",
        "",
        "- Walk or route each level to its objective and confirm which exposed sector(s) are actually reached by normal play.",
        "- Decode resident cases for codes `3` and `4` and the `FUNC_8004A700` destination/resource semantics for code `1`.",
        "- Tie boss/special objective success to overlay verbs and HUD/objective state; those are not sector-table-only exits.",
        "- Trace the converter/source mapping for every non-LEVEL01 table if source-side editing of these triggers is required. Runtime indices are now known for the save-state anchors; exact disc-source record offsets are not yet proven for every level.",
        "",
        "## Tool Output",
        "",
        "```bash",
        "python3 tools/level_goal_trigger_catalog.py --root . --json build/level_goal_trigger_catalog.json --markdown 'ObsidianVault/Systems/Level Goal and Exit Trigger Matrix.md'",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."), help="directory containing level*.sav files")
    ap.add_argument("--save", action="append", type=Path, help="specific save-state path; may repeat")
    ap.add_argument("--json", type=Path, help="write JSON metadata")
    ap.add_argument("--markdown", type=Path, help="write Obsidian markdown")
    args = ap.parse_args()

    saves = args.save if args.save else default_saves(args.root)
    rows = [scan_save(path) for path in saves]

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps([asdict(r) for r in rows], indent=2) + "\n")
        print(f"wrote {args.json} ({len(rows)} save states)")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(rows))
        print(f"wrote {args.markdown} ({len(rows)} save states)")
    if not args.json and not args.markdown:
        print(json.dumps([asdict(r) for r in rows], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
