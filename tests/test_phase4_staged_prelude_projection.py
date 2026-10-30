from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_staged_prelude_projection.py"


def _fixture() -> dict:
    job_ids = ["passive-native", "passive-repeat"]
    jobs = []
    for job_id in job_ids:
        jobs.append(
            {
                "id": job_id,
                "state": "completed",
                "recipe": "bootAndRun",
                "result": {
                    "atomic_setup": True,
                    "media_verified": True,
                    "media": {
                        "game_serial": "SCUS-94288",
                        "sha256": "4" * 64,
                    },
                    "instrumentation": [],
                    "staged_prelude": {
                        "start_frame": 1,
                        "target_frame": 15720,
                        "frames_advanced": 15719,
                        "status": {
                            "cycle": 123456,
                            "frame": 15720,
                            "paused": True,
                            "pc": "0x800b7420",
                            "running": False,
                            "sp": "0x801ff0c8",
                            "valid": True,
                        },
                    },
                    "run": {"frames_advanced": 400},
                },
            }
        )
    return {
        "schema": "abl-phase4-duckstation-batch-result/1",
        "campaign_id": "fmv_playback",
        "row_ids": ["E15_fmv"],
        "expected_media": {
            "serial": "SCUS-94288",
            "sha256": "4" * 64,
            "tracks": [{"sha256": "6" * 64}],
        },
        "expected_debugger": {
            "binary_sha256": "5" * 64,
            "source_revision": "revision",
            "dirty_state_hash": "dirty-state",
        },
        "mounted_media": {"game_serial": "SCUS-94288"},
        "result": {"state": "completed", "jobs": jobs},
    }


def _query(source: Path) -> dict:
    return {
        "kind": "staged_prelude_projection",
        "expected_schema": "abl-phase4-duckstation-batch-result/1",
        "expected_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "expected_cue_sha256": "4" * 64,
        "expected_track_sha256": "6" * 64,
        "expected_serial": "SCUS-94288",
        "expected_binary_sha256": "5" * 64,
        "expected_source_revision": "revision",
        "expected_dirty_state_hash": "dirty-state",
        "campaign_id": "fmv_playback",
        "row_id": "E15_fmv",
        "job_ids": ["passive-native", "passive-repeat"],
        "expected_start_frame": 1,
        "expected_frame": 15720,
        "expected_frames_advanced": 15719,
        "expected_run_frames": 400,
        "expected_pc": "0x800b7420",
    }


def _run(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    source = tmp_path / "source.json"
    output = tmp_path / "output.json"
    source.write_text(json.dumps(payload))
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--input",
            str(source),
            "--output",
            str(output),
            "--query-json",
            json.dumps(_query(source)),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_staged_prelude_projection_retains_equal_cpu_boundary(tmp_path):
    completed = _run(tmp_path, _fixture())
    assert completed.returncode == 0, completed.stdout
    assert completed.stdout == "PASS: offline query\n"
    result = json.loads((tmp_path / "output.json").read_text())
    assert result["result"]["paired_cpu_boundary_equal"] is True
    assert result["result"]["boundary"] == {
        "cycle": 123456,
        "frame": 15720,
        "pc": "0x800b7420",
        "pc_expected": "0x800b7420",
        "sp": "0x801ff0c8",
    }
    assert result["result"]["payload_retained"] is False


def test_staged_prelude_projection_rejects_pc_drift(tmp_path):
    payload = _fixture()
    payload["result"]["jobs"][1]["result"]["staged_prelude"]["status"][
        "pc"
    ] = "0x8004fea4"
    completed = _run(tmp_path, payload)
    assert completed.returncode == 1
    assert "differs from the expected boundary" in completed.stdout


def test_staged_prelude_projection_rejects_track_identity_drift(tmp_path):
    payload = _fixture()
    payload["expected_media"]["tracks"][0]["sha256"] = "7" * 64
    completed = _run(tmp_path, payload)
    assert completed.returncode == 1
    assert "mounted-media identity drifted" in completed.stdout


def test_staged_prelude_projection_rejects_paired_cycle_drift(tmp_path):
    payload = _fixture()
    payload["result"]["jobs"][1]["result"]["staged_prelude"]["status"][
        "cycle"
    ] += 1
    completed = _run(tmp_path, payload)
    assert completed.returncode == 1
    assert "CPU boundaries diverged" in completed.stdout
