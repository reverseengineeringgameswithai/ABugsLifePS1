"""Fail-closed guards for per-session scenario debugger identity."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import ps1_scenario  # noqa: E402


def capabilities(binary: Path) -> dict:
    return {
        "binary": {
            "path": str(binary.resolve()),
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        },
        "method_count": 2,
        "methods": {"debugger.capabilities": {}, "emulator.getMediaInfo": {}},
    }


def test_runtime_capabilities_bind_exact_binary_and_method_count(tmp_path):
    binary = tmp_path / "duckstation-qt"
    binary.write_bytes(b"candidate-binary")
    ps1_scenario.verify_runtime_capabilities(capabilities(binary), binary)


def test_runtime_capabilities_reject_binary_hash_path_and_schema_drift(tmp_path):
    binary = tmp_path / "duckstation-qt"
    binary.write_bytes(b"candidate-binary")

    mutated = capabilities(binary)
    mutated["binary"]["sha256"] = "0" * 64
    with pytest.raises(ps1_scenario.ScenarioError, match="binary identity"):
        ps1_scenario.verify_runtime_capabilities(mutated, binary)

    mutated = capabilities(binary)
    mutated["binary"]["path"] = str(tmp_path / "other-binary")
    with pytest.raises(ps1_scenario.ScenarioError, match="binary identity"):
        ps1_scenario.verify_runtime_capabilities(mutated, binary)

    mutated = capabilities(binary)
    mutated["method_count"] = 3
    with pytest.raises(ps1_scenario.ScenarioError, match="method count"):
        ps1_scenario.verify_runtime_capabilities(mutated, binary)

    mutated = capabilities(binary)
    mutated["methods"].pop("emulator.getMediaInfo")
    mutated["method_count"] = len(mutated["methods"])
    with pytest.raises(ps1_scenario.ScenarioError, match="missing required methods"):
        ps1_scenario.verify_runtime_capabilities(
            mutated, binary, required_methods={"emulator.getMediaInfo"})
