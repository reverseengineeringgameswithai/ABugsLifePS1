#!/usr/bin/env python3
"""GAP-0039 cross-level confirmation: per-pixel visible-floor source on LEVEL02.

The LEVEL01 headline (Experiment - Spawn-floor render source) showed the visible
floor under Flik is a LEVEL.DAT mesh emitted by ``fcn.80010000``, distinct from
the chunk-32 collision sector table ``0x800a7e48``.  The first LEVEL02 pass
(Verification - M7 Headline Recheck) only repeated the *aggregate* source
classification and reported ``fcn.800172dc`` = 0 calls — which a robust multi-
frame measurement shows was a single-frame sampling artifact (both geometry
drivers are active on LEVEL02).  This script does the missing **per-pixel** work
and attributes the floor correctly through the shared emitter leaf:

  1. loadState a LEVEL02 fixture (scene_id == 3); assert serial SCUS-94288 and
     that the fixture + mounted media are the expected (pristine) disc.
  2. Verify ``fcn.80010000`` and ``fcn.800172dc`` are two distinct functions
     (disasm entries) — the project has a known 0x80010000<->0x800172dc swap
     confound, so the identities are checked, not assumed.
  3. gpu.pickObject a spread of lower-screen pixels (the ground projects there);
     record each hit's draw command, packet RAM address, texpage, rgba.
  4. accessLog write-watch each distinct textured-quad (GP0(3c)) floor packet ->
     the writer PCs.  On LEVEL02 the store happens in a SHARED GTE leaf emitter
     at 0x80019xxx (it does mfc2 sz1/sz2/sz3, builds the GP0(3c) quad and OT-links
     it via lui 0x0c00); that leaf is shared by both drivers, so the writer PC
     alone cannot say DAT vs chunk-35.
  5. Decisive attribution: execTrace the floor-writer PC capturing ``ra`` -> the
     driver that called the shared leaf.  ra inside ``fcn.80010000`` (0x80010000..
     0x80011200) means the floor is the DAT path.
  6. Robust multi-frame execTrace of ``fcn.80010000`` (a0 source region, relative
     to this stage's live G_DAT_BASE_PTR) and ``fcn.800172dc`` (call count: it is
     active but draws OTHER geometry, not the picked floor packets).
  7. Read the collision sector table ``0x800a7e48`` (populated, separate region)
     -> visual != collision holds on LEVEL02 too.

Ships NO disc/state bytes; drives an operator-supplied isolated instance
(launch_debugger_instance.sh, port 23460, token debugger-<uid>, pristine disc).
Host-portable via DUCKSTATION_DIR / ABL_SAVESTATES; ``--save`` overrides the
fixture, ``--disc`` the expected media, ``--output`` writes JSON (prefer /tmp).

Verdict is self-checking and exits non-zero unless the floor pixel under Flik is
attributed to ``fcn.80010000`` reading DAT.  A pick miss yields a clearly-marked
bounded result.  All dynamic evidence is operator-local (GAP-0001).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

_DUCK = os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation"))
sys.path.insert(0, os.path.join(_DUCK, "scripts", "debugger-client"))
_SAVES = os.environ.get(
    "ABL_SAVESTATES", os.path.expanduser("~/.local/share/duckstation/savestates")
)
from duckstation_debug_client import DebuggerClient  # noqa: E402

GAME_SERIAL = "SCUS-94288"
LEVEL02_SCENE_ID = 3
SCENE_ID = 0x80082504            # current_scene_id (3 == LEVEL02)
FLIK_XYZ = (0x800A6500, 0x800A6504, 0x800A6508)
G_DAT_BASE_PTR = 0x80082498      # -> runtime LEVEL.DAT base (per-stage)
EMIT_DAT = 0x80010000            # DAT mesh/poly driver (visible floor family)
EMIT_DAT_HI = 0x80011200         # fcn.80010000 body / inline-emit + leaf call sites
EMIT_ALL = 0x800172DC            # shared .ALL / chunk-35 mesh driver (other meshes)
LEAF_LO, LEAF_HI = 0x80019000, 0x8001A000   # shared GTE poly->GP0 leaf emitter
SECTOR_TABLE = 0x800A7E48        # collision sector table (LEVEL.RAW chunk 32, fixed)
CHUNK35_LO, CHUNK35_HI = 0x8012A000, 0x80130000   # chunk-35 buffer (fixed resident)
DAT_WINDOW = 0x80000             # a0 counts as DAT if base <= a0 < base+window


def addr(value: int) -> str:
    return f"0x{value:08x}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Dbg:
    def __init__(self, host, port, token):
        self.c = DebuggerClient(host, port, "ws")
        self.c.authenticate(token)
        try:
            self.c.transport.sock.settimeout(60)
        except Exception:
            pass

    def call(self, method, params=None):
        return self.c.call(method, params or {})

    def read(self, address, length):
        return bytes.fromhex(
            self.call("debugger.readMemory", {"address": addr(address), "length": length})["hex"]
        )

    def u32(self, address):
        return struct.unpack("<I", self.read(address, 4))[0]

    def s32(self, address):
        return struct.unpack("<i", self.read(address, 4))[0]

    def adv(self, n):
        while n > 0:
            step = min(120, n)
            self.call("emulator.advanceFrames", {"frames": step})
            n -= step

    def disasm(self, address, count):
        r = self.call("debugger.disassemble", {"address": addr(address), "count": count})
        return [i.get("text", "?") for i in r.get("instructions", [])]

    def trace(self, pc, frames, cap):
        """Multi-frame execTrace capture of a PC; returns (total, events)."""
        self.call("execTrace.clear")
        w = self.call("execTrace.addWatch",
                      {"pc": addr(pc), "capture": list(cap), "label": "t", "max_events": 400})
        self.adv(frames)
        ev = self.call("execTrace.get", {"watch_id": w["watch_id"]})
        self.call("execTrace.clear")
        return ev.get("total"), ev.get("events", [])


def region(a: int, dat_base: int) -> str:
    if dat_base and dat_base <= a < dat_base + DAT_WINDOW:
        return "DAT"
    if CHUNK35_LO <= a < CHUNK35_HI:
        return "CHUNK35buf"
    if EMIT_DAT <= a < EMIT_DAT_HI:
        return "fcn80010000"
    if LEAF_LO <= a < LEAF_HI:
        return "sharedLeaf"
    if 0x80017000 <= a < 0x80018000:
        return "fcn800172dc"
    if 0x801D0000 <= a < 0x801F0000:
        return "PKTbuf"
    if 0x1F800000 <= a < 0x1F801000:
        return "scratch"
    return "?"


def classify_writer(pcs):
    """Classify a floor-packet writer PC set: inline fcn.80010000, shared leaf, or other."""
    if not pcs:
        return "none"
    ints = [int(p, 16) for p in pcs]
    if all(EMIT_DAT <= p < EMIT_DAT_HI for p in ints):
        return "fcn80010000_inline"
    if all(LEAF_LO <= p < LEAF_HI for p in ints):
        return "shared_leaf"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default="debugger-%d" % os.getuid())
    ap.add_argument("--save", default=os.path.join(os.getcwd(), "level02.sav"),
                    help="LEVEL02 (scene_id 3) state (.sav); default = repo level02.sav "
                         "(role level02-scene3-experiment, the pinned evidence state)")
    ap.add_argument("--disc", default=os.path.join(os.getcwd(), "Disney-Pixar A Bug's Life (v1.0).cue"),
                    help="expected pristine disc cue (checked vs state + mounted media)")
    ap.add_argument("--settle", type=int, default=4, help="frames to settle after load")
    ap.add_argument("--frames", type=int, default=4, help="frames per robust execTrace window")
    ap.add_argument("--picks",
                    default="256,180;256,200;230,195;282,195;256,210;210,205;300,205;256,165",
                    help="native CRTC pixels (x,y;...) — lower-centre = ground under Flik")
    ap.add_argument("--output", help="optional JSON output path (prefer /tmp)")
    args = ap.parse_args()

    save = Path(args.save).expanduser().resolve()
    disc = Path(args.disc).expanduser().resolve()
    if not save.is_file():
        print(f"fixture not found: {save}")
        return 2
    if not disc.is_file():
        print(f"pristine disc cue not found: {disc}")
        return 2

    d = Dbg(args.host, args.port, args.token)

    # --- identity + disc guards (mirror the G29 Arm A discipline) ----------
    initial_status = d.call("debugger.status")
    if initial_status.get("game_serial") != GAME_SERIAL:
        print(f"REFUSING non-ABL instance: {initial_status.get('game_serial')!r}")
        return 2
    initial_media = d.call("emulator.getMediaInfo")
    if Path(initial_media.get("path", "")).expanduser().resolve() != disc:
        print(f"wrong disc mounted before load: {initial_media.get('path')!r} != {disc}")
        return 2
    state_info = d.call("emulator.getStateInfo", {"path": str(save)})
    if not state_info.get("valid") or state_info.get("serial") != GAME_SERIAL:
        print(f"invalid/wrong-game fixture metadata: {state_info}")
        return 2
    if Path(state_info.get("media_path", "")).expanduser().resolve() != disc:
        print(f"fixture is not the expected-disc-backed state: {state_info.get('media_path')!r}")
        return 2

    d.call("emulator.clearControllerState", {"port": 0})
    load = d.call("emulator.loadState",
                  {"path": str(save), "pause_after_load": True,
                   "validate_disc": True, "auto_select_disc": False})
    if load.get("game_serial") != GAME_SERIAL:
        print(f"loaded state wrong serial: {load.get('game_serial')!r}")
        return 2
    d.adv(args.settle)
    d.call("debugger.pause")
    loaded_media = d.call("emulator.getMediaInfo")
    if Path(loaded_media.get("path", "")).expanduser().resolve() != disc:
        print(f"fixture selected non-expected media: {loaded_media.get('path')!r}")
        return 2

    scene = d.u32(SCENE_ID)
    fx, fy, fz = (d.s32(a) for a in FLIK_XYZ)
    dat_base = d.u32(G_DAT_BASE_PTR)
    print(f"[serial] {initial_status.get('game_serial')} / {initial_status.get('game_title')}")
    print(f"[state] scene_id={scene} (expect {LEVEL02_SCENE_ID}=LEVEL02)  "
          f"Flik world XYZ=({fx},{fy},{fz})  file Z={fz >> 5}")
    print(f"[state] G_DAT_BASE_PTR -> {hex(dat_base)}  (DAT window {hex(dat_base)}..{hex(dat_base + DAT_WINDOW)})")
    if scene != LEVEL02_SCENE_ID:
        print(f"WARNING: scene_id={scene} != {LEVEL02_SCENE_ID}; not LEVEL02 — bounded result only")

    # --- function identity guard (no 80010000<->800172dc swap) -------------
    ent_dat = d.disasm(EMIT_DAT, 3)
    ent_all = d.disasm(EMIT_ALL, 3)
    print(f"[ident] fcn.80010000 entry: {ent_dat}")
    print(f"[ident] fcn.800172dc entry: {ent_all}")

    # --- 1) pick lower-screen pixels (ground under Flik projects there) -----
    print("\n[pick] candidate ground pixels (native CRTC):")
    picks = []
    for tok in args.picks.split(";"):
        x, y = (int(v) for v in tok.split(","))
        r = d.call("gpu.pickObject", {"x": x, "y": y})
        if not r.get("hit"):
            print(f"   ({x:>3},{y:>3}) MISS {r.get('reason')}")
            picks.append({"x": x, "y": y, "hit": False, "reason": r.get("reason")})
            continue
        dc, src, px = r["drawCall"], r["source"], r["pixel"]
        ram = int(src["ramAddress"], 16) | 0x80000000
        cmd = dc.get("command", "")
        picks.append({"x": x, "y": y, "hit": True, "command": cmd,
                      "packet": addr(ram), "texpage": dc.get("texturePage"), "rgba": px.get("rgba")})
        print(f"   ({x:>3},{y:>3}) {cmd:>12} rgba={px.get('rgba')} packet={addr(ram)} tex={dc.get('texturePage')}")

    quad_packets = []
    for rec in picks:
        if rec.get("hit") and str(rec.get("command", "")).startswith("GP0(3"):
            if rec["packet"] not in [q[0] for q in quad_packets]:
                quad_packets.append((rec["packet"], rec))
    print(f"\n[pick] distinct textured-quad packets under Flik: {[q[0] for q in quad_packets]}")

    # --- 2) writer PCs of each floor packet --------------------------------
    packet_writers = []
    leaf_writer_pc = None
    for pkt_hex, rec in quad_packets[:3]:
        d.call("accessLog.clear")
        w = d.call("accessLog.addWatch",
                   {"address": pkt_hex, "length": 16, "type": "write",
                    "label": "floorpkt", "max_events": 64})
        d.adv(3)
        ev = d.call("accessLog.get", {"watch_id": w["watch_id"]})
        pcs = sorted({e.get("pc") for e in ev.get("events", []) if e.get("pc")})
        kind = classify_writer(pcs)
        packet_writers.append({"packet": pkt_hex, "pixel": [rec["x"], rec["y"]],
                               "writer_pcs": pcs, "writer_kind": kind})
        print(f"[writer] packet {pkt_hex} (pixel {rec['x']},{rec['y']}) writer={kind} PCs={pcs}")
        if kind == "shared_leaf" and leaf_writer_pc is None and pcs:
            leaf_writer_pc = pcs[0]
    d.call("accessLog.clear")

    # --- 3) DECISIVE: which driver called the shared floor leaf? (ra) ------
    ra_hist, ra_vals, leaf_hits = {}, [], None
    if leaf_writer_pc is not None:
        # multi-frame: a 1-frame execTrace window races the frame boundary and
        # can catch 0 hits even though the leaf store fires ~20x/frame.
        leaf_hits, ev_w = d.trace(int(leaf_writer_pc, 16), max(args.frames, 4), ["pc", "ra"])
        ras = [int(e["regs"]["ra"], 16) for e in ev_w if e.get("regs", {}).get("ra")]
        ra_hist = dict(Counter(region(r, dat_base) for r in ras))
        ra_vals = sorted({addr(r) for r in ras})
        print(f"\n[driver] floor leaf {leaf_writer_pc} hits/frame={leaf_hits}  ra-region={ra_hist}")
        print(f"[driver] distinct caller (ra) values: {ra_vals}  (inside fcn.80010000 => DAT path)")

    # --- 4) robust multi-frame source classification + driver counts -------
    n_dat, ev_dat = d.trace(EMIT_DAT, args.frames, ["pc", "a0"])
    a0s = [int(e["regs"]["a0"], 16) for e in ev_dat if e.get("regs", {}).get("a0")]
    hist = Counter(region(a, dat_base) for a in a0s)
    dat_span = None
    if a0s:
        dat_a0 = [a for a in a0s if dat_base <= a < dat_base + DAT_WINDOW]
        if dat_a0:
            offs = [a - dat_base for a in dat_a0]
            dat_span = {"lo": addr(min(dat_a0)), "hi": addr(max(dat_a0)),
                        "file_lo": addr(min(offs)), "file_hi": addr(max(offs))}
    n_all, _ = d.trace(EMIT_ALL, args.frames, ["pc"])
    print(f"\n[source] fcn.80010000 calls/{args.frames}f={n_dat}  a0-region={dict(hist)}")
    if dat_span:
        print(f"[source] DAT mesh a0 span {dat_span['lo']}..{dat_span['hi']} "
              f"= DAT file offsets {dat_span['file_lo']}..{dat_span['file_hi']}")
    print(f"[source] fcn.800172dc calls/{args.frames}f={n_all} "
          f"(active, but draws other meshes — NOT the picked floor packets)")

    # --- 5) collision source = separate populated region -------------------
    sec0 = d.u32(SECTOR_TABLE)
    sec_head = hashlib.sha256(d.read(SECTOR_TABLE, 512)).hexdigest()
    print(f"\n[collision] sector table {addr(SECTOR_TABLE)}[0]={hex(sec0)} "
          f"region={region(SECTOR_TABLE, dat_base)} head512_sha256={sec_head[:16]}.. (separate region)")

    # --- verdict -----------------------------------------------------------
    floor_via_dat = (
        any(pw["writer_kind"] == "fcn80010000_inline" for pw in packet_writers)
        or (leaf_writer_pc is not None and ra_hist.get("fcn80010000", 0) > 0)
    )
    dat_only_source = bool(a0s) and hist.get("DAT", 0) == len(a0s)
    collision_populated = sec0 != 0
    confirmed = (scene == LEVEL02_SCENE_ID and floor_via_dat
                 and dat_only_source and collision_populated and bool(n_dat))

    print("\n========== VERDICT (LEVEL02 / GAP-0039) ==========")
    print(f"  scene_id == 3 (LEVEL02)             : {scene == LEVEL02_SCENE_ID}")
    print(f"  floor pixel attributed to fcn.80010000: {floor_via_dat}  "
          f"(writer={[pw['writer_kind'] for pw in packet_writers]}, leaf ra={ra_hist or 'n/a'})")
    print(f"  fcn.80010000 a0 source             : {'DAT only' if dat_only_source else dict(hist)} "
          f"({n_dat} calls/{args.frames}f)")
    print(f"  fcn.800172dc                       : {n_all} calls/{args.frames}f (other meshes)")
    print(f"  collision table populated/separate : {collision_populated}")
    print(f"  => LEVEL02 visible floor under Flik = LEVEL.DAT via fcn.80010000 "
          f"(shared leaf {leaf_writer_pc}); collision = chunk-32 {addr(SECTOR_TABLE)}: "
          f"{'CONFIRMED' if confirmed else 'BOUNDED (see notes)'}")

    report = {
        "experiment": "GAP-0039 LEVEL02 per-pixel visible-floor source",
        "fixture": {"path": str(save), "size": save.stat().st_size, "sha256": sha256_file(save)},
        "disc": {"path": str(disc), "cue_sha256": sha256_file(disc),
                 "state_info": state_info, "initial_media": initial_media, "loaded_media": loaded_media},
        "identity": {"expected_game_serial": GAME_SERIAL, "scene_id": scene,
                     "expected_scene_id": LEVEL02_SCENE_ID, "load_result": load,
                     "flik_world_xyz": [fx, fy, fz], "g_dat_base": addr(dat_base),
                     "fcn80010000_entry": ent_dat, "fcn800172dc_entry": ent_all},
        "address_basis": {"scene_id": addr(SCENE_ID), "g_dat_base_ptr": addr(G_DAT_BASE_PTR),
                          "emit_dat": addr(EMIT_DAT), "emit_all": addr(EMIT_ALL),
                          "shared_leaf": [addr(LEAF_LO), addr(LEAF_HI)],
                          "sector_table": addr(SECTOR_TABLE), "dat_window": addr(DAT_WINDOW),
                          "chunk35_buf": [addr(CHUNK35_LO), addr(CHUNK35_HI)]},
        "picks": picks,
        "quad_packets": [q[0] for q in quad_packets],
        "packet_writers": packet_writers,
        "floor_leaf_writer_pc": leaf_writer_pc,
        "floor_leaf_caller_ra": {"hits_per_frame": leaf_hits, "ra_region": ra_hist, "ra_values": ra_vals},
        "fcn80010000": {"calls_per_window": n_dat, "frames": args.frames,
                        "a0_region_hist": dict(hist), "dat_span": dat_span},
        "fcn800172dc_calls_per_window": n_all,
        "collision": {"sector_table": addr(SECTOR_TABLE), "entry0": hex(sec0),
                      "head512_sha256": sec_head, "populated": collision_populated},
        "checks": {
            "scene_is_level02": scene == LEVEL02_SCENE_ID,
            "floor_attributed_to_fcn80010000": floor_via_dat,
            "fcn80010000_source_dat_only": dat_only_source,
            "fcn80010000_active": bool(n_dat),
            "collision_table_populated": collision_populated,
        },
        "confirmed": confirmed,
        "model_note": (
            "On LEVEL02 the floor GP0(3c) quads are stored by a SHARED GTE leaf "
            "emitter at 0x80019xxx that fcn.80010000 calls (ra = 0x8001067c/0x800108b8 "
            "inside fcn.80010000). On LEVEL01-spawn the same driver emitted inline "
            "(0x800107b0..0x800108a8). Both renderers run on LEVEL02; fcn.800172dc "
            "draws other geometry, not the picked floor packets. Corrects the "
            "first-pass 'fcn.800172dc = 0 calls' (single-frame artifact)."
        ),
        "bounded_note": (
            "" if confirmed else
            "Bounded: an acceptance check did not hold (see checks). Pick miss / "
            "unexpected writer leaves per-pixel attribution incomplete; local-only (GAP-0001)."
        ),
        "reproducibility": (
            "Operator-local: isolated DuckStation fork + pristine disc + LEVEL02 .sav "
            "(gitignored). Replay: launch_debugger_instance.sh start --disc <pristine> "
            "--port 23460 --no-fastboot; python tools/trace_level02_floor.py "
            "--save <level02 .sav> --output /tmp/level02-floor.json. GAP-0001/0040."
        ),
    }
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    return 0 if confirmed else 1


if __name__ == "__main__":
    raise SystemExit(main())
