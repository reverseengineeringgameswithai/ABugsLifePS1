"""Gates for the affine index-bound recovery capability.

Exit-gate item 2 has stopped three rows on one deficiency: a base register is
provably `K + i*S` but `i` is unbounded. tools/affine_bound_recovery.c recovers
the bounds that ARE in the code but sit in a form a per-register bound table
cannot use -- a range test on a DERIVED value, or an `andi` mask.

These gates pin the ground truth, the yield, and -- most importantly -- that the
capability is reported as insufficient rather than as a closure.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/affine_bound_recovery.c"
ART = ROOT / "analysis/phase4_bound_recovery.json"
EXE = ROOT / "REBUILD/files/SCUS_942.88"
FUNCS = ROOT / "analysis/functions_resident.txt"


def _art():
    return json.loads(ART.read_text())


def test_tool_compiles_and_recovers_the_ground_truth_case():
    """0x8003BF48 is the case that defeated the previous analyser: it was excluded
    as out-of-bound while runtime shows it firing 36 times. The recovered range
    must be exactly [48, 88), which is the empirically established window."""
    binp = "/tmp/_abr_gate"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", binp, str(SRC)],
                   check=True)
    r = subprocess.run([binp, str(EXE), str(FUNCS), "--verify"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "VERIFY OK: 0x8003BF48 -> [48, 88)" in r.stderr
    assert "RECOVERED [48, 88)" in r.stdout


def test_symbols_are_keyed_by_definition_site_not_by_visit():
    """The bug that silently reduced the analysis to almost nothing: allocating a
    fresh symbol per VISIT means the same definition gets a new symbol every
    fixed-point round, so joins never agree and every value decays to UNKNOWN."""
    src = SRC.read_text()
    assert "sym_of_pc" in src and "sym_of_block" in src
    assert "not the visit" in src
    assert "g_next_sym" not in src          # the broken scheme must not come back


def test_yield_is_recorded_honestly():
    y = _art()["yield"]
    assert y["region_formed_sites"] == 6230
    assert y["bounded_sites"] == 899           # 702 intra-only -> 710 +IPA -> 899 +range arith
    assert 14.0 <= y["percent"] <= 14.8


def test_bounded_sites_mostly_EXCLUDE_rather_than_reach():
    """A bound is only useful if it can prove disjointness. For every target the
    bounded sites overwhelmingly exclude."""
    for name, v in _art()["per_target"].items():
        assert v["excluded_by_bound"] > 10 * v["reaching"], name


def test_item_2_is_still_reported_as_NOT_met():
    """The capability is necessary, not sufficient -- and must say so. 5,527 of
    6,229 sites still have no recoverable bound."""
    v = _art()["verdict"]
    assert v["item_2_met"] is False
    assert "not a sufficient one" in v["what_did_not"]
    assert "interprocedural" in v["why_the_rest_resist"]
    for t in _art()["per_target"].values():
        assert t["undecided"] == 5399


def test_the_disclosed_assumption_travels_with_the_range():
    """slti gives an upper bound only; pairing it with an implicit lower bound of
    0 is an assumption, and it has to be stated where the range is produced."""
    src = SRC.read_text()
    assert "non-negative-index convention" in src
    idioms = _art()["capability"]["idioms_recovered"]
    assert "non-negative-index convention" in idioms["slti idx, N"]


# ---- the capability is wired into the SHARED analyser, not just a side tool ----

def test_mask_bound_is_in_the_shared_analyser_not_only_the_side_tool():
    """The question that decides whether anyone benefits by default: does the tool
    every row already runs consume the capability, or must each agent be told to
    run a second binary? The mask bound is ported INTO region_provenance.c."""
    src = (ROOT / "tools/region_provenance.c").read_text()
    assert "TIER 3 BOUND FROM A MASK" in src
    assert "affine_bound_recovery.c" in src          # provenance of the idiom
    assert "bound_hint[d.rt] = (int32_t)((uint16_t)d.imm) + 1" in src


def test_it_advanced_the_row_that_originally_hit_the_wall():
    """B06/B08 stopped at a 251-site residual and declared the technique exhausted.
    The mask bound discharged 59 more, soundly -- so the technique was not
    exhausted, it was unbuilt."""
    a = json.loads((ROOT / "analysis/phase4_region_provenance.json").read_text())
    r = a["result"]
    assert r["baseline_residual"] == 416
    assert r["excluded_out_of_bound"] == 59
    assert r["still_open_after_region_provenance"] == 192
    # the guard that matters: no exclusion may collide with a known-real access
    v = a["validation"]
    assert v["hit_set_matches_python"] is True
    assert v["c_exclusions_colliding_with_python_hits (MUST be empty)"] == []
    assert v["reconciles_exactly"] is True


def test_interprocedural_gain_is_reported_as_small():
    """The hypothesis was that the missing bounds live in callers. Measured, that is
    largely FALSE: full argument-range propagation added 8 sites. Recording the
    disappointment is the point -- it redirects the next build."""
    ip = _art()["interprocedural"]
    assert "+8 sites" in ip["MEASURED_GAIN"]
    assert "NOT the missing lever" in ip["MEASURED_GAIN"]
    assert ip["eligible"] == 447
    assert ip["with_a_bounded_parameter"] == 149


def test_ipa_soundness_exclusions_are_enumerated():
    """Propagating into a function that can be entered unseen would make every
    downstream bound unsound, so each escape route is counted explicitly."""
    x = _art()["interprocedural"]["soundness_exclusions"]
    assert x["address_taken"] == 85
    assert x["overlay_called"] == 129
    assert x["no_static_caller"] == 337
    assert x["cycle_or_unsettled"] == 0          # the fixed point settled
    assert "different binary" in x["why"]


def test_the_residual_is_diagnosed_by_measurement():
    """'The rest resist' is only useful if you know WHY. Every unbounded site is
    classified by where its index symbol was born, and the answer overturned the
    working hypothesis: it is neither data nor callers, it is `addu` of two values
    that each already lack a range."""
    w = _art()["why_the_residual_resists"]
    o = w["origins"]
    assert o["alu"] > o["load"] * 3             # ALU dominates, not loads
    assert o["func_entry"] < 200                # and not arguments either
    assert "addu" in w["conclusion"]
    assert "ORIGINATE" in w["conclusion"]
