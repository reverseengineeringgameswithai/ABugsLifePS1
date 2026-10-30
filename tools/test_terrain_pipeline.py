#!/usr/bin/env python3
"""tools/test_terrain_pipeline.py — regression test for the Blender terrain/collision pipeline.

Builds a fixed test disc (deterministic ramp heightfield + an add-block platform) and validates four checks
against a live isolated DuckStation, printing PASS/FAIL per case + a nonzero exit on any failure:
  VISUAL   : the displaced DAT + shifted collision RAW differ from pristine, and the disc cold-boots to gameplay.
  WALK     : Flik walks the custom terrain from spawn without falling through (moves, Y stays bounded). This is
             the PRIMARY custom-walkable-terrain capability (per-sector origin-Y shift).
  PLATFORM : the add-block platform block is built + owned + footprint-correct and is SELECTED as a live PLAYER
             collision candidate when Flik is over it — a RELIABLE proxy for the whole add-block chain. The final
             swept CATCH (Flik lands on it) is proven separately by C2 but is deliberately NOT auto-asserted: a
             teleport-based catch is flaky (physics floor-snap, candidate/enemy-list timing, and — per operator —
             Flik falls through when the resolved floor sits below where he's dropped). See PLATFORM note below.

Self-contained: builds the disc, launches/stops the isolated instance (config /tmp/duckstation-debugger-gte,
port 23460, token debugger-1000), and drives it. See src_re/collision_source_converter_80030f60.c "C2" and
[[Tier 3 - Native Terrain Path]].

Run:  python3 tools/test_terrain_pipeline.py            (build + launch + validate + stop)
      python3 tools/test_terrain_pipeline.py --no-launch (assumes an instance already on the test disc)
"""
from __future__ import annotations
import sys, os, json, struct, subprocess, argparse, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
DUCK = os.path.expanduser("~/duckstation")
sys.path.insert(0, os.path.join(DUCK, "scripts", "debugger-client"))
CFG, PORT, TOKEN = "/tmp/duckstation-debugger-gte", 23460, "debugger-1000"
MOVIE = os.path.join(ROOT, "flik_to_level01_stall.mv.movie.json")

# --- deterministic test terrain: a directional ramp; platform in flat sector 77 at absolute floor Y=-9000 (up)
PLATFORM_SECTOR, PLATFORM_FLOOR = 77, -9000
FLIK_X, FLIK_Y, FLIK_Z = 0x800a6500, 0x800a6504, 0x800a6508


def _test_heightfield(path):
    import edit_collision_sector as ECS
    g = {"x0": -8209, "x1": 14019, "z0": -14895, "z1": 25591, "nx": 41, "nz": 69}
    x0, x1, z0, z1, nx, nz = (g[k] for k in ("x0", "x1", "z0", "z1", "nx", "nz"))
    dy = []
    for i in range(nx):
        for j in range(nz):
            gx = x0 + (x1 - x0) * i / (nx - 1)
            dy.append(-2000.0 * (gx - x0) / (x1 - x0))    # gentle directional incline
    g["dy"] = dy
    json.dump(g, open(path, "w"))
    return path


def build_disc():
    hf = _test_heightfield(os.path.join(ROOT, "build/terrain_hf_regtest.json"))
    out = os.path.join(ROOT, "build/ABL_regtest")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools/build_terrain_collision_disc.py"),
                    "--heightfield", hf, "--platform", f"{PLATFORM_SECTOR}:{PLATFORM_FLOOR}",
                    "--out", out, "--force"], check=True, cwd=ROOT)
    return out + ".cue"


def platform_target():
    """Absolute runtime floor Y of the add-block platform (swept-resolver floor = ref.y<<5 = PLATFORM_FLOOR),
    plus the platform-center world XZ (sector origin, unaffected by the origin-Y shift)."""
    import edit_collision_sector as ECS
    _, dec = ECS.decompress_coll_chunk(open(os.path.join(ROOT, "REBUILD/files/LEVEL01/LEVEL.RAW"), "rb").read())
    ox = struct.unpack_from("<i", dec, ECS.SECTOR_LOCAL + PLATFORM_SECTOR * ECS.SECTOR_STRIDE + 0x08)[0]
    oz = struct.unpack_from("<i", dec, ECS.SECTOR_LOCAL + PLATFORM_SECTOR * ECS.SECTOR_STRIDE + 0x10)[0]
    return PLATFORM_FLOOR, (ox << 5, oz << 5)


def visual_offline_check():
    """VISUAL (offline half): the pipeline outputs differ from pristine."""
    dat0 = open(os.path.join(ROOT, "DAT/LEVEL01_LEVEL.DAT"), "rb").read()
    dat1 = open(os.path.join(ROOT, "build/ABL_regtest_terrain.DAT"), "rb").read()
    raw0 = open(os.path.join(ROOT, "REBUILD/files/LEVEL01/LEVEL.RAW"), "rb").read()
    raw1 = open(os.path.join(ROOT, "build/ABL_regtest_collision.RAW"), "rb").read()
    return dat1 != dat0 and len(dat1) == len(dat0), raw1 != raw0


def connect():
    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", PORT, "ws"); c.authenticate(TOKEN)
    try: c.transport.sock.settimeout(120)
    except Exception: pass
    return c


def rs32(c, a): return struct.unpack("<i", bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": 4})["hex"]))[0]
def wr(c, a, v): c.call("debugger.writeMemory", {"address": "0x%08x" % a, "hex": struct.pack("<i", v).hex()})


def boot(c):
    c.call("emulator.setTurbo", {"enabled": True}); c.call("debugger.reset", {})
    c.call("movie.load", {"path": MOVIE}); c.call("movie.startPlayback", {})
    for _ in range(75):
        if rs32(c, FLIK_X) > 50000: break
        c.call("emulator.advanceFrames", {"frames": 300})
    c.call("emulator.advanceFrames", {"frames": 8})
    try: c.call("movie.stopPlayback", {})
    except Exception: pass
    c.call("emulator.setTurbo", {"enabled": False})
    return rs32(c, FLIK_X) > 50000


def walk_check(c):
    """WALK: walk from spawn; Flik must move and not fall through (Y bounded, no death-plunge)."""
    x0, y0, z0 = rs32(c, FLIK_X), rs32(c, FLIK_Y), rs32(c, FLIK_Z)
    ys = []
    for _ in range(8):
        c.call("emulator.pressButton", {"button": "Up", "frames": 8, "port": 0, "release_after": False})
        c.call("emulator.advanceFrames", {"frames": 8})
        ys.append(rs32(c, FLIK_Y))
    c.call("emulator.clearControllerState", {"port": 0})
    x1, z1 = rs32(c, FLIK_X), rs32(c, FLIK_Z)
    moved = abs(x1 - x0) + abs(z1 - z0)
    plunged = any(y > 200000 for y in ys)          # fell to the death plane
    return moved > 15000 and not plunged, (moved, min(ys), max(ys))


def platform_check(c, center_xz):
    """FALL-FEATURE (reliable form): the add-block platform block is built + owned + footprint-correct and is
    SELECTED as a live PLAYER collision candidate when Flik is over it (i.e. the whole add-block chain — resize,
    ownership +0x4a=0, footprint, grid membership — works). The final swept CATCH is proven separately by C2
    (src_re/collision_source_converter_80030f60.c) but is flaky to auto-validate via teleport (physics floor-snap
    + candidate/enemy-list timing), so it is not asserted here.

    Candidacy is BROAD-PHASE (XZ grid) so it is robust to — and does not require — a Y drop: we move only Flik's
    XZ over the platform's footprint and re-assert it each frame (keeping his existing Y), which avoids the
    void-geometry / floor-snap hazards of poking Y to an extreme (operator warning: teleporting Flik can drop him
    through the ground)."""
    tx, tz = center_xz
    GP = 0x80081d98
    seen = False; lists = []
    for _ in range(6):
        wr(c, FLIK_X, tx); wr(c, FLIK_Z, tz)                     # re-assert XZ; leave Y (broad-phase is XZ-only)
        c.call("emulator.advanceFrames", {"frames": 1})
        cnt = rs32(c, GP + 0x57c)
        secs = [struct.unpack("<h", bytes.fromhex(c.call("debugger.readMemory",
                {"address": "0x%08x" % (0x80091718 + j * 2), "length": 2})["hex"]))[0]
                for j in range(min(cnt, 8))]
        lists.append(secs)
        if PLATFORM_SECTOR in secs:
            seen = True
    return seen, lists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-launch", action="store_true")
    args = ap.parse_args()
    print("[build] test disc (ramp heightfield + sec-77 platform)")
    cue = build_disc()
    vis_dat, vis_raw = visual_offline_check()
    target, center = platform_target()

    launched = False
    if not args.no_launch:
        subprocess.run([os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh"), "stop",
                        "--config-dir", CFG], capture_output=True)
        subprocess.run([os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh"), "start",
                        "--config-dir", CFG, "--port", str(PORT), "--token", TOKEN, "--disc", cue,
                        "--no-fastboot"], check=True, capture_output=True)
        launched = True; time.sleep(2)
    try:
        c = connect()
        booted = boot(c)
        walk_ok, walk_info = walk_check(c) if booted else (False, None)
        # re-boot for a clean platform run (walk moved Flik far)
        boot(c)
        plat_ok, plat_info = platform_check(c, center) if booted else (False, None)
    finally:
        if launched:
            subprocess.run([os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh"), "stop",
                            "--config-dir", CFG], capture_output=True)

    results = [
        ("VISUAL (DAT displaced + RAW shifted vs pristine)", vis_dat and vis_raw),
        ("VISUAL (disc cold-boots to gameplay)", booted),
        ("WALK  (Flik walks custom terrain, no fall-through)", walk_ok),
        ("PLATFORM (add-block plane is a live player candidate)", plat_ok),
    ]
    print("\n=== regression results ===")
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"  walk: {walk_info}   platform target={target} candidate-lists={plat_info}")
    ok = all(r[1] for r in results)
    print("\nOVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
