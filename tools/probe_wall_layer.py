#!/usr/bin/env python3
"""tools/probe_wall_layer.py -- identify WHICH data draws LEVEL01's cliff/wall masses.

Chunk 35 was long believed to be the wall layer. Editing it on disc and cold-booting falsified that
in the most direct way available: the changed pixels trace Flik's silhouette, never terrain
(2026-08-11, docs/CHUNK35_MASTER_MESH_DECODE.md). So the wall layer is unidentified, and it is the
one layer a Tier-3 replacement level still cannot author.

This asks the screen instead of the notes: cold boot, turn the camera onto the cliff, then sweep
`gpu.pickObject` over a grid of native-CRTC pixels and cluster the hits by what actually drew them
(GP0 command, texture page, CLUT, and `source.ramAddress`). Whatever draws the cliff pixels names
the layer.

Deliberately non-mutating and CPU-hook-free: pickObject, captureFrame and reads only -- no
accessLog/execTrace, which P52 recorded as perturbing frame pacing on this game.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import struct
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCK = os.path.expanduser("~/duckstation")
sys.path.insert(0, os.path.join(DUCK, "scripts", "debugger-client"))

MOVIE = os.path.join(ROOT, "flik_to_level01_stall.mv.movie.json")
FORK_LAUNCHER = os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh")
REPRO_LAUNCHER = os.path.join(ROOT, "tools/launch_repro_playback.sh")
FLIK_X = 0x800A6500
LEVEL01_X_MIN = 50000

# Known runtime bases, so a picked ramAddress can be attributed instead of guessed.
KNOWN = [
    ("chunk-32 collision live base", 0x800C1688, 0x40000),
    ("chunk-35 runtime render quads (the old 'wall' buffer)", 0x8012C1D0, 0x4000),
]


def connect(port, token):
    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", port, "ws")
    c.authenticate(token)
    try:
        c.transport.sock.settimeout(180)
    except Exception:
        pass
    return c


def rd32(c, addr):
    h = c.call("debugger.readMemory", {"address": "0x%08x" % addr, "length": 4})["hex"]
    return struct.unpack("<i", bytes.fromhex(h))[0]


def boot(c):
    c.call("emulator.setTurbo", {"enabled": True})
    c.call("debugger.reset", {})
    c.call("movie.load", {"path": MOVIE})
    c.call("movie.startPlayback", {})
    for _ in range(75):
        if rd32(c, FLIK_X) > LEVEL01_X_MIN:
            break
        c.call("emulator.advanceFrames", {"frames": 300})
    c.call("emulator.advanceFrames", {"frames": 8})
    try:
        c.call("movie.stopPlayback", {})
    except Exception:
        pass
    c.call("emulator.setTurbo", {"enabled": False})
    c.call("emulator.clearControllerState", {"port": 0})


def turn_to_cliff(c, down_frames, l1_frames, settle):
    """The recorded way to put LEVEL01's cliff on screen (work-order reproduction note)."""
    c.call("emulator.pressButton", {"button": "Down", "frames": down_frames, "port": 0,
                                    "release_after": True})
    c.call("emulator.advanceFrames", {"frames": down_frames + 2})
    c.call("emulator.pressButton", {"button": "L1", "frames": l1_frames, "port": 0,
                                    "release_after": True})
    c.call("emulator.advanceFrames", {"frames": l1_frames + settle})


def frame_bounds(c):
    """Discover the native CRTC extent from pickObject's own outside_frame reason."""
    w = h = 0
    for x in range(0, 1024, 8):
        if c.call("gpu.pickObject", {"x": x, "y": 0}).get("reason") == "outside_frame":
            w = x
            break
    for y in range(0, 1024, 8):
        if c.call("gpu.pickObject", {"x": 0, "y": y}).get("reason") == "outside_frame":
            h = y
            break
    return w, h


def attribute(addr_hex):
    if not addr_hex:
        return "(no ramAddress -- arrived via GP0 MMIO)"
    a = int(addr_hex, 16)
    for name, base, size in KNOWN:
        if base <= a < base + size:
            return f"{name} (+0x{a - base:x})"
    return "unattributed"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--disc", default=os.path.join(ROOT, "Disney-Pixar A Bug's Life (v1.0).cue"))
    ap.add_argument("--config-dir", default="/tmp/dsrepro-wall")
    ap.add_argument("--port", type=int, default=23468)
    ap.add_argument("--token", default="debugger-wall")
    ap.add_argument("--down-frames", type=int, default=2)
    ap.add_argument("--l1-frames", type=int, default=40)
    ap.add_argument("--settle", type=int, default=90)
    ap.add_argument("--step", type=int, default=16)
    ap.add_argument("--png", default=os.path.join(ROOT, "build/wall_layer_probe.png"))
    ap.add_argument("--out-json", default=os.path.join(ROOT, "build/wall_layer_probe.json"))
    ap.add_argument("--causality", action="store_true",
                    help="arm gpu.causality AFTER the movie stops (arm-late), then traceCausality on\n                         the cliff pixels to recover the submitting instruction PC / call stack")
    ap.add_argument("--cliff", nargs=4, type=int, default=[150, 380, 20, 105],
                    metavar=("X0", "X1", "Y0", "Y1"), help="native-CRTC box to trace as the cliff")
    ap.add_argument("--wall-clut-x", type=int, default=976,
                    help="VRAM CLUT X of the wall palette; 976 -> word (255<<6)|61 = 0x3FFD")
    ap.add_argument("--writer", action="store_true",
                    help="write-watch a wall packet address and report who BUILDS it. Causality on a\n                         DMA-submitted draw only names the DrawOTag kick, not the geometry builder.")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    subprocess.run([FORK_LAUNCHER, "stop", "--config-dir", a.config_dir], capture_output=True)
    r = subprocess.run([REPRO_LAUNCHER, "--config-dir", a.config_dir, "--port", str(a.port),
                        "--token", a.token, "--disc", os.path.abspath(a.disc)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[wall] launch failed:\n{r.stdout}{r.stderr}")
    print(f"[wall] {r.stdout.strip()}")
    time.sleep(2)

    report = {"disc": os.path.abspath(a.disc)}
    try:
        c = connect(a.port, a.token)
        media = c.call("emulator.getMediaInfo", {})
        report["media"] = media.get("path") or media.get("filename")
        print(f"[wall] media {report['media']}")
        boot(c)
        # ARM LATE: the boot movie is a CachedInterpreter recording, so anything that forces
        # Interpreter would desync it. Playback has stopped by here, and the camera turn below is
        # driven by pressButton rather than the movie, so arming now is safe.
        if a.causality:
            c.call("gpu.causality.start", {})
            print("[wall] gpu.causality armed AFTER movie stop (arm-late)")
        turn_to_cliff(c, a.down_frames, a.l1_frames, a.settle)
        c.call("emulator.captureFrame", {"path": os.path.abspath(a.png)})
        c.call("emulator.advanceFrames", {"frames": 1})
        # pause so draw state and the picked frame describe the same instant
        try:
            c.call("debugger.pause", {})
        except Exception:
            pass
        w, h = frame_bounds(c)
        print(f"[wall] native CRTC frame {w}x{h}; sweeping every {a.step}px")
        report["frame"] = {"w": w, "h": h}

        cells = []
        clusters = collections.Counter()
        for y in range(0, h, a.step):
            for x in range(0, w, a.step):
                p = c.call("gpu.pickObject", {"x": x, "y": y})
                if not p.get("hit"):
                    cells.append({"x": x, "y": y, "miss": p.get("reason")})
                    clusters[("MISS", p.get("reason"), "", "")] += 1
                    continue
                dc = p.get("drawCall", {}) or {}
                src = p.get("source", {}) or {}
                tex = p.get("texture", {}) or {}
                key = (dc.get("command"), f"page({tex.get('pageX')},{tex.get('pageY')})",
                       f"clut({tex.get('clutX')},{tex.get('clutY')})",
                       attribute(src.get("ramAddress")))
                clusters[key] += 1
                cells.append({"x": x, "y": y, "cmd": dc.get("command"),
                              "ram": src.get("ramAddress"),
                              "pageX": tex.get("pageX"), "pageY": tex.get("pageY"),
                              "clutX": tex.get("clutX"), "clutY": tex.get("clutY"),
                              "rgba": (p.get("pixel", {}) or {}).get("rgba")})
        report["cells"] = cells
        report["clusters"] = [{"count": n, "command": k[0], "page": k[1], "clut": k[2],
                               "attribution": k[3]} for k, n in clusters.most_common()]
        print(f"[wall] {len(cells)} picks -> {len(clusters)} distinct draw signatures:")
        for row in report["clusters"]:
            print(f"   {row['count']:5d}  {str(row['command']):<22} {row['page']:<16} "
                  f"{row['clut']:<16} {row['attribution']}")
        if a.causality:
            # Trace the wall-CLUT pixels the sweep ACTUALLY found, not a fixed box: arming
            # causality shifts CPU timing, so the camera swing does not land identically and a
            # hard-coded cliff rectangle traces empty air (it did, on the first attempt).
            targets = [(cc["x"], cc["y"]) for cc in cells
                       if cc.get("clutX") == a.wall_clut_x and cc.get("clutY") == 255]
            print(f"[wall] {len(targets)} sweep cells carry the wall CLUT "
                  f"(clutX={a.wall_clut_x}, clutY=255)")
            pcs = collections.Counter()
            stacks = collections.Counter()
            traced = 0
            for (x, y) in targets:
                    t = c.call("gpu.traceCausality", {"x": x, "y": y})
                    if not t.get("hit"):
                        continue
                    cc = t.get("cpuCausality", {}) or {}
                    if not cc.get("available"):
                        continue
                    traced += 1
                    pcs[cc.get("instruction_pc")] += 1
                    st = cc.get("call_stack") or []
                    # call_stack frames are objects; key on their PC so they stay hashable
                    def _fr(f):
                        if isinstance(f, dict):
                            return str(f.get("pc") or f.get("address") or f.get("function") or f)
                        return str(f)
                    stacks[tuple(_fr(f) for f in st[:6])] += 1
            report["causality"] = {
                "traced_wall_pixels": traced,
                "instruction_pcs": [{"pc": k, "count": v} for k, v in pcs.most_common()],
                "call_stacks": [{"stack": list(k), "count": v} for k, v in stacks.most_common(4)],
            }
            print(f"[wall] traced {traced} wall-CLUT pixels")
            for k, v in pcs.most_common(8):
                print(f"   submitting PC {k}  x{v}")
            for k, v in stacks.most_common(3):
                print(f"   stack x{v}: {' <- '.join(str(f) for f in k)}")
            try:
                c.call("gpu.causality.stop", {})
            except Exception:
                pass
        if a.writer:
            # pickObject's source.ramAddress is the assembled GP0 PACKET in the 0x801Dxxxx arena.
            # Whoever WROTE that packet is the wall geometry builder -- accessLog is the "who wrote
            # this" tool. Safe here: the movie has stopped, so forcing Interpreter desyncs nothing.
            wall_cells = [cc for cc in cells
                          if cc.get("clutX") == a.wall_clut_x and cc.get("clutY") == 255
                          and cc.get("ram")]
            floor_cells = [cc for cc in cells
                           if cc.get("clutX") == 960 and cc.get("clutY") == 255 and cc.get("ram")]
            report["writers"] = {}
            for label, sel in (("wall_clut_0x3ffd", wall_cells), ("floor_clut_0x3ffc", floor_cells)):
                if not sel:
                    print(f"[wall] no cells for {label}")
                    continue
                addr = int(sel[0]["ram"], 16) | 0x80000000
                c.call("accessLog.clear", {})
                wid = c.call("accessLog.addWatch", {"address": "0x%08x" % addr, "length": 32,
                                                    "type": "write", "label": label})["watch_id"]
                try:
                    c.call("debugger.resume", {})
                except Exception:
                    pass
                ev = c.call("accessLog.run", {"frames": 4})
                pcs = collections.Counter()
                for e in ev.get("events", []):
                    pcs[e.get("pc")] += 1
                c.call("accessLog.removeWatch", {"watch_id": wid})
                report["writers"][label] = {
                    "packet_addr": "0x%08x" % addr,
                    "events": len(ev.get("events", [])),
                    "writer_pcs": [{"pc": k, "count": v} for k, v in pcs.most_common(8)],
                }
                print(f"[wall] {label} packet 0x{addr:08x}: {len(ev.get('events', []))} writes")
                for k, v in pcs.most_common(6):
                    print(f"       writer PC {k}  x{v}")
        try:
            c.call("debugger.resume", {})
        except Exception:
            pass
    finally:
        if not a.keep:
            subprocess.run([FORK_LAUNCHER, "stop", "--config-dir", a.config_dir],
                           capture_output=True)
    json.dump(report, open(a.out_json, "w"), indent=1)
    print(f"[wall] frame -> {a.png}\n[wall] report -> {a.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
