"""Safe format regression for the persisted M3 symbol baseline."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_symbol_map_is_import_safe() -> None:
    result = subprocess.run(
        [sys.executable, "tools/validate_symbol_map.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unique, sorted symbols" in result.stdout


def _map_size() -> int:
    """Derive the expected count from the map itself (the map legitimately grows —
    e.g. the 2026-07-08 PsyQ signature merge took it 129 -> 761)."""
    sym = ROOT / "symbols" / "re_symbols.sym"
    return len(sym.read_text(encoding="ascii").splitlines())


def test_symbol_consumer_round_trips(tmp_path: Path) -> None:
    count = _map_size()
    for format_name, suffix in (("duckstation-csv", ".csv"), ("r2", ".r2")):
        output = tmp_path / f"re_symbols{suffix}"
        result = subprocess.run(
            [
                sys.executable,
                "tools/symbol_roundtrip.py",
                "--format",
                format_name,
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert f"{count} symbols round-tripped" in result.stdout
        lines = output.read_text(encoding="ascii").splitlines()
        if format_name == "duckstation-csv":
            assert lines[0] == "address,name,comment"
            assert lines[1] == "0x1F800374,provisional_camera_scratch_1F800374,"
            assert len(lines) == count + 1
        else:
            assert lines[0] == "f provisional_camera_scratch_1F800374 = 0x1F800374"
            assert len(lines) == count
