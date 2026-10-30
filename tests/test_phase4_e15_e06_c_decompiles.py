"""Guards for the 2026-08-02 real-C-decompile pass on E15 (FMV) and E06 (contact pool).

Two new documentation-grade src_re files, neither a build unit (matching the existing
contact_alloc_80059e44.c / contact_walker_800586b0.c convention): the FMV movie-id
dispatch table (fmv_movie_dispatch_800b6250.c) and the contact-object billboard renderer
(contact_billboard_render_80014844.c). This pins that they compile and that the FMV table
matches the JSON artifact it was transcribed from -- catches transcription drift.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_RE = ROOT / "src_re"
FMV_C = SRC_RE / "fmv_movie_dispatch_800b6250.c"
RENDER_C = SRC_RE / "contact_billboard_render_80014844.c"
SCATTER_C = SRC_RE / "contact_scatter_component_800593e8.c"
ALLOC_C = SRC_RE / "contact_alloc_80059e44.c"

HAVE_GCC = shutil.which("gcc") is not None
skip_no_gcc = pytest.mark.skipif(not HAVE_GCC, reason="gcc not available")


@skip_no_gcc
@pytest.mark.parametrize("src", [FMV_C, RENDER_C, SCATTER_C, ALLOC_C])
def test_c_file_compiles_with_no_errors(src):
    # -Wall intentionally NOT used: these files model 32-bit PS1 addresses via uintptr_t
    # casts on a 64-bit host (pointer-size-cast warnings are expected, not a defect), and
    # some GTE FIFO outputs are deliberately left as opaque locals (unused-variable
    # warnings, not a defect -- the real hardware register has no C representation here).
    # The property this guards is "no syntax/type ERRORS" -- it would have caught the
    # actual bug found while writing these files (a missing <stddef.h> for NULL).
    proc = subprocess.run(
        ["gcc", "-fsyntax-only", "-std=c99", "-I", str(SRC_RE), str(src)],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "error" not in proc.stderr.lower(), proc.stderr


def test_fmv_dispatch_table_matches_the_json_artifact_exactly():
    artifact = json.loads(
        (ROOT / "analysis/phase4_e15_fmv_frontier.json").read_text())
    table = artifact["MOVIE_ID_TABLE_2026-08-02"]["table"]

    text = FMV_C.read_text()
    rows = re.findall(
        r'/\*\s*(\d+)\s*\*/\s*\{\s*(NULL|"[^"]+")\s*,\s*(\d+)\s*\}', text)
    assert len(rows) == 47
    for idx_s, path_s, frames_s in rows:
        idx = int(idx_s)
        expected_path, expected_frames = table[str(idx)]
        if path_s == "NULL":
            assert expected_path == "DEFAULT", idx
        else:
            c_path = path_s.strip('"').replace("\\\\", "\\")
            assert c_path == expected_path, idx
            assert int(frames_s) == expected_frames, idx


def test_fmv_dispatch_c_file_carries_the_supersession_and_irregularity_notes():
    text = FMV_C.read_text()
    assert "SUPERSEDES an earlier" in text
    assert "swapped" in text.lower()
    assert "4-clip special case" in text


def test_renderer_c_file_documents_the_shared_descriptor_table_correction():
    text = RENDER_C.read_text()
    assert "REFUTED" in text
    assert "0x8001B570" in text
    assert "0x2E" in text and "bubble" in text.lower()


def test_renderer_c_file_encodes_the_action_id_zero_do_not_draw_rule():
    text = RENDER_C.read_text()
    assert "action_id == 0" in text
    assert "do not draw" in text.lower() or "do-not-draw" in text.lower()


def test_scatter_component_filename_matches_its_own_documented_address():
    # a real typo caught while writing this file: the filename originally read
    # "80059e3e8" (9 hex digits, one extra) instead of the correct "800593e8".
    assert SCATTER_C.exists(), "renamed file must exist at the corrected address"
    assert not (SRC_RE / "contact_scatter_component_80059e3e8.c").exists()
    text = SCATTER_C.read_text()
    assert "0x800593E8" in text
    assert hex(0x800593E8)[2:] in SCATTER_C.stem


def test_alloc_c_points_at_the_now_solved_scatter_component_file():
    text = ALLOC_C.read_text()
    assert "contact_scatter_component_800593e8.c" in text
    assert "SOLVED" in text
