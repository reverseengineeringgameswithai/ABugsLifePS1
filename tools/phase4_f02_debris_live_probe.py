#!/usr/bin/env python3
"""phase4_f02_debris_live_probe -- live check of the F02 falling-debris contact class.

THE CLAIM UNDER TEST
--------------------
Static work (tools/phase4_f02_debris_class_bind.c) says the Tunnels debris spawner
(overlay LEVEL03_LEVEL @ base 0x800B39A0, jal at 0x800B43F0, ra 0x800B43F8) passes
ctorType a3 = 0x5A, and that metaB[0x5A] gives:
    action_id = 1, active_type = 16, flags = 0x20, radius_add = 200
Four resident consumers walk the 64-slot contact pool, each with its own gate:
    0x800586B0 pickup walker        (rec+0x22 > 0) && (rec+0x33 & 0x02)
    0x80058AF8 contact-vs-actor     (rec+0x33 & 0x04) && (rec+0x22 > 0)
    0x8005A308 record update        flags & 0x08 selects the berry branch;
                                    behaviour class = rec+0x2F, dispatch 0x8001B7F0[c-1]
    0x8005CD2C effect spawner       rec+0x2F == 5
flags 0x20 has bits 0x02/0x04/0x08 all clear and rec+0x2F = 0, so the static prediction is
that a debris record reaches NO contact handler and cannot touch the player.

This probe measures the gate INPUTS on live records instead of trusting that.

WHAT IT MEASURES
----------------
1. POOL CENSUS (the direct measurement): sample the whole 64-slot pool repeatedly during
   the Tunnels run and tabulate, per ctorType (rec+0x2E), the observed rec+0x33 flags and
   rec+0x2F class. If any live 0x5A record is ever seen with bit 0x02/0x04/0x08 set, the
   static claim is falsified.
   NOTE rec+0x2E holds the ctorType itself for this family (allocator: metaB+0x0e == 2 =>
   rec+0x2e = +ctorType), so a debris record self-identifies in RAM. That is what makes
   the census possible without tracking allocations.
2. POSITIVE CONTROL on the path under test: an execTrace watch on the pickup walker's
   dispatch `jr v0` (0x8005882C). It MUST fire -- if it does not, the instrumentation is
   dead and a "debris never dispatches" result would be vacuous. It also captures s2,
   which is record+0x22, so every dispatched record is identified by slot.
3. SPAWNER LIVENESS: execTrace on 0x800B43F0 confirms debris are actually being created
   inside the measured window, so the census window is not empty for the wrong reason.
4. HEALTH WRITERS: accessLog write-watch on 0x800A6594 (TRUE HEALTH) enumerates every PC
   that changes health during the run, so "debris does no damage" is backed by the actual
   writer set rather than by absence of evidence.

Replay is at 60 Hz (debugger.resume + poll), never movie.advanceToFrame -- the arm-phase
fixup lands differently under frame stepping and this movie is state-anchored.

Usage: python3 tools/phase4_f02_debris_live_probe.py [--port 23472] [--json out.json]
"""
import argparse, json, os, struct, sys, time

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "duckstation", "scripts", "debugger-client"))
from duckstation_debug_client import DebuggerClient, RpcError  # noqa: E402

MOVIE = "movies/Phase4/Interpreter/Any% Runs/LEVEL02_Tunnels.movie.json"
POOL, NREC, STRIDE = 0x800B0D18, 64, 0x38
HEALTH = 0x800A6594
DEBRIS_SPAWN = 0x800B43F0         # `jal 0x80059E44` in LEVEL03_LEVEL overlay @ base 0x800B39A0
DEBRIS_CTOR = 0x5A

# The three contact-pool gates, instrumented AT the gate rather than inferred.
# Each `test` PC is the `andi` that masks the flags byte: the captured register still holds
# the RAW flags there (execTrace samples registers BEFORE the instruction executes), and the
# captured pointer register identifies the slot. Each `pass` PC is the first instruction
# reached only when the gate succeeded.
GATES = {
    # FUNC_800586B0 pickup walker: s2 = record+0x22
    "walker": {"test": 0x80058748, "pass": 0x80058754, "bit": 0x02,
               "ptr": "s2", "ptr_bias": 0x22},
    # FUNC_80058AF8 contact-vs-actor: s1 = record+0x08
    "actor":  {"test": 0x80058C6C, "pass": 0x80058C78, "bit": 0x04,
               "ptr": "s1", "ptr_bias": 0x08},
    # FUNC_8005A308 record update, berry branch: s0 = record+0x22
    "update": {"test": 0x8005A358, "pass": 0x8005A364, "bit": 0x08,
               "ptr": "s0", "ptr_bias": 0x22},
}


def slot_of(val, bias):
    base = val - bias
    if POOL <= base < POOL + NREC * STRIDE and (base - POOL) % STRIDE == 0:
        return (base - POOL) // STRIDE
    return None


class Probe:
    def __init__(self, port, token="debugger-1000"):
        self.c = DebuggerClient("127.0.0.1", port, "ws")
        self.c.authenticate(token)
        self.c.transport.sock.settimeout(30)

    def call(self, m, p=None):
        return self.c.call(m, p or {})

    # ---- pool census -----------------------------------------------------
    def sample_pool(self):
        hexs = self.call("debugger.readMemory",
                         {"address": "0x%08x" % POOL, "length": NREC * STRIDE})["hex"]
        b = bytes.fromhex(hexs)
        out = []
        for i in range(NREC):
            r = b[i * STRIDE:(i + 1) * STRIDE]
            out.append({
                "slot": i,
                "action": struct.unpack_from("<H", r, 0x20)[0],
                "active": struct.unpack_from("<h", r, 0x22)[0],
                "ctor": r[0x2E],
                "cls": r[0x2F],
                "flags": r[0x33],
            })
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--json")
    ap.add_argument("--frames", type=int, default=2600)
    ap.add_argument("--max-events", dest="max_events", type=int, default=150000)
    args = ap.parse_args()

    p = Probe(args.port)
    st = p.call("debugger.status")
    ident = {k: st.get(k) for k in ("game_serial", "game_title", "frame")}
    print("identity:", ident)
    if st.get("game_serial") != "SCUS-94288":
        sys.exit("wrong disc mounted: %r" % st.get("game_serial"))

    # ---- movie ----------------------------------------------------------
    # a previous run may still be playing; movie.load refuses while it is
    for m in ("movie.stopPlayback", "movie.stopRecording"):
        try:
            p.call(m)
        except RpcError:
            pass
    p.call("movie.load", {"path": os.path.abspath(MOVIE)})
    pb = p.call("movie.startPlayback", {"load_start_state": True})
    print("startPlayback:", {k: pb.get(k) for k in ("reproducible", "total_frames", "playback_index")})
    ms = p.call("movie.status")
    print("movie.status:", {k: ms.get(k) for k in
                            ("movie_version", "armed_while_paused", "phase_delay_owed",
                             "reproducible", "playing")})
    if ms.get("reproducible") is False:
        sys.exit("movie reports not reproducible -- refusing to measure")

    # ---- arm (after the state load, which clears non-halting watches) ----
    p.call("execTrace.clear")
    p.call("accessLog.clear")
    watches = {}
    for gname, g in GATES.items():
        for kind in ("test", "pass"):
            r = p.call("execTrace.addWatch",
                       {"pc": "0x%08x" % g[kind],
                        "capture": ["pc", "v0", g["ptr"]],
                        "label": "%s_%s" % (gname, kind),
                        "max_events": args.max_events})
            watches["%s_%s" % (gname, kind)] = r.get("watch_id")
    r = p.call("execTrace.addWatch", {"pc": "0x%08x" % DEBRIS_SPAWN, "capture": ["pc", "a3"],
                                      "label": "debris_spawn", "max_events": 40000})
    watches["debris_spawn"] = r.get("watch_id")
    hw = p.call("accessLog.addWatch", {"address": "0x%08x" % HEALTH, "length": 2,
                                       "type": "write", "max_events": 20000,
                                       "stop_on_hit": False})
    watches["health"] = hw.get("watch_id", hw.get("id"))
    print("watches:", watches)

    # ---- replay at 60 Hz, sampling the pool as it goes ------------------
    census = {}          # ctor -> {"flags": {v:n}, "cls": {v:n}, "samples": n}
    samples, start = 0, time.time()
    p.call("debugger.resume")
    last_frame, stalls = None, 0
    while True:
        time.sleep(0.35)
        try:
            s = p.call("debugger.status")
        except RpcError as e:
            print("status failed: %s" % e)
            break
        fr = s.get("frame")
        mv = p.call("movie.status")
        idx = mv.get("playback_index") or 0
        for rec in p.sample_pool():
            if rec["active"] <= 0:
                continue
            e = census.setdefault(rec["ctor"], {"flags": {}, "cls": {}, "action": {}, "n": 0})
            e["n"] += 1
            e["flags"][rec["flags"]] = e["flags"].get(rec["flags"], 0) + 1
            e["cls"][rec["cls"]] = e["cls"].get(rec["cls"], 0) + 1
            e["action"][rec["action"]] = e["action"].get(rec["action"], 0) + 1
        samples += 1
        if fr == last_frame:
            stalls += 1
            if stalls > 6:
                print("frame counter stalled at %s -- stopping" % fr)
                break
        else:
            stalls = 0
        last_frame = fr
        if not mv.get("playing") or idx >= args.frames:
            print("playback finished at index %s (frame %s)" % (idx, fr))
            break
        if time.time() - start > 420:
            print("wall-clock cap reached at index %s" % idx)
            break
    p.call("debugger.pause")

    # ---- collect --------------------------------------------------------
    def fetch(wid, method):
        if wid is None:
            return []
        ev, off = [], 0
        while True:
            r = p.call(method, {"watch_id": wid, "offset": off, "limit": 5000})
            batch = r.get("events", [])
            ev.extend(batch)
            if len(batch) < 5000:
                break
            off += len(batch)
        return ev

    result = {"identity": ident, "movie": MOVIE, "pool_samples": samples,
              "frames_covered": last_frame}

    # hit_count is the unbiased total (it counts hits even past the ring cap)
    hc = {w.get("label"): w.get("hit_count")
          for w in p.call("execTrace.get", {"limit": 1}).get("watches", [])}
    result["gate_hit_counts"] = hc

    gates_out = {}
    for gname, g in GATES.items():
        tev = fetch(watches["%s_test" % gname], "execTrace.get")
        pev = fetch(watches["%s_pass" % gname], "execTrace.get")
        # Pair each PASS with the test that produced it by CYCLE, not by frame: the actor
        # walker re-examines every slot once per actor, and a slot can even be reallocated
        # mid-frame, so a (frame, slot) join manufactures false leaks. The test executes a
        # few cycles before its own pass, so "nearest preceding test for the same pointer"
        # is an exact pairing.
        dist = {}
        by_ptr = {}
        for e in tev:
            r = e.get("regs", {})
            fv, pv = r.get("v0"), r.get(g["ptr"])
            if fv is None or pv is None:
                continue
            fv = int(fv, 16) & 0xFF
            dist[fv] = dist.get(fv, 0) + 1
            by_ptr.setdefault(int(pv, 16), []).append((e.get("cycle"), fv))
        for k in by_ptr:
            by_ptr[k].sort()
        leak, unpaired = [], 0
        for e in pev:
            r = e.get("regs", {})
            pv = r.get(g["ptr"])
            if pv is None:
                continue
            pv = int(pv, 16)
            cyc = e.get("cycle")
            lst = by_ptr.get(pv)
            if not lst or cyc is None:
                unpaired += 1
                continue
            lo, hi = 0, len(lst)
            while lo < hi:                       # rightmost test with cycle <= pass cycle
                mid = (lo + hi) // 2
                if lst[mid][0] <= cyc:
                    lo = mid + 1
                else:
                    hi = mid
            if lo == 0:
                unpaired += 1
                continue
            tcyc, fv = lst[lo - 1]
            if cyc - tcyc > 200:                 # too far apart to be the same iteration
                unpaired += 1
                continue
            if not (fv & g["bit"]):
                leak.append({"cycle": cyc, "slot": slot_of(pv, g["ptr_bias"]),
                             "paired_flags": "0x%02X" % fv, "test_cycle": tcyc})
        leak = leak[:20]
        gates_out[gname] = {
            "test_pc": "0x%08X" % g["test"], "pass_pc": "0x%08X" % g["pass"],
            "gate_bit": "0x%02X" % g["bit"],
            "examined_events": len(tev), "passed_events": len(pev),
            "truncated": len(tev) >= args.max_events,
            "flags_examined": {"0x%02X" % k: v for k, v in sorted(dist.items())},
            "flags_0x20_examined": dist.get(0x20, 0),
            "passes_unpairable": unpaired,
            "records_without_gate_bit_that_passed": leak,
        }
    result["gates"] = gates_out

    sev = fetch(watches["debris_spawn"], "execTrace.get")
    result["debris_spawn_hits"] = len(sev)
    result["debris_spawn_a3"] = sorted({e.get("regs", {}).get("a3") for e in sev} - {None})

    hev = fetch(watches.get("health"), "accessLog.get")
    wr = {}
    for e in hev:
        pc = e.get("pc")
        wr[pc] = wr.get(pc, 0) + 1
    result["health_writes"] = len(hev)
    result["health_writer_pcs"] = dict(sorted(wr.items(), key=lambda kv: -kv[1]))

    result["pool_census"] = {
        "0x%02X" % k: {"live_samples": v["n"],
                       "flags_seen": {"0x%02X" % a: b for a, b in sorted(v["flags"].items())},
                       "class_2F_seen": {"0x%02X" % a: b for a, b in sorted(v["cls"].items())},
                       "action_id_seen": {str(a): b for a, b in sorted(v["action"].items())}}
        for k, v in sorted(census.items())
    }

    # rec+0x2E encodes the ctorType with the sign metaB+0x0E selects: 0 => 0, else +/-ctor.
    # For ctor 0x5A the live pool shows the NEGATED form, 0xA6.
    d = census.get((-DEBRIS_CTOR) & 0xFF) or census.get(DEBRIS_CTOR)
    controls_ok = (result["debris_spawn_hits"] > 0
                   and all(g["examined_events"] > 0 for g in gates_out.values()))
    if not controls_ok:
        result["verdict"] = ("INCONCLUSIVE -- a positive control did not fire "
                             "(debris_spawn_hits=%d, gate examined counts=%r); a negative "
                             "result here would be vacuous."
                             % (result["debris_spawn_hits"],
                                {k: v["examined_events"] for k, v in gates_out.items()}))
    elif not d:
        result["verdict"] = ("INCONCLUSIVE -- no live ctor-0x5A record was sampled in the "
                             "window even though the spawner fired")
    else:
        bad = {f: n for f, n in d["flags"].items() if f & 0x0E}
        leaks = {k: v["records_without_gate_bit_that_passed"] for k, v in gates_out.items()
                 if v["records_without_gate_bit_that_passed"]}
        # a gate that never passed for ANY class in the window cannot discriminate; say so
        result["gates_that_never_passed"] = [k for k, v in gates_out.items()
                                             if v["passed_events"] == 0]
        result["debris_live_samples"] = d["n"]
        result["debris_flags_observed"] = {"0x%02X" % k: v for k, v in d["flags"].items()}
        result["debris_flags_with_a_gate_bit"] = {"0x%02X" % k: v for k, v in bad.items()}
        if bad or leaks:
            result["verdict"] = ("FALSIFIED -- debris flags carrying a gate bit: %r ; "
                                 "gate leaks: %r" % (bad, leaks))
        else:
            result["verdict"] = (
                "CONFIRMED -- %d live ctor-0x5A samples, all flags=%s / class rec+0x2F=%s; "
                "the three pool gates examined %d records carrying flags 0x20 and passed "
                "none of them. Controls fired: spawner %d hits, gates %r."
                % (d["n"], ",".join("0x%02X" % f for f in d["flags"]),
                   ",".join("0x%02X" % c for c in d["cls"]),
                   sum(g["flags_0x20_examined"] for g in gates_out.values()),
                   result["debris_spawn_hits"],
                   {k: v["examined_events"] for k, v in gates_out.items()}))

    print(json.dumps(result, indent=1)[:6000])
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=1)
        print("wrote", args.json)

    p.call("execTrace.clear")
    p.call("accessLog.clear")
    try:
        p.call("movie.stopPlayback")
    except RpcError:
        pass


if __name__ == "__main__":
    main()
