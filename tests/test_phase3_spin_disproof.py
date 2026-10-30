"""Phase-3 W2: the A07 spin-move bounded negative, pinned from its artifact.

The live tool needs the emulator, so it is not re-run here. This guard requires the
artifact to preserve what the battery observed without converting writer naming into
a proof that no branch exists inside a named function."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
A = json.loads((ROOT / "analysis" / "phase3_spin_functional.json").read_text())


def test_runtime_result_is_a_bounded_negative_not_a_disproof():
    assert A["classification"] == "bounded_negative"
    assert A["bounded_negative_supported"] is True
    assert A["disproven"] is False
    # (a) no distinct spin STATE
    assert A["undocumented_values"] == []
    assert set(A["state_word_values"]) <= set(A["documented_vocabulary"])
    assert A["state_word_single_owner"] is True
    # (b) no distinct/unknown spin ROUTINE: every player-block writer is NAMED
    assert A["unnamed_block_writer_pcs"] == []
    # the verdict is COMPUTED from those stable facts, not a hand-set flag
    recomputed = (not A["undocumented_values"]
                  and A["state_word_single_owner"]
                  and not A["unnamed_block_writer_pcs"]
                  and bool(A["state_word_writer_pcs"])
                  and A["access_log_accounting"]["truncated_batches"] == 0)
    assert recomputed == A["bounded_negative_supported"]


def test_watch_covers_the_whole_player_block_including_the_kick_timer():
    """The kick proves an action can live in a separate field (0x800A657A) with no
    state-word mode, so the watch must span the block, not just the mode word."""
    reg = A["watched_region"]
    assert reg["base"] == "0x800A6500" and reg["length"] >= 0xC0
    assert reg["includes"]["kick_timer"] == "0x800A657A"
    assert len(A["player_block_addresses_written"]) >= 2


def test_all_block_writers_are_named_generic_gameplay_functions():
    names = set(A["player_block_writer_names"])
    assert "player_vertical_update" in names
    # the collision/throw/state functions the rotation battery exercised are named
    assert names & {"collision_resolve_pass", "berry_throw_dispatch",
                    "gameplay_state_machine"}


def test_the_rotation_specific_split_is_labeled_coverage_noise_not_a_signal():
    cov = A["coverage_note_rotation_specific"]
    assert "COVERAGE" in cov["_comment"] and "not the criterion" in cov["_comment"]


def test_scope_is_honestly_bounded_not_absolute():
    """Codex's point, encoded: the artifact must NOT claim absolute non-existence.
    It states the bound — a kick-shaped branch inside a named function, or an
    untested trigger, is not excluded."""
    sr = A["scope_residual"]
    assert "BOUNDED" in sr and "not a disproof" in sr
    assert "kick" in sr and "0x800A657A" in sr
    assert "Does NOT exclude" in sr or "does NOT exclude" in sr


def test_a07_registry_remains_an_external_lead_with_actionable_residuals():
    rows = {r["id"]: r for r in yaml.safe_load(
        (ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]}
    row = rows["A07_spin"]
    assert row["status"] == "external_lead"
    assert "branch" in row["missing"].lower()
    assert "exact" in row["next"].lower()
    assert "closed" not in row["next"].lower()


def test_provenance_and_media_identity_recorded():
    media = A["media_identity_after_connect"]
    assert media["game_serial"] == "SCUS-94288"
    assert media["has_media"] is True
    assert media["serials_agree"] is True
    assert media["rpc_before_hash"]["path"] == media["rpc_after_hash"]["path"]
    verification = media["hash_verification"]
    assert verification["pristine_verified"] is True
    assert verification["mounted_path"] == media["rpc_before_hash"]["path"]
    assert verification["files"]["Disney-Pixar A Bug's Life (v1.0).bin"]["actual_sha1"] == \
        "0bc1a29748d4bd608d076495d085e825574880d1"
    assert A["fixture_sha256"].get("level01.sav")
    accounting = A["access_log_accounting"]
    assert accounting["truncated_batches"] == 0
    assert accounting["unstable_total_batches"] == 0
    assert accounting["watch_cap_saturated_batches"] == 0
    assert accounting["incomplete_batches"] == 0
    assert accounting["events_returned"] == accounting["events_total"]
    assert accounting["pages"] >= accounting["batches"]
    assert accounting["batch_details"]
    assert all(batch["complete"] for batch in accounting["batch_details"])
    assert all(batch["paused_snapshot"] for batch in accounting["batch_details"])
    assert (ROOT / "analysis" / "phase2_spin_disproof.json").exists()
    assert A["trial_count"] >= 150
