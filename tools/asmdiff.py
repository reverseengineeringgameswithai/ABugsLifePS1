#!/usr/bin/env python3
"""Per-function original-vs-rebuilt assembly diff (docs/SUBSTRATE.md).

For every `attempted` entry in config/segments.yml: assemble its source and
compare against the original bytes word-by-word. Mismatching words are shown
disassembled (tools/exe_read.disasm_one) so branch-sense / immediate / reorder
problems are readable at a glance. Exit 0 iff every attempted function is
byte-identical.

  python tools/asmdiff.py            # diff all attempted
  python tools/asmdiff.py 80065eec   # diff one (hex start VA)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exe_read  # noqa: E402
from substrate_common import (BUILD, HANDWRITTEN, ROOT, build_entry,  # noqa: E402
                              load_segments, original_exe, va_to_off)


def diff_function(seg: dict, exe: bytes, a: dict) -> bool:
    src = ROOT / a["source"]
    want = a["end"] - a["start"]
    orig = exe[va_to_off(seg, a["start"]):va_to_off(seg, a["start"]) + want]
    new = build_entry(a, seg, include_dirs=[BUILD, HANDWRITTEN])
    tag = "C" if src.suffix == ".c" else "asm"
    if src.suffix == ".c":
        ct = seg.get("c_toolchain", {})
        tag = f"C[{ct.get('compiler')} {' '.join(ct.get('cc1_flags', []))}]"
    if new == orig:
        print(f"[asmdiff] {a['start']:#010x} {src.name}: MATCH ({want} B, {tag})")
        return True
    print(f"[asmdiff] {a['start']:#010x} {src.name}: DIFFERS "
          f"(built {len(new)} B vs {want} B original, {tag})")
    n = max(len(orig), len(new))
    for off in range(0, n, 4):
        ow = orig[off:off + 4]
        nw = new[off:off + 4]
        if ow == nw:
            continue
        va = a["start"] + off
        def dis(bs):
            if len(bs) != 4:
                return f"<{bs.hex() or 'missing'}>"
            w = struct.unpack("<I", bs)[0]
            return f"{w:08x}  {exe_read.disasm_one(w, va)}"
        print(f"  {va:#010x}  orig: {dis(ow)}")
        print(f"  {'':10}  new : {dis(nw)}")
    return False


def main() -> int:
    seg = load_segments()
    exe = original_exe(seg)
    only = sys.argv[1].lower().lstrip("0x") if len(sys.argv) > 1 else None
    picked = [a for a in seg["attempted"]
              if only is None or f"{a['start']:x}" == only]
    if not picked:
        print("[asmdiff] nothing attempted yet (config/segments.yml attempted: [])"
              if only is None else f"[asmdiff] no attempted entry {only}")
        return 0
    ok = all([diff_function(seg, exe, a) for a in picked])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
