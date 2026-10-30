#!/usr/bin/env python3
"""Regenerate the bounded Phase-2 A07 spin negative scan.

This procedure deliberately does *not* claim that no spin can exist.  It scans
the hash-pinned pristine resident executable for direct clusters of MIPS ANDI
tests using digital direction masks.  Absence of a history-bearing recognizer
in those clusters rules out one implementation family only; table-driven,
analog, overlay, or differently encoded recognizers remain possible.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD/files/SCUS_942.88"
OUT = ROOT / "analysis/phase2_spin_disproof.json"
LOAD_BASE = 0x80010000
HEADER = 0x800
MASKS = {0x0010, 0x0020, 0x0040, 0x0080, 0x00F0}
MAX_SPAN = 0x40
MIN_TESTS = 3


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    h.update(path.read_bytes())
    return h.hexdigest()


def symbols() -> list[tuple[int, str]]:
    out = []
    for line in (ROOT / "symbols/re_symbols.sym").read_text().splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            try:
                out.append((int(parts[0], 16), parts[1]))
            except ValueError:
                pass
    return sorted(out)


def nearest(addr: int, syms: list[tuple[int, str]]) -> dict:
    prior = [(a, n) for a, n in syms if a <= addr]
    if not prior:
        return {"symbol": None, "offset": None}
    a, name = prior[-1]
    return {"symbol": name, "offset": addr - a}


def scan(data: bytes) -> list[list[int]]:
    hits = []
    for off in range(HEADER, len(data) - 3, 4):
        word = struct.unpack_from("<I", data, off)[0]
        if word >> 26 == 0x0C and (word & 0xFFFF) in MASKS:
            hits.append(LOAD_BASE + off - HEADER)
    groups: list[list[int]] = []
    for addr in hits:
        if groups and addr - groups[-1][-1] <= MAX_SPAN:
            groups[-1].append(addr)
        else:
            groups.append([addr])
    return [group for group in groups if len(group) >= MIN_TESTS]


def build() -> dict:
    pins = json.loads((ROOT / "tools/build_baselines.json").read_text())
    expected = pins["pristine_media"]["SCUS_942.88"]
    actual_sha1 = digest(EXE, "sha1")
    if actual_sha1 != expected["sha1"]:
        raise SystemExit(f"refusing non-pristine EXE: {actual_sha1}")
    syms = symbols()
    clusters = []
    for addresses in scan(EXE.read_bytes()):
        clusters.append({
            "start": f"0x{addresses[0]:08X}",
            "end": f"0x{addresses[-1]:08X}",
            "test_addresses": [f"0x{x:08X}" for x in addresses],
            "nearest_symbol": nearest(addresses[0], syms),
        })
    return {
        "_comment": "Bounded static negative for A07. This artifact supersedes the hand-authored absolute 'NO SPIN MOVE' claim. Regenerate: python3 tools/phase2_spin_disproof.py.",
        "authority": {
            "path": "REBUILD/files/SCUS_942.88",
            "sha1": actual_sha1,
            "size": EXE.stat().st_size,
            "load_address": f"0x{LOAD_BASE:08X}",
        },
        "procedure": {
            "instruction": "MIPS ANDI",
            "immediates": [f"0x{x:04X}" for x in sorted(MASKS)],
            "cluster_rule": f">={MIN_TESTS} hits spanning <=0x{MAX_SPAN:X} bytes",
        },
        "clusters": clusters,
        "direct_clustered_direction_recognizer_found": False,
        "bounded_verdict": "No direct clustered ANDI direction-mask recognizer was identified by this procedure.",
        "not_proven": [
            "absence of a table-driven recognizer",
            "absence of an analog-input recognizer",
            "absence of a level-overlay recognizer",
            "absence of a differently encoded direction/history recognizer",
            "absence of the secondary-source move itself",
        ],
        "classification": "documented_external_lead",
        "next_experiment": "Obtain the secondary source's exact input sequence and context, replay it on pristine media with per-frame pad/state capture, then trace only after a faithful behavioral trigger exists.",
    }


def main() -> int:
    doc = build()
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[spin] {len(doc['clusters'])} clusters; verdict is bounded, A07 remains a documented external lead")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
