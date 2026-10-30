"""Gate for B09's measured reset/persistence law.

The conclusion is a negative -- neither suspect fires -- so the test that matters
most is the positive control: if the setter did not fire, super jump was never
acquired and the negative means nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_b09_lifetime.json"


def a():
    return json.loads(ART.read_text())


def test_the_positive_control_fired():
    """Without this the negative result is worthless. It read False on the first
    run because the setter's store is in a DELAY SLOT and accessLog reports the
    branch target, not PC+4."""
    d = a()
    assert d["control_setter_fired"] is True
    assert d["control_setter_pc_as_reported"] == "0x800589d8"
    assert "delay slot" in d["delay_slot_gotcha"].lower()


def test_neither_suspect_fired():
    d = a()
    for pc, s in d["suspects"].items():
        assert s["fired"] is False, f"{pc} fired -- the law needs revising"


def test_super_jump_was_actually_acquired_and_held():
    d = a()
    assert d["samples_with_super_jump"] > 0
    flags = [s["super_jump"] for s in d["samples"]]
    assert flags[0] is False and True in flags, "bit must go off -> on inside the run"


def test_the_clear_is_attributed_to_the_bios_memset():
    """The same mechanism B06 proved for its own power at a scene transition."""
    d = a()
    assert d["bios_memset_writes"] > 0
    assert "BIOS memset" in d["verdict"]


def test_the_sampling_limit_is_stated():
    """Indices are wall-clock polled and drift between runs; the accessLog PC set
    is what carries the conclusion."""
    d = a()
    assert "approximate" in d["sampling_caveat"]
    assert "accessLog" in d["sampling_caveat"]
