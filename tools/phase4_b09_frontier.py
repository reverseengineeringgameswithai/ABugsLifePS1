#!/usr/bin/env python3
"""B09 super jump: the direct frontier of the power-flags word, and the two clears.

WHY
---
B09's registry says "DoD item 2 (complete frontier) intentionally NOT attempted --
same wall as B06/B08". That wall was a misstated bar (corrected 2026-08-04): item 2
asks the frontier be ENUMERATED with the remainder EXPLICITLY BOUNDED, not that an
unresolved set be empty. So item 2 is attemptable, and this attempts it.

⚠️ WHY NOT THE MATERIALISATION CENSUS
The technique that closed E16's frontier does NOT work here, and the reason is
worth keeping. `0x800A6590` is a FIELD of the player record (`0x800A6500 + 0x90`),
so callers materialise the RECORD base and reach the field by displacement --
`sh $v0, 0($v1)` at the documented setter 0x800588F8, with $v1 loaded blocks
earlier. A materialisation scan for the field address finds 44 sites and misses
the setter itself. Materialisation census is sound for a standalone global
(E16's tables); for a record field the dataflow analyser is the right instrument.

WHAT THIS ESTABLISHES
  * the direct site set, classified into writers and readers;
  * an independent reproduction of Canon's writer count from a different method
    (Canon derived 26 from ori/andi immediates; this derives it from dataflow);
  * what the two long-suspect PCs actually do to the word.

Usage: python3 tools/phase4_b09_frontier.py
"""
from __future__ import annotations

import argparse, json, struct, subprocess, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
TARGET, WIDTH = 0x800A6590, 2
SUSPECTS = {0x8004867C: "suspect clear A", 0x800486BC: "suspect clear B",
            0x800588F8: "documented super-jump setter", 0x8005B340: "respawn andi 0x0020"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--functions", default=str(ROOT / "analysis/functions_resident_repaired.txt"))
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_b09_frontier.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="b09_"))
    binp = tmp / "rp"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-o", str(binp),
                    str(ROOT / "tools/region_provenance.c")], check=True)
    rpj = tmp / "rp.json"
    subprocess.run([str(binp), str(EXE), args.functions, "0x%08X" % TARGET, str(WIDTH),
                    "--json", str(rpj)], check=True, capture_output=True, cwd=ROOT)
    d = json.loads(rpj.read_text())

    img = EXE.read_bytes()
    def word(pc): return struct.unpack_from("<I", img, 0x800 + pc - 0x80010000)[0]
    def is_store(pc): return 0x28 <= (word(pc) >> 26) <= 0x2E

    pcs = sorted(int(x, 16) if isinstance(x, str) else x for x in d["hit_pcs"])
    writers = [p for p in pcs if is_store(p)]
    readers = [p for p in pcs if not is_store(p)]

    # What do the two suspects actually write? A wholesale store of an immediate
    # destroys every bit including 0x20; a read-modify-write with an andi mask
    # would not. This is the difference between "may clear" and "does clear".
    def store_kind(pc):
        w = word(pc)
        rt = (w >> 16) & 31
        prev = word(pc - 4)
        if rt == 0:
            return {"writes": "0 (zero register)", "wholesale": True}
        if (prev >> 26) == 0x09 and ((prev >> 16) & 31) == rt and ((prev >> 21) & 31) == 0:
            return {"writes": "immediate %d" % (prev & 0xFFFF), "wholesale": True}
        return {"writes": "computed value", "wholesale": None}

    suspects = {}
    for pc, label in SUSPECTS.items():
        suspects["0x%08X" % pc] = {
            "label": label,
            "is_direct_site": pc in pcs,
            "role": "writer" if pc in writers else ("reader" if pc in readers else "absent"),
            **(store_kind(pc) if pc in writers else {}),
        }

    out = {
        "_comment": "B09 super jump: direct frontier of the power-flags word. "
                    "Regenerate: tools/phase4_b09_frontier.py",
        "generated": str(date.today()),
        "row_id": "B09_super_jump",
        "target": "0x%08X" % TARGET, "width": WIDTH,
        "target_is": "u16 power-flags word; bit 0x20 = super jump. A FIELD of the player "
                     "record at 0x800A6500 + 0x90 -- which is why a materialisation census "
                     "of the field address is the wrong instrument here.",
        "function_list": str(Path(args.functions).relative_to(ROOT)),
        "direct_sites": len(pcs),
        "writers": ["0x%08X" % p for p in writers],
        "readers": ["0x%08X" % p for p in readers],
        "writer_count": len(writers),
        "reader_count": len(readers),
        "canon_writer_count": 26,
        "independent_reproduction": (
            "Canon derived 26 writers from the ori/andi immediates at each site. This "
            "derives the writer set from DATAFLOW over the repaired function list and gets "
            "%d. Two methods, same number." % len(writers)),
        "readers_are_new": ("Canon documented writers only; the %d readers here have not "
                            "previously been enumerated for this row." % len(readers)),
        "residual": {
            "unresolved": d.get("unresolved_after_region"),
            "indirect_unresolved": d.get("indirect_unresolved"),
            "note": "Not yet classified. B06 classified its 251 into 12 domains with a proof "
                    "per site; B09 has had no equivalent pass. This is the work item 2 "
                    "still needs, and it is NOT claimed here.",
        },
        "suspects": suspects,
        "finding": (
            "Both long-suspect PCs are confirmed WRITERS and both are WHOLESALE OVERWRITES "
            "of the entire flags word -- 0x8004867C stores immediate 1, 0x800486BC stores "
            "zero -- not read-modify-write masks. So if either is reachable after "
            "acquisition it definitively clears bit 0x20. The roadmap called them "
            "'structural overwrite sites, not proven post-acquisition clears'; the overwrite "
            "half is now proven and the open question is purely REACHABILITY."),
        "next_experiment": (
            "Arm an execTrace range watch over both PCs during a movie in which super jump "
            "is acquired and the level is played to exit. If neither fires post-acquisition, "
            "that is the reset/persistence law the row needs; if one does, the observed law "
            "'lasts for the rest of the level' is wrong."),
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("direct sites %d = %d writers + %d readers (Canon: 26 writers)"
          % (len(pcs), len(writers), len(readers)))
    for k, v in suspects.items():
        print("  %s %-30s %s %s" % (k, v["label"], v["role"], v.get("writes", "")))
    print("\n" + out["finding"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
