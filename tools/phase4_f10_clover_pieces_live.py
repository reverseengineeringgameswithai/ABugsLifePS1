#!/usr/bin/env python3
"""F10: verify the piece table and the death gate LIVE, not just from the image.

The first F10 pass verified the objective law against the operator's Any% run: the
mask took five distinct bits and the latch fired at the pinned PC. The follow-up pass
that added the PIECE TABLE and named the 0x800A6590 bit-0x04 gate was **static only**,
and the operator asked the right question -- three claims this session that were
static-only turned out to be wrong in ways only play could catch.

So this checks the two additions against the same recording:

  1. THE PIECE TABLE. A halting breakpoint on the mask store 0x800B4244 stops the
     core at each collection. At that instant, read Flik's position, the bit being
     OR'd, and all five records. The static claim is that record N's first three
     words are the position of the piece whose bit is 1<<N -- so at each hit, the
     record matching the bit just set must be the one Flik is standing next to, and
     its shifted squared distance must be < 1600. Any other record being closer, or
     the matching one being far, refutes the mapping.

  2. THE DEATH GATE. Watch 0x800A6590. If bit 0x04 is ever set during the run, the
     static claim says it is the death path doing it. Whether the operator died in
     this particular run is not known in advance; if they did not, that is reported
     as NOT EXERCISED rather than quietly dropped.

⚠️ Breakpoint addresses must be PHYSICAL (addr & 0x1FFFFFFF) -- a KSEG0 address is
accepted and silently never fires. Halting breakpoints do NOT desync the run, but
they stop the core MID-FRAME, so the reads here are register/RAM reads only; no
frame-boundary snapshot is compared.

⚠️⚠️ AND: an execute breakpoint inside the shared region-A overlay window fires for
WHATEVER OVERLAY happens to be resident there. 0x800B4244 is this stage's mask store,
but the same physical address holds unrelated code in every other overlay, and the
first version of this tool dutifully recorded those hits -- with the mask reading 0
and every record reading (0,0,0), because scene 7 had not loaded yet. Every hit must
be gated on the scene id, or the capture is of some other level's code.

    tools/phase4_f10_clover_pieces_live.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("~/Downloads/ABL")
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

MOVIE = ROOT / "movies/Phase4/Interpreter/Any% Runs/LEVEL10_cloverforest.movie.json"
PORT = 23911
MASK_STORE_PC = 0x800B4244          # sw v1, 0x800B5774 -- the collect commit
MASK, POWER = 0x800B5774, 0x800A6590
FLIK = (0x800A6500, 0x800A6504, 0x800A6508)
RECORDS = [0x800B56D8 + n * 0x18 for n in range(5)]


def s32(v):
    return v - 0x100000000 if v & 0x80000000 else v


def sq(ax, ay, az, bx, by, bz):
    dx, dy, dz = (ax - bx) >> 8, (ay - by) >> 8, (az - bz) >> 8
    return dx * dx + dy * dy + dz * dz


def main() -> int:
    cfg = Path("/tmp/abl-scratch/f10-live-%d/cfg" % PORT)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    log = cfg.parent / "launch.log"
    with log.open("w") as fh:
        subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                        "--execution-mode", "Interpreter", "--config-dir", str(cfg),
                        "--port", str(PORT), "--token", "debugger-1000",
                        "--disc", str(ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")],
                       cwd=str(ROOT), stdout=fh, stderr=fh, check=False)
    t = log.read_text()
    assert "READY" in t, t[-700:]
    pid = t.split("pid=")[1].split()[0]

    out = {
        "row": "F10_clover_forest",
        "question": "are the piece table and the 0x04 death gate true of the RUN?",
        "movie": MOVIE.name,
        "static_claims": {
            "piece_table": "record N at 0x800B56D8 + N*0x18; its first three words are "
                           "the position of the piece whose bit is 1<<N",
            "death_gate": "0x800A6590 bit 0x04 is set only by the death path 0x8004A8E0",
        },
    }
    hits = []
    try:
        c = DebuggerClient("127.0.0.1", PORT, "ws")
        c.authenticate("debugger-1000")
        c.transport.sock.settimeout(1800)
        st = c.call("movie.load", {"path": str(MOVIE.resolve())})
        out["frames"] = st.get("frame_count")
        assert c.call("movie.startPlayback", {"load_start_state": True}).get("playing")

        c.call("accessLog.clear", {})
        c.call("accessLog.addWatch", {"address": "0x%08x" % POWER, "length": 2,
                                      "type": "write", "max_events": 200000})
        # ⚠️ PHYSICAL address, or it silently never fires
        bp = c.call("debugger.addBreakpoint",
                    {"address": "0x%08x" % (MASK_STORE_PC & 0x1FFFFFFF),
                     "type": "execute"})
        out["breakpoint"] = {"requested_pc": "0x%08X" % MASK_STORE_PC,
                             "physical": "0x%08X" % (MASK_STORE_PC & 0x1FFFFFFF),
                             "id": bp.get("id")}

        def rd(a, n):
            return bytes.fromhex(c.call("debugger.readMemory",
                                        {"address": "0x%08x" % a, "length": n})["hex"])

        began = time.time()
        while len(hits) < 5 and time.time() - began < 2000:
            c.call("debugger.resume", {})
            ev = c.wait_event(lambda e: e.get("event") in ("breakpointHit", "paused"),
                              timeout=600.0)
            if not ev:
                break
            # gate on the scene, or this is another overlay's code at the same
            # physical address
            scene = int.from_bytes(rd(0x80082504, 4), "little")
            if scene != 7:
                out.setdefault("foreign_overlay_hits", 0)
                out["foreign_overlay_hits"] += 1
                continue
            # ⚠️ ASK THE CPU which record this is, do not infer it from a table of
            # addresses I believe in. s0 holds the record pointer (0x800B3FD8
            # `addu s0,a0,zero`) and s2 holds the bit (0x800B4004 `addu s2,a2,zero`).
            # An earlier revision compared Flik against all five ASSUMED record
            # addresses and "refuted" a claim that the registers confirm.
            regs = c.call("debugger.getRegisters").get("registers_hex", {})
            def reg(name):
                v = regs.get(name)
                return int(str(v), 16) if v is not None else None
            s0, s2 = reg("s0"), reg("s2")
            fx, fy, fz = (s32(int.from_bytes(rd(a, 4), "little")) for a in FLIK)
            mask = int.from_bytes(rd(MASK, 4), "little")
            rec = None
            if s0 and 0x800B0000 <= s0 < 0x800B5788:
                wds = rd(s0, 12)
                rec = tuple(s32(int.from_bytes(wds[k*4:k*4+4], "little")) for k in range(3))
            hits.append({
                "mask_before": mask, "flik": [fx, fy, fz],
                "s0_record_ptr": ("0x%08X" % s0) if s0 else None,
                "s2_bit": ("0x%X" % s2) if s2 is not None else None,
                "record_xyz": rec,
                "d2_to_its_own_record": sq(fx, fy, fz, *rec) if rec else None,
                "scene": scene,
                "record_index_from_s0": (((s0 - 0x800B56D8) // 0x18)
                                         if (s0 and 0x800B56D8 <= s0 <= 0x800B5738
                                             and (s0 - 0x800B56D8) % 0x18 == 0)
                                         else None),
            })
        c.call("debugger.removeBreakpoint", {"id": bp.get("id")})

        ev, off = [], 0
        while True:
            p = c.call("accessLog.get", {"offset": off, "limit": 10000})
            g = p.get("events") or []
            ev.extend(g)
            if len(g) < 10000:
                break
            off += len(g)
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    out["hits"] = hits
    # The claim under test: the record s0 points at is the one Flik is next to, its
    # index matches the bit in s2, and the distance is inside the 1600 radius.
    mapping = []
    for h in hits:
        idx = h["record_index_from_s0"]
        bit = int(h["s2_bit"], 16) if h["s2_bit"] else None
        if idx is None or idx < 0:
            mapping.append({"s0": h["s0_record_ptr"], "record_index": None,
                            "bit": h["s2_bit"], "bit_matches_index": False,
                            "d2": h["d2_to_its_own_record"], "inside_1600": False,
                            "mask_before": hex(h["mask_before"])})
            continue
        mapping.append({
            "s0": h["s0_record_ptr"], "record_index": idx, "bit": h["s2_bit"],
            "bit_matches_index": (bit == (1 << idx)) if (bit is not None and idx is not None) else None,
            "d2": h["d2_to_its_own_record"],
            "inside_1600": (h["d2_to_its_own_record"] is not None
                            and h["d2_to_its_own_record"] < 1600),
            "mask_before": hex(h["mask_before"]),
        })
    out["piece_mapping_observed"] = mapping
    out["piece_table_confirmed"] = (
        len(mapping) == 5
        and all(m["bit_matches_index"] for m in mapping)
        and all(m["inside_1600"] for m in mapping)
        and sorted(m["record_index"] for m in mapping) == [0, 1, 2, 3, 4])

    pw = []
    for e in ev:
        a = int(str(e.get("address", "0")), 16) & 0x1FFFFFFF | 0x80000000
        if POWER <= a < POWER + 2:
            pw.append({"f": e.get("frame"),
                       "pc": str(e.get("instruction_pc") or e.get("pc") or "").lower(),
                       "v": e.get("new_value")})
    out["power_word_writes"] = pw[:60]
    # ⚠️ A write whose RESULT has bit 0x04 set is not the same as a write that SETS
    # it -- once set, every later write preserving it matches. Only 0->1 transitions
    # answer "who sets it". The first version of this filter did not distinguish
    # them and reported seven "setters".
    set04, prevv = [], 0
    for x in pw:
        v = x["v"] or 0
        if (v & 0x04) and not (prevv & 0x04):
            set04.append(x)
        prevv = v
    out["bit04_set_events"] = set04[:20]
    out["bit04_setter_pcs"] = sorted({x["pc"] for x in set04})
    out["death_gate_exercised"] = bool(set04)

    (ROOT / "analysis/phase4_f10_clover_pieces_live.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("frames", "breakpoint", "piece_mapping_observed",
                       "distinct_records_touched", "all_hits_inside_radius",
                       "piece_table_confirmed", "death_gate_exercised",
                       "bit04_setter_pcs")}, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
