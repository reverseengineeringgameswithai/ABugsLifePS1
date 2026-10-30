"""E16's bounded_residuals block, and what the promotion linter says about it.

The linter applies exactly two rules per residual: RESIDUAL_MALFORMED (boundary,
evidence and next_experiment must all be non-empty) and RESIDUAL_INTERSECTS
(intersects_dimension must be exactly False). These gates pin that E16's packet
is emitted in that schema and that, now that it PASSES, each entry paid for its
assertion -- above all the >=1k remainder, which may assert only while citing the
campaign that executed its falsifier and while still refusing to claim proof.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e16_promotion_residuals.json"


def _a():
    return json.loads(ART.read_text())


def test_packet_is_emitted_in_the_linters_schema():
    a = _a()
    assert a["row_id"] == "E16_streaming_overlays" and a["dimension"] == 2
    for r in a["bounded_residuals"]:
        assert set(("boundary", "evidence", "next_experiment",
                    "intersects_dimension")) <= set(r)


def test_the_packet_now_passes_and_the_last_blocker_paid_for_it():
    """It rejected on two, then one, now none.

    This test used to pin "rejects on exactly one named blocker". That was the
    honest state while the >=1k remainder had no evidence beyond plausibility.
    It is now asserted -- but relaxing a gate is only legitimate if what replaces
    it is STRONGER, so the bar here is no longer "does it reject" but "if it
    asserts, did it pay the price": the entry must cite the executed campaign,
    and it must still refuse to call itself a proof."""
    a = _a()
    lr = a["linter_result"]
    assert lr["passes_the_residual_rules"] is True
    assert lr["rejections"] == []

    ge1k = [r for r in a["bounded_residuals"] if "index >= 1k" in r["boundary"]]
    assert len(ge1k) == 1
    e = ge1k[0]
    assert e["intersects_dimension"] is False
    assert "phase4_e16_campaign_verdict.json" in e["evidence"], \
        "the assertion must cite the campaign that licensed it"
    assert "16-level" in e["evidence"] and "1,930 events" in e["evidence"]
    assert "not a proof" in e["evidence"] or "not PROVEN" in e["evidence"], \
        "asserting must not quietly become claiming proof"
    assert "untaken branch" in e["evidence"], \
        "the limit of a replay must stay stated in the entry itself"


def test_the_two_scope_limits_the_campaign_exposed_are_in_the_packet():
    """SCOPE (46 KB of live code no static pass had read) and FORM (register-based
    accesses the affine census cannot see) were both live holes under every
    earlier E16 number. They must appear as declared, closed boundaries."""
    rs = _a()["bounded_residuals"]
    scope = [r for r in rs if r["boundary"].startswith("SCOPE:")]
    form = [r for r in rs if r["boundary"].startswith("FORM:")]
    assert len(scope) == 1 and len(form) == 1
    assert scope[0]["intersects_dimension"] is False
    assert form[0]["intersects_dimension"] is False
    assert "text_coverage_audit" in scope[0]["evidence"]
    assert "address_materialization" in form[0]["evidence"]
    assert "0 priority sites" in scope[0]["evidence"]


def test_the_convention_residual_now_asserts_non_intersection_on_magnitude():
    """It is sound because ZERO discharged sites need a SMALL negative index --
    the convention rules out an array running thousands of elements backwards,
    not an off-by-one. The raw signed fraction was the wrong metric."""
    conv = [r for r in _a()["bounded_residuals"]
            if "ABOVE the target window" in r["boundary"]]
    assert len(conv) == 1
    assert conv[0]["intersects_dimension"] is False
    assert "ZERO need a small" in conv[0]["evidence"]
    assert "signed-CAPABLE" in conv[0]["evidence"]
    assert "0x8005D69C" in conv[0]["evidence"]     # the exception, resolved


def test_every_entry_asserts_non_intersection_with_evidence():
    a = _a()
    ok = [r for r in a["bounded_residuals"] if r["intersects_dimension"] is False]
    assert len(ok) == len(a["bounded_residuals"]), \
        "with the packet passing, every entry must assert -- and carry its evidence"
    for r in ok:
        assert len(r["evidence"].strip()) > 40
        assert len(r["next_experiment"].strip()) > 40


def test_the_overlay_scope_is_declared_as_checked():
    """The scope hole that invalidated earlier framing has to appear in the packet
    as a closed boundary, not be silently absent."""
    ov = [r for r in _a()["bounded_residuals"] if "Overlay code" in r["boundary"]]
    assert len(ov) == 1
    assert "No new" in ov[0]["evidence"] or "no new" in ov[0]["evidence"].lower()
    assert ov[0]["intersects_dimension"] is False


def test_the_full_gate_cannot_be_run_here_and_says_so():
    assert "unmerged tranche" in _a()["cannot_run_the_full_gate_here"]


def test_the_signed_index_risk_set_is_empty_and_measured():
    """The gate on recording: the convention is only worth a movie campaign if the
    exception is narrow. Measured, the fragile case does not occur at all."""
    a = json.loads((ROOT / "analysis/phase4_e16_signed_index_audit.json").read_text())
    assert a["true_risk_set"]["count"] == 0
    assert a["sites_discharged_by_the_convention"] == 2922
    m = a["by_required_magnitude"]
    assert sum(v for k, v in m.items() if k.startswith("small")) == 0
    assert "SAFE TO LEAN ON" in a["verdict"]
