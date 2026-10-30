"""Guards for the C11 (seed tokens, kind->color map) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_c11_seed_tokens.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c11_seed_tokens.json"
SOURCE = ROOT / "src_re" / "pickup_handlers_80054288_80054554.c"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_kind_to_color_map_matches_source():
    doc = load_artifact()
    kmap = doc["SYNTHESIZED_FROM_EXISTING_EVIDENCE_2026-08-03"]["kind_to_color_map"]
    for kind, color, addr in [
        ("0x29", "brown/orange", "0x800A6598"),
        ("0x2A", "blue", "0x800A6599"),
        ("0x2B", "green", "0x800A659A"),
        ("0x2C", "purple", "0x800A659B"),
        ("0x2D", "yellow", "0x800A659C"),
    ]:
        assert kind in kmap and color in kmap and addr in kmap


def test_source_file_actually_implements_the_cited_handler():
    src = SOURCE.read_text()
    assert "source_seed_token_action" in src
    assert "case 0x29:" in src
    assert "case 0x2a:" in src
    assert "case 0x2b:" in src
    assert "case 0x2c:" in src
    assert "case 0x2d:" in src
    assert "fcn_80050994(-3)" in src


def test_counter_encoding_confirmed():
    doc = load_artifact()
    enc = doc["SYNTHESIZED_FROM_EXISTING_EVIDENCE_2026-08-03"]["counter_encoding_confirmed"]
    assert "n*17" in enc
    assert "17==1 mod 8" in enc or "17 ≡ 1" in enc or "mod 8" in enc


def test_pickup_feedback_answered():
    doc = load_artifact()
    fb = doc["SYNTHESIZED_FROM_EXISTING_EVIDENCE_2026-08-03"]["pickup_feedback_confirmed"]
    assert "fcn_80050994(-3)" in fb


def test_still_open_distinguishes_counter_lifecycle_from_output_array():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "0x800A6598" in still_open
    assert "distinct" in still_open.lower()


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: C11_seed_tokens")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "C11_seed_tokens"
    assert row["status"] == "partial"
    assert "SYNTHESIZED FROM EXISTING EVIDENCE 2026-08-03" in " ".join(row["bindings"])
    assert "bounded via synthesis 2026-08-03" in row["next"]
