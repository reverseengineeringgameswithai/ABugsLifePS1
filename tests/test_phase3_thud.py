"""Phase-3 W1: the F09/D18 Thud boss binding, pinned from its committed artifact.

The trace (tools/phase3_thud_trace.py) is LIVE, so it is not re-run here; this
guards the COMMITTED poke-falsification result and that the registry rows actually
cite it. Thud is setpiece-spawned (chunk-31 all-zero), so this runtime binding is
the only way F09 leaves the narrative-only frontier."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
T = json.loads((ROOT / "analysis" / "phase3_thud.json").read_text())


def test_boss_binding_is_confirmed_by_poke_falsification():
    assert T["bound"] is True
    b = T["boss_identity"]
    assert b["id"] == 0x24                       # Thud, the stage-9 boss
    assert b["hp_at_0x6e"] == 50
    assert b["live_table"] == "0x80090748"
    assert b["berry_damageable_bit_0x40"] is True
    # the defeat is FALSIFIABLE and was falsified both ways
    thr = T["defeat_threshold"]
    assert thr["hp1_survives"]["boss_still_live"] is True     # HP=1 does NOT retire
    assert thr["hp0_retires"]["boss_removed"] is True         # HP=0 DOES retire
    assert thr["hp0_retires"]["active_bit_after"] is False    # active bit cleared


def test_retire_handler_is_the_mover_updater():
    assert "mover_updater" in T["retire_handler"]["functions"]
    # the two retire writes: zero the live-table slot, clear the +0x5c active flag
    targets = {w["target"] for w in T["retire_handler"]["writes"].values()}
    assert "0x80090748" in targets


def test_registry_rows_cite_the_artifact_and_are_no_longer_unresolved():
    reg = {r["id"]: r for r in yaml.safe_load(
        (ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]}
    for rid in ("F09_bug_bar", "D18_thud"):
        row = reg[rid]
        assert row["status"] == "partial"        # boss bound; arena/phases still open
        blob = " ".join(str(b) for b in row["bindings"])
        assert "analysis/phase3_thud.json" in blob
        assert "0x80090748" in blob                  # the live enemy table
        assert "FUNC_8004D224" in blob               # the mover_updater retire handler


def test_ownership_frontier_has_no_open_gaps():
    """A07 remains an external lead but maps to a bounded semantic frontier; Thud is
    runtime-bound. Neither row therefore has an ownership gap."""
    g = json.loads((ROOT / "analysis" / "phase3_ownership_graph.json").read_text())
    assert sum(len(r["gaps"]) for r in g["rows"].values()) == 0


def test_live_evidence_hash_verifies_the_mounted_media_and_complete_access_log():
    media = T["media_identity_after_connect"]
    assert media["has_media"] is True
    assert media["serials_agree"] is True
    assert media["rpc_before_hash"]["path"] == media["rpc_after_hash"]["path"]
    verification = media["hash_verification"]
    assert verification["pristine_verified"] is True
    assert verification["mounted_path"] == media["rpc_before_hash"]["path"]
    assert verification["files"]["Disney-Pixar A Bug's Life (v1.0).bin"]["actual_sha1"] == \
        "0bc1a29748d4bd608d076495d085e825574880d1"
    accounting = T["retire_handler"]["access_log"]
    assert accounting["truncated"] is False
    assert accounting["returned"] == accounting["total"]
    assert accounting["pages"] >= 1
    assert accounting["totals_stable"] is True
    assert accounting["paused_snapshot"] is True
    assert accounting["watch_cap_saturated"] is False
    assert accounting["complete"] is True
    assert len(accounting["watches"]) == 2
