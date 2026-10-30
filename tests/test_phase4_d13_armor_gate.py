#!/usr/bin/env python3
"""Guard for D13's one named residual: the berry-tough gate PC.

The rest of D13 was closed on 2026-08-02. This pins the instruction that the earlier
pass looked for and did not find, and -- just as importantly -- keeps the boundary of
the claim: the gate and its condition are pinned; which berry writes class 1 is still
the operator's behavioural result, not a static finding.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/phase4_d13_armor_gate.c"


def rows():
    d = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text(
        encoding="utf-8"))
    for v in d.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {x["id"]: x for x in v}
    raise AssertionError("no row list")


@pytest.fixture(scope="module")
def gate(tmp_path_factory):
    exe = tmp_path_factory.mktemp("d13") / "gate"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL)], check=True, cwd=ROOT)
    return subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)


def test_tool_builds_and_every_pin_holds(gate):
    assert gate.returncode == 0, gate.stdout[-3000:]
    assert "0 failed" in gate.stdout


def test_the_gate_is_identified_not_merely_found(gate):
    """Two sites test bit 0x40 against an actor's +0x5C in that handler. Naming
    'the gate' means having distinguished them."""
    assert "exactly two, at 0x80058DFC and 0x80058EE4" in gate.stdout
    assert "guards a specific action type, not the damage path" in gate.stdout


def test_exclusion_is_an_equality_test_not_a_power_threshold(gate):
    """The earlier speculation was a power comparison or a vulnerability window."""
    assert "it is an equality test on one class value" in gate.stdout


def test_rejection_path_is_the_visible_bounce(gate):
    assert "velocity -1280" in gate.stdout


def test_row_credits_d04_for_the_pin():
    """The pin was D04's, a day earlier. This row's `missing` was stale and I wrote a
    tool against it without reading the sibling note. The credit correction must
    survive, or the duplicate-discovery story is lost."""
    b = " ".join(rows()["D13_armored_beetles"]["bindings"])
    assert "CREDIT CORRECTION" in b
    assert "D04 had ALREADY pinned 0x80058EE4" in b
    assert "0x80058EE4" in b


def test_tool_header_carries_the_same_correction():
    src = TOOL.read_text()
    assert "CREDIT CORRECTION" in src
    assert "Reading the sibling row's note first would have found it" in src
