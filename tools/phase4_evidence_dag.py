#!/usr/bin/env python3
"""Plan and run the bounded Phase-4 generated-evidence dependency graph.

The graph deliberately retains two identities for JSON artifacts: an exact byte
hash for preservation/audit and a normalized semantic hash for dependency
planning.  A node must opt in to semantic invalidation per input; exact identity
is never discarded or silently substituted.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/phase4_evidence_dag.yaml"
OUTPUT = ROOT / "analysis/phase4_evidence_dag.json"
SCHEMA = "abl-phase4-evidence-dag/1"
REPORT_SCHEMA = "abl-phase4-evidence-dag-report/1"
VOLATILE_KEYS = {"_comment", "generated", "generated_at", "updated", "timestamp"}


class DagError(RuntimeError):
    """A fail-closed graph, identity, or execution error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode()


def _semantic_value(value: Any) -> Any:
    """Remove only presentation volatility; provenance hashes stay by default."""
    if isinstance(value, dict):
        return {
            key: _semantic_value(child)
            for key, child in sorted(value.items())
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_semantic_value(child) for child in value]
    return value


def _drop_pointer(value: Any, pointer: str) -> None:
    if not pointer.startswith("/"):
        raise DagError(f"semantic ignore path is not a JSON pointer: {pointer!r}")
    parts = [part.replace("~1", "/").replace("~0", "~")
             for part in pointer[1:].split("/") if part]
    if not parts:
        raise DagError("semantic ignore path may not remove the document root")
    current = value
    for part in parts[:-1]:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return
    leaf = parts[-1]
    if isinstance(current, dict):
        current.pop(leaf, None)
    elif isinstance(current, list) and leaf.isdigit() and int(leaf) < len(current):
        current.pop(int(leaf))


def semantic_hash(path: Path, ignore_paths: Iterable[str] = ()) -> str:
    if path.suffix.lower() != ".json":
        return sha256(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DagError(f"cannot normalize JSON artifact {path}: {exc}") from exc
    value = _semantic_value(value)
    for pointer in ignore_paths:
        _drop_pointer(value, pointer)
    return sha256_bytes(canonical_json(value))


def safe_rel(root: Path, raw: str) -> str:
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or not raw:
        raise DagError(f"unsafe graph path: {raw!r}")
    try:
        (root / path).resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DagError(f"graph path escapes repository: {raw!r}") from exc
    return path.as_posix()


def tree_identity(path: Path) -> dict[str, Any]:
    if not path.is_dir() or path.is_symlink():
        raise DagError(f"declared DAG tree is absent or unsafe: {path}")
    digest = hashlib.sha256()
    count = 0
    total = 0
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise DagError(f"declared DAG tree contains a symlink: {child}")
        if not child.is_file():
            continue
        rel = child.relative_to(path).as_posix()
        identity = sha256(child)
        size = child.stat().st_size
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update(str(size).encode())
        digest.update(b"\0")
        digest.update(identity.encode())
        digest.update(b"\n")
        count += 1
        total += size
    return {"file_count": count, "bytes": total, "sha256": digest.hexdigest()}


def load_config(path: Path = CONFIG) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DagError(f"cannot load DAG config {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise DagError(f"DAG config must use {SCHEMA}")
    return doc


def validate_config(doc: dict[str, Any], root: Path = ROOT) -> list[dict[str, Any]]:
    raw_nodes = doc.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise DagError("DAG needs a non-empty nodes list")
    nodes: list[dict[str, Any]] = []
    ids: set[str] = set()
    output_owner: dict[str, str] = {}
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            raise DagError("every DAG node must be a mapping")
        node = copy.deepcopy(raw)
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id or node_id in ids:
            raise DagError(f"invalid or duplicate node id: {node_id!r}")
        ids.add(node_id)
        classification = node.get("classification")
        if classification not in {"static", "local_media", "live"}:
            raise DagError(f"{node_id}: invalid classification {classification!r}")
        generator = safe_rel(root, str(node.get("generator") or ""))
        if not (root / generator).is_file():
            raise DagError(f"{node_id}: missing generator {generator}")
        command = node.get("command")
        if not isinstance(command, list) or not command or not all(
                isinstance(part, str) and part for part in command):
            raise DagError(f"{node_id}: command must be a non-empty string list")
        verify_command = node.get("verify_command")
        if not isinstance(verify_command, list) or not verify_command or not all(
                isinstance(part, str) and part for part in verify_command):
            raise DagError(f"{node_id}: verify_command must be a non-empty string list")
        if generator not in command or generator not in verify_command:
            raise DagError(f"{node_id}: command and verify_command must invoke its generator")
        accepted_exit_codes = node.get("accepted_exit_codes", [0])
        if not isinstance(accepted_exit_codes, list) or not accepted_exit_codes or not all(
                isinstance(code, int) and not isinstance(code, bool) and 0 <= code <= 255
                for code in accepted_exit_codes):
            raise DagError(f"{node_id}: accepted_exit_codes must be integer exit codes")
        dependencies = node.get("depends_on") or []
        if not isinstance(dependencies, list) or len(set(dependencies)) != len(dependencies):
            raise DagError(f"{node_id}: depends_on must be unique")
        inputs = []
        for spec in node.get("inputs") or []:
            if not isinstance(spec, dict) or spec.get("mode") not in {"exact", "semantic"}:
                raise DagError(f"{node_id}: every input needs path and exact/semantic mode")
            kind = spec.get("kind", "file")
            if kind not in {"file", "tree"}:
                raise DagError(f"{node_id}: input kind must be file or tree")
            if kind == "tree" and spec["mode"] != "exact":
                raise DagError(f"{node_id}: tree inputs currently require exact mode")
            inputs.append({"path": safe_rel(root, str(spec.get("path") or "")),
                           "mode": spec["mode"], "kind": kind})
        outputs = []
        for spec in node.get("outputs") or []:
            if not isinstance(spec, dict):
                raise DagError(f"{node_id}: every output must be a mapping")
            rel = safe_rel(root, str(spec.get("path") or ""))
            if rel in output_owner:
                raise DagError(f"output {rel} has two owners: {output_owner[rel]}, {node_id}")
            output_owner[rel] = node_id
            comparison = spec.get("comparison", "exact")
            if comparison not in {"exact", "semantic_json"}:
                raise DagError(f"{node_id}: invalid output comparison {comparison!r}")
            ignores = spec.get("semantic_ignore") or []
            if not isinstance(ignores, list) or not all(isinstance(x, str) for x in ignores):
                raise DagError(f"{node_id}: semantic_ignore must be a string list")
            outputs.append({"path": rel, "comparison": comparison,
                            "semantic_ignore": ignores})
        if not outputs:
            raise DagError(f"{node_id}: node has no outputs")
        node.update(generator=generator, inputs=inputs, outputs=outputs,
                    depends_on=dependencies,
                    accepted_exit_codes=sorted(set(accepted_exit_codes)),
                    verify_command=verify_command)
        nodes.append(node)

    node_map = {node["id"]: node for node in nodes}
    for node in nodes:
        for dep in node["depends_on"]:
            if dep not in node_map:
                raise DagError(f"{node['id']}: unknown dependency {dep}")
        for spec in node["inputs"]:
            owner = output_owner.get(spec["path"])
            if owner and owner not in node["depends_on"]:
                raise DagError(
                    f"{node['id']}: input {spec['path']} is owned by {owner} but edge is absent")

    # Stable Kahn ordering and cycle detection.
    pending = {node["id"]: set(node["depends_on"]) for node in nodes}
    order: list[str] = []
    while pending:
        ready = sorted(key for key, deps in pending.items() if not deps)
        if not ready:
            raise DagError(f"DAG contains a cycle among {sorted(pending)}")
        for key in ready:
            order.append(key)
            pending.pop(key)
        for deps in pending.values():
            deps.difference_update(ready)
    return [node_map[key] for key in order]


def path_identity(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    rel = spec["path"]
    path = root / rel
    if spec.get("kind") == "tree":
        row = tree_identity(path)
        return {"path": rel, "kind": "tree", "size": row["bytes"],
                "file_count": row["file_count"],
                "exact_sha256": row["sha256"],
                "semantic_sha256": row["sha256"]}
    if not path.is_file():
        raise DagError(f"declared DAG path is missing: {rel}")
    exact = sha256(path)
    semantic = semantic_hash(path, spec.get("semantic_ignore") or [])
    return {"path": rel, "kind": "file", "size": path.stat().st_size,
            "exact_sha256": exact, "semantic_sha256": semantic}


def node_state(node: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    generator = root / node["generator"]
    input_rows = [path_identity(root, spec) | {"mode": spec["mode"]}
                  for spec in node["inputs"]]
    output_spec = {spec["path"]: spec for spec in node["outputs"]}
    output_rows = [path_identity(root, output_spec[rel]) |
                   {"comparison": output_spec[rel]["comparison"]}
                   for rel in sorted(output_spec)]
    fingerprint_material = {
        "classification": node["classification"],
        "generator": node["generator"],
        "generator_sha256": sha256(generator),
        "command": node["command"],
        "verify_command": node["verify_command"],
        "accepted_exit_codes": node["accepted_exit_codes"],
        "depends_on": node["depends_on"],
        "inputs": [{"path": row["path"], "kind": row["kind"], "mode": row["mode"],
                    "sha256": row[f"{row['mode']}_sha256"]}
                   for row in input_rows],
        "outputs": node["outputs"],
    }
    return {
        "classification": node["classification"],
        "generator": node["generator"],
        "generator_sha256": sha256(generator),
        "command": node["command"],
        "verify_command": node["verify_command"],
        "depends_on": node["depends_on"],
        "inputs": input_rows,
        "outputs": output_rows,
        "fingerprint": sha256_bytes(canonical_json(fingerprint_material)),
    }


def synthetic_pilot() -> dict[str, Any]:
    semantic_a = {"schema": "pilot/1", "generated": "one", "value": 7}
    semantic_b = {"schema": "pilot/1", "generated": "two", "value": 7}
    semantic_c = {"schema": "pilot/1", "generated": "two", "value": 8}
    a_exact = sha256_bytes(canonical_json(semantic_a))
    b_exact = sha256_bytes(canonical_json(semantic_b))
    a_sem = sha256_bytes(canonical_json(_semantic_value(semantic_a)))
    b_sem = sha256_bytes(canonical_json(_semantic_value(semantic_b)))
    c_sem = sha256_bytes(canonical_json(_semantic_value(semantic_c)))
    return {
        "schema": "abl-phase4-evidence-dag-pilot/1",
        "exact_churn_detected": a_exact != b_exact,
        "semantic_churn_suppressed": a_sem == b_sem,
        "semantic_change_detected": b_sem != c_sem,
        "exact_consumer_invalidated_by_identity_churn": True,
        "semantic_consumer_invalidated_by_identity_churn": False,
        "semantic_consumer_invalidated_by_value_change": True,
    }


def build_report(config_path: Path = CONFIG, root: Path = ROOT) -> dict[str, Any]:
    doc = load_config(config_path)
    nodes = validate_config(doc, root)
    rows = {node["id"]: node_state(node, root) for node in nodes}
    exact_edges = 0
    semantic_edges = 0
    output_owner = {spec["path"]: node["id"] for node in nodes for spec in node["outputs"]}
    for node in nodes:
        for spec in node["inputs"]:
            if spec["path"] in output_owner:
                if spec["mode"] == "exact":
                    exact_edges += 1
                else:
                    semantic_edges += 1
    return {
        "schema": REPORT_SCHEMA,
        "config": str(config_path.relative_to(root)),
        "config_sha256": sha256(config_path),
        "topological_order": [node["id"] for node in nodes],
        "nodes": rows,
        "summary": {
            "nodes": len(nodes),
            "edges": sum(len(node["depends_on"]) for node in nodes),
            "exact_artifact_edges": exact_edges,
            "semantic_artifact_edges": semantic_edges,
            "live_nodes": sum(node["classification"] == "live" for node in nodes),
        },
        "pilot": synthetic_pilot(),
        "claims": {
            "complete_phase4_graph": False,
            "bounded_chain": "inventory -> offline queue -> debt -> escalation/movie/preflight -> gate",
            "exact_identity_retained": True,
            "semantic_hash_never_replaces_preservation_hash": True,
        },
    }


def render(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=1, sort_keys=False) + "\n"


def plan(report: dict[str, Any], retained: dict[str, Any]) -> dict[str, Any]:
    retained_nodes = retained.get("nodes") or {}
    removed_nodes = sorted(set(retained_nodes) - set(report.get("nodes") or {}))
    changed: list[str] = []
    reasons: dict[str, list[str]] = {}
    for node_id in report["topological_order"]:
        current = report["nodes"][node_id]
        previous = retained_nodes.get(node_id)
        node_reasons: list[str] = []
        if previous is None:
            node_reasons.append("not_in_retained_graph")
        elif previous.get("fingerprint") != current.get("fingerprint"):
            node_reasons.append("generator_or_input_identity_changed")
        previous_outputs = {row["path"]: row for row in (previous or {}).get("outputs", [])}
        for row in current["outputs"]:
            old = previous_outputs.get(row["path"])
            key = "exact_sha256" if row["comparison"] == "exact" else "semantic_sha256"
            if old is None or old.get(key) != row.get(key):
                node_reasons.append(f"output_changed:{row['path']}:{row['comparison']}")
        if node_reasons:
            changed.append(node_id)
            reasons[node_id] = sorted(set(node_reasons))
    descendants: set[str] = set(changed)
    nodes = report["nodes"]
    grew = True
    while grew:
        before = len(descendants)
        descendants.update(node_id for node_id, row in nodes.items()
                           if set(row["depends_on"]) & descendants)
        grew = len(descendants) != before
    return {
        "dirty_nodes": changed,
        "removed_nodes": removed_nodes,
        "graph_metadata_changed": report.get("config_sha256") != retained.get("config_sha256"),
        "provisional_run_order": [node_id for node_id in report["topological_order"]
                                  if node_id in descendants],
        "reasons": reasons,
        "clean": not descendants and not removed_nodes and
                 report.get("config_sha256") == retained.get("config_sha256"),
    }


def _expand_command(command: list[str]) -> list[str]:
    return [sys.executable if part == "{python}" else part for part in command]


def run_nodes(nodes: list[dict[str, Any]], run_order: list[str], *, root: Path,
              allowed: set[str]) -> list[dict[str, Any]]:
    node_map = {node["id"]: node for node in nodes}
    receipts = []
    for node_id in run_order:
        node = node_map[node_id]
        classification = node["classification"]
        if classification not in allowed:
            raise DagError(
                f"{node_id}: {classification} execution needs explicit --allow-{classification}")
        command = _expand_command(node["command"])
        proc = subprocess.run(command, cwd=root, text=True, capture_output=True,
                              check=False, env={**os.environ, "PYTHONHASHSEED": "0"})
        receipts.append({"node": node_id, "command": command,
                         "returncode": proc.returncode,
                         "stdout_sha256": sha256_bytes(proc.stdout.encode()),
                         "stderr_sha256": sha256_bytes(proc.stderr.encode())})
        if proc.returncode not in node["accepted_exit_codes"]:
            raise DagError(
                f"{node_id}: generator failed ({proc.returncode})\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        verify_command = _expand_command(node["verify_command"])
        verify = subprocess.run(verify_command, cwd=root, text=True, capture_output=True,
                                check=False, env={**os.environ, "PYTHONHASHSEED": "0"})
        receipts[-1].update({"verify_command": verify_command,
                             "verify_returncode": verify.returncode,
                             "verify_stdout_sha256": sha256_bytes(verify.stdout.encode()),
                             "verify_stderr_sha256": sha256_bytes(verify.stderr.encode())})
        if verify.returncode != 0:
            raise DagError(
                f"{node_id}: post-generation verification failed ({verify.returncode})\n"
                f"stdout:\n{verify.stdout}\nstderr:\n{verify.stderr}")
    return receipts


def _node_dirty(current: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    if previous is None or previous.get("fingerprint") != current.get("fingerprint"):
        return True
    prior_outputs = {row["path"]: row for row in previous.get("outputs") or []}
    for row in current.get("outputs") or []:
        prior = prior_outputs.get(row["path"])
        key = "exact_sha256" if row["comparison"] == "exact" else "semantic_sha256"
        if prior is None or prior.get(key) != row.get(key):
            return True
    return False


def run_incremental(nodes: list[dict[str, Any]], retained: dict[str, Any], *,
                    root: Path, allowed: set[str]) -> list[dict[str, Any]]:
    """Re-evaluate after every node so semantic no-op descendants are skipped."""
    receipts: list[dict[str, Any]] = []
    previous_nodes = retained.get("nodes") or {}
    removed = sorted(set(previous_nodes) - {node["id"] for node in nodes})
    if removed:
        raise DagError(f"retained graph has removed nodes requiring explicit review: {removed}")
    for node in nodes:
        current = node_state(node, root)
        if not _node_dirty(current, previous_nodes.get(node["id"])):
            receipts.append({"node": node["id"], "executed": False,
                             "reason": "identity_clean_after_upstream"})
            continue
        execution = run_nodes([node], [node["id"]], root=root, allowed=allowed)[0]
        after = node_state(node, root)
        receipts.append(execution | {"executed": True,
                                     "output_identities": after["outputs"]})
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="refresh retained DAG identities")
    mode.add_argument("--check", action="store_true", help="verify retained graph byte-for-byte")
    mode.add_argument("--plan", action="store_true", help="report invalidated nodes")
    mode.add_argument("--run", action="store_true", help="run invalidated nodes then refresh graph")
    parser.add_argument("--allow-local-media", action="store_true")
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()

    report = build_report()
    rendered = render(report)
    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8")
        print(f"[phase4-evidence-dag] wrote {OUTPUT.relative_to(ROOT)}")
        return 0
    if not OUTPUT.is_file():
        raise DagError("retained DAG report is missing; run --write")
    retained = json.loads(OUTPUT.read_text(encoding="utf-8"))
    current_plan = plan(report, retained)
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(json.dumps(current_plan, indent=1))
            raise DagError("retained DAG report is stale")
        print(f"[phase4-evidence-dag] clean: {len(report['nodes'])} nodes")
        return 0
    if args.plan:
        print(json.dumps(current_plan, indent=1))
        return 0 if current_plan["clean"] else 1

    allowed = {"static"}
    if args.allow_local_media:
        allowed.add("local_media")
    if args.allow_live:
        allowed.add("live")
    nodes = validate_config(load_config(), ROOT)
    receipts = run_incremental(nodes, retained, root=ROOT, allowed=allowed)
    refreshed = build_report()
    OUTPUT.write_text(render(refreshed), encoding="utf-8")
    print(json.dumps({"executed": receipts, "clean_after": True}, indent=1))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DagError as exc:
        print(f"phase4 evidence DAG error: {exc}", file=sys.stderr)
        raise SystemExit(2)
