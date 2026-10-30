#!/usr/bin/env python3
"""Phase-3 WP5/WP4: the object render-descriptor table (0x80096B98), live.

The dispatch map deliberately deferred this one: object_pointer_list is NOT an
EXE table — it is RAM/BSS populated at load time, so it can only be enumerated
from a running game. That makes it the natural place to ask the question a mod
actually cares about:

    which descriptor bytes are invariant, and which are scene-dependent?

Method: across every hash-pinned pristine stage anchor, read the 50-entry kind ->
descriptor pointer table, follow each pointer, and read the 0xC-byte descriptor
(Canon: kind -> 0xC-byte descriptor; 0x1D = sprite). Then compare, per byte, what
is invariant across loaded anchors and what varies.

This experiment observes post-load snapshots. Cross-anchor variation proves
scene dependence, not which instruction wrote the byte. Loader causality remains
explicitly unresolved until a cold-boot/transition write trace attributes it.

Usage: python3 tools/phase3_render_descriptors.py [--port 23473]
Output: analysis/phase3_render_descriptors.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         select_pristine_save_anchors,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               select_pristine_save_anchors,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

OBJECT_POINTER_LIST = 0x80096B98
KINDS = 50
DESC_LEN = 0xC
RAM_LO, RAM_HI = 0x80000000, 0x80200000


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def write_render_evidence(path: Path, doc: dict) -> bool:
    """Compare the same JSON value that will be retained on disk.

    Descriptor ids are naturally integer mapping keys while the live document is
    assembled, but JSON object keys are always strings.  Canonicalising through a
    JSON round trip before the shared semantic comparison prevents a byte-identical
    replay from looking different solely because the retained mapping was decoded
    from JSON.
    """
    json_doc = json.loads(json.dumps(doc))
    return write_live_evidence(path, json_doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap)
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    baseline = json.loads(
        (ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
    anchors, anchor_selection = select_pristine_save_anchors(baseline)

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)
    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    per_anchor = {}
    used = []
    state_inspections = []
    for label, save in anchors:
        state_inspections.append(
            inspect_state_before_load(c, ROOT / save, media_identity))
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / save), "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        used.append((label, save))
        tab = rd(OBJECT_POINTER_LIST, KINDS * 4)
        ptrs = [struct.unpack_from("<I", tab, i * 4)[0] for i in range(KINDS)]
        descs = {}
        for kind, p in enumerate(ptrs):
            if RAM_LO <= p < RAM_HI:
                descs[kind] = rd(p, DESC_LEN).hex()
        per_anchor[label] = {"pointers": [f"0x{p:08X}" for p in ptrs],
                             "descriptors": descs}

    # 1. are the POINTERS scene-invariant?
    ptr_sets = defaultdict(set)
    for a in per_anchor.values():
        for kind, p in enumerate(a["pointers"]):
            ptr_sets[kind].add(p)
    ptr_stable = {k: (len(v) == 1) for k, v in ptr_sets.items()}

    # 2. which descriptor BYTES vary between loaded scene anchors?
    byte_variance = {i: set() for i in range(DESC_LEN)}
    for a in per_anchor.values():
        for kind, hexs in a["descriptors"].items():
            b = bytes.fromhex(hexs)
            for i in range(DESC_LEN):
                byte_variance[i].add((kind, b[i]))
    per_byte = {}
    for i in range(DESC_LEN):
        by_kind = defaultdict(set)
        for kind, v in byte_variance[i]:
            by_kind[kind].add(v)
        varying_kinds = sum(1 for vs in by_kind.values() if len(vs) > 1)
        per_byte[f"+0x{i:02X}"] = {
            "kinds_whose_value_changes_between_levels": varying_kinds,
            "varying_kind_ids": sorted(kind for kind, values in by_kind.items()
                                       if len(values) > 1),
            "invariant": varying_kinds == 0,
        }

    scene_dependent = [k for k, v in per_byte.items() if not v["invariant"]]
    invariant = [k for k, v in per_byte.items() if v["invariant"]]
    used_saves = [save for _, save in used]
    run_provenance = finish_run(
        args, generator="tools/phase3_render_descriptors.py",
        anchor={"saves": used_saves, "fixture_sha256": fixture_pin(*used_saves),
                "selection": anchor_selection,
                "state_inspections": state_inspections,
                "media_identity": media_identity},
        timing={"anchors_loaded": len(used), "descriptor_bytes": DESC_LEN,
                "kinds": KINDS},
    )
    doc = {
        "_comment": "Phase-3 object render-descriptor table (0x80096B98), "
                    "enumerated LIVE across every strict-pristine stage anchor. This is a "
                    "post-load snapshot comparison: it proves which bytes are "
                    "scene-dependent, but does NOT attribute their writers to the "
                    "loader. Regenerate: tools/phase3_render_descriptors.py",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media": {"serial": status.get("game_serial")},
        "media_identity_after_connect": media_identity,
        "anchor_selection": anchor_selection,
        "fixture_sha256": fixture_pin(*[s for _, s in used]),
        "anchors_used": len(used),
        "table": {"address": f"0x{OBJECT_POINTER_LIST:08X}", "kinds": KINDS,
                  "descriptor_bytes": DESC_LEN},
        "pointer_table_is_scene_invariant": all(ptr_stable.values()),
        "kinds_with_a_descriptor": len(per_anchor[used[0][0]]["descriptors"])
        if used else 0,
        "descriptor_bytes": per_byte,
        "scene_dependent_bytes": scene_dependent,
        "invariant_bytes": invariant,
        "writer_attribution": {
            "status": "unresolved",
            "reason": "loadState restores the post-load RAM snapshot and clears "
                      "non-halting instrumentation; cross-anchor variance is not a "
                      "write trace",
            "next_experiment": "cold-boot or transition into a second scene with a "
                               "write watch armed over 0x80081D98..0x80082060, then "
                               "bank instruction-attributed writer PCs",
        },
        "verdict": (
            "The kind -> descriptor POINTERS are the same in every level, but the "
            f"post-load values of descriptor bytes {', '.join(scene_dependent)} "
            "vary between scene anchors. Only the remaining offsets are observed "
            "invariant. This bounds durability risk but does not identify the writer; "
            "loader causality requires the recorded transition write-trace experiment."
            if scene_dependent else
            "Descriptors are fully invariant across levels."),
        "per_anchor": per_anchor,
    }
    path = ROOT / "analysis" / "phase3_render_descriptors.json"
    write_render_evidence(path, doc)
    print(f"[descriptors] {len(used)} strict-pristine anchors "
          f"({anchor_selection['anchors_rejected']} refused); pointer table scene-invariant: "
          f"{doc['pointer_table_is_scene_invariant']}")
    print(f"[descriptors] scene-dependent bytes: {scene_dependent or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
