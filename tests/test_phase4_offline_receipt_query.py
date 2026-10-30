import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_offline_receipt_query.py"


def _run(tmp_path: Path, payload: dict, query: dict) -> dict:
    source = tmp_path / "source.json"
    output = tmp_path / "output.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--input",
            str(source),
            "--output",
            str(output),
            "--query-json",
            json.dumps(query),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    assert completed.stdout == "PASS: offline query\n"
    return json.loads(output.read_text(encoding="utf-8"))


def test_movie_query_retains_complete_input_spans(tmp_path):
    frames = [
        {"frame": 40, "ports": {"0": {"Cross": False, "LeftX": 128}}},
        {"frame": 41, "ports": {"0": {"Cross": True, "LeftX": 128}}},
        {"frame": 42, "ports": {"0": {"Cross": True, "LeftX": 127}}},
        {"frame": 43, "ports": {"0": {"Cross": False, "LeftX": 127}}},
    ]
    payload = {
        "format": "DuckStationInputMovie",
        "version": 3,
        "game_serial": "SCUS-94288",
        "initial_frame": 40,
        "start_state": {"from_boot": True},
        "frames": frames,
    }
    source_bytes = json.dumps(payload).encode()
    result = _run(tmp_path, payload, {
        "kind": "movie_inputs",
        "expected_frames": 4,
        "expected_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "row_id": "E15_fmv",
    })

    assert result["frames"] == {
        "active_count": 3,
        "active_spans": [{"start": 41, "stop": 43}],
        "count": 4,
        "explicit_frame_numbers": True,
        "first_active": 41,
        "last_active": 43,
    }
    assert result["controls"]["0:Cross"]["spans"] == [
        {"start": 41, "stop": 42}]
    assert result["controls"]["0:LeftX"]["spans"] == [
        {"start": 42, "stop": 43}]


def test_json_search_reports_bounded_exact_paths_and_absence(tmp_path):
    result = _run(tmp_path, {
        "schema": "example/1",
        "capsules": [
            {"movie": "movies/a.movie.json", "pc": "0x8004ffd4"},
            {"movie": "movies/b.movie.json", "pc": "0x8004ffd4"},
        ],
    }, {
        "kind": "json_search",
        "terms": ["0x8004FFD4", "Menu-Navigation.movie.json"],
        "match": "substring",
        "case_sensitive": False,
        "path_limit": 1,
        "row_id": "E15_fmv",
    })

    assert result["terms"]["0x8004FFD4"] == {
        "count": 2,
        "paths": ["/capsules/0/pc"],
        "paths_truncated": True,
    }
    assert result["terms"]["Menu-Navigation.movie.json"] == {
        "count": 0,
        "paths": [],
        "paths_truncated": False,
    }
    assert result["top_level"]["capsules"] == {
        "count": 2,
        "type": "list",
    }


def test_function_event_retention_derives_finite_same_anchor_bound(tmp_path):
    events = [
        {
            "index": index,
            "type": "entry" if index % 2 else "exit",
            "function": "0x800b6c24",
            "caller": "0x800b7280",
            "frame": 265900 + index,
            "cycle": 150500000000 + index * 100,
        }
        for index in range(27, 91)
    ]
    payload = {
        "schema": "abl-phase4-duckstation-batch-result/1",
        "result": {
            "jobs": [{
                "id": "decoded_record_native_nonzero_negative",
                "state": "completed",
                "result": {
                    "staged_prelude": {
                        "target_frame": 650,
                        "frames_advanced": 650,
                    },
                    "run": {
                        "start_playback_index": 650,
                        "target_frame": 850,
                        "frames_advanced": 200,
                    },
                    "capture": {
                        "traces": {"functions": events},
                    },
                },
            }],
        },
    }
    result = _run(tmp_path, payload, {
        "kind": "function_event_retention",
        "job_id": "decoded_record_native_nonzero_negative",
        "window": {"clock": "movie_frame", "start": 650, "stop": 850},
        "configured_max_events": 64,
        "expected_function": "0x800b6c24",
        "expected_caller": "0x800b7280",
        "proposed_max_events": 128,
        "required_headroom_events": 32,
        "row_id": "E15_fmv",
    })

    assert result["observed"]["total_emitted_events"] == 90
    assert result["observed"]["discarded_prefix_events"] == 26
    assert result["observed"]["event_rate"] == {
        "events": 90,
        "movie_frames": 200,
        "events_per_movie_frame": "0.450000",
    }
    assert result["successor_retention_contract"] == {
        "same_anchor_window": {
            "clock": "movie_frame", "start": 650, "stop": 850},
        "max_events": 128,
        "observed_event_upper_bound": 90,
        "headroom_events": 38,
        "required_headroom_events": 32,
        "require_first_retained_index": 1,
        "require_last_retained_index_lte": 90,
        "require_returned_events_lte": 90,
        "require_returned_events_lt_max": True,
        "discarded_event_types_claimed": False,
        "bounded_for_same_anchor_window": True,
    }


def test_receipt_authoring_records_replayable_command(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    receipt = tmp_path / "receipt.json"
    preservation = tmp_path / "preservation.json"
    source.write_text('{"needle":"present"}\n', encoding="utf-8")
    query = {
        "kind": "json_search",
        "terms": ["present"],
        "match": "exact",
        "case_sensitive": True,
        "path_limit": 4,
        "row_id": "E15_fmv",
    }
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--input",
            str(source),
            "--output",
            str(output),
            "--query-json",
            json.dumps(query),
            "--emit-receipt",
            str(receipt),
            "--preservation-manifest",
            str(preservation),
            "--run-root",
            str(tmp_path),
            "--input-media-class",
            "derived_pristine_evidence",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    document = json.loads(receipt.read_text(encoding="utf-8"))
    assert document["schema"] == "abl-phase4-offline-query/1"
    assert document["command"] == [
        "python3",
        "tools/phase4_offline_receipt_query.py",
        "--input",
        "@run/input.json",
        "--output",
        "@run/output.json",
        "--query-json",
        "@query",
    ]
    assert document["execution"]["stdout"] == "PASS: offline query\n"
    assert document["external_inputs"][0]["sha256"] == hashlib.sha256(
        source.read_bytes()).hexdigest()
    assert json.loads(preservation.read_text())["complete"] is True
