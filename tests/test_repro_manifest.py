"""Safe validation of the committed reproducibility manifest."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_reproducibility_manifest_matches() -> None:
    result = subprocess.run(
        [sys.executable, "tools/verify_repro_inputs.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
