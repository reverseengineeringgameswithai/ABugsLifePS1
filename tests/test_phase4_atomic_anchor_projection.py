from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_atomic_anchor_projection.py"


def _fixture() -> tuple[dict, bytes, bytes]:
    memory = bytes(range(32))
    retired = bytes(reversed(range(32)))
    payload = {
        "schema": "abl-phase4-fmv-levelb-region-b-dma-exact-pc-live-result/1",
        "complete": True,
        "errors": [],
        "variant": "native",
        "server_session_id": "session-1",
        "normalized_identity": {
            "media": {"game_serial": "SCUS-94288", "sha256": "4" * 64},
        },
        "result": {
            "state": "completed",
            "jobs": [{
                "id": "anchor-job",
                "state": "completed",
                "result": {
                    "atomic_setup": True,
                    "media_verified": True,
                    "media": {
                        "game_serial": "SCUS-94288",
                        "sha256": "4" * 64,
                    },
                    "capture": {
                        "cpu": {
                            "status": {
                                "cycle": 123456,
                                "frame": 15816,
                                "paused": True,
                                "pc": "0x8004fea4",
                                "running": False,
                                "sp": "0x801fffd0",
                                "valid": True,
                            },
                            "registers": {
                                "registers_hex": {
                                    "pc": "0x8004fea4",
                                    "ra": "0x8004fe98",
                                    "s0": "0x8009ec68",
                                    "v0": "0x00000001",
                                    "v1": "0x00000001",
                                },
                            },
                        },
                        "memory": [{
                            "label": "region_b_head",
                            "address": "0x800b5788",
                            "length": len(memory),
                            "valid_bytes": len(memory),
                            "hex": memory.hex(),
                        }],
                    },
                },
            }],
        },
    }
    return payload, memory, retired


def _query(payload: dict, source_sha256: str, memory: bytes,
           retired: bytes) -> dict:
    return {
        "kind": "atomic_anchor_projection",
        "expected_schema": payload["schema"],
        "expected_variant": "native",
        "expected_source_sha256": source_sha256,
        "expected_media_sha256": "4" * 64,
        "expected_serial": "SCUS-94288",
        "job_id": "anchor-job",
        "expected_frame": 15816,
        "expected_cycle": 123456,
        "expected_pc": "0x8004fea4",
        "memory_label": "region_b_head",
        "expected_memory_address": "0x800B5788",
        "expected_memory_length": len(memory),
        "expected_memory_sha256": hashlib.sha256(memory).hexdigest(),
        "retired_memory_sha256": hashlib.sha256(retired).hexdigest(),
        "row_id": "E15_fmv",
    }


def test_atomic_anchor_projection_retains_identity_without_payload(tmp_path):
    payload, memory, retired = _fixture()
    source = tmp_path / "source.json"
    output = tmp_path / "output.json"
    source.write_text(json.dumps(payload))
    query = _query(
        payload, hashlib.sha256(source.read_bytes()).hexdigest(),
        memory, retired)
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--input", str(source),
            "--output", str(output),
            "--query-json", json.dumps(query),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    assert completed.stdout == "PASS: offline query\n"
    result = json.loads(output.read_text())
    assert result["result"]["anchor"] == {
        "cycle": 123456,
        "frame": 15816,
        "paused": True,
        "pc": "0x8004fea4",
        "selected_registers": {
            "pc": "0x8004fea4",
            "ra": "0x8004fe98",
            "s0": "0x8009ec68",
            "v0": "0x00000001",
            "v1": "0x00000001",
        },
        "sp": "0x801fffd0",
    }
    assert result["result"]["memory"]["payload_retained"] is False
    assert memory.hex() not in output.read_text()


def test_atomic_anchor_projection_rejects_media_identity_drift(tmp_path):
    payload, memory, retired = _fixture()
    source = tmp_path / "source.json"
    output = tmp_path / "output.json"
    payload["result"]["jobs"][0]["result"]["media"]["sha256"] = "5" * 64
    source.write_text(json.dumps(payload))
    query = _query(
        payload, hashlib.sha256(source.read_bytes()).hexdigest(),
        memory, retired)
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--input", str(source),
            "--output", str(output),
            "--query-json", json.dumps(query),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 1
    assert "pristine media identity drifted" in completed.stdout
