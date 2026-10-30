"""Prevent host-specific paths from returning to tracked Python tools/tests.

Enforces the GAP-0003 portability rule: no tracked tool or test may embed a
user-home literal — an absolute path under ``/home`` or ``/Users``. Host-specific
locations must come from environment variables / CLI args (see ``tools/_env.py``).
"""

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOME_LITERAL = re.compile(r"/(?:home|Users)/[^/\s]+/")


def test_tracked_python_has_no_user_home_literals() -> None:
    from conftest import require_git
    require_git()
    result = subprocess.run(
        ["git", "ls-files", "tools/*.py", "tests/*.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    offenders = []
    for relative in result.stdout.splitlines():
        text = (ROOT / relative).read_text(encoding="utf-8")
        if HOME_LITERAL.search(text):
            offenders.append(relative)

    assert not offenders, (
        "tracked Python embeds user-home literals (use tools/_env.py / env "
        f"vars instead): {offenders}"
    )
