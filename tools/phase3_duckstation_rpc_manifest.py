#!/usr/bin/env python3
"""Generate and verify the exact DuckStation RPC surface used by Phase 3.

The external-debugger fork carries an uncommitted layer, so its Git revision is
not sufficient identity.  This generator extracts the brace-bounded
``IsKnownMethod`` allow-list from both HEAD and the working tree, records the
dispatcher/docs/client/binary hashes, and renders the authoritative Markdown
method list.  ``--check`` compares the retained artifacts with a fresh extraction
and exits non-zero on source, binary, method, Markdown, or Canon drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = Path.home() / "duckstation"
JSON_OUTPUT = ROOT / "analysis" / "phase3_duckstation_rpc_manifest.json"
MARKDOWN_OUTPUT = ROOT / "tools" / "duckstation_rpc_method_manifest.md"
CANON_INDEX = ROOT / "ObsidianVault" / "Canon" / "Indexes" / "DuckStation_API_Index.md"
DISPATCH_REL = Path("src/duckstation-qt/debuggerrpc.cpp")
SOURCE_RELS = (
    DISPATCH_REL,
    Path("EXTERNAL_DEBUGGER_CONTROL.md"),
    Path("docs/external-debugger.md"),
    Path("docs/external-debugger-api-safety.md"),
    Path("docs/external-debugger-determinism.md"),
    Path("docs/external-debugger-experiment-runner.md"),
    Path("docs/external-debugger-movie.md"),
    Path("docs/external-debugger-scenarios.md"),
    Path("docs/external-debugger-trace-capsules.md"),
    Path("scripts/debugger-client/README.md"),
    Path("scripts/debugger-client/launch_debugger_instance.sh"),
    Path("scripts/debugger-client/duckstation_debug_client.py"),
    Path("scripts/debugger-client/mcp_bridge.py"),
)
BINARY_RELS = (
    Path("build/bin/duckstation-qt"),
    Path("build-release/bin/duckstation-qt"),
)
RUNTIME_TREE_RELS = (Path("build-release/bin"),)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
METHOD_RE = re.compile(r'QStringLiteral\("([^"\\]+)"\)')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def runtime_tree_files(path: Path) -> list[Path]:
    """Hash the release support tree independently of the selected binary.

    The replay helper gives ``duckstation-qt`` its own immutable copy.  Shared
    libraries, resources, translations, and the optional logged executable
    must remain beside it because Qt/DuckStation resolve them relative to the
    application directory.  Excluding the mutable canonical executable here
    lets a replay prove both identities independently.
    """
    return sorted(
        candidate for candidate in path.rglob("*")
        if candidate.is_file() and not candidate.is_symlink()
        and (
            candidate.relative_to(path).parts[0] in {"resources", "translations"}
            or candidate.parent == path
            and (candidate.name == "duckstation-qt-logged"
                 or candidate.name.startswith("lib"))
        )
    )


def runtime_tree_identity(path: Path) -> dict:
    rows = []
    for candidate in runtime_tree_files(path):
        rel = candidate.relative_to(path).as_posix()
        rows.append((rel, candidate.stat().st_size, sha256_file(candidate)))
    encoded = "".join(f"{rel}\0{size}\0{digest}\n"
                      for rel, size, digest in rows).encode()
    return {
        "file_count": len(rows),
        "total_size": sum(size for _, size, _ in rows),
        "manifest_sha256": sha256_bytes(encoded),
    }


def git(source_root: Path, *args: str, text: bool = True):
    return subprocess.check_output(
        ["git", "-C", str(source_root), *args], text=text,
    )


def function_block(source: str, marker: str) -> str:
    """Return one function using balanced braces from its signature marker."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for offset in range(brace, len(source)):
        char = source[offset]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:offset + 1]
    raise ValueError(f"unterminated function: {marker}")


def extract_methods(source: str) -> list[str]:
    """Return the exact known-method allow-list.

    Scoping the extraction matters: method-shaped strings also occur in request
    dispatch and documentation helpers, and counting the whole file inflated an
    earlier manual census.  Older revisions listed the strings directly inside
    ``IsKnownMethod``; the current fork keeps the same set in ``KnownMethods``
    and makes ``IsKnownMethod`` a one-line membership test.  Accept only those
    two brace-bounded representations and still require exact agreement with the
    request-dispatch branches below.
    """
    marker = ("const QSet<QString>& KnownMethods()"
              if "const QSet<QString>& KnownMethods()" in source
              else "bool IsKnownMethod(const QString& method)")
    methods = METHOD_RE.findall(function_block(source, marker))
    if not methods:
        raise ValueError(f"{marker.split('(')[0]} contains no QStringLiteral methods")
    duplicates = sorted({method for method in methods if methods.count(method) > 1})
    if duplicates:
        raise ValueError(f"duplicate methods in IsKnownMethod: {duplicates}")
    return sorted(methods)


def extract_handlers(source: str) -> list[str]:
    marker = ("MethodResult DispatchMethod"
              if "MethodResult DispatchMethod" in source
              else "MethodResult HandleMethod")
    handlers = re.findall(
        r'QLatin1String\("([^"\\]+)"\)', function_block(source, marker))
    if handlers != list(dict.fromkeys(handlers)):
        raise ValueError("duplicate method branches in request dispatcher")
    return sorted(handlers)


def build_manifest(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict:
    source_root = source_root.expanduser().resolve()
    dispatcher = source_root / DISPATCH_REL
    if not dispatcher.is_file():
        raise FileNotFoundError(f"DuckStation dispatcher missing: {dispatcher}")

    revision = git(source_root, "rev-parse", "HEAD").strip()
    branch = git(source_root, "branch", "--show-current").strip()
    status_raw = git(
        source_root, "status", "--porcelain=v1", text=False,
    )
    status_lines = status_raw.decode("utf-8", errors="surrogateescape").splitlines()
    current_source = dispatcher.read_text()
    committed_source = git(source_root, "show", f"{revision}:{DISPATCH_REL.as_posix()}")
    current = extract_methods(current_source)
    committed = extract_methods(committed_source)
    current_handlers = extract_handlers(current_source)
    committed_handlers = extract_handlers(committed_source)
    if current != current_handlers:
        raise ValueError("working-tree IsKnownMethod and dispatch-handler sets differ")
    if committed != committed_handlers:
        raise ValueError("HEAD IsKnownMethod and dispatch-handler sets differ")
    current_set = set(current)
    committed_set = set(committed)
    dirty_only = sorted(current_set - committed_set)
    removed = sorted(committed_set - current_set)

    source_files = {}
    for rel in SOURCE_RELS:
        path = source_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"required DuckStation source/doc missing: {path}")
        source_files[rel.as_posix()] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }

    binaries = {}
    for rel in BINARY_RELS:
        path = source_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"Phase-3 DuckStation binary missing: {path}")
        binaries[rel.as_posix()] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }

    runtime_trees = {
        rel.as_posix(): runtime_tree_identity(source_root / rel)
        for rel in RUNTIME_TREE_RELS
    }

    return {
        "_comment": "Machine-readable DuckStation external-debugger method/source "
                    "identity used by Phase 3. Regenerate or verify with: python3 "
                    "tools/phase3_duckstation_rpc_manifest.py --check",
        "generated": date.today().isoformat(),
        "source": {
            "canonical_path": "~/duckstation",
            "revision": revision,
            "branch": branch,
            "dirty": bool(status_lines),
            "status_lines": status_lines,
            "status_line_count": len(status_lines),
            "status_sha256": sha256_bytes(status_raw),
            "dispatcher_path": DISPATCH_REL.as_posix(),
            "dispatcher_sha256": sha256_file(dispatcher),
            "dispatcher_head_sha256": sha256_bytes(committed_source.encode()),
            "dispatcher_patch_sha256": sha256_bytes(git(
                source_root, "diff", "--binary", revision, "--",
                DISPATCH_REL.as_posix(), text=False,
            )),
            "files": source_files,
        },
        "binaries": binaries,
        "runtime_trees": runtime_trees,
        "methods": {
            "committed": committed,
            "dirty_only": dirty_only,
            "removed_from_head": removed,
            "current": current,
            "counts": {
                "committed": len(committed),
                "dirty_only": len(dirty_only),
                "removed_from_head": len(removed),
                "current": len(current),
            },
        },
    }


def semantic(doc: dict) -> dict:
    result = dict(doc)
    result.pop("generated", None)
    return result


def current_fork_gaps(doc: dict, source_root: Path = DEFAULT_SOURCE_ROOT) -> list[str]:
    """Compare retained identity with a fresh external source/binary extraction.

    This predicate is intentionally usable by the executable Phase-3 gate.  A
    separate ``--check`` command is useful validation, but closure must not stay
    green merely because nobody happened to invoke that separate command after
    the fork or either binary changed.
    """
    try:
        fresh = build_manifest(source_root)
    except Exception as exc:  # surface an absent, mid-build, or unparsable fork
        return [f"current DuckStation extraction failed: {type(exc).__name__}: {exc}"]
    if semantic(doc) != semantic(fresh):
        return ["retained JSON differs from fresh DuckStation source/binary extraction"]
    return []


def render_markdown(doc: dict) -> str:
    source = doc["source"]
    methods = doc["methods"]
    counts = methods["counts"]
    lines = [
        "# DuckStation external-debugger RPC method manifest",
        "",
        "> Generated by `tools/phase3_duckstation_rpc_manifest.py` from the exact",
        "> dirty DuckStation source and binaries used by retained Phase 3 live evidence.",
        "> Method syntax still comes from current fork docs/source/runtime; this file",
        "> is the authoritative source-pinned method census, not a parameter schema.",
        "",
        "## Exact source and binary identity",
        "",
        "| Property | Retained value |",
        "|---|---|",
        f"| Fork revision | `{source['revision']}` |",
        f"| Branch | `{source['branch']}` |",
        f"| Dirty status | {source['status_line_count']} paths; SHA-256 `{source['status_sha256']}` |",
        f"| Dispatcher | `{source['dispatcher_path']}`; SHA-256 `{source['dispatcher_sha256']}` |",
        f"| Dispatcher at HEAD | SHA-256 `{source['dispatcher_head_sha256']}` |",
        f"| Dispatcher dirty patch | SHA-256 `{source['dispatcher_patch_sha256']}` |",
    ]
    for rel, row in doc["binaries"].items():
        lines.append(
            f"| Binary `~/duckstation/{rel}` | SHA-256 `{row['sha256']}`; "
            f"{row['size']} bytes |"
        )
    for rel, row in doc.get("runtime_trees", {}).items():
        lines.append(
            f"| Runtime tree `~/duckstation/{rel}` | SHA-256 "
            f"`{row['manifest_sha256']}`; {row['file_count']} files; "
            f"{row['total_size']} bytes |"
        )
    lines.extend([
        "",
        f"Totals: **{counts['committed']} at HEAD + {counts['dirty_only']} dirty-only "
        f"- {counts['removed_from_head']} removed = {counts['current']} current dispatched methods**.",
        "The current total is extracted only from the balanced `IsKnownMethod` allow-list.",
        "The generator fails on duplicate entries and the freshness guard recomputes the",
        "committed/current set difference rather than trusting these totals.",
        "",
        "The older GAP-0001 preservation snapshot at revision `296955321` (141 methods)",
        "is historical evidence only. It does not describe the `fe0cca16` Phase 3 runtime.",
        f"The complete current {source['status_line_count']}-path dirty status is retained below.",
        "Source, docs, client, launcher, and both current binaries are hash-pinned",
        "in `analysis/phase3_duckstation_rpc_manifest.json`.",
        "",
        f"## {counts['dirty_only']} dirty-only methods",
        "",
    ])
    lines.extend(f"- `{method}`" for method in methods["dirty_only"])
    lines.extend([
        "",
        f"## {counts['committed']} methods at HEAD `{source['revision'][:12]}`",
        "",
    ])
    lines.extend(f"- `{method}`" for method in methods["committed"])
    if methods["removed_from_head"]:
        lines.extend([
            "",
            f"## {counts['removed_from_head']} methods removed by the dirty layer",
            "",
        ])
        lines.extend(f"- `{method}`" for method in methods["removed_from_head"])
    lines.extend([
        "",
        "## Supporting source and documentation hashes",
        "",
        "| Path under `~/duckstation` | SHA-256 | Bytes |",
        "|---|---|---:|",
    ])
    for rel, row in source["files"].items():
        lines.append(f"| `{rel}` | `{row['sha256']}` | {row['size']} |")
    lines.extend([
        "",
        "## Complete dirty status used by the Phase 3 runs",
        "",
        "```text",
        *source["status_lines"],
        "```",
        "",
        "## Freshness commands",
        "",
        "- Regenerate both retained artifacts: `python3 tools/phase3_duckstation_rpc_manifest.py`",
        "- Verify them against `~/duckstation`: `python3 tools/phase3_duckstation_rpc_manifest.py --check`",
        "- Run the external-source guard: `python3 -m pytest -q -m local_media tests/test_phase3_duckstation_rpc_manifest.py`",
        "",
    ])
    return "\n".join(lines)


def retained_gaps(doc: dict, markdown: str, canon: str) -> list[str]:
    gaps: list[str] = []
    methods = doc.get("methods") or {}
    counts = methods.get("counts") or {}
    committed = methods.get("committed") or []
    dirty_only = methods.get("dirty_only") or []
    removed = methods.get("removed_from_head") or []
    current = methods.get("current") or []
    if committed != sorted(set(committed)):
        gaps.append("committed method list is not sorted and unique")
    if current != sorted(set(current)):
        gaps.append("current method list is not sorted and unique")
    if dirty_only != sorted(set(current) - set(committed)):
        gaps.append("dirty-only methods do not equal current minus committed")
    if removed != sorted(set(committed) - set(current)):
        gaps.append("removed methods do not equal committed minus current")
    expected_counts = {
        "committed": len(committed),
        "dirty_only": len(dirty_only),
        "removed_from_head": len(removed),
        "current": len(current),
    }
    if counts != expected_counts:
        gaps.append(f"method counts are stale: retained={counts}, computed={expected_counts}")
    source = doc.get("source") or {}
    status_lines = source.get("status_lines") or []
    if source.get("status_line_count") != len(status_lines):
        gaps.append("dirty status line count is stale")
    status_bytes = (("\n".join(status_lines) + "\n").encode()
                    if status_lines else b"")
    if source.get("status_sha256") != sha256_bytes(status_bytes):
        gaps.append("dirty status SHA-256 does not match retained status lines")
    for field in ("revision", "status_sha256", "dispatcher_sha256",
                  "dispatcher_head_sha256", "dispatcher_patch_sha256"):
        value = source.get(field, "")
        expected = 40 if field == "revision" else 64
        exact_hex = re.fullmatch(rf"[0-9a-f]{{{expected}}}", value)
        if not exact_hex:
            gaps.append(f"source.{field} is not an exact {expected}-hex identity")
    dispatcher_row = (source.get("files") or {}).get(
        source.get("dispatcher_path", ""), {})
    if dispatcher_row.get("sha256") != source.get("dispatcher_sha256"):
        gaps.append("dispatcher SHA-256 disagrees with source file inventory")
    for rel, row in (source.get("files") or {}).items():
        if not SHA256_RE.fullmatch(row.get("sha256", "")) or not row.get("size"):
            gaps.append(f"source file identity incomplete: {rel}")
    for rel, row in (doc.get("binaries") or {}).items():
        if not SHA256_RE.fullmatch(row.get("sha256", "")) or not row.get("size"):
            gaps.append(f"binary identity incomplete: {rel}")
    for rel, row in (doc.get("runtime_trees") or {}).items():
        if (not SHA256_RE.fullmatch(row.get("manifest_sha256", ""))
                or not row.get("file_count") or not row.get("total_size")):
            gaps.append(f"runtime tree identity incomplete: {rel}")
    if markdown != render_markdown(doc):
        gaps.append("Markdown method manifest differs from deterministic rendering")
    required_canon = (
        str(counts.get("current", "")), source.get("revision", ""),
        source.get("status_sha256", ""), source.get("dispatcher_sha256", ""),
        "analysis/phase3_duckstation_rpc_manifest.json",
        "tools/phase3_duckstation_rpc_manifest.py --check",
    )
    for token in required_canon:
        if token and token not in canon:
            gaps.append(f"Canon API index omits retained identity token: {token}")
    return gaps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--check", action="store_true",
                        help="verify retained JSON/Markdown/Canon against current source")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fresh = build_manifest(args.source_root)
    if args.check:
        retained = json.loads(JSON_OUTPUT.read_text())
        gaps = retained_gaps(retained, MARKDOWN_OUTPUT.read_text(), CANON_INDEX.read_text())
        gaps.extend(current_fork_gaps(retained, args.source_root))
        if gaps:
            print("[duckstation-rpc] STALE")
            for gap in gaps:
                print(f"  - {gap}")
            return 1
        print(
            f"[duckstation-rpc] FRESH: {fresh['methods']['counts']['current']} methods "
            f"at {fresh['source']['revision']} with {fresh['source']['status_line_count']} dirty paths"
        )
        return 0

    JSON_OUTPUT.write_text(json.dumps(fresh, indent=1) + "\n")
    MARKDOWN_OUTPUT.write_text(render_markdown(fresh))
    print(
        f"[duckstation-rpc] wrote {fresh['methods']['counts']['current']} methods "
        f"({fresh['methods']['counts']['committed']} committed + "
        f"{fresh['methods']['counts']['dirty_only']} dirty-only)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
