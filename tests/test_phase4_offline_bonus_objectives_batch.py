"""Falsification guards for the generated bonus-objectives offline batch."""

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_offline_bonus_objectives_batch as batch  # noqa: E402


def document() -> dict:
    return json.loads(batch.OUTPUT.read_text())


def test_bonus_batch_recomputes_exact_external_index():
    _, rebuilt = batch.build(Path(document()["external_index"]["absolute_path"]))
    assert batch.render(rebuilt) == batch.OUTPUT.read_bytes()


def test_bonus_batch_pins_all_rows_capsules_and_domains():
    doc = document()
    assert doc["schema"] == "abl-phase4-offline-bonus-objectives-batch/1"
    assert doc["valid"] is True and doc["errors"] == []
    assert [row["row_id"] for row in doc["selected_rows"]] == [
        "C18_bonus_entry", "F16_bonus1_spiders",
        "F17_bonus2_mushrooms", "F18_bonus3_grasshoppers"]
    assert doc["offline_batch"]["capsule_count"] == 3
    assert doc["offline_batch"]["reconstructed_records"] == 18721
    assert doc["offline_batch"]["reader_sha256"] == \
        "b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde"
    assert doc["offline_batch"]["domains"] == [
        "registers", "ram", "vram", "spu_ram", "block_flow"]
    external = doc["external_index"]
    path = Path(external["absolute_path"])
    assert path.stat().st_size == external["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == external["sha256"]
    assert all(row["control_match"] is True for row in doc["capsule_summaries"])


def test_bonus_progress_and_shared_entry_are_exact():
    findings = document()["derived_findings"]
    assert [row["after"] for row in findings["F16_bonus1_spiders"]["progress_events"]] == \
        [1, 2, 3, 4, 0]
    assert [row["after"] for row in findings["F17_bonus2_mushrooms"]["progress_events"]] == [
        [6, -1, -1, -1, -1], [6, 5, -1, -1, -1],
        [6, 5, 4, -1, -1], [6, 5, 4, 2, -1], [6, 5, 4, 2, 3]]
    assert [row["after"] for row in findings["F18_bonus3_grasshoppers"]["progress_events"]] == \
        [1, 2, 3, 4, 0]
    assert findings["C18_bonus_entry"]["completion_frames"] == {
        "F16_bonus1_spiders": 1072,
        "F17_bonus2_mushrooms": 313,
        "F18_bonus3_grasshoppers": 2467,
    }
    assert findings["C18_bonus_entry"]["scene_16_frames"] == {
        "F16_bonus1_spiders": 1131,
        "F17_bonus2_mushrooms": 431,
        "F18_bonus3_grasshoppers": 2526,
    }
    for row_id in ("F16_bonus1_spiders", "F17_bonus2_mushrooms",
                   "F18_bonus3_grasshoppers"):
        completion = findings[row_id]["completion"]
        assert completion["state_changes"]["transition_latch"] == {
            "before": 0, "after": 6}
        assert any(value["decisive_block_start_covered"]
                   for value in completion["candidate_flow"].values())


def test_bonus_summary_excludes_raw_copyrighted_domains():
    text = batch.OUTPUT.read_text()
    assert "raw_ram" not in text
    assert "raw_vram" not in text
    assert "raw_spu_ram" not in text
    assert all(row["media_class"].endswith("never commit")
               for row in [document()["external_index"]])
