"""Adversarial guards for the E15 residency-qualified shared-PC boundary."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_resident_identity as identity  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_resident_identity.json"
ARTIFACT_SHA256 = \
    "cf048f8fbb732e41180a59549b330ff504e835d6e195469c7a025d252264798b"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_resident_identity_recomputes_from_hash_verified_pristine_inputs():
    retained = load_artifact()
    assert identity.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["inputs"]["exact_owner_source"]["pin_verified"] is True
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_both_shared_pcs_require_exact_resident_code_identity_and_abi():
    retained = load_artifact()
    assert retained["resident_owner"] == {
        **retained["resident_owner"],
        "start": "0x8004FCA0",
        "end": "0x800502C4",
        "size": 1572,
        "sha256": "02fc946a4c8757792f646d23e5cabdac5e0cf4755211b733cc75aa15b2f0592f",
    }
    calls = {row["id"]: row for row in retained["callsites"]}
    assert set(calls) == {"game_over_lose", "finale_lev15c"}
    assert calls["game_over_lose"]["selector"]["value"] == 46
    assert calls["game_over_lose"]["call"]["instruction"]["pc"] == "0x800500D8"
    assert calls["game_over_lose"]["delay"]["mode"] == 0
    assert calls["game_over_lose"]["return_pc"] == "0x800500E0"
    assert calls["finale_lev15c"]["selector"]["value"] == 40
    assert calls["finale_lev15c"]["call"]["instruction"]["pc"] == "0x80050284"
    assert calls["finale_lev15c"]["delay"]["mode"] == 0
    assert calls["finale_lev15c"]["return_pc"] == "0x8005028C"
    assert all(len(row["runtime_admission"]) == 6 for row in calls.values())
    assert retained["summary"]["unclassified_shared_pcs"] == 0


def test_synthetic_control_binds_the_executed_staged_interface():
    control = load_artifact()["synthetic_control"]
    assert control["only_difference"] == {
        "kind": "code_write",
        "address": 0x800500D4,
        "original_word": 0x2404002E,
        "replacement_word": 0x24040028,
    }
    assert control["baseline"] == {
        "caller": 0x800500D8,
        "return_pc": 0x800500E0,
        "selector": 46,
        "mode": 0,
        "selected_frame_limit": 281,
    }
    assert control["positive"] == {
        "caller": 0x800500D8,
        "return_pc": 0x800500E0,
        "selector": 40,
        "mode": 0,
        "selected_frame_limit": 3162,
    }
    assert control["passive_prelude"]["start"] < \
        control["execution_bound"]["start"]
    assert control["admissibility"]["static_specification_complete"] is True
    assert control["admissibility"]["scenario_method_supported"] is True
    assert control["admissibility"]["atomic_staged_prelude_supported"] is True
    assert control["admissibility"]["live_execution_predeclared"] is True
    assert control["admissibility"]["intrinsic_v2_receipts_valid"] is True
    assert control["admissibility"][
        "method_trial_receipts_admissible"] is False
    assert "P4-ITER99" in control["admissibility"]["reason"]
    assert control["method_support"]["predeclared_plans"] == {
        "escalation_id":
            "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL",
        "missing_fact_id": "E15/c16-staged-selector40-lifecycle",
        "passive":
            "config/phase4_fmv_c16_staged_selector_passive_batch.yaml",
        "precise":
            "config/phase4_fmv_c16_staged_selector_control_batch.yaml",
        "execution_state": "executed",
    }
    assert control["runtime_result"] == {
        "path": "analysis/phase4_fmv_c16_selector_control_result.json",
        "sha256":
            "831389a00758bf3fa75dfd6fdd46e2115b72cb5c04a517b716c1750c330bdcaf",
        "classification":
            "confirmed_staged_selector_interface_control_unadmitted",
        "falsifier": "survived",
        "intrinsically_valid_live_receipts": 2,
        "method_trial_admissible_live_receipts": 0,
        "method_admission_status": "rejected_conservative_pre_v2_overlap",
        "dimension_promoted": False,
    }
    assert control["method_support"]["adapter"][
        "atomic_staged_prelude_supported"] is True
    assert control["method_support"]["adapter"][
        "raw_counter_clock_derived"] is True
    assert control["method_support"]["staged_prelude"] == {
        "kind": "movie_advance",
        "exact_keys": ["kind", "target_frame", "max_frames"],
        "require_loaded_movie": True,
        "require_positive_target": True,
        "require_actual_playback_counters": True,
        "boot_recipe_rejected": True,
    }
    assert control["method_support"]["operation"] == control["only_difference"]
    assert control["method_support"]["fail_closed"] == {
        "exact_keys": [
            "kind", "address", "original_word", "replacement_word",
        ],
        "require_aligned_cached_main_ram": True,
        "require_original_word_match": True,
        "require_replacement_readback": True,
        "invalidate_code_cache": True,
        "boot_recipe_rejected": True,
    }
    assert load_artifact()["summary"]["dimension_promoted"] is False
    assert load_artifact()["summary"]["live_runs_authorized"] == 2


@pytest.mark.local_media
def test_callsite_owner_and_synthetic_contract_mutations_fail_closed():
    exe = bytearray(identity.EXE_PATH.read_bytes())
    offset = identity.EXE_HEADER + 0x800500D8 - identity.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="resident scene-flow owner identity"):
        identity.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(identity.EXE_PATH.read_bytes())
    offset = identity.EXE_HEADER + 0x80050284 - identity.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="resident scene-flow owner identity"):
        identity.build(exe_data=bytes(exe), verify_identity=False)

    source = yaml.safe_load(identity.SOURCE.read_text())
    changed = copy.deepcopy(source)
    changed["synthetic_control"]["only_difference"]["replacement_word"] = \
        0x2404002D
    with pytest.raises(
            SystemExit, match="synthetic selector only-difference"):
        identity.build(source_doc=changed)

    changed = copy.deepcopy(source)
    changed["callsites"][0]["call"]["target"] = 0x8003E7C4
    with pytest.raises(SystemExit, match="callsite source contract drifted"):
        identity.build(source_doc=changed)

    changed = copy.deepcopy(source)
    changed["synthetic_control"]["method_support"]["fail_closed"][
        "require_original_word_match"] = False
    with pytest.raises(SystemExit, match="method-support contract drifted"):
        identity.build(source_doc=changed)

    changed = copy.deepcopy(source)
    changed["synthetic_control"]["method_support"]["staged_prelude"][
        "require_actual_playback_counters"] = False
    with pytest.raises(SystemExit, match="method-support contract drifted"):
        identity.build(source_doc=changed)

    changed = copy.deepcopy(source)
    changed["synthetic_control"]["method_support"]["duckstation"][
        "release_binary_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="method-support contract drifted"):
        identity.build(source_doc=changed)
