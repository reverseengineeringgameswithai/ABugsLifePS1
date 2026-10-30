#!/usr/bin/env python3
"""Phase-4 E03: diff the C OT-walker (RAM side) against gp0Trace (dispatch side).

For each mid-frame capture produced by tools/phase4_e03_midframe_walk.py:
  - the frame presents SEPARATE linked lists (env preamble list, then the
    depth-bucket body chain, then auxiliary lists); the body list head is the
    a1 register captured live at the kick-1 breakpoint;
  - the C walker (tools/phase4_e03_ot_walk.c) walks the dump from that head and
    its per-opcode histogram must EQUAL the trace's DMA stream for the frame
    (any env-node commands the trace caught are stripped by source address);
  - the walker's empty-link-node count measures the depth-bucket table
    (1228 entries, invariant across the three scene classes).

Usage: python3 tools/phase4_e03_crosscheck.py --dump-dir <dir> \
           [--walker <bin>] [--out analysis/phase4_e03_ot_walk_crosscheck.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", required=True)
    ap.add_argument("--walker", default="")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e03_ot_walk_crosscheck.json"))
    args = ap.parse_args()

    dump_dir = Path(args.dump_dir)
    walker = args.walker
    if not walker:
        walker = str(dump_dir / "ot_walk")
        subprocess.run(["cc", "-O2", "-o", walker,
                        str(ROOT / "tools/phase4_e03_ot_walk.c")], check=True)

    results, failures = {}, []
    for meta_path in sorted(dump_dir.glob("*_midframe.json")):
        m = json.loads(meta_path.read_text())
        label = m["label"]
        dma = [e for e in m["trace_entries"] if e["source"] == "dma"]
        frame0 = dma[0]["frame"]
        dma = [e for e in dma if e["frame"] == frame0]
        # body list head captured live in a1 at the kick-1 breakpoint
        head = int(m["body_list_head_a1"], 16)
        # strip leading env-node commands only if the trace caught them (the
        # two-halt driver arms after the env kick, so normally it doesn't)
        env_head = int(m["env_list_head_a1"], 16)
        env_ops = []
        while dma and 0 <= (int(dma[0]["source_addr"], 16) | 0x80000000) - (env_head + 4) < 0x28:
            env_ops.append(dma.pop(0)["command_id"])

        w = subprocess.run([walker, m["ram_dump"], hex(head)],
                           capture_output=True, text=True)
        walk = json.loads(w.stdout)
        trace_hist = Counter(e["command_id"] for e in dma)
        walk_hist = {int(k, 16): v for k, v in walk["opcodes"].items()}
        mismatches = {f"0x{op:02x}": {"trace": trace_hist.get(op, 0),
                                      "walk": walk_hist.get(op, 0)}
                      for op in set(trace_hist) | set(walk_hist)
                      if trace_hist.get(op, 0) != walk_hist.get(op, 0)}
        ok = (not mismatches and walk["terminated"] == "true"
              or not mismatches and walk["terminated"] is True)
        if not ok:
            failures.append(label)
        results[label] = {
            "meta": {k: m[k] for k in ("save", "save_sha256", "present_pc",
                                       "ram_dump_sha256")},
            "traced_frame": frame0,
            "env_node_ops": [f"0x{o:02x}" for o in env_ops],
            "body_head_node": f"0x{head:08x}",
            "walk": {k: walk[k] for k in ("nodes", "empty_link_nodes",
                                          "max_empty_run", "packets",
                                          "payload_words", "min_node",
                                          "max_node", "terminated", "cycle",
                                          "oob")},
            "trace_body_cmds": sum(trace_hist.values()),
            "opcode_mismatches": mismatches,
            "ok": ok,
        }
        print(f"{label}: walk={walk['packets']} trace={sum(trace_hist.values())} "
              f"buckets(empty)={walk['empty_link_nodes']} ok={ok}")

    out = {
        "_comment": "Phase-4 E03 double-implementation cross-check: C linked-list "
                    "walker over a mid-frame RAM dump vs gp0Trace dispatch stream "
                    "of the same frame. Agreement proves both readings "
                    "(region_provenance.c pattern). Regenerate: midframe_walk.py "
                    "per scene, then this script.",
        "generated": str(date.today()),
        "scenes": results,
        "failing": failures,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out}; failing: {failures or 'none'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
