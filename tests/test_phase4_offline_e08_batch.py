"""Falsification guards for the generated E08 offline batch."""

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_offline_e08_batch as batch  # noqa: E402


def document() -> dict:
    return json.loads(batch.OUTPUT.read_text())


def test_e08_batch_recomputes_from_the_exact_preserved_index():
    rebuilt = batch.build(Path(document()["external_index"]["absolute_path"]))
    assert batch.render(rebuilt) == batch.OUTPUT.read_bytes()


def test_e08_batch_rejects_an_unpinned_index_generation_ancestor(monkeypatch):
    configuration = copy.deepcopy(batch.CONFIGURATION)
    configuration["external_index"]["generation_capsule_set_sha256"] = "0" * 64
    monkeypatch.setattr(batch, "CONFIGURATION", configuration)
    with pytest.raises(ValueError, match="capsule-set pin drifted"):
        batch.build(Path(document()["external_index"]["absolute_path"]))


def test_e08_batch_pins_complete_cluster_reader_and_queries():
    doc = document()
    assert doc["schema"] == "abl-phase4-offline-e08-batch/1"
    assert doc["valid"] is True and doc["errors"] == []
    assert [row["row_id"] for row in doc["selected_rows"]] == [
        "E08_props_movers_gates"]
    assert doc["offline_batch"]["capsule_count"] == 13
    assert doc["offline_batch"]["reconstructed_records"] == 5753
    assert doc["offline_batch"]["actor_typed_event_records"] == 2165
    assert doc["offline_batch"]["actor_change_records"] == 3364
    assert doc["offline_batch"]["actor_change_records_joined"] == 3364
    assert doc["offline_batch"]["query_count"] == 156
    assert doc["offline_batch"]["reader_sha256"] == \
        "b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde"
    assert doc["external_index"]["sha256"] == \
        "413151a8100bdfac686d0cddea136e53972536b4d797fafe9ced016c1ba065f0"
    assert all(row["actor_change_records"] == row["actor_change_records_joined"]
               for row in doc["capsule_summaries"])


def test_e08_uncontrolled_frontier_is_bounded_not_promoted():
    findings = document()["derived_findings"]
    assert findings["uncontrolled_type_words_observed"] == [
        "0x050d", "0x1b1f", "0x1e20", "0x1f04", "0x2223", "0x2528", "0x2629"]
    assert findings["uncontrolled_type_words_with_significant_changes"] == [
        "0x050d", "0x1b1f", "0x1e20", "0x2528", "0x2629"]
    assert findings["uncontrolled_type_words_with_only_vm_timing_changes"] == [
        "0x1f04", "0x2223"]
    assert len(findings["uncontrolled_type_words_absent"]) == 21
    assert findings["native_control_frontier_unchanged"] == {
        "class_owners_promoted": 0,
        "unclassified_with_native_outcome_controls": 19,
        "unclassified_without_native_outcome_control": 28,
    }
    assert document()["campaign_closed"] is False


def test_e08_known_live_boundaries_are_independently_reproduced():
    boundaries = document()["derived_findings"]["known_native_boundaries_reproduced"]
    assert [(row["movie_frame"], row["slot"], row["type_word"])
            for row in boundaries] == [
        (426, 11, "0x0f06"), (437, 23, "0x0c13"),
        (343, 1, "0x060c"), (400, 26, "0x0b11")]
    assert [row["changes"]["hp"] for row in boundaries] == [
        {"before": 8, "after": 6}, {"before": 6, "after": 4},
        {"before": 999, "after": 0}, {"before": 999, "after": 0}]
    assert all(row["reproduced"] for row in boundaries)


def test_e08_level11_correlation_remains_frame_boundary_only():
    correlations = document()["derived_findings"][
        "same_boundary_uncontrolled_player_actor_correlations"]
    assert [(row["movie"], row["movie_frame"], row["type_word"])
            for row in correlations] == [
        ("movies/Phase4/E10/hazard_acorn_LEVEL11.movie.json", 428, "0x1b1f"),
        ("movies/Phase4/E10/hazard_acorn_LEVEL11.movie.json", 548, "0x1b1f")]
    assert [row["player_fields"]["health"] for row in correlations] == [
        {"before": 1, "after": 0}, {"before": 0, "after": -1}]
    assert document()["live_escalation_ids"] == []
    assert "not causal or semantic ownership proof" in \
        document()["bounded_conclusions"][2]


def test_e08_summary_excludes_raw_copyrighted_domains():
    text = batch.OUTPUT.read_text()
    for forbidden in ("raw_ram", "raw_vram", "raw_spu_ram", "capsule_chunks",
                      "movie_bytes", "save_bytes"):
        assert forbidden not in text
    assert document()["external_index"]["media_class"].endswith("never commit")


def test_significant_policy_rejects_timer_noise_and_keeps_activations():
    assert not batch.significant_change({"vm_wait": {"before": 3, "after": 2}})
    assert not batch.significant_change({"knockback": {"before": 9, "after": 8}})
    assert batch.significant_change({"knockback": {"before": 0, "after": 15}})
    assert batch.significant_change({"hp": {"before": 8, "after": 6}})
