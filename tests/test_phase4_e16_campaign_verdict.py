"""Gate for tools/phase4_e16_campaign_verdict.py.

The tool decides whether E16's systematic residuals survived their own declared
falsifier. Two ways it could quietly go wrong, and one test each:

  * an EXPLAINED entry becomes an excuse -- a PC waved away without a
    characterisation or an artifact behind it;
  * a genuinely unexplained PC stops falsifying.

Both are the failure mode this row has already had once (a false closure from
reading runtime silence as proof), so they are gated rather than trusted.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_e16_campaign_verdict.py"
RES = ROOT / "analysis/phase4_e16_bounded_residuals.json"

sys.path.insert(0, str(ROOT / "tools"))
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("cv", TOOL)
cv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cv)


def movie(name, verdict="USABLE AND CLEAN -- x", events=118, unenum=None):
    return {"movie": f"movies/Phase4/Interpreter/Any% Runs/{name}.movie.json",
            "verdict": verdict, "events": events, "unenumerated_pcs": unenum or {}}


def full_campaign(unenum_on_one=None):
    ms = []
    for i in range(16):
        u = unenum_on_one if i == 1 else None
        v = ("USABLE AND IT FOUND SOMETHING -- x" if u else "USABLE AND CLEAN -- x")
        ms.append(movie("LEVEL%02d_x" % i, v, 118, u))
    return {"movies": ms}


def run(tmp, validation):
    vp = tmp / "val.json"
    vp.write_text(json.dumps(validation))
    op = tmp / "out.json"
    r = subprocess.run([sys.executable, str(TOOL), "--validation", str(vp),
                        "--residuals", str(RES), "--out", str(op)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(op.read_text())


def test_explained_entries_carry_a_real_characterisation():
    """An EXPLAINED entry must say what it is, what was measured, why it cannot be
    deliberate, and name artifacts that exist on disk."""
    assert cv.EXPLAINED, "the mechanism must not be empty and unexercised"
    assert cv.MEASURED, "at least one entry must rest on an actual measurement"
    for pc, e in cv.EXPLAINED.items():
        basis = e.get("basis")
        assert basis in ("measured", "static-idiom"), f"{pc} declares no valid basis"
        for field in ("what", "why_it_cannot_be_deliberate"):
            assert e.get(field, "").strip(), f"{pc} missing {field}"
        if basis == "measured":
            assert e.get("measured", "").strip(), f"{pc} claims measurement but states none"
        else:
            assert "hoisted_load_idiom_scan.json" in " ".join(e["artifacts"]), \
                f"{pc} rests on the idiom without citing the scan"
            assert "address_materialization.json" in " ".join(e["artifacts"]), \
                f"{pc} rests on the idiom without citing the materialisation census"
        assert e["artifacts"], f"{pc} names no artifact"
        for a in e["artifacts"]:
            assert (ROOT / a).exists(), f"{pc} cites missing artifact {a}"


def test_the_whole_hoisted_family_is_admitted_not_just_what_movies_caught():
    """Two were found one movie at a time. The scan closes the family so the rest
    cannot arrive as fresh surprises -- but only because each is machine-matched,
    never because it looks similar."""
    assert len(cv.EXPLAINED) >= 22
    for pc in ("0x80010bf8", "0x80010da0"):
        assert pc in cv.EXPLAINED, f"{pc} was actually observed and must be admitted"


def test_an_unexplained_pc_falsifies(tmp_path):
    out = run(tmp_path, full_campaign({"0xdeadbeef": 3}))
    assert out["falsifier_result"]["falsified"] is True
    assert "0xdeadbeef" in out["falsifier_result"]["unexplained"]
    assert out["verdict"].startswith("FALSIFIED")
    assert "Do NOT assert" in out["recommendation"]


def test_an_explained_pc_does_not_falsify_but_is_reported(tmp_path):
    out = run(tmp_path, full_campaign({"0x80010bf8": 1}))
    assert out["falsifier_result"]["falsified"] is False
    assert "0x80010bf8" in out["falsifier_result"]["explained"]
    assert out["verdict"].startswith("NOT FALSIFIED")
    assert "DID find something" in out["verdict"], \
        "a characterised find must stay visible in the verdict, not vanish"


def test_a_mix_still_falsifies(tmp_path):
    out = run(tmp_path, full_campaign({"0x80010bf8": 1, "0xcafebabe": 2}))
    assert out["falsifier_result"]["falsified"] is True
    assert out["verdict"].startswith("FALSIFIED")


def test_partial_coverage_cannot_license_the_claim(tmp_path):
    v = full_campaign()
    v["movies"] = v["movies"][:9]
    out = run(tmp_path, v)
    assert out["coverage"]["is_full_campaign"] is False
    assert out["verdict"].startswith("PARTIAL COVERAGE")


def test_it_still_refuses_to_call_a_clean_campaign_proof(tmp_path):
    out = run(tmp_path, full_campaign())
    assert out["verdict"].startswith("NOT FALSIFIED")
    assert "not proof" in out["what_a_clean_campaign_does_NOT_mean"]
    assert "LIMIT" in out["what_a_clean_campaign_does_NOT_mean"]


def test_the_static_frontier_is_reported_and_is_the_stronger_argument(tmp_path):
    out = run(tmp_path, full_campaign())
    sf = out["static_frontier"]
    assert sf is not None
    assert sf["materialisation_sites_into_the_windows"] == 5
    assert "complete over the scanned text" in sf["why_this_is_stronger_than_the_campaign"]


def test_the_scope_correction_is_carried_into_the_verdict(tmp_path):
    out = run(tmp_path, full_campaign())
    sc = out["scope_correction"]
    assert sc is not None
    assert 89.0 < sc["text_covered_by_function_census_percent"] < 91.0
    assert sc["live_code_the_census_omitted_bytes"] > 40000
