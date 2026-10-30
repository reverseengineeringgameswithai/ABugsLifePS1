#!/usr/bin/env python3
"""Shared `movie.loadAndArm` helper -- the one correct way to start a movie experiment.

⚠ CORRECTION 2026-08-05 -- READ BEFORE CITING THIS FILE. The original headline reason
for this helper was that `movie.startPlayback` did not verify `start_state.sha256`.
THAT IS NO LONGER TRUE and must not be repeated. The fork now checks the digest on the
direct path too: a mismatch raises -32006 with `mutation_performed: false`,
`load_attempted: false`, verified live by forging a hash on a copy of F16_Bonus01.
Recording also binds the state at record time now (`sha256_origin: "recording"`,
`sha256_provenance: "recording_start"`) -- a recorded movie's digest was reproduced
against an independently computed sha256 of the same .sav. So the silent-drift hole
this helper was written to plug is closed at BOTH entry points.

WHY STILL USE `loadAndArm`. Not for the hash any more -- for the setup contract, which
`startPlayback` still does not give you. It removes two failures that cost real replays:

  * arming after playback starts is a race -- observers can miss the opening frames,
    and the arm-phase correction may already have been consumed;
  * a save state can REPLACE THE MOUNTED DISC. `loadAndArm` re-verifies
    `expected_media` after the state load, before clearing traces or executing.

WHAT THIS HELPER ADDS over calling the RPC directly: it enforces the safety contract
instead of trusting the happy path. Every field the contract says to check is checked
here once, so 78 call sites do not each have to remember:

  - `atomic_scope` must be "serialized_request_to_paused_arm_boundary"
  - `transactional_rollback` is False -- so a mid-setup failure leaves state behind
    and `error.data.failure_cleanup` must be inspected, not assumed
  - after a state-driven disc swap, `media_identity_restored` must be true; machine
    state being restored is NOT the same as the mount being restored
  - the returned movie/emulator coordinates are preserved, never re-derived. Labelling
    an observation with an unqualified frame number is how movie-frame and
    emulator-frame get silently confused.

Usage:

    from movie_arm import arm_movie
    armed = arm_movie(c, movie_path, watches=[
        {"method": "accessLog.addWatch",
         "params": {"address": "0x8008223c", "length": 4, "type": "write"}},
    ])
    anchor = armed["anchor_emulator_frame"]      # never hand-compute this
"""

from __future__ import annotations

import json
from pathlib import Path


class ArmError(RuntimeError):
    """Setup failed. Carries the cleanup report, because rollback is not transactional."""

    def __init__(self, message, cleanup=None, raw=None):
        super().__init__(message)
        self.cleanup = cleanup
        self.raw = raw


REQUIRED_SCOPE = "serialized_request_to_paused_arm_boundary"


def arm_movie(client, movie_path, watches=None, breakpoints=None,
              load_start_state=True, expected_media=None, phase_correction="schedule",
              clear_traces=True, clear_breakpoints=True, require_state_hash=True):
    """Load a movie, arm instrumentation, and stop at a defined paused boundary.

    Returns a dict with the contract fields already validated, plus the coordinate
    mapping. Raises ArmError with the cleanup report if setup failed.
    """
    movie_path = Path(movie_path).resolve()

    params = {
        "movie": {"path": str(movie_path), "load_start_state": bool(load_start_state)},
        "trace_state": {"clear": bool(clear_traces)},
        "breakpoint_state": {"clear": bool(clear_breakpoints)},
        "phase_correction": phase_correction,
    }
    if watches:
        params["instrumentation"] = list(watches)
    if breakpoints:
        params["breakpoints"] = list(breakpoints)
    if expected_media:
        params["expected_media"] = expected_media

    try:
        r = client.call("movie.loadAndArm", params)
    except Exception as e:
        data = getattr(e, "data", None) or {}
        raise ArmError("loadAndArm failed: %s" % e,
                       cleanup=data.get("failure_cleanup"), raw=data) from e

    # --- the contract, checked rather than assumed -------------------------------
    # ⚠ Field paths below are the OBSERVED response shape, confirmed against a live
    # call -- not inferred from the request schema. The first version of this helper
    # guessed `start_state_hash_preflight` at top level and rejected a movie whose
    # hash HAD been preflighted, which would have blocked every migrated tool.
    atomicity = r.get("atomicity") or {}
    scope = atomicity.get("atomic_scope") or r.get("atomic_scope")
    if scope != REQUIRED_SCOPE:
        raise ArmError("unexpected atomic_scope %r (wanted %r) -- the guarantee this "
                       "helper relies on is not the one that was provided"
                       % (scope, REQUIRED_SCOPE), raw=r)

    media = {
        "media_changed_during_setup": r.get("media_changed_during_setup"),
        "media_identity_restored": (r.get("media") or {}).get("media_identity_restored",
                                                              r.get("media_identity_restored")),
        "media_after_start_state": r.get("media_after_start_state"),
    }
    if media["media_changed_during_setup"] and not media["media_identity_restored"]:
        raise ArmError("the start state replaced the mounted disc and the mount was "
                       "NOT restored -- machine-state restoration is not mount "
                       "restoration; the run would be against the wrong media",
                       cleanup=r.get("failure_cleanup"), raw=r)

    # The backfill put a hash in every state-anchored fixture. If a preflight did not
    # happen, say so loudly rather than let the caller assume it did -- an unverified
    # replay that looks verified is the exact failure being designed out.
    pre = (r.get("preflight") or {})
    ss_pre = pre.get("start_state") or {}
    hash_pre = ss_pre.get("sha256")
    hash_valid = ss_pre.get("valid")
    if require_state_hash and load_start_state and not (hash_pre and hash_valid):
        raise ArmError("no start-state hash preflight was performed for %s. Every "
                       "anchored fixture carries a hash since 2026-08-05, so this "
                       "means the binding was not checked. Pass "
                       "require_state_hash=False only if you intend an unverified run."
                       % movie_path.name, raw=r)

    boundary = r.get("boundary") or {}
    out = {
        "movie": str(movie_path),
        "atomic_scope": scope,
        "full_transactional_rollback": atomicity.get("full_transactional_rollback"),
        "failure_cleanup_mode": atomicity.get("failure_cleanup_mode"),
        "pause_boundary": boundary.get("name"),
        "boundary_emulator_frame": boundary.get("frame"),
        "boundary_movie_frame": boundary.get("movie_frame"),
        "start_state_sha256_preflighted": hash_pre,
        "start_state_hash_valid": hash_valid,
        "media_changed_during_setup": media["media_changed_during_setup"],
        "media_identity_restored": media["media_identity_restored"],
        "phase_correction_policy": boundary.get("phase_correction_policy"),
        "phase_correction_pending": boundary.get("phase_correction_pending"),
        "phase_correction_consumed": boundary.get("phase_correction_consumed"),
        "phase_correction_consumed_at": boundary.get("phase_correction_consumed_at"),
        "raw": r,
    }

    # coordinates come FROM the emulator; never hand-compute anchor = f - offset
    st = client.call("movie.status", {})
    out.update({
        "anchor_emulator_frame": st.get("anchor_emulator_frame"),
        "current_movie_frame": st.get("current_movie_frame"),
        "current_emulator_frame": st.get("current_emulator_frame"),
        "movie_to_emulator_offset": st.get("movie_to_emulator_offset"),
        "movie_version": st.get("movie_version"),
        "armed_while_paused": st.get("armed_while_paused"),
        "status_raw": st,
    })
    return out


def to_movie_frame(armed, emulator_frame):
    """Convert an emulator frame to a movie frame using the emulator's OWN observed
    pairing, not a field whose convention I have assumed.

    ⚠ `movie_to_emulator_offset` and `anchor_emulator_frame` do NOT always agree. At
    a freshly armed boundary with a phase correction still pending, the emulator
    reports anchor=9238, offset=9239, and its own current pair as
    (emulator 9238 <-> movie 0).

    RESOLVED 2026-08-05 -- the disagreement is INTENTIONAL, not a bug, and the fork
    now says so in the response rather than leaving it to be inferred:

        movie_to_emulator_offset_basis : "movie_sample_effective_frame"
        anchor_emulator_frame          : the playback-ARM boundary        (9238)
        mapped_anchor_emulator_frame   : the effective SAMPLE frame       (9239)
        anchor_to_mapped_frame_delta   : 1  -> a phase correction is owed

    So the two fields answer different questions and were never interchangeable.
    This still calibrates on the reported PAIR, which remains correct under both
    readings, and `coordinate_disagreement()` now reports the delta with its
    documented meaning instead of flagging it as an unexplained conflict.
    """
    if emulator_frame is None:
        return None
    cur_e = armed.get("current_emulator_frame")
    cur_m = armed.get("current_movie_frame")
    if cur_e is not None and cur_m is not None:
        return emulator_frame - (cur_e - cur_m)
    anchor = armed.get("anchor_emulator_frame")
    return emulator_frame - anchor if anchor is not None else emulator_frame


def coordinate_disagreement(armed):
    """None if anchor and offset agree; otherwise the two candidate conversions.

    Worth surfacing in any artifact: it is the difference between labelling an event
    at movie frame N and at N-1, which is exactly the confusion these fields exist to
    remove.
    """
    anchor = armed.get("anchor_emulator_frame")
    off = armed.get("movie_to_emulator_offset")
    cur_e, cur_m = armed.get("current_emulator_frame"), armed.get("current_movie_frame")
    if None in (anchor, off, cur_e, cur_m):
        return None
    observed = cur_e - cur_m
    if anchor == off == observed:
        return None
    st = armed.get("status_raw") or {}
    return {"observed_pair_delta": observed,
            "anchor_emulator_frame": anchor,
            "movie_to_emulator_offset": off,
            # The fork's own explanation, when it provides one -- these fields make
            # the delta self-describing instead of something to be guessed at.
            "offset_basis": st.get("movie_to_emulator_offset_basis"),
            "mapped_anchor_emulator_frame": st.get("mapped_anchor_emulator_frame"),
            "anchor_to_mapped_frame_delta": st.get("anchor_to_mapped_frame_delta"),
            "phase_correction_pending": st.get("phase_correction_pending"),
            "note": "calibrated on the observed pair; offset differs by %d. A delta of "
                    "1 with a pending phase correction is EXPECTED: anchor is the arm "
                    "boundary, offset is based on the effective sample frame."
                    % (off - observed)}


if __name__ == "__main__":  # tiny self-description, not a test
    print(json.dumps({"required_atomic_scope": REQUIRED_SCOPE,
                      "checks": ["atomic_scope", "media_identity_restored",
                                 "start_state_hash_preflight",
                                 "phase_correction audit", "coordinate mapping"]},
                     indent=1))
