"""Falsification guards for the bounded E08 original-game oracle promotion."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_e08_oracle_audit as audit  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_e08_oracle_audit.json"


def load_props() -> dict:
    return json.loads((ROOT / "analysis/phase4_props_movers.json").read_text())


def test_oracle_audit_recomputes_from_retained_pristine_evidence():
    recomputed = audit.build()
    assert ARTIFACT.read_text() == audit.render(recomputed)
    assert recomputed["schema"] == "abl-phase4-e08-original-oracle-audit/1"
    assert recomputed["oracle"] == {
        "movie": {
            "path": "movies/go_to_end/LEVEL01.movie.json",
            "sha256": "bfedc0d0f4828998fc598257b35ad090180ad6cb01ea317bc40229f977dc40fb",
            "bytes": 7631156,
            "frames": 10348,
            "media_class": "pristine_serial",
            "game_serial": "SCUS-94288",
            "from_boot": True,
        },
        "media_verified": True,
        "mounted_serial": "SCUS-94288",
        "from_boot": True,
        "reproducible": True,
        "window": [8550, 8580],
        "scene": 1,
        "pass1_rows": 484,
        "pass3_rows": 140,
        "actor_capacity": 64,
        "collision_sha256": (
            "6b7d858f913b7f04fb40ed45f673cc264a0dd4a34a7fc045db982b4e91499793"
        ),
        "collision_stable_across_window": True,
    }
    assert recomputed["paired_controls"]["changed_pixels"] == [2872, 5938, 0]
    assert recomputed["static_identity"]["all_regions_match"] is True
    assert recomputed["offline_reuse"]["e08_catalog_join"] is True
    assert recomputed["offline_reuse"]["direct_e08_literal_absent"] is True
    assert recomputed["claim_boundary"] == {
        "original_oracle_met": True,
        "promoted_dimensions": ["original_oracle"],
        "coupled_rows_promoted": [],
        "other_e08_dimensions_promoted": [],
        "live_escalation_authorized": False,
        "residuals": [
            (
                "Native interaction owners, authored state, denial/success, and "
                "persistence remain outside this scene-1 oracle predicate."
            ),
            (
                "E10 and D11 movie/index coupling provides reusable inputs but "
                "promotes no E10/D11 ownership or dimension."
            ),
        ],
    }


def test_oracle_audit_rejects_low_level_identity_and_behavior_mutations():
    props = load_props()
    mutated = copy.deepcopy(props)
    mutated["live"]["cold_boot"]["started"]["start_state"]["from_boot"] = False
    with pytest.raises(audit.AuditError, match="cold-boot execution"):
        audit.build(props_doc=mutated)

    mutated = copy.deepcopy(props)
    mutated["live"]["render_controls"]["pass3_bitmap_disable"]["frame_diff"][
        "changed_pixels"
    ] = 0
    with pytest.raises(audit.AuditError, match="paired render control"):
        audit.build(props_doc=mutated)

    mutated = copy.deepcopy(props)
    mutated["live"]["render_controls"]["pass1_payload_swap"]["edited"]["after"][
        "collision"
    ]["sha256"] = "0" * 64
    with pytest.raises(audit.AuditError, match="paired render control"):
        audit.build(props_doc=mutated)

    executable = bytearray((ROOT / "REBUILD/files/SCUS_942.88").read_bytes())
    executable[audit.EXE_HEADER + 0x14360 - 0x10000] ^= 1
    with pytest.raises(audit.AuditError, match="executable identity"):
        audit.build(executable=bytes(executable))


def test_oracle_audit_rejects_offline_boundary_inflation():
    output = json.loads(
        Path(
            "~/.local/state/flik-phase4-method-ratchet/runs/"
            "phase4-20260730-021829-1425442/iteration-1-receipts/"
            "offline-contact-index/selected-movie-row-coverage.json"
        ).read_text()
    )
    output["terms"]["E08_props_movers_gates"]["count"] = 1
    with pytest.raises(audit.AuditError, match="offline exact count"):
        audit.build(receipt_output=output)
