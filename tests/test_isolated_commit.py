"""Guards on tools/isolated_commit.sh.

Several agents share one checkout and therefore one .git/index. Anything staged
can be swept into another agent's `git commit -a` -- it happened twice in one
session. This script commits via a PRIVATE index so the shared one is never
staged into.

Its first version had a defect worse than the bug: it left the shared index
describing the old HEAD, so a just-added path showed there as a staged DELETION.
These gates keep both the isolation and that fix in place.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SH = ROOT / "tools/isolated_commit.sh"


def test_script_exists_and_parses():
    assert SH.is_file()
    subprocess.run(["bash", "-n", str(SH)], check=True)


def test_it_uses_a_private_index_not_the_shared_one():
    s = SH.read_text()
    assert "GIT_INDEX_FILE" in s
    assert "git read-tree" in s              # seeded from HEAD, not from shared state
    assert "commit-tree" in s and "update-ref" in s


def test_it_refuses_to_write_if_HEAD_moved():
    """A tree built on a stale base must not be forced onto the branch."""
    s = SH.read_text()
    assert 'if [[ "$NOW" != "$BEFORE" ]]' in s
    assert "exit 3" in s
    # update-ref is given the expected old value, so the ref move is itself guarded
    assert 'update-ref -m "isolated_commit" "refs/heads/$BRANCH" "$COMMIT" "$BEFORE"' in s


def test_it_resyncs_the_shared_index_so_no_phantom_deletion_is_left():
    """The defect that was worse than the bug: without this, a path just ADDED
    shows in the shared index as a staged DELETION, and the next agent's commit
    would apply it."""
    s = SH.read_text()
    assert "staged DELETION" in s
    assert "update-index --add --cacheinfo" in s
    assert "never stages working-tree content" in s


def test_it_does_not_git_add_shared_files_wholesale():
    """A shared file may carry other agents' edits; only our hunks go in, via a
    patch applied to the private index."""
    s = SH.read_text()
    assert "git apply --cached" in s
    assert "-p <patchfile>" in s or "patchfile" in s
