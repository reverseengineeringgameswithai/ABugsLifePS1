#!/usr/bin/env python3
"""Pre/post-rebuild guard for the DuckStation fork.

WHY THIS EXISTS, AND WHY IT IS TIME-SENSITIVE. The debugger API is being extended.
Additive RPC changes cannot touch movies, save states or findings -- the RPC lives in
src/duckstation-qt/ while movies and the state serializer live in src/core/. But if
any change bumps SAVE_STATE_VERSION (84 at capture time), every .sav dies and every
state-anchored movie with it, and the failure is SILENT: playback still succeeds,
`reproducible` still reports true, and the run drifts off-script.

That is not hypothetical. The movie format records neither the CPU mode nor the arm
phase nor the start state's sha256 (`start_state.sha256` is null on every fixture),
so a movie replaying against a state whose meaning has shifted looks exactly like a
movie replaying correctly.

The baseline can only be captured while the OLD binary still exists. Afterwards there
is no way to establish what it produced.

  --capture   record binary identity, fork HEAD, state/movie versions, and the RPC
              method surface, into analysis/duckstation_prechange_baseline.json
  --diff      compare the current build against the captured baseline and say which
              of movies / save states / tools are at risk
  --verify    replay two fixtures whose answers are already banked and confirm they
              still reproduce. This is the part that actually proves evidence
              survived; the version numbers only predict whether it should have.

The two oracles are chosen because their expected values are exact, published, and
independently derived:

  F16_Bonus01           -> 5 increments at 0x8004B3A8 valued 1..5, unlock at frame 9923
  LEVEL10_cloverforest  -> mask 0x10, 0x14, 0x1C, 0x1E, 0x1F; latch set at movie 10461

    tools/rebuild_guard.py --capture      # BEFORE the rebuild
    tools/rebuild_guard.py --diff         # after
    tools/rebuild_guard.py --verify       # after, ~20 min, the real check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORK = Path.home() / "duckstation"
BIN = FORK / "build-release/bin/duckstation-qt"
BASELINE = ROOT / "analysis/duckstation_prechange_baseline.json"


def sh(*args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip()


def capabilities_from_live(port: int = 23961, token: str = "debugger-1000"):
    """Authoritative method surface, from a throwaway isolated instance.

    Returns (sorted_method_names, features) or None if an instance cannot be raised --
    in which case the caller must record that its list is an approximation rather than
    quietly presenting a regex result as the emulator's own answer.
    """
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    cfg = Path("/tmp/abl-scratch/rebuild-guard-%d/cfg" % port)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    log = cfg.parent / "launch.log"
    pid = None
    try:
        with log.open("w") as fh:
            subprocess.run(["bash", str(ROOT / "tools/launch_repro_playback.sh"),
                            "--execution-mode", "Interpreter", "--config-dir", str(cfg),
                            "--port", str(port), "--token", token,
                            "--disc", str(ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")],
                           cwd=str(ROOT), stdout=fh, stderr=fh, check=False, timeout=180)
        txt = log.read_text()
        if "READY" not in txt:
            return None
        pid = txt.split("pid=")[1].split()[0]
        from duckstation_debug_client import DebuggerClient
        c = DebuggerClient("127.0.0.1", port, "ws")
        c.authenticate(token)
        c.transport.sock.settimeout(60)
        caps = c.call("debugger.capabilities", {})
        names = sorted((caps.get("methods") or {}).keys())
        return (names, caps.get("features")) if names else None
    except Exception:
        return None
    finally:
        if pid:
            subprocess.run(["kill", pid], check=False)


def capture() -> dict:
    out = {
        "captured_for": "DuckStation debugger-API extension handed to another agent",
        "binary": str(BIN),
        "binary_sha256": hashlib.sha256(BIN.read_bytes()).hexdigest() if BIN.exists() else None,
        "binary_size": BIN.stat().st_size if BIN.exists() else None,
        "fork_head": sh("git", "rev-parse", "HEAD", cwd=FORK),
    }
    sv = (FORK / "src/core/save_state_version.h")
    if sv.exists():
        t = sv.read_text()
        for k, pat in (("save_state_version", r"SAVE_STATE_VERSION = (\d+)"),
                       ("save_state_minimum", r"SAVE_STATE_MINIMUM_VERSION = (\d+)")):
            m = re.search(pat, t)
            out[k] = int(m.group(1)) if m else None

    # THE METHOD SURFACE MUST COME FROM THE EMULATOR, NOT FROM ITS SOURCE.
    # The first version of this regexed debuggerrpc.cpp and counted 202 where the
    # fork actually dispatches 220 -- leaving ~18 methods invisible to the one check
    # whose entire job is noticing that a method disappeared. Asserting a fact about
    # the emulator by parsing its C++ is the same error as trusting a census name
    # over the code. Ask the emulator; fall back only with the provenance recorded.
    methods, source, feats = capabilities_from_live(), "live_capabilities", None
    if methods is None:
        rpc = FORK / "src/duckstation-qt/debuggerrpc.cpp"
        methods = sorted(set(re.findall(r'QStringLiteral\("([a-zA-Z]+\.[a-zA-Z]+)"\)',
                                        rpc.read_text()))) if rpc.exists() else []
        source = "source_regex_APPROXIMATION"
    else:
        methods, feats = methods
    out["rpc_methods"] = methods
    out["rpc_method_count"] = len(methods)
    out["rpc_methods_source"] = source
    if feats:
        out["capability_features"] = feats

    # what WE call -- the surface that breaks if a method is renamed
    used = set()
    for p in (ROOT / "tools").glob("*.py"):
        used |= set(re.findall(
            r'"((?:debugger|movie|emulator|accessLog|execTrace|transferLog|gpu|'
            r'memoryScan|spu|findings|reverse|trace|provenance)\.[a-zA-Z]+)"',
            p.read_text(errors="replace")))
    # Intersect with the AUTHORITATIVE method list. A bare regex over source also
    # catches Python attribute access ("movie.str") and filenames
    # ("provenance.json"), which would then be reported as vanished methods after a
    # rebuild -- a false alarm in the one tool whose job is to not raise those.
    known = set(out.get("rpc_methods", []))
    out["methods_used_by_our_tools"] = sorted(used & known) if known else sorted(used)
    out["methods_used_count"] = len(out["methods_used_by_our_tools"])
    out["regex_nonmethods_ignored"] = sorted(used - known) if known else []

    # fixtures that are anchored to a save state, i.e. at risk from a version bump
    anchored = []
    for m in sorted(ROOT.glob("movies/**/*.movie.json")):
        try:
            d = json.loads(m.read_text())
        except Exception:
            continue
        ss = d.get("start_state") or {}
        if not ss.get("from_boot", True):
            anchored.append({"movie": str(m.relative_to(ROOT)),
                             "version": d.get("version"),
                             "anchor_frame": ss.get("frame"),
                             "state_sha256": ss.get("sha256")})
    out["state_anchored_movies"] = anchored
    out["state_anchored_count"] = len(anchored)
    out["movies_without_state_hash"] = sum(1 for a in anchored if not a["state_sha256"])
    return out


def diff() -> int:
    if not BASELINE.exists():
        print("no baseline -- run --capture BEFORE the rebuild"); return 2
    old = json.loads(BASELINE.read_text())
    new = capture()
    print("=== build identity ===")
    for k in ("fork_head", "binary_sha256", "save_state_version", "save_state_minimum"):
        o, n = old.get(k), new.get(k)
        print("  %-20s %s" % (k, "unchanged" if o == n else "%s -> %s" % (o, n)))

    risk = []
    if old.get("save_state_version") != new.get("save_state_version"):
        risk.append("SAVE STATE VERSION CHANGED -- every .sav and every state-anchored "
                    "movie (%d of them) is suspect. %d have no state hash, so drift "
                    "would be SILENT."
                    % (old.get("state_anchored_count", 0),
                       old.get("movies_without_state_hash", 0)))
    if old.get("binary_sha256") != new.get("binary_sha256"):
        risk.append("binary changed -- expected; run --verify to prove evidence survived")

    # Never diff a live-derived surface against a regex-derived one without saying
    # so: the counts differ by construction, and the difference would be reported as
    # methods appearing or vanishing that did neither.
    os_, ns_ = old.get("rpc_methods_source"), new.get("rpc_methods_source")
    comparable = (os_ == ns_) and os_ is not None
    print("  %-20s %s" % ("method surface from",
                          ns_ if os_ == ns_ else "%s -> %s  (NOT COMPARABLE)" % (os_, ns_)))

    gone = set(old.get("methods_used_by_our_tools", [])) - set(new.get("rpc_methods", []))
    if gone and comparable:
        risk.append("METHODS WE CALL NO LONGER EXIST: %s" % ", ".join(sorted(gone)))
    elif gone:
        print("\n  (method-set comparison skipped: the two captures used different "
              "sources, so apparent additions/removals are an artifact)")
    if comparable:
        added = set(new.get("rpc_methods", [])) - set(old.get("rpc_methods", []))
        if added:
            print("\n=== new methods (additive, safe) ===\n  " + ", ".join(sorted(added)))

    print("\n=== risk ===")
    if not risk:
        print("  none detected. Still run --verify: version numbers predict, they do "
              "not prove.")
        return 0
    for r in risk:
        print("  ⚠ " + r)
    return 1


ORACLES = [
    {
        "name": "F16_Bonus01 -- Bonus-1 unlock",
        "tool": ["python3", "tools/phase4_f16_streak_reset_trace.py",
                 "--row", "F16_bonus1_spiders",
                 "--movie", str(ROOT / "movies/Phase4/Interpreter/F16_Bonus01.movie.json"),
                 "--port", "23951",
                 "--json", "/tmp/rebuild_guard_f16.json"],
        "artifact": "/tmp/rebuild_guard_f16.json",
        # ⚠ Assert the SUBSTANTIVE evidence, not a summary flag. The first version
        # of this check keyed on `domain_closed`, which was later RENAMED to
        # `no_observed_writer_outside_resolved_set` when that overclaim was retracted
        # -- so the guard reported "DID NOT REPRODUCE" against a run that had
        # reproduced perfectly. A rebuild guard that cries wolf is worse than none:
        # the next person disbelieves it when it is right. Values move only if the
        # emulator moved; field names move whenever we correct ourselves.
        "check": lambda d: (
            [s["v"] for s in d["streak_timeline"] if s["pc"] == "0x8004b3a8"] == [1, 2, 3, 4, 5]
            and any(x["f"] == 9923 and x["v"] == 2 for x in d["flags_timeline"])
            and any(r["pc"] == "0x8004b3d0" and r["lost"] == 5
                    for r in d["destructive_resets"])),
        "expected": "5 increments at 0x8004B3A8 valued 1..5; unlock flag 0x02 at frame "
                    "9923; the fifth clears a streak of 5 at 0x8004B3D0",
    },
    {
        "name": "LEVEL10_cloverforest -- F10 objective mask",
        "tool": ["python3", "tools/phase4_f10_clover_trace.py"],
        "artifact": str(ROOT / "analysis/phase4_f10_clover_objective.json"),
        "check": lambda d: (
            [int(b["new_bit"], 16) for b in d["distinct_bits_set"]] == [0x10, 0x04, 0x08, 0x02, 0x01]
            and d["mask_reached_1f"] is True),
        "expected": "bits 0x10,0x04,0x08,0x02,0x01 in that order; mask reaches 0x1F",
    },
]


def verify() -> int:
    bad = 0
    for o in ORACLES:
        print("=== %s ===\n  expected: %s" % (o["name"], o["expected"]))
        r = subprocess.run(o["tool"], cwd=ROOT, capture_output=True, text=True, timeout=2400)
        try:
            d = json.loads(Path(o["artifact"]).read_text())
            ok = o["check"](d)
        except Exception as e:
            ok, d = False, None
            print("  could not evaluate: %s" % e)
            print(r.stdout[-500:])
        print("  RESULT  : %s\n" % ("REPRODUCED" if ok else "*** DID NOT REPRODUCE ***"))
        if not ok:
            bad += 1
    if bad:
        print("%d oracle(s) failed -- the rebuild moved something. Do NOT trust "
              "existing fixtures until this is understood." % bad)
        return 1
    print("both oracles reproduced -- movies, states and instrumentation survived.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.capture:
        d = capture()
        BASELINE.write_text(json.dumps(d, indent=1) + "\n")
        print("baseline -> %s" % BASELINE.relative_to(ROOT))
        for k in ("fork_head", "save_state_version", "rpc_method_count",
                  "methods_used_count", "state_anchored_count",
                  "movies_without_state_hash"):
            print("  %-26s %s" % (k, d.get(k)))
        return 0
    if a.diff:
        return diff()
    if a.verify:
        return verify()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
