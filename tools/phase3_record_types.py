#!/usr/bin/env python3
"""Phase-3 WP5/WP6: typed records with FULL byte accounting, verified live.

The Phase-3 gate says records must be typed "without erasing unknown fields".
So this tool refuses to let typing hide ignorance: for every record in
config/record_types.yaml it accounts for EVERY byte of the declared extent as
either a declared field or an explicit UNKNOWN span, and reports the known/
unknown split. Typing progress is then a number that can only improve by
adding evidence.

Two modes:

  (offline, default)  validate the layout — no overlaps, in-extent, aligned,
                      known vocabulary — and compute the byte accounting.
                      -> analysis/phase3_record_types.json

  --probe             LIVE: load each hash-pinned pristine anchor from the
                      Phase-2 stage baseline, read every record instance, and
                      report the OBSERVED domain of each declared field plus,
                      crucially, the observed behaviour of each UNKNOWN span:
                      always-zero / constant / varying. That triages the
                      unknowns — a varying unknown byte is live state worth
                      reversing; an always-zero span is probably padding.
                      Also samples pool occupancy for WP6 (capacity/lifetime).
                      -> analysis/phase3_record_probe.json

Usage:
    python3 tools/phase3_record_types.py                 # offline
    python3 tools/phase3_record_types.py --probe --port 23472
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import date
from pathlib import Path

import yaml

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         require_optional_live_args,
                                         select_pristine_save_anchors,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               require_optional_live_args,
                                               select_pristine_save_anchors,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

WIDTHS = {"u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4}
CONFIDENCE = {"hypothesized", "static_seen", "runtime_seen", "confirmed"}
FMT = {"u8": "<B", "s8": "<b", "u16": "<H", "s16": "<h", "u32": "<I", "s32": "<i"}


class LayoutError(Exception):
    pass


def load_records() -> list[dict]:
    doc = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())
    return doc["records"]


def validate(rec: dict) -> None:
    rid = rec["id"]
    size = rec["size"]
    seen: dict[int, str] = {}
    for f in rec["fields"]:
        w = f["width"]
        if w not in WIDTHS:
            raise LayoutError(f"{rid}.{f['name']}: bad width {w!r}")
        if f.get("confidence") not in CONFIDENCE:
            raise LayoutError(f"{rid}.{f['name']}: bad confidence")
        n = WIDTHS[w]
        off = f["offset"]
        if off < 0 or off + n > size:
            raise LayoutError(f"{rid}.{f['name']}: outside the {size:#x} extent")
        if n > 1 and off % n:
            raise LayoutError(f"{rid}.{f['name']}: {w} at {off:#x} is misaligned")
        for b in range(off, off + n):
            if b in seen:
                raise LayoutError(f"{rid}: byte {b:#x} claimed by both "
                                  f"{seen[b]} and {f['name']}")
            seen[b] = f["name"]
    if not rec.get("lifetime", "").strip():
        raise LayoutError(f"{rid}: WP6 requires a lifetime statement")


def unknown_spans(rec: dict) -> list[tuple[int, int]]:
    """Maximal runs of bytes not covered by any declared field."""
    covered = set()
    for f in rec["fields"]:
        covered.update(range(f["offset"], f["offset"] + WIDTHS[f["width"]]))
    spans, start = [], None
    for b in range(rec["size"]):
        if b not in covered and start is None:
            start = b
        elif b in covered and start is not None:
            spans.append((start, b - start))
            start = None
    if start is not None:
        spans.append((start, rec["size"] - start))
    return spans


def accounting(rec: dict) -> dict:
    spans = unknown_spans(rec)
    unknown = sum(n for _, n in spans)
    known = rec["size"] - unknown
    return {
        "size": rec["size"],
        "known_bytes": known,
        "unknown_bytes": unknown,
        "known_pct": round(100.0 * known / rec["size"], 1),
        "unknown_spans": [{"offset": f"0x{o:02X}", "length": n} for o, n in spans],
        "fields": len(rec["fields"]),
    }


def offline() -> int:
    recs = load_records()
    out, total_known, total_size = {}, 0, 0
    for r in recs:
        validate(r)
        acct = accounting(r)
        acct["base"] = f"0x{r['base']:08X}"
        acct["instances"] = r["instances"]
        acct["owner"] = r["owner"]
        acct["lifetime"] = " ".join(r["lifetime"].split())
        out[r["id"]] = acct
        total_known += acct["known_bytes"]
        total_size += r["size"]
    doc = {
        "_comment": "Phase-3 WP5/WP6 typed records with FULL byte accounting: "
                    "every byte of every record is a declared field or an "
                    "explicit UNKNOWN span — typing never erases ignorance. "
                    "Regenerate: tools/phase3_record_types.py (add --probe for "
                    "the live domain/lifetime pass).",
        "generated": date.today().isoformat(),
        "records": out,
        "totals": {
            "records": len(recs),
            "bytes": total_size,
            "known_bytes": total_known,
            "known_pct": round(100.0 * total_known / total_size, 1),
        },
    }
    path = ROOT / "analysis" / "phase3_record_types.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[records] {len(recs)} records validated; "
          f"{total_known}/{total_size} bytes typed "
          f"({doc['totals']['known_pct']}%)")
    for rid, a in out.items():
        print(f"  {rid:16s} {a['known_bytes']:3d}/{a['size']:3d} B "
              f"({a['known_pct']:5.1f}%)  {len(a['unknown_spans'])} unknown spans")
    return 0


def fixture_pin(*rels):
    """DoF #1 (provenance): hash-pin every fixture a finding rests on, plus the
    EXE identity. A finding whose fixtures are not pinned cannot be re-verified
    later — the file could change underneath it silently."""
    import hashlib
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    exe = ROOT / "REBUILD" / "files" / "SCUS_942.88"
    if exe.exists():
        out["REBUILD/files/SCUS_942.88"] = hashlib.sha256(exe.read_bytes()).hexdigest()
    return out

def _eval(expr: str, vals: dict) -> bool:
    return bool(eval(expr, {"__builtins__": {}}, dict(vals)))   # our own config


def is_live(rec: dict, vals: dict) -> bool:
    expr = rec.get("live_predicate")
    return _eval(expr, vals) if expr else True      # single-instance records


def is_occupied(rec: dict, vals: dict) -> bool:
    """The ALLOCATOR's skip test, where the record has one — this is the number
    the capacity law is about, and it is NOT the same as the live/walker gate."""
    expr = rec.get("alloc_occupied_predicate") or rec.get("live_predicate")
    return _eval(expr, vals) if expr else True


def probe(args) -> int:
    from duckstation_debug_client import DebuggerClient

    recs = load_records()
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

    # per record: field -> set of observed values; unknown byte -> set of values
    seen_fields: dict[str, dict[str, set]] = {r["id"]: {} for r in recs}
    seen_unknown: dict[str, dict[int, set]] = {r["id"]: {} for r in recs}
    occupancy: dict[str, list[int]] = {r["id"]: [] for r in recs}
    alloc_occupancy: dict[str, list[int]] = {r["id"]: [] for r in recs}
    used_anchors = []
    state_inspections = []

    for label, save in anchors:
        p = ROOT / save
        state_inspections.append(
            inspect_state_before_load(c, p, media_identity))
        r = c.call("emulator.loadState",
                   {"path": str(p), "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        used_anchors.append(label)

        for rec in recs:
            rid, size, n = rec["id"], rec["size"], rec["instances"]
            buf = rd(rec["base"], size * n)
            live = occupied = 0
            for i in range(n):
                blob = buf[i * size:(i + 1) * size]
                vals = {f["name"]: struct.unpack_from(FMT[f["width"]], blob,
                                                      f["offset"])[0]
                        for f in rec["fields"]}
                # A dead slot keeps RESIDUE, so "has non-zero bytes" is NOT
                # occupancy. Use the GAME's predicates; only learn field domains
                # and triage unknown bytes from slots the game considers LIVE.
                if not is_live(rec, vals):
                    if is_occupied(rec, vals):
                        occupied += 1
                    continue
                live += 1
                occupied += 1
                for name, v in vals.items():
                    seen_fields[rid].setdefault(name, set()).add(v)
                for off, length in unknown_spans(rec):
                    for b in range(off, off + length):
                        seen_unknown[rid].setdefault(b, set()).add(blob[b])
            occupancy[rid].append(live)
            alloc_occupancy[rid].append(occupied)

    out = {}
    for rec in recs:
        rid = rec["id"]
        fields = {}
        for f in rec["fields"]:
            vals = sorted(seen_fields[rid].get(f["name"], set()))
            fields[f["name"]] = {
                "offset": f"0x{f['offset']:02X}", "width": f["width"],
                "distinct_values": len(vals),
                "min": vals[0] if vals else None,
                "max": vals[-1] if vals else None,
                "domain_sample": vals[:12],
            }
        # triage the unknown bytes — this is what makes the unknowns actionable
        triage = {"always_zero": [], "constant_nonzero": [], "varying": []}
        for b in sorted(seen_unknown[rid]):
            vals = seen_unknown[rid][b]
            key = ("always_zero" if vals == {0}
                   else "constant_nonzero" if len(vals) == 1 else "varying")
            triage[key].append(f"0x{b:02X}")
        occ, aocc = occupancy[rid], alloc_occupancy[rid]
        cap = rec["instances"]
        out[rid] = {
            "instances": cap,
            "live_predicate": rec.get("live_predicate", "(single instance)"),
            "alloc_occupied_predicate": rec.get("alloc_occupied_predicate"),
            "fields": fields,
            "unknown_byte_triage": {k: {"count": len(v), "offsets": v}
                                    for k, v in triage.items()},
            "occupancy": {
                "_comment": "live = the game's walker/live gate; alloc_occupied = "
                            "the allocator's skip test (the number the capacity "
                            "law is about). Residue in dead slots is NOT occupancy.",
                "live_min": min(occ) if occ else None,
                "live_max": max(occ) if occ else None,
                "alloc_occupied_max": max(aocc) if aocc else None,
                "capacity": cap,
                "peak_alloc_pct": (round(100.0 * max(aocc) / cap, 1)
                                   if aocc else None),
                "headroom_at_peak": (cap - max(aocc)) if aocc else None,
            },
        }

    run_provenance = finish_run(
        args, generator="tools/phase3_record_types.py",
        anchor={"saves": [save for _, save in anchors if (ROOT / save).exists()],
                "fixture_sha256": fixture_pin(*[save for _, save in anchors
                                                  if (ROOT / save).exists()]),
                "selection": anchor_selection,
                "state_inspections": state_inspections,
                "media_identity": media_identity},
        timing={"anchors_requested": anchor_selection["anchors_requested"],
                "anchors_accepted": len(anchors),
                "anchors_used": len(used_anchors),
                "snapshot": "paused after each validated loadState"},
    )
    doc = {
        "_comment": "Phase-3 WP5/WP6 LIVE record probe: every declared field's "
                    "observed domain plus a triage of every UNKNOWN byte "
                    "(always_zero / constant_nonzero / varying) across the "
                    "centrally classified strict-pristine anchors — varying unknowns are live "
                    "state worth reversing, always-zero spans are likely "
                    "padding. Occupancy feeds the WP6 capacity picture. "
                    "Regenerate: tools/phase3_record_types.py --probe.",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media": media_identity,
        "anchor_selection": anchor_selection,
        "anchors_used": len(used_anchors),
        "fixture_sha256": fixture_pin(*[s for _, s in anchors
                                        if (ROOT / s).exists()]),
        "records": out,
    }
    path = ROOT / "analysis" / "phase3_record_probe.json"
    write_live_evidence(path, doc)
    print(f"[probe] {len(used_anchors)} strict-pristine anchors sampled; "
          f"{anchor_selection['anchors_rejected']} non-pristine/uncertain refused")
    for rid, r in out.items():
        t = r["unknown_byte_triage"]
        o = r["occupancy"]
        print(f"  {rid:16s} live {o['live_min']}-{o['live_max']}, "
              f"alloc-occupied peak {o['alloc_occupied_max']}/{o['capacity']} "
              f"(headroom {o['headroom_at_peak']})  unknown bytes: "
              f"{t['varying']['count']} varying, "
              f"{t['constant_nonzero']['count']} constant, "
              f"{t['always_zero']['count']} zero")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true")
    add_required_live_args(ap, optional=True)
    args = ap.parse_args()
    rc = offline()
    if args.probe:
        require_optional_live_args(args)
        rc |= probe(args)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
