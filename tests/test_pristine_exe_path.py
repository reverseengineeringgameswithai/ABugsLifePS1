"""No tool or test may reach for the pristine EXE at a path git ignores.

Two fresh verifiers found the same defect from opposite directions: a soundness
gate that silently did not execute, and a corroboration test that could not run.
Both hardcoded `ROOT/"SCUS_942.88"` -- a convenience copy in the operator's
working tree, listed in `.gitignore`. The canonical location is
`REBUILD/files/SCUS_942.88`, which is where the project asks the operator to put
the disc.

The consequence was worse than a failing test: a test that only passes on one
machine is not a test, and one of these was F01's own independent corroboration.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "REBUILD/files/SCUS_942.88"


def _bad_exe_paths(tree: ast.AST) -> list[str]:
    """Path expressions that reach the EXE anywhere but the canonical location.

    Matched on the parsed AST, not on text: a docstring explaining this very rule
    contains the pattern verbatim, and so does this file. A prose mention is not a
    path reference -- the same distinction the extent audit had to learn.

    TWO spellings, because checking only the first is how this guard was wrong the
    first time it was written:

      ROOT / "SCUS_942.88"     the operator's convenience copy
      Path("SCUS_942.88")      relative to the CURRENT WORKING DIRECTORY, so it
                               depends on where the tool happens to be invoked

    NOT flagged: `EXE_REL = "SCUS_942.88"` joined to `REBUILD_FILES` elsewhere,
    and pin/baseline dictionary keys. Those are the correct idiom -- a bare name,
    resolved against the canonical root by its consumer.
    """
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            right = node.right
            if (isinstance(right, ast.Constant) and right.value == "SCUS_942.88"
                    and isinstance(node.left, ast.Name)
                    and node.left.id.endswith("ROOT")):
                hits.append(f'{node.lineno} (ROOT / "SCUS_942.88")')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "Path" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and arg.value == "SCUS_942.88":
                hits.append(f'{node.lineno} (Path("SCUS_942.88"), cwd-relative)')
    return hits


def _tracked(suffix: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", suffix], capture_output=True,
                         text=True, cwd=ROOT)
    return [ROOT / p for p in out.stdout.split() if p]


def test_no_tracked_source_uses_the_gitignored_copy():
    offenders = []
    for path in _tracked("tools/*.py") + _tracked("tests/*.py"):
        try:
            tree = ast.parse(path.read_text(errors="replace"))
        except SyntaxError:
            continue
        for hit in _bad_exe_paths(tree):
            offenders.append(f"{path.relative_to(ROOT)}:{hit}")
    assert not offenders, (
        "these reach the pristine EXE at a .gitignore'd path, so they work only on "
        "a machine that happens to have the convenience copy:\n" + "\n".join(offenders))


def test_the_canonical_path_is_the_one_the_project_declares():
    """Guard the premise.

    BOTH paths are git-ignored -- the disc is copyrighted and lives outside the
    repository by design. So "ignored vs tracked" is not the distinction. The
    canonical location is the one the project's own static index declares, and
    that is what every tool should resolve.
    """
    index = json.loads((ROOT / "analysis/phase4_static_frontier_index.json").read_bytes())
    declared = [i["path"] for i in index["images"] if i["image_id"] == "SCUS_942_88"]
    assert declared == [CANONICAL], (
        f"the static index now declares {declared}; this suite enforces "
        f"{CANONICAL} and should be updated deliberately, not left enforcing a "
        "path the project no longer uses")


def test_no_retained_artifact_embeds_this_checkout_s_absolute_path():
    """A correct artifact that cannot be regenerated elsewhere is unverifiable.

    Three separate artifacts have now shipped with an absolute path baked in --
    the typed-state image map, the extent audit's file list, and the static
    index's jump-table provenance -- and each one silently failed `--check` for an
    independent verifier on a clean checkout while passing for its author.
    """
    offenders = []
    for name in ("phase4_static_frontier_index.json", "phase4_f01_typed_state.json",
                 "phase4_extent_audit.json", "phase4_f01_frontier_blockers.json",
                 "phase4_f01_frontier_extraction.json", "phase4_evidence_dag.json"):
        path = ROOT / "analysis" / name
        if not path.is_file():
            continue
        if str(ROOT) in path.read_text(errors="replace"):
            offenders.append(name)
    assert not offenders, (
        "these embed this checkout's absolute path and will not reproduce "
        f"elsewhere: {offenders}")
