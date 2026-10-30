"""Bounded MIPS32LE oracle, model, and forbidden-domain tests."""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest


pytest.importorskip("unicorn")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_mips_oracle as oracle  # noqa: E402


def test_pilot_reproduces_all_generated_boundary_cases():
    report = oracle.build_report()
    assert report["schema"] == oracle.REPORT_SCHEMA
    assert report["engine"]["version"] == "2.1.4"
    assert report["summary"] == {
        "routines": 4, "generated_cases": 21, "passed_cases": 21,
        "failed_cases": 0, "all_models_match": True,
    }
    assert report["mutation_guards"]["all_passed"] is True
    assert report["boundary"]["behavioral_authority"] is False
    assert (ROOT / "analysis/phase4_mips_oracle_pilot.json").read_bytes() == \
        oracle.canonical_json(report)


def test_signed_unsigned_and_wrap_models_are_explicit():
    assert oracle.s32(0xFFFFFFFF) == -1
    assert oracle.evaluate_model(
        {"op": "slt_signed", "args": [{"reg": "a0"}, {"const": 0}]},
        {"a0": 0xFFFFFFFF}) == 1
    assert oracle.evaluate_model(
        {"op": "slt_unsigned", "args": [{"reg": "a0"}, {"const": 0}]},
        {"a0": 0xFFFFFFFF}) == 0
    assert oracle.evaluate_model(
        {"op": "add32", "args": [{"reg": "a0"}, {"const": 1}]},
        {"a0": 0xFFFFFFFF}) == 0


def test_static_preflight_rejects_cop0_gte_syscall_and_timing_class():
    assert oracle.validate_static_words([0x40026000])
    assert oracle.validate_static_words([0x4A000000])
    assert oracle.validate_static_words([0x0000000C])
    assert oracle.validate_static_words([0x0000000D])
    assert oracle.validate_static_words([0xBC000000])
    doc = oracle.load_spec()
    changed = copy.deepcopy(doc)
    changed["pilots"][0]["class"] = "timing_sensitive"
    with pytest.raises(oracle.OracleError, match="class"):
        oracle.validate_spec(changed)


def test_spec_rejects_engine_limits_and_unsafe_ram_contracts():
    doc = oracle.load_spec()
    changed = copy.deepcopy(doc)
    changed["engine"]["version"] = "2.1.3"
    with pytest.raises(oracle.OracleError, match="engine identity"):
        oracle.validate_spec(changed)
    changed = copy.deepcopy(doc)
    changed["pilots"][0]["max_instructions"] = doc["policy"]["max_instructions"] + 1
    with pytest.raises(oracle.OracleError, match="max_instructions"):
        oracle.validate_spec(changed)
    changed = copy.deepcopy(doc)
    changed["pilots"][0]["input_domains"]["a1"] = list(range(513))
    with pytest.raises(oracle.OracleError, match="max_cases"):
        oracle.validate_spec(changed)
    ram = copy.deepcopy(doc["pilots"][-1])
    ram["allowed_memory"] = [{"start": doc["policy"]["code_base"], "size": 4}]
    with pytest.raises(oracle.OracleError, match="overlaps code"):
        oracle.execute_case(ram, {"a0": doc["policy"]["code_base"]}, doc["policy"])
    ram = copy.deepcopy(doc["pilots"][-1])
    ram["memory_init"] = [{"address": 0x80030000, "words": [1]}]
    with pytest.raises(oracle.OracleError, match="outside allowed_memory"):
        oracle.execute_case(ram, {"a0": 0x80020000}, doc["policy"])


def test_wrong_model_is_detected_with_shrunk_counterexample():
    doc = oracle.load_spec()
    routine = copy.deepcopy(doc["pilots"][0])
    routine["model"] = {"const": 0}
    report = oracle.run_routine(routine, doc["policy"])
    assert report["status"] == "model_mismatch"
    assert report["failed_cases"] > 0
    assert report["minimal_counterexample"] is not None


def test_dynamic_self_modifying_mmio_and_unbounded_control_are_rejected():
    policy = oracle.load_spec()["policy"]
    self_modifying = {
        "id": "self_modifying", "class": "pure",
        # sw zero,0(a0); jr ra; nop
        "code_words": [0xAC800000, 0x03E00008, 0],
        "input_domains": {"a0": [policy["code_base"]]},
        "observe": {"type": "register", "name": "v0"}, "model": {"const": 0},
    }
    with pytest.raises(oracle.OracleError, match="self-modifying"):
        oracle.execute_case(self_modifying, {"a0": policy["code_base"]}, policy)
    mmio = copy.deepcopy(self_modifying)
    mmio["id"] = "mmio"
    mmio["code_words"][0] = 0x8C820000  # lw v0,0(a0)
    with pytest.raises(oracle.OracleError, match="MMIO"):
        oracle.execute_case(mmio, {"a0": 0x1F801000}, policy)
    loop = copy.deepcopy(self_modifying)
    loop["id"] = "loop"
    loop["code_words"] = [0x1000FFFF, 0x00000000]  # beq zero,zero,self; nop
    with pytest.raises(oracle.OracleError, match="did not return"):
        oracle.execute_case(loop, {"a0": 0}, policy)
