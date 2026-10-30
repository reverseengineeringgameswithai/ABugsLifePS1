#!/usr/bin/env python3
"""Find hand-typed function extents that stop short of the real function.

WHY THIS EXISTS
---------------
`tools/phase4_f01_frontier_resolve.c` carried a hand-typed `EXTENTS` table and 20
of its 29 entries had ends SHORTER than the functions they named -- 28,252 bytes
/ 7,063 instructions inside the very extents its census claimed to cover were
never read. Every count it reported as a total was a lower bound: 1,960 accesses
(really 3,681), 106 unresolved stores (really 231).

Nothing in that tool could detect it. The truncated range was self-consistent,
and the scope was declared in prose while the walk used a constant nobody
re-derived. The same pattern is cheap to write and easy to repeat, so this
audits every source file against the authoritative function ends in
`analysis/phase4_static_frontier_index.json`.

HOW IT DECIDES SOMETHING IS AN EXTENT
-------------------------------------
Two conditions, and the second is what makes the result readable.

1. The FIRST address is an exact function entry the index knows.
2. The line also carries that function's NAME.

Condition 1 alone yields 343 "findings", and every one inspected was noise: an
access-site id (`...player_vertical_update@0x80048138_0x80048518`), a decomp
segment range in `segments.yml`, prose `0x80048138..0x800498AB` in a campaign
row, a data-table boundary. Functions are ~1 KB, so any nearby constant lands
inside one.

A row that gives a start, an end, AND the function's own name is a declaration
*about that function*, which is precisely the F01 shape:

    { "SCUS", 0x8004abf4, 0x8004b5f4, "actor_player_contact_resolver" }

A coincidental address pair does not also carry the name.

Verdicts:
  exact        end == the index's end. Nothing to do.
  inclusive    end == index end - 1, i.e. an inclusive range written as
               `0x80048138..0x800498AB`. A notation difference, not a truncation.
  TRUNCATED    entry < end < index end. The F01 bug. Reports the missed bytes.
  over_extent  end > index end. Not the same bug, but the range covers code the
               index attributes to another function; worth knowing.
  unrelated    end is nowhere near the index's end -- almost certainly not an
               extent at all, just two addresses sharing a line. Reported in the
               counts so the filter's own reach is visible, never as a finding.

AMBIGUITY IS NOT RESOLVED SILENTLY
----------------------------------
All 20 level overlays load at the same address, so one entry can belong to many
images. When a line does not name an image, every candidate end is reported and
the row is marked ambiguous rather than guessed -- the same identity discipline
the rest of this pipeline uses.

Usage
  tools/phase4_extent_audit.py [--json OUT] [PATH ...]
Exit 1 if any TRUNCATED extent is found.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "analysis/phase4_static_frontier_index.json"
ADDR = re.compile(r"0x[0-9A-Fa-f]{6,8}")
# A declaration whose STRUCTURE says "range", so no name match is needed:
#   name: (0xA, 0xB)      name: [0xA, 0xB]      {start: 0xA, end: 0xB}
# This is the complement to the name test -- a tool that calls a function by its
# own local name (`damage_and_death_initiator` for what the index calls
# `resident_level_transition_initiator`) is invisible to a name match, and those
# are exactly the tables most likely to have been typed by hand.
STRUCTURAL = re.compile(
    r"""(?:\(|\[)\s*(0x[0-9A-Fa-f]{6,8})\s*,\s*(0x[0-9A-Fa-f]{6,8})\s*(?:\)|\])"""
    r"""|start\s*[:=]\s*['"]?(0x[0-9A-Fa-f]{6,8})['"]?\s*,\s*end\s*[:=]\s*['"]?(0x[0-9A-Fa-f]{6,8})""",
    re.VERBOSE)
# Beyond this a pair is two unrelated constants, not a function and its end.
MAX_EXTENT = 0x20000
DEFAULT_PATHS = ("tools", "config")
ACK_PATH = ROOT / "config/phase4_extent_audit_acknowledged.yaml"
SKIP_DIRS = {".git", "__pycache__", "build", "REBUILD"}
# This file quotes a specimen extent row in its own docstring; auditing itself
# would report that specimen as a finding.
SKIP_FILES = {"tools/phase4_extent_audit.py"}
SUFFIXES = {".c", ".h", ".py", ".yaml", ".yml", ".json"}


def rel(path: Path) -> str:
    """Repo-relative when inside the repo, absolute when not.

    `Path.relative_to` raises for anything outside ROOT, which made auditing a
    scratch directory crash instead of answering.
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_index() -> tuple[dict[int, list[tuple[str, int, str]]], set[str]]:
    index = json.loads(INDEX_PATH.read_bytes())
    by_entry: dict[int, list[tuple[str, int, str]]] = {}
    for record in index["records"]:
        if not record.get("entry") or not record.get("end"):
            continue
        # CODE only. The index also records data extents -- `master_game_state`
        # spans 0x800823A0..0x800823CC -- and a schema declaring a two-byte
        # watched window at 0x800823A0 is not a truncated function.
        if record.get("range_type") != "code":
            continue
        entry = int(str(record["entry"]), 16)
        by_entry.setdefault(entry, []).append(
            (record["image_id"], int(str(record["end"]), 16),
             str(record.get("name") or "")))
    return by_entry, {i["image_id"] for i in index["images"]}


BLOCK_COMMENT = re.compile(r"/\*.*?\*/")
LINE_COMMENT_C = re.compile(r"//.*$")
LINE_COMMENT_HASH = re.compile(r"(?:^|\s)#.*$")


def strip_comments(line: str, suffix: str) -> str:
    """A comment is not a declaration.

    Fixing F01's table left the old value in a trailing comment --
    `{ ..., 0x8004b6dc, "..." },   /* was 0x8004b5f4 */` -- and the audit
    dutifully reported the corrected file as still truncated. Reporting a repair
    as the bug it repaired is worse than useless.
    """
    if suffix in (".c", ".h"):
        return LINE_COMMENT_C.sub("", BLOCK_COMMENT.sub(" ", line))
    if suffix in (".py", ".yaml", ".yml"):
        return LINE_COMMENT_HASH.sub("", line)
    return line


def audit_file(path: Path, by_entry: dict, images: set[str]) -> list[dict]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    findings = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = strip_comments(raw, path.suffix)
        spans = [(int(m.group(0), 16), m.start(), m.end()) for m in ADDR.finditer(line)]
        if len(spans) < 2:
            continue
        addrs = [v for v, _, _ in spans]
        named = sorted(i for i in images if i in line)
        structural_pairs = {}
        for m in STRUCTURAL.finditer(line):
            a, b = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            structural_pairs[int(a, 16)] = int(b, 16)
        for i, (entry, _e_start, e_end) in enumerate(spans):
            candidates = by_entry.get(entry)
            if not candidates:
                continue
            if named:
                candidates = [c for c in candidates if c[0] in named] or candidates
            structural = entry in structural_pairs
            # The line must NAME the function it is declaring an extent for,
            # UNLESS its structure already says the pair is a range.
            # Without this the join is dominated by unrelated constants that
            # happen to land inside a ~1 KB function.
            named_here = [c for c in candidates if c[2] and c[2] in line]
            if named_here:
                candidates = named_here
            elif not structural:
                findings.append({"verdict": "unnamed"})
                continue
            ends_here = {c[1] for c in candidates}
            # If this line ALSO states the correct end for this entry, then the
            # extent it declares is right and every other address on the line is
            # something else -- a writer_pc, an arm_pc, a sub-part start. A line
            # does not declare both the true extent and a truncated one.
            if not structural and any(v in ends_here for v, _, _ in spans[i + 1:]):
                findings.append({"verdict": "exact"})
                continue
            if structural:
                # Judge the STRUCTURAL pair, not every address on the line.
                spans_to_check = [(structural_pairs[entry], 0, 0)]
            else:
                spans_to_check = spans[i + 1:]
            for end, b_start, _b_end in spans_to_check:
                if not entry < end <= entry + MAX_EXTENT:
                    continue
                # A declaration separates its fields. When the two addresses are
                # glued inside ONE token they are not a start and an end -- they
                # are an identifier, and the commonest such identifier in this
                # repo is an access-site id:
                #     SCUS_942_88:player_vertical_update@0x80048138_0x80048518
                # which carries the function name too, so the name test alone
                # cannot see it.
                gap = line[e_end:b_start] if not structural else " , "
                if not gap or not re.search(r"[\s,]", gap):
                    findings.append({"verdict": "glued_token"})
                    continue
                ends = {c[1] for c in candidates}
                if any(end == e - 1 for e in ends):
                    findings.append({"verdict": "inclusive"})
                    continue
                # `unrelated` when the stated end matches nothing plausible: it is
                # not within any candidate function and not close to any end.
                if all(end > e or end < entry for e in ends) and end not in ends:
                    verdict = "TRUNCATED" if any(entry < end < e for e in ends) else "unrelated"
                elif end in ends:
                    verdict = "exact"
                elif any(end > e for e in ends):
                    verdict = "over_extent"
                else:
                    verdict = "TRUNCATED"
                if verdict == "unrelated":
                    findings.append({"verdict": verdict})
                    continue
                missed = max((e - end for e in ends if e > end), default=0)
                if verdict == "TRUNCATED" and missed < 8:
                    findings.append({"verdict": "inclusive"})
                    continue
                findings.append({
                    "verdict": verdict,
                    "file": rel(path),
                    "line": lineno,
                    "entry": f"0x{entry:08x}",
                    "declared_end": f"0x{end:08x}",
                    "index_ends": sorted(f"0x{e:08x}" for e in ends),
                    "ambiguous_image": len({c[0] for c in candidates}) > 1,
                    "candidates": sorted({c[0] for c in candidates}),
                    "names": sorted({c[2] for c in candidates if c[2]}),
                    "missed_bytes": missed,
                    "missed_instructions": missed // 4,
                    "detected_by": "structure" if structural else "name",
                    "source": line.strip()[:140],
                })
    return findings


def load_acknowledged() -> dict[tuple[str, int, str], dict]:
    """Rows a human has already looked at.

    The audit is only useful if it stays quiet about what has been reviewed and
    loud about what has not. Keyed by (file, line, declared end) so moving a line
    re-raises it -- a truncation that drifts to a new line is a new declaration
    worth a second look, and a stale allowlist that silences real findings is
    exactly the failure this repo keeps hitting.
    """
    if not ACK_PATH.is_file():
        return {}
    doc = yaml.safe_load(ACK_PATH.read_text()) or {}
    return {(r["file"], int(r["line"]), str(r["declared_end"]).lower()): r
            for r in doc.get("acknowledged") or []}


def tracked_files() -> set[str] | None:
    """Repo-relative paths git knows about, or None outside a repo.

    The retained report must reproduce from a committed clean checkout -- that is
    what an independent verifier does. Scanning whatever happens to be on disk
    made `files_scanned` and `candidate_pairs` depend on the operator's untracked
    working files, so the retained artifact regenerated only on the machine that
    wrote it. Same defect as the typed-state image map, found the same way.
    """
    proc = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        return None
    return set(proc.stdout.split())


def build(paths: list[Path]) -> dict:
    by_entry, images = load_index()
    tracked = tracked_files()
    files, findings = 0, []
    for root in paths:
        targets = [root] if root.is_file() else [
            p for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix in SUFFIXES
            and not any(part in SKIP_DIRS for part in p.parts)
            and rel(p) not in SKIP_FILES
            # Out-of-tree paths (an explicit scratch directory) are always scanned;
            # inside the repo only tracked files count, so the result is a property
            # of the commit rather than of the working tree.
            and (tracked is None or not rel(p).startswith(("tools/", "config/"))
                 or rel(p) in tracked)]
        for path in targets:
            files += 1
            findings.extend(audit_file(path, by_entry, images))

    real = [f for f in findings
            if f["verdict"] not in ("unrelated", "unnamed", "inclusive", "glued_token")]
    ack = load_acknowledged()
    truncated = []
    for f in real:
        if f["verdict"] != "TRUNCATED":
            continue
        seen = ack.get((f["file"], f["line"], f["declared_end"].lower()))
        f["acknowledged"] = bool(seen)
        f["review_verdict"] = (seen or {}).get("verdict")
        f["review_reason"] = (seen or {}).get("reason")
        truncated.append(f)
    unacknowledged = [f for f in truncated if not f["acknowledged"]]
    # One file can declare the same extent twice; count distinct declarations.
    distinct = {(f["file"], f["entry"], f["declared_end"]) for f in truncated}
    by_file: dict[str, dict] = {}
    for f in truncated:
        row = by_file.setdefault(f["file"], {"truncated_extents": 0, "missed_bytes": 0})
        row["truncated_extents"] += 1
        row["missed_bytes"] += f["missed_bytes"]
    return {
        "schema": "abl-phase4-extent-audit/1",
        "question": ("Does any hand-typed function extent stop short of the real "
                     "function, making a census report a lower bound as a total?"),
        "authority": INDEX_PATH.name,
        "files_scanned": files,
        "candidate_pairs": len(findings),
        "pairs_rejected": {
            "unnamed": sum(1 for f in findings if f["verdict"] == "unnamed"),
            "unrelated": sum(1 for f in findings if f["verdict"] == "unrelated"),
            "inclusive_notation": sum(1 for f in findings if f["verdict"] == "inclusive"),
            "glued_into_one_token": sum(1 for f in findings if f["verdict"] == "glued_token"),
        },
        "extent_declarations": len(real),
        "verdicts": {v: sum(1 for f in real if f["verdict"] == v)
                     for v in sorted({f["verdict"] for f in real})},
        "truncated_declarations": len(truncated),
        "acknowledged_declarations": len(truncated) - len(unacknowledged),
        "unacknowledged_declarations": len(unacknowledged),
        "review_verdicts": {v: sum(1 for f in truncated if f["review_verdict"] == v)
                            for v in sorted({f["review_verdict"] for f in truncated
                                             if f["review_verdict"]})},
        "unacknowledged": unacknowledged,
        "truncated_distinct": len(distinct),
        "total_missed_bytes": sum(f["missed_bytes"] for f in truncated),
        "total_missed_instructions": sum(f["missed_instructions"] for f in truncated),
        "by_file": dict(sorted(by_file.items(),
                               key=lambda kv: -kv[1]["missed_bytes"])),
        "truncated": sorted(truncated, key=lambda f: -f["missed_bytes"]),
        "note": ("`unnamed` pairs are the big rejection class: the line gives an "
                 "entry address but never names the function, so it is not a "
                 "declaration about that function. `inclusive` is `end == index "
                 "end - 1`, a notation difference. Neither is a finding. "
                 "`unrelated` pairs are counted but never reported as findings -- "
                 "they are two addresses that happen to share a line. An ambiguous "
                 "row means the entry exists in several overlay images and the line "
                 "names none of them; the candidate ends are listed rather than "
                 "picked."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    paths = [p if p.is_absolute() else ROOT / p
             for p in (args.paths or [Path(p) for p in DEFAULT_PATHS])]
    report = build(paths)
    if args.json:
        args.json.write_bytes(
            (json.dumps(report, indent=1, sort_keys=True) + "\n").encode())
        print(f"[extent-audit] wrote {args.json}")
    print(f"[extent-audit] {report['files_scanned']} files, "
          f"{report['extent_declarations']} extent declarations, "
          f"{report['truncated_declarations']} truncated "
          f"({report['acknowledged_declarations']} reviewed, "
          f"{report['unacknowledged_declarations']} NEW)")
    for verdict, n in sorted(report["review_verdicts"].items()):
        print(f"    reviewed as {verdict}: {n}")
    for f in report["unacknowledged"]:
        print(f"    NEW  {f['file']}:{f['line']}  {f['entry']} -> "
              f"{f['declared_end']} (real {', '.join(f['index_ends'])}), "
              f"{f['missed_bytes']} bytes unread")
    return 1 if report["unacknowledged_declarations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
