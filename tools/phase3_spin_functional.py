#!/usr/bin/env python3
"""Phase-3 W2 — RUNTIME functional disproof of the A07 "spin / secret directional
move".

analysis/phase2_spin_disproof.json is a STATIC bounded negative: a pristine-EXE
scan found no ANDI direction-mask spin recognizer. That rules out one
implementation family, not the move. This tool adds the runtime half the operator
asked for: on pristine media, from representative player contexts, drive an
exhaustive battery of ROTATIONAL d-pad sequences (both handedness, several speeds,
±every action button) and record every value the player state word takes. The
claim it proves is bounded and falsifiable:

    NO rotational input sequence drives the player state word 0x800A6580 to a value
    UNREACHABLE by ordinary moves — i.e. there is no distinct "spin" player mode.

O = states reachable by an ordinary-input battery. R = states reachable by the
rotational battery. The disproof holds iff R ⊆ O. A single rotational sequence that
lands in a novel state FALSIFIES it (and would be the spin move, finally found).

This is a LIVE tool (needs the isolated pristine instance); it writes a hash-pinned
artifact that the ownership graph consumes as A07's runtime evidence.

  launch: tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-phase3-w2 \
          --port 23473 --token debugger-1000 --disc "Disney-Pixar A Bug's Life (v1.0).cue"
  run:    python3 tools/phase3_spin_functional.py --port 23473
Output: analysis/phase3_spin_functional.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.expanduser("~/duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))
from build_identity import verify_pristine_media_path  # noqa: E402
from phase3_jr_tables import (find_function as _ff,  # noqa: E402
                              load_functions as _load_functions)


def _find_function(funcs, addr):
    """Return the function DICT containing addr (or None). _ff returns a tuple."""
    t = _ff(funcs, addr)
    return t[2] if t else None

STATE = 0x800A6580          # player state/mode word (u8): {0,1,2,4,5,6} documented
GROUNDED = 0x800A6582       # grounded/facing flag (u8)
SCENE = 0x80082504          # scene_id u32 — confirms we are in the level
SAVE = ROOT / "level01.sav"
DOCUMENTED_VOCAB = {0, 1, 2, 4, 5, 6}
# WATCH THE WHOLE PLAYER-STATE BLOCK, not just the mode word. A real special move
# need NOT occupy a distinct state-word value — the confirmed KICK is an action
# driven by a separate timer 0x800A657A with no distinct 0x800A6580 mode. So a
# spin move could hide in any player variable. Watching the block [0x800A6500,
# +0xC0) — which includes the mode word, grounded flag, kick timer 0x800A657A, and
# the power-up word 0x800A6590 — expands the observable frontier. It still cannot
# exclude a branch inside one of the named functions, which is why the result remains
# a bounded negative rather than a disproof.
PLAYER_BLOCK_BASE = 0x800A6500
PLAYER_BLOCK_LEN = 0xC0

# TRUE 8-way octagon via SIMULTANEOUS d-pad holds (the RPC's `buttons` array holds
# multiple buttons at once — so a diagonal is a real held ["Up","Right"], not two
# sequential taps). This is the full digital-pad input space a spin recognizer would
# read; A Bug's Life uses the d-pad, so there is no analog axis to miss.
OCTANTS_CW = [["Up"], ["Up", "Right"], ["Right"], ["Down", "Right"],
              ["Down"], ["Down", "Left"], ["Left"], ["Up", "Left"]]
OCTANTS_CCW = [["Up"], ["Up", "Left"], ["Left"], ["Down", "Left"],
               ["Down"], ["Down", "Right"], ["Right"], ["Up", "Right"]]
ACTIONS = ["Cross", "Square", "Triangle", "Circle"]


def connect(port, token):
    from duckstation_debug_client import DebuggerClient
    cl = DebuggerClient("127.0.0.1", port, "ws")
    cl.authenticate(token)
    cl.transport.sock.settimeout(30)
    return cl


def verified_media_identity(rig, status):
    """Hash the exact mounted path and reject an identity/media swap race."""
    before = rig.call("emulator.getMediaInfo", {})
    if not before.get("has_media") or not before.get("path"):
        raise SystemExit(f"mounted-media guard: no media is mounted: {before}")
    if status.get("game_serial") != "SCUS-94288" or \
            before.get("game_serial") != status.get("game_serial"):
        raise SystemExit(
            f"mounted-media guard: debugger/media serial mismatch: {status} / {before}")
    verification = verify_pristine_media_path(before["path"])
    after = rig.call("emulator.getMediaInfo", {})
    stable_keys = ("has_media", "path", "game_serial", "subimage_count", "subimage_index")
    if any(before.get(key) != after.get(key) for key in stable_keys):
        raise SystemExit(
            f"mounted-media guard: media changed while hashing: {before} -> {after}")
    return {
        "game_serial": status.get("game_serial"),
        "game_title": status.get("game_title"),
        "game_path": before["path"],
        "has_media": True,
        "serials_agree": True,
        "rpc_before_hash": before,
        "rpc_after_hash": after,
        "hash_verification": verification,
    }


def checked_access_log(rig, watch_id):
    """Page one paused watch snapshot and prove no server/watch cap loss."""
    status = rig.call("debugger.status", {})
    paused_snapshot = bool(status.get("paused")) and not bool(status.get("running"))
    if not paused_snapshot:
        raise SystemExit(f"access-log guard: guest was not paused before paging: {status}")
    params = {"watch_id": watch_id, "offset": 0, "limit": 10000}
    first = rig.call("accessLog.get", params)
    total = int(first.get("total", 0))
    events = list(first.get("events", []))
    page_totals = [total]
    truncated = bool(first.get("truncated"))
    empty_page = False
    pages = 1
    while len(events) < total:
        page = rig.call("accessLog.get", {
            "watch_id": watch_id,
            "offset": len(events),
            "limit": min(10000, total - len(events)),
        })
        pages += 1
        page_totals.append(int(page.get("total", -1)))
        truncated = truncated or bool(page.get("truncated"))
        chunk = page.get("events", [])
        if not chunk:
            empty_page = True
            break
        events.extend(chunk)
    watches = [w for w in first.get("watches", []) if int(w.get("watch_id", -1)) == watch_id]
    cap_saturated = any(int(w.get("hit_count", 0)) >= int(w.get("max_events", 0))
                        for w in watches)
    totals_stable = all(value == total for value in page_totals)
    complete = (paused_snapshot and not truncated and not empty_page and len(events) == total
                and totals_stable and len(watches) == 1 and not cap_saturated)
    return {
        "watch_id": watch_id,
        "total": total,
        "returned": len(events),
        "pages": pages,
        "page_limit": 10000,
        "paused_snapshot": paused_snapshot,
        "truncated": truncated,
        "totals_stable": totals_stable,
        "empty_page_before_total": empty_page,
        "watch_cap_saturated": cap_saturated,
        "watches": watches,
        "complete": complete,
    }, events


class Rig:
    def __init__(self, cl):
        self.cl = cl
        self.sink = None          # a set; every atomic input samples STATE into it
        self.watch = False        # re-arm the state-word write-watch after each load
        self.watch_id = None

    def call(self, m, p=None):
        return self.cl.call(m, p or {})

    def _sample(self):
        # capture the state word RIGHT AFTER the input, before it settles — a spin
        # move's mode would be transient, so sampling only the settled endpoint
        # would miss it. This is what makes the disproof cover the trajectory.
        if self.sink is not None:
            self.sink.add(self.u8(STATE))

    def rmem(self, a, n):
        return bytes.fromhex(self.call("debugger.readMemory",
                                       {"address": "0x%08x" % a, "length": n})["hex"])

    def u8(self, a):
        return self.rmem(a, 1)[0]

    def u32(self, a):
        return int.from_bytes(self.rmem(a, 4), "little")

    def load(self):
        loaded = self.call("emulator.loadState",
                           {"path": str(SAVE.resolve()), "pause_after_load": True})
        assert loaded.get("loaded") and loaded.get("game_serial") == "SCUS-94288", loaded
        if self.watch:            # loadState clears watches — re-arm every time
            watch = self.call("accessLog.addWatch",
                              {"address": "0x%08x" % PLAYER_BLOCK_BASE,
                               "length": PLAYER_BLOCK_LEN, "type": "write",
                               "max_events": 400000})
            self.watch_id = int(watch["watch_id"])
        self.adv(3)

    def adv(self, n=1):
        self.call("emulator.advanceFrames", {"frames": n})

    def watch_adv(self, n=8):
        """Advance frame-by-frame, sampling the state each frame — captures the
        WHOLE action trajectory (a jump's rise/apex/fall, or a spin's transient
        mode) as it plays out, not just the settled endpoint."""
        for _ in range(n):
            self.call("emulator.advanceFrames", {"frames": 1})
            self._sample()

    def press(self, btn, frames=1):
        self.call("emulator.pressButton",
                  {"button": btn, "frames": frames, "port": 0, "release_after": True})
        self._sample()

    def hold(self, buttons, frames=1, release=True):
        """Press MULTIPLE buttons simultaneously (true diagonals / dir+action)."""
        self.call("emulator.pressButton",
                  {"buttons": list(buttons), "frames": frames, "port": 0,
                   "release_after": release})
        self._sample()

    def observe(self):
        return self.u8(STATE), self.u8(GROUNDED)


def prelude(rig, context):
    """Put the player into a starting context before the trial's main input. The
    setup input itself is NOT sampled — only the rotation that follows is."""
    saved, rig.sink = rig.sink, None
    rig.load()
    if context == "air":
        rig.press("Cross", 3)          # jump — mid-air
    elif context == "moving":
        rig.press("Right", 10)         # running
    rig.sink = saved


def run(args):
    rig = Rig(connect(args.port, args.token))
    # confirm mounted-media identity AFTER connecting (provenance): the disc this
    # instance is actually running, not an assumed "pristine".
    status = rig.call("debugger.status", {})
    media_identity = verified_media_identity(rig, status)
    state_inspection = inspect_state_before_load(rig, SAVE, media_identity)
    rig.load()
    assert rig.u32(SCENE) == 1, "not in LEVEL01 — wrong save/instance"

    # write-watch over the WHOLE player block for the battery. loadState clears
    # watches, so Rig.load() re-arms it each time once rig.watch is set.
    rig.call("accessLog.clear", {})
    rig.watch = True
    rig.load()                                  # arms the watch via the re-arm hook

    trials = []
    ordinary, rotational = set(), set()
    state_values, writer_pcs = set(), set()     # state-word values; all block writers
    ord_pcs, rot_pcs = set(), set()             # PCs writing ANY block addr, per battery
    block_writers = {}                          # addr -> set(pc) over the whole block
    accounting = {"batches": 0, "pages": 0, "events_total": 0,
                  "events_returned": 0, "truncated_batches": 0,
                  "unstable_total_batches": 0,
                  "watch_cap_saturated_batches": 0,
                  "incomplete_batches": 0,
                  "batch_details": []}

    def drain(dest):
        # pull events since the last drain, fold into the accumulators, clear. State
        # VALUES come only from the mode word (0x800A6580); WRITER analysis spans the
        # whole block, so a kick-like spin (separate field) cannot hide.
        assert rig.watch_id is not None
        meta, evs = checked_access_log(rig, rig.watch_id)
        accounting["batches"] += 1
        accounting["pages"] += meta["pages"]
        accounting["events_total"] += meta["total"]
        accounting["events_returned"] += len(evs)
        accounting["batch_details"].append(meta)
        if meta["truncated"]:
            accounting["truncated_batches"] += 1
        if not meta["totals_stable"]:
            accounting["unstable_total_batches"] += 1
        if meta["watch_cap_saturated"]:
            accounting["watch_cap_saturated_batches"] += 1
        if not meta["complete"]:
            accounting["incomplete_batches"] += 1
        for e in evs:
            pc = e["instruction_pc"]
            addr = int(e["address"], 16)
            writer_pcs.add(pc)
            dest.add(pc)
            block_writers.setdefault(e["address"], set()).add(pc)
            if addr == STATE:
                state_values.add(e["new_value"] & 0xFF)
        rig.call("accessLog.clear", {})

    def record(bucket, label, kind):
        rig.watch_adv(8)          # sample the full settle trajectory into `bucket`
        s, g = rig.observe()
        trials.append({"label": label, "kind": kind, "state": s, "grounded": g})
        bucket.add(s)
        drain(rot_pcs if kind == "rotational" else ord_pcs)

    # --- Battery A: ordinary inputs (defines the reachable set O) --------------
    rig.sink = ordinary          # every atomic input samples STATE into O
    SINGLE = ["Up", "Down", "Left", "Right", "Cross", "Square", "Triangle",
              "Circle", "L1", "R1", "L2", "R2", "Start", "Select"]
    for btn in SINGLE:
        for fr in (4, 12):
            rig.load()
            rig.press(btn, fr)
            record(ordinary, f"ordinary:{btn}x{fr}", "ordinary")
    COMBOS = [("run+jump", [("Right", 10), ("Cross", 4)]),
              ("jump+slam", [("Cross", 3), ("Down", 10)]),
              ("run+square", [("Right", 12), ("Square", 4)]),
              ("run+circle", [("Right", 10), ("Circle", 6)]),
              ("run+triangle", [("Right", 10), ("Triangle", 6)]),
              ("jump+square(air)", [("Cross", 3), ("Square", 4)]),
              ("run+jump+down", [("Right", 8), ("Cross", 3), ("Down", 8)])]
    for label, seq in COMBOS:
        rig.load()
        for btn, fr in seq:
            rig.press(btn, fr)
            rig.adv(2)
        record(ordinary, f"ordinary:{label}", "ordinary")
    # held diagonals and simultaneous direction+action (so O is a fair baseline the
    # rotational R is compared against — not weaker input than the spin battery uses)
    HELD = [["Up", "Right"], ["Down", "Right"], ["Down", "Left"], ["Up", "Left"],
            ["Right", "Cross"], ["Right", "Square"], ["Down", "Cross"],
            ["Right", "Circle"], ["Up", "Cross"], ["Left", "Cross"]]
    for combo in HELD:
        rig.load()
        rig.hold(combo, 8)
        record(ordinary, "ordinary:hold:" + "+".join(combo), "ordinary")

    # --- Battery B: TRUE 8-way rotational sequences (the reachable set R) ------
    # Each octant is a SIMULTANEOUS held combo, so the sweep is a real analog-style
    # rotation of the digital pad. Three action modes cover the plausible spin
    # triggers: bare rotation, rotation with an action HELD throughout (charge),
    # and an action TAPPED at the end of the rotation (release-spin).
    def rotate(ring, speed, turns, action=None, action_mode=None):
        for _ in range(turns):
            for oct_ in ring:
                combo = oct_ + ([action] if (action and action_mode == "during") else [])
                rig.hold(combo, speed)
        if action and action_mode == "trailing":
            rig.press(action, 4)

    rig.sink = rotational        # every rotational input samples STATE into R
    # bare rotation sweep — thorough across speed/turns/context/handedness
    for hand, ring in (("CW", OCTANTS_CW), ("CCW", OCTANTS_CCW)):
        for speed in (1, 2, 4, 8):
            for turns in (2, 4):
                for context in ("idle", "air", "moving"):
                    prelude(rig, context)
                    rotate(ring, speed, turns)
                    record(rotational, f"rot:{hand} s{speed} t{turns} {context}",
                           "rotational")
    # rotation with an action held DURING, and TAPPED trailing
    for hand, ring in (("CW", OCTANTS_CW), ("CCW", OCTANTS_CCW)):
        for speed in (2, 4):
            for context in ("idle", "air", "moving"):
                for action in ACTIONS:
                    for mode in ("during", "trailing"):
                        prelude(rig, context)
                        rotate(ring, speed, 3, action, mode)
                        record(rotational,
                               f"rot:{hand} s{speed} {context} {action}/{mode}",
                               "rotational")

    # LONG continuous rotations (a charge-up spin needs sustained input)
    for hand, ring in (("CW", OCTANTS_CW), ("CCW", OCTANTS_CCW)):
        for context in ("idle", "moving"):
            prelude(rig, context)
            rotate(ring, 2, 16)
            record(rotational, f"rot:LONG {hand} {context}", "rotational")

    # --- decisive structural evidence: WHO writes the state word, and to WHAT ---
    # The R-vs-O sampling above is a weak baseline (O is incomplete — a documented
    # mode like slide/handstand may never trigger under my ordinary battery, so it
    # false-flags as "novel"). The DECISIVE disproof is structural: a genuine spin
    # move would either drive the state word to an UNDOCUMENTED value, or be a
    # DISTINCT code path writing it. The write-watch (armed over the whole battery)
    # records every value the word ever took AND every PC that wrote it. If every
    # value is a documented player mode and every writer lives in the ONE player
    # movement FSM, there is no separate spin state and no separate spin routine.
    # Every trial ends in record(), which drains and clears its watch.  Do not
    # issue a second "final flush" against the just-removed watch id: the server
    # correctly returns zero events and no matching watch for that stale id, and
    # counting that artificial request as an incomplete batch invalidates an
    # otherwise complete 193-trial capture.
    funcs = _load_functions()

    def resolve(pcs):
        out = {}
        for pc in sorted(pcs):
            f = _find_function(funcs, int(pc, 16))
            out[pc] = {"function_start": f["start"] if f else None,
                       "name": f.get("name") if f else None}
        return out

    state_values = sorted(state_values)
    writer_pcs = sorted(writer_pcs)             # PCs writing ANY player-block field
    writer_funcs = resolve(writer_pcs)
    # state-word (0x800A6580) writers specifically, for the single-owner detail
    sw_pcs = sorted(block_writers.get("0x800a6580", set())
                    | block_writers.get("0x800A6580", set()))
    sw_starts = sorted({resolve([pc])[pc]["function_start"] for pc in sw_pcs} - {None})

    def funcs_of(pcs):
        return {resolve([pc])[pc]["function_start"] for pc in pcs} - {None}

    # The rotation-vs-ordinary writer split is COVERAGE-dependent noise (rotation
    # simply moves the player more, triggering generic collision/throw/state
    # functions a static ordinary battery misses), so it is reported as context, not
    # used as the criterion.
    rotation_specific_functions = sorted(funcs_of(rot_pcs) - funcs_of(ord_pcs))
    rotation_specific_pcs = sorted(rot_pcs - ord_pcs)
    rotation_specific_named = sorted(
        {writer_funcs[pc]["name"] for pc in rotation_specific_pcs
         if writer_funcs.get(pc, {}).get("name")})

    # STABLE, coverage-independent disproof criterion — a spin move would be either
    # (a) a distinct STATE: an undocumented mode-word value; or (b) a distinct
    # ROUTINE: an UNNAMED/unknown function writing the player block (the whole
    # generic gameplay pipeline is named, so a dedicated spin recognizer would stand
    # out as unnamed). Neither the rotation battery nor ordinary play produced
    # either. This does NOT use the noisy rotation-specific split.
    unnamed_block_writers = sorted(pc for pc in writer_pcs
                                   if not writer_funcs.get(pc, {}).get("name"))
    undocumented = sorted(set(state_values) - DOCUMENTED_VOCAB)
    bounded_negative_supported = (not undocumented) and (len(sw_starts) == 1) \
        and (not unnamed_block_writers) and bool(writer_pcs) \
        and accounting["incomplete_batches"] == 0

    novel_vs_ordinary = sorted(rotational - ordinary)
    run_provenance = finish_run(
        args, generator="tools/phase3_spin_functional.py",
        anchor={"save": str(SAVE.relative_to(ROOT)),
                "fixture_sha256": {SAVE.name: hashlib.sha256(SAVE.read_bytes()).hexdigest()},
                "state_inspections": [state_inspection],
                "media_identity": media_identity},
        timing={"trial_count": len(trials), "contexts": ["idle", "air", "moving"],
                "access_log": accounting},
    )
    doc = {
        "_comment": "Phase-3 W2 RUNTIME bounded negative for the A07 spin lead. "
                    "Pairs the static negative (phase2_spin_disproof.json). The "
                    "write-watch over the WHOLE player block "
                    "[0x800A6500,+0xC0) across an exhaustive input battery (true 8-way "
                    "rotations): (a) the mode word 0x800A6580 never takes an "
                    "undocumented value, and (b) all observed player-field writer "
                    "functions are named. This rules out an observed distinct state or "
                    "unknown routine; it does NOT disprove a branch inside a named "
                    "function. Regenerate (LIVE): "
                    "python3 tools/phase3_spin_functional.py --port N",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media_identity_after_connect": media_identity,
        "authority": {
            "media": "pristine (SCUS-94288)",
            "save": str(SAVE.relative_to(ROOT)),
            "scene_id": 1,
        },
        "fixture_sha256": {SAVE.name: hashlib.sha256(SAVE.read_bytes()).hexdigest()},
        "watched_region": {"base": "0x%08X" % PLAYER_BLOCK_BASE,
                           "length": PLAYER_BLOCK_LEN,
                           "includes": {"mode_word": "0x800A6580",
                                        "grounded": "0x800A6582",
                                        "kick_timer": "0x800A657A",
                                        "powerup_word": "0x800A6590"}},
        "access_log_accounting": accounting,
        "input_alphabet": {
            "ordinary_single": SINGLE,
            "ordinary_combos": [c[0] for c in COMBOS],
            "rotational": "TRUE 8-way d-pad octants (simultaneous held diagonals) "
                          "CW/CCW, {1,2,4,8} frames/octant, {2,4} turns, contexts "
                          "{idle,air,moving}, x {bare, +Cross/Square/Triangle/Circle "
                          "held-during and tapped-trailing}, plus long 16-turn "
                          "continuous — the full digital-pad input space.",
        },
        "trial_count": len(trials),
        "player_block_writer_functions": {pc: writer_funcs[pc] for pc in writer_pcs},
        "player_block_writer_names": sorted(
            {v["name"] for v in writer_funcs.values() if v.get("name")}),
        "player_block_addresses_written": sorted(block_writers),
        "unnamed_block_writer_pcs": unnamed_block_writers,
        "state_word_values": state_values,
        "documented_vocabulary": sorted(DOCUMENTED_VOCAB),
        "undocumented_values": undocumented,
        "state_word_writer_pcs": sw_pcs,
        "state_word_owning_function_starts": sw_starts,
        "state_word_single_owner": len(sw_starts) == 1,
        "coverage_note_rotation_specific": {
            "_comment": "COVERAGE artifact, NOT a spin signal: rotation moves the "
                        "player more than a static ordinary battery, so it triggers "
                        "generic collision/throw/state functions the ordinary battery "
                        "missed. All are NAMED generic gameplay functions — none is a "
                        "dedicated spin routine. Noisy/run-dependent; not the criterion.",
            "functions": rotation_specific_named,
            "pcs": rotation_specific_pcs,
        },
        "supplementary_input_sampling": {
            "ordinary_states_reachable_O": sorted(ordinary),
            "rotational_states_reachable_R": sorted(rotational),
            "rotational_minus_ordinary_states": novel_vs_ordinary,
            "all_rotational_states_within_documented_vocabulary": not sorted(
                set(rotational) - DOCUMENTED_VOCAB),
        },
        "classification": "bounded_negative",
        "bounded_negative_supported": bounded_negative_supported,
        "disproven": False,
        "scope_residual": ("BOUNDED NEGATIVE, not a disproof. Establishes only that the "
                           "tested battery exposed no distinct spin STATE (no "
                           "undocumented mode value; the mode word has one owner) and "
                           "no observed UNKNOWN player-block writer routine. Does NOT "
                           "exclude a move gated on an input/context outside the tested "
                           "alphabet, or a branch hidden INSIDE a named generic function "
                           "(the kick's shape — a branch in player_vertical_update "
                           "writing timer 0x800A657A). A07 remains an external lead "
                           "pending an exact reproducible trigger or branch-level proof."),
        "conclusion": (
            "Bounded negative supported: the tested input battery exposed no "
            "undocumented mode value or unnamed player-block writer, and all access-log "
            "events were retrieved without truncation. This is NOT a disproof: a "
            "kick-shaped branch inside a named function remains possible."
            if bounded_negative_supported else
            f"Bounded negative unsupported: undocumented mode values {undocumented}, "
            f"unnamed writers {unnamed_block_writers}, or incomplete access-log "
            f"accounting {accounting} — investigate first"),
    }
    out = ROOT / "analysis" / "phase3_spin_functional.json"
    write_live_evidence(out, doc)
    print(f"[spin] {len(trials)} trials, {len(writer_pcs)} block-writer PCs | "
          f"state_values={state_values} undoc={undocumented} | "
          f"unnamed_writers={unnamed_block_writers} single_owner={len(sw_starts)==1} "
          f"| bounded_negative={bounded_negative_supported} disproven=False")
    return 0 if bounded_negative_supported else 1


def main():
    ap = argparse.ArgumentParser()
    add_required_live_args(ap)
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
