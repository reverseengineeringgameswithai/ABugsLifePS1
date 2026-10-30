"""Compile and import checks for tracked Python tools."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def tracked_python_tools() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "tools/*.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines()]


def test_tracked_tools_compile_without_writing_bytecode() -> None:
    from conftest import require_git
    require_git()
    paths = tracked_python_tools()
    assert paths
    for path in paths:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec", dont_inherit=True)


def test_safe_codec_modules_import() -> None:
    import decode_level_raw  # noqa: F401
    import recompress_level_raw  # noqa: F401
