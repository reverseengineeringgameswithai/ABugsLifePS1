"""Phase-4 E08 pristine-ASM/runtime-semantics gate."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_e08_runtime_static_frontier(tmp_path):
    exe = tmp_path / "phase4_e08_runtime_static"
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(exe),
            str(ROOT / "tools/phase4_e08_runtime_static.c"),
        ],
        check=True,
    )
    dats = sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.DAT"))
    bins = sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.BIN"))
    result = subprocess.run(
        [
            str(exe),
            str(ROOT / "REBUILD/files/SCUS_942.88"),
            *(str(path) for path in dats),
            "--bins",
            *(str(path) for path in bins),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["asm_pins"] == {"checked": 21, "ok": True}
    assert data["metadata_b_ctors_84_88"] == {"checked": 5, "ok": True}
    assert data["kind31"] == {
        "records": 39,
        "files": 8,
        "groups_of_5": 7,
        "groups_of_4": 1,
        "all_y_minus_600_status_0_rest_0": True,
    }
    assert data["pass3_direct_formed_xrefs"] == {
        "resident_and_level_overlays": 21,
        "reads": 1,
        "writes": 0,
    }


def test_e08_runtime_disposition_is_bounded_partial():
    data = json.loads(
        (ROOT / "analysis/phase4_e08_runtime_semantics.json").read_text()
    )
    assert data["status"] == "substantiated_partial"
    assert data["disposition"] == "bounded_exhausted_move_on"
    assert data["movie"]["required_now"] is False
