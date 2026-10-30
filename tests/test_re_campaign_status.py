import json
from pathlib import Path

import tools.re_campaign_status as status


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_status_snapshot_is_current():
    committed = json.loads((ROOT / "analysis" / "re_campaign_status.json").read_text())
    assert committed == status.derive_status()


def test_campaign_status_cross_checks_live_artifacts():
    report = status.derive_status()
    assert report["reconstruction"]["resident_c_functions"] == 287
    assert report["reconstruction"]["resident_asm_functions"] > 0
    assert report["reconstruction"]["source_tree_c"] == {
        "resident": 287,
        "overlay": 15,
        "wip": 2,
    }
    assert report["resident"]["unknown"] == report["understanding"]["resident_unknown"]
    assert report["overlay"]["unknown"] == 0
    assert report["formats"]["level_raw_roles_total"] == 69
    assert set(report["subsystem_slices"]) == {
        "audio_xa_start",
        "fmv_str_stream_start",
        "anm_crossfade",
        "collision_contact_scatter",
    }
    assert all(row["status"] == "closed" for row in report["subsystem_slices"].values())


def test_acceptance_cannot_claim_closed_with_unknown_functions():
    # The gate must equal "there are no unknown resident functions" — it can never
    # be claimed True while any unknown remains (guards against false closure), and
    # once the census reaches zero unknowns it is legitimately True (sc-1/sc-2).
    report = status.derive_status()
    assert report["acceptance"]["all_resident_candidates_classified"] == (
        report["resident"]["unknown"] == 0
    )
