#!/usr/bin/env python3
"""Guards for the shared loadAndArm helper.

It exists so 78 call sites need not each remember the safety contract. Its own
failure modes are therefore the ones that matter, and two already occurred while it
was being written -- both the same shape as the session's other errors: a field path
assumed rather than observed.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/movie_arm.py"


def src():
    return TOOL.read_text()


def test_it_enforces_the_atomic_scope():
    assert 'REQUIRED_SCOPE = "serialized_request_to_paused_arm_boundary"' in src()


def test_it_checks_mount_restoration_not_just_machine_state():
    """A save state can replace the mounted disc; restoring machine state is not
    restoring the mount."""
    s = src()
    assert "media_identity_restored" in s
    assert "machine-state restoration is not mount" in s


def test_it_refuses_an_unverified_start_state_by_default():
    """Every anchored fixture has carried a hash since the 2026-08-05 backfill, so a
    missing preflight means the binding was not checked."""
    s = src()
    assert "require_state_hash=True" in s
    assert 'ss_pre.get("sha256")' in s


def test_field_paths_are_documented_as_observed_not_inferred():
    """The first version guessed `start_state_hash_preflight` at top level and
    rejected a movie whose hash HAD been preflighted."""
    assert "OBSERVED response shape" in src()


def test_coordinate_conversion_calibrates_on_the_reported_pair():
    """anchor and offset differ by one at a boundary with a pending phase correction.

    RESOLVED 2026-08-05: the difference is intentional -- anchor is the playback-ARM
    boundary, offset is based on the effective SAMPLE frame, and the fork now reports
    `movie_to_emulator_offset_basis` / `mapped_anchor_emulator_frame` /
    `anchor_to_mapped_frame_delta` so it no longer has to be inferred. Calibrating on
    the reported pair stays correct under both readings, which is why the conversion
    itself did not change."""
    s = src()
    assert "current_emulator_frame" in s and "current_movie_frame" in s
    assert "coordinate_disagreement" in s
    assert "movie_sample_effective_frame" in s
    assert "anchor_to_mapped_frame_delta" in s
    assert "INTENTIONAL, not a bug" in s
    assert "never interchangeable" in s or "were never interchangeable" in s


def test_no_silent_fallback_to_startPlayback():
    """The helper must not quietly drop to the raw RPC, which gives none of the setup
    contract above -- no atomic arm boundary, no media-identity recheck."""
    assert "startPlayback" not in src().split('"""', 2)[2]


def test_the_retracted_startPlayback_claim_stays_dead():
    """This helper was introduced saying `startPlayback` does not verify the start
    state. As of the 2026-08-05 fork change that is FALSE: forging a hash on a copy of
    F16_Bonus01 raised -32006 with mutation_performed false and load_attempted false,
    on both startPlayback and loadAndArm. Recording binds the state too
    (sha256_origin "recording"), reproduced against an independently computed digest.

    The claim is wrong, it was mine, and it is the kind that survives in a docstring
    long after the code moves -- so guard its absence, not just the correction's
    presence."""
    s = src()
    assert "It does not verify `start_state.sha256` even when the" not in s
    assert "the direct path is now the only place where a drifted state" not in s
    assert "CORRECTION 2026-08-05" in s
    assert "-32006" in s and 'sha256_origin: "recording"' in s


def test_module_is_importable_and_exports_the_api():
    tree = ast.parse(src())
    names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert {"arm_movie", "to_movie_frame", "coordinate_disagreement", "ArmError"} <= names
