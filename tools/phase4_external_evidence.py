#!/usr/bin/env python3
"""Generate and verify a hash-only registry for private external evidence."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/phase4_external_evidence.yaml"
CAPSULE_SET_PATH = ROOT / "analysis/phase4_trace_capsule_set.json"
REGISTRY_PATH = ROOT / "analysis/phase4_external_evidence_manifest.json"
PILOT_PATH = ROOT / "analysis/phase4_external_evidence_pilot.json"
POLICY_SCHEMA = "abl-phase4-external-evidence-policy/1"
REGISTRY_SCHEMA = "abl-phase4-external-evidence-registry/1"
RECEIPT_SCHEMA = "abl-phase4-external-evidence-receipts/1"
PILOT_SCHEMA = "abl-phase4-external-evidence-pilot/1"
CAPSULE_SET_SCHEMAS = frozenset({
    "abl-phase4-trace-capsule-set-v1",
    "abl-phase4-trace-capsule-set-v2",
})
SHA_LINE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
EXPECTED_POLICY = {
    "schema": POLICY_SCHEMA,
    "hash": "sha256",
    "registry_schema": REGISTRY_SCHEMA,
    "receipt_schema": RECEIPT_SCHEMA,
    "minimum_independent_copies": 2,
    "content_layout": "objects/sha256/{prefix}/{sha256}",
    "external_only": True,
    "allow_public_remote": False,
    "allow_repository_root": False,
    "allow_symlinks": False,
    "allow_overwrite": False,
    "allowed_remote_kinds": ["offline_local", "offline_removable", "private_annex"],
    "physical_domain_policy": {
        "verified_local_kinds": ["offline_local", "offline_removable"],
        "local_identity": "st_dev",
        "unverified_without_attestation": ["private_annex"],
        "reject_overlapping_roots": True,
    },
    "allowed_media_classes": [
        "pristine_media",
        "capsule_tree",
        "collection_manifest",
        "input_movie",
        "save_state",
        "emulator_binary",
        "emulator_runtime_bundle",
        "emulator_source_snapshot",
        "offline_reader",
    ],
    "backend_pilot": {
        "name": "git-annex",
        "execute_automatically": False,
        "initialize_repository": False,
        "publish_remote": False,
        "preferred_content": "present",
    },
    "authority": {
        "hash_registry_is_not_availability": True,
        "same_failure_domain_counts_once": True,
        "caller_labels_are_not_physical_identity": True,
        "private_annex_requires_immutable_attestation": True,
        "preservation_is_not_behavioral_evidence": True,
        "no_campaign_promotion": True,
    },
}


class EvidenceError(RuntimeError):
    """Evidence identity, location, or preservation policy failed closed."""


def _assert_exact(actual: Any, expected: Any, field: str, *, ordered_dicts: bool) -> None:
    """Require an exact recursively typed contract (bool never aliases int)."""
    if type(actual) is not type(expected):
        raise EvidenceError(f"{field} type drifted")
    if type(expected) is dict:
        actual_keys = list(actual)
        expected_keys = list(expected)
        if (ordered_dicts and actual_keys != expected_keys) or \
                (not ordered_dicts and set(actual_keys) != set(expected_keys)):
            raise EvidenceError(f"{field} fields/order drifted")
        for key in expected_keys:
            _assert_exact(actual[key], expected[key], f"{field}.{key}",
                          ordered_dicts=ordered_dicts)
    elif type(expected) is list:
        if len(actual) != len(expected):
            raise EvidenceError(f"{field} list length drifted")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            _assert_exact(actual_item, expected_item, f"{field}[{index}]",
                          ordered_dicts=ordered_dicts)
    elif actual != expected:
        raise EvidenceError(f"{field} value drifted")


def _validate_policy(policy: Any) -> dict[str, Any]:
    _assert_exact(policy, EXPECTED_POLICY, "external-evidence policy", ordered_dicts=True)
    return policy


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value):
        raise EvidenceError(f"{field} must be a lowercase SHA-256")
    return value


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise EvidenceError(f"cannot load external-evidence policy: {exc}") from exc
    return _validate_policy(doc)


def _object(object_id: str, media_class: str, identity_kind: str, sha256: str,
            size: int | None, role: str, required_copies: int,
            verification: str = "file_sha256",
            verification_manifest_sha256: str | None = None) -> dict[str, Any]:
    return {
        "id": object_id, "media_class": media_class,
        "identity_kind": identity_kind, "sha256": _hex64(sha256, object_id),
        "bytes": size, "role": role, "required_copies": required_copies,
        "verification": verification,
        "verification_manifest_sha256": (
            _hex64(verification_manifest_sha256, f"{object_id}.verification_manifest")
            if verification_manifest_sha256 is not None else None),
        "availability": "unverified",
    }


def build_registry(capsule_set: dict[str, Any], policy: dict[str, Any] | None = None,
                   capsule_set_path: Path | None = None) -> dict:
    policy = load_policy() if policy is None else _validate_policy(policy)
    if capsule_set.get("schema") not in CAPSULE_SET_SCHEMAS or \
            capsule_set.get("complete") is not True or capsule_set.get("errors") != []:
        raise EvidenceError("only a complete, error-free retained capsule set may seed registry")
    if (capsule_set.get("reproducibility_comparison") or {}).get("mismatches") != []:
        raise EvidenceError("capsule set reproducibility mismatches forbid registry generation")
    minimum = policy["minimum_independent_copies"]
    allowed = set(policy["allowed_media_classes"])
    objects: dict[str, dict] = {}

    def add(row: dict) -> None:
        if row["media_class"] not in allowed or row["id"] in objects:
            raise EvidenceError(f"duplicate/forbidden registry object: {row['id']}")
        objects[row["id"]] = row

    for media in capsule_set.get("pristine_media") or []:
        role = "cue" if str(media.get("path", "")).lower().endswith(".cue") else "disc_track"
        add(_object(f"pristine:{role}", "pristine_media", "file_sha256", media["sha256"],
                    media.get("bytes"), role, minimum))
    for collection in capsule_set.get("capsule_collections") or []:
        role = collection["role"]
        add(_object(f"collection:{role}:manifest", "collection_manifest", "file_sha256",
                    collection["collection_manifest_sha256"], None,
                    "capsule collection manifest", minimum))
        add(_object(f"collection:{role}:batch", "collection_manifest", "file_sha256",
                    collection["batch_manifest_sha256"], None,
                    "capsule batch completion manifest", minimum))
    for capsule in capsule_set.get("capsules") or []:
        logical = capsule["movie"]
        safe_id = sha256_bytes(logical.encode())[:16]
        add(_object(f"capsule:{safe_id}", "capsule_tree", "tree_sha256",
                    capsule["capsule_tree_sha256"], capsule.get("capsule_bytes"),
                    "frame-boundary trace capsule", minimum,
                    "capsule_manifest_tree_v1", capsule["capsule_manifest_sha256"]))
        add(_object(f"movie:{safe_id}", "input_movie", "file_sha256",
                    capsule["movie_sha256"], capsule.get("movie_bytes"),
                    "timing input movie", minimum))
        state = capsule.get("start_state")
        if state:
            add(_object(f"save:{safe_id}", "save_state", "file_sha256",
                        state["sha256"], state.get("bytes"),
                        "hash-pinned movie start state", minimum))
    binary = capsule_set.get("duckstation_binary_snapshot") or {}
    add(_object("duckstation:binary", "emulator_binary", "file_sha256",
                binary["sha256"], binary.get("bytes"), "capsule emulator binary", minimum))
    runtime = capsule_set.get("duckstation_runtime_bundle")
    if capsule_set["schema"] == "abl-phase4-trace-capsule-set-v2":
        if not isinstance(runtime, dict) or runtime.get("validated") is not True or \
                runtime.get("manifest_covers_runtime_exactly") is not True:
            raise EvidenceError("DuckStation runtime bundle is not exact and validated")
        add(_object("duckstation:runtime", "emulator_runtime_bundle", "tree_sha256",
                    runtime["tree_sha256"], runtime.get("total_file_bytes"),
                    "complete runnable capsule emulator bundle", minimum,
                    "runtime_sha256sums_tree_v1", runtime["manifest"]["sha256"]))
        add(_object("duckstation:runtime-manifest", "emulator_runtime_bundle", "file_sha256",
                    runtime["manifest"]["sha256"], runtime["manifest"].get("bytes"),
                    "runtime SHA256SUMS", minimum))
    elif runtime is not None:
        raise EvidenceError("retained v1 capsule set may not smuggle a runtime bundle")
    source = capsule_set.get("duckstation_source_snapshot") or {}
    add(_object("duckstation:source", "emulator_source_snapshot", "file_sha256",
                source["sha256"], source.get("bytes"), "capsule source snapshot", minimum))
    reader = capsule_set.get("offline_reader_snapshot") or {}
    add(_object("capsule:offline-reader", "offline_reader", "file_sha256",
                reader["sha256"], reader.get("bytes"), "offline capsule reader", minimum))
    sorted_objects = [objects[key] for key in sorted(objects)]
    unknown_sizes = [row["id"] for row in sorted_objects if row["bytes"] is None]
    return {
        "schema": REGISTRY_SCHEMA,
        "source": {
            "trace_capsule_set_schema": capsule_set["schema"],
            "trace_capsule_set_sha256": sha256_bytes(canonical_json(capsule_set)),
            "capsule_count": capsule_set["capsule_count"],
        },
        "policy": {
            "minimum_independent_copies": minimum,
            "public_remotes_allowed": False,
            "repository_bytes_allowed": False,
            "content_layout": policy["content_layout"],
        },
        "objects": sorted_objects,
        "summary": {
            "objects": len(sorted_objects),
            "declared_bytes": sum(row["bytes"] or 0 for row in sorted_objects),
            "unknown_size_objects": unknown_sizes,
            "fully_replicated": 0,
            "preservation_ready": False,
        },
        "authority": policy["authority"],
        "source_dependencies": {
            "tools/phase4_external_evidence.py": sha256_file(Path(__file__)),
            "config/phase4_external_evidence.yaml": sha256_file(POLICY_PATH),
            **({"analysis/phase4_trace_capsule_set.json": sha256_file(capsule_set_path)}
               if capsule_set_path is not None else {}),
        },
    }


def validate_registry(registry: dict[str, Any], policy: dict[str, Any]) -> dict[str, dict]:
    policy = _validate_policy(policy)
    if type(registry) is not dict or set(registry) != {
            "schema", "source", "policy", "objects", "summary", "authority",
            "source_dependencies"}:
        raise EvidenceError("registry top-level field contract mismatch")
    if registry["schema"] != REGISTRY_SCHEMA or type(registry["schema"]) is not str:
        raise EvidenceError(f"registry must use {REGISTRY_SCHEMA}")
    expected_registry_policy = {
        "minimum_independent_copies": 2,
        "public_remotes_allowed": False,
        "repository_bytes_allowed": False,
        "content_layout": EXPECTED_POLICY["content_layout"],
    }
    _assert_exact(registry["policy"], expected_registry_policy, "registry.policy",
                  ordered_dicts=False)
    _assert_exact(registry["authority"], EXPECTED_POLICY["authority"],
                  "registry.authority", ordered_dicts=False)
    objects = registry["objects"]
    if type(objects) is not list or not objects:
        raise EvidenceError("registry has no objects")
    allowed_classes = set(policy["allowed_media_classes"])
    result: dict[str, dict] = {}
    required_keys = {"id", "media_class", "identity_kind", "sha256", "bytes", "role",
                     "required_copies", "verification", "verification_manifest_sha256",
                     "availability"}
    for row in objects:
        if type(row) is not dict or set(row) != required_keys:
            raise EvidenceError("registry object field contract mismatch")
        object_id = row["id"]
        if type(object_id) is not str or not object_id or object_id in result:
            raise EvidenceError("registry object IDs must be non-empty and unique")
        _hex64(row["sha256"], f"{object_id}.sha256")
        if type(row["media_class"]) is not str or row["media_class"] not in allowed_classes:
            raise EvidenceError(f"{object_id}: forbidden media class")
        if type(row["identity_kind"]) is not str or \
                row["identity_kind"] not in {"file_sha256", "tree_sha256"}:
            raise EvidenceError(f"{object_id}: unsupported identity kind")
        verification = row["verification"]
        manifest_sha256 = row["verification_manifest_sha256"]
        if verification == "file_sha256":
            if row["identity_kind"] != "file_sha256" or manifest_sha256 is not None:
                raise EvidenceError(f"{object_id}: file verification contract mismatch")
        elif verification in {"capsule_manifest_tree_v1", "runtime_sha256sums_tree_v1"}:
            if row["identity_kind"] != "tree_sha256":
                raise EvidenceError(f"{object_id}: tree verification contract mismatch")
            _hex64(manifest_sha256, f"{object_id}.verification_manifest_sha256")
        else:
            raise EvidenceError(f"{object_id}: unsupported verification method")
        if row["bytes"] is not None and (type(row["bytes"]) is not int or row["bytes"] < 0):
            raise EvidenceError(f"{object_id}: invalid byte count")
        if type(row["required_copies"]) is not int or row["required_copies"] != 2:
            raise EvidenceError(f"{object_id}: required-copy policy mismatch")
        if type(row["role"]) is not str or not row["role"].strip():
            raise EvidenceError(f"{object_id}: role must be a non-empty string")
        if type(row["availability"]) is not str or row["availability"] != "unverified":
            raise EvidenceError(f"{object_id}: retained registry may not author availability")
        result[object_id] = row
    if list(result) != sorted(result):
        raise EvidenceError("registry objects must be ordered by object ID")

    expected_summary = {
        "objects": len(objects),
        "declared_bytes": sum(row["bytes"] or 0 for row in objects),
        "unknown_size_objects": [row["id"] for row in objects if row["bytes"] is None],
        "fully_replicated": 0,
        "preservation_ready": False,
    }
    _assert_exact(registry["summary"], expected_summary, "registry.summary",
                  ordered_dicts=False)

    source = registry["source"]
    dependencies = registry["source_dependencies"]
    if type(source) is dict and set(source) == {"synthetic"}:
        _assert_exact(source, {"synthetic": True}, "registry.source", ordered_dicts=False)
        _assert_exact(dependencies, {}, "registry.source_dependencies", ordered_dicts=False)
        for object_id, row in result.items():
            if not object_id.startswith("synthetic:") or \
                    row["media_class"] != "offline_reader" or \
                    row["identity_kind"] != "file_sha256" or \
                    row["verification"] != "file_sha256" or \
                    row["role"] != "synthetic pilot object":
                raise EvidenceError("synthetic registry object contract mismatch")
    else:
        expected_source_keys = {
            "trace_capsule_set_schema", "trace_capsule_set_sha256", "capsule_count"}
        if type(source) is not dict or set(source) != expected_source_keys:
            raise EvidenceError("retained registry source field contract mismatch")
        if source["trace_capsule_set_schema"] not in CAPSULE_SET_SCHEMAS:
            raise EvidenceError("retained registry capsule-set schema drifted")
        _hex64(source["trace_capsule_set_sha256"], "registry.source.trace_capsule_set_sha256")
        if type(source["capsule_count"]) is not int or source["capsule_count"] < 1:
            raise EvidenceError("retained registry capsule count is invalid")
        dependency_keys = {
            "tools/phase4_external_evidence.py",
            "config/phase4_external_evidence.yaml",
            "analysis/phase4_trace_capsule_set.json",
        }
        if type(dependencies) is not dict or set(dependencies) != dependency_keys:
            raise EvidenceError("retained registry source-dependency contract mismatch")
        for name, value in dependencies.items():
            _hex64(value, f"registry.source_dependencies.{name}")
        try:
            retained_capsules = json.loads(CAPSULE_SET_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceError("retained capsule-set source is unreadable") from exc
        expected_source = {
            "trace_capsule_set_schema": retained_capsules.get("schema"),
            "trace_capsule_set_sha256": sha256_bytes(canonical_json(retained_capsules)),
            "capsule_count": retained_capsules.get("capsule_count"),
        }
        _assert_exact(source, expected_source, "registry.source", ordered_dicts=False)
        expected_dependencies = {
            "tools/phase4_external_evidence.py": sha256_file(Path(__file__)),
            "config/phase4_external_evidence.yaml": sha256_file(POLICY_PATH),
            "analysis/phase4_trace_capsule_set.json": sha256_file(CAPSULE_SET_PATH),
        }
        _assert_exact(dependencies, expected_dependencies, "registry.source_dependencies",
                      ordered_dicts=False)
        if source["capsule_count"] != sum(
                row["media_class"] == "capsule_tree" for row in objects):
            raise EvidenceError("retained registry capsule count/object set mismatch")
        expected_registry = build_registry(
            retained_capsules, policy, capsule_set_path=CAPSULE_SET_PATH)
        _assert_exact(registry, expected_registry, "retained registry",
                      ordered_dicts=False)
    return result


def content_relative(sha256: str) -> str:
    return f"objects/sha256/{sha256[:2]}/{sha256}"


def _safe_remote_root(raw: Any) -> Path:
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise EvidenceError("remote roots must be absolute")
    root = Path(raw)
    if root.is_symlink() or not root.is_dir():
        raise EvidenceError("remote root must be a non-symlink directory")
    resolved = root.resolve(strict=True)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise EvidenceError("remote root must remain outside the repository")


def _safe_content(root: Path, relative: Any) -> Path:
    parsed = PurePosixPath(relative) if isinstance(relative, str) else None
    if parsed is None or parsed.is_absolute() or relative != parsed.as_posix() or \
            any(part in {"", ".", ".."} for part in parsed.parts):
        raise EvidenceError("unsafe content path")
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise EvidenceError("symlinked evidence content is forbidden")
    resolved = current.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceError("evidence content escapes remote root") from exc
    return resolved


def _tree_files(root: Path) -> set[str]:
    """Enumerate an exact regular-file tree without following any symlink."""
    files: set[str] = set()
    pending = [root]
    while pending:
        directory = pending.pop()
        for child in directory.iterdir():
            if child.is_symlink():
                raise EvidenceError("evidence tree contains a symlink")
            if child.is_dir():
                pending.append(child)
            elif child.is_file():
                files.add(child.relative_to(root).as_posix())
            else:
                raise EvidenceError("evidence tree contains a non-file entry")
    return files


def _capsule_tree(path: Path, expected_manifest_sha256: str) -> tuple[str, int]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise EvidenceError("capsule tree lacks a regular manifest.json")
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise EvidenceError("capsule manifest identity mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError("capsule manifest is unreadable") from exc
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise EvidenceError("capsule manifest has no files")
    digest = hashlib.sha256()
    total = 0
    seen: set[str] = set()
    for row in files:
        relative = row.get("path") if isinstance(row, dict) else None
        if not isinstance(relative, str) or relative in seen:
            raise EvidenceError("capsule manifest paths must be unique")
        seen.add(relative)
        file_path = _safe_content(path, relative)
        if not file_path.is_file():
            raise EvidenceError("capsule manifest entry is not a file")
        actual = sha256_file(file_path)
        size = file_path.stat().st_size
        if actual != row.get("sha256") or size != row.get("bytes"):
            raise EvidenceError("capsule manifest entry identity mismatch")
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(actual.encode())
        digest.update(b"\0")
        total += size
    if _tree_files(path) != {"manifest.json", *seen}:
        raise EvidenceError("capsule manifest does not cover the exact tree")
    return digest.hexdigest(), total


def _runtime_tree(path: Path, expected_manifest_sha256: str) -> tuple[str, int]:
    manifest_path = path / "SHA256SUMS"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise EvidenceError("runtime tree lacks a regular SHA256SUMS")
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise EvidenceError("runtime SHA256SUMS identity mismatch")
    digest = hashlib.sha256()
    total = 0
    declared: set[str] = set()
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        match = SHA_LINE.fullmatch(line)
        if not match:
            raise EvidenceError("runtime SHA256SUMS is malformed or duplicated")
        expected, relative = match.groups()
        logical = PurePosixPath(relative).as_posix()
        if relative != logical or logical in declared:
            raise EvidenceError("runtime SHA256SUMS path is noncanonical or duplicated")
        declared.add(logical)
        file_path = _safe_content(path, logical)
        if not file_path.is_file():
            raise EvidenceError("runtime manifest entry is not a file")
        actual = sha256_file(file_path)
        size = file_path.stat().st_size
        if actual != expected:
            raise EvidenceError("runtime manifest entry hash mismatch")
        digest.update(logical.encode())
        digest.update(b"\0")
        digest.update(actual.encode())
        digest.update(b"\0")
        digest.update(str(size).encode())
        digest.update(b"\0")
        total += size
    if _tree_files(path) != {"SHA256SUMS", *declared}:
        raise EvidenceError("runtime SHA256SUMS does not cover the exact tree")
    return digest.hexdigest(), total


def verify_object(path: Path, row: dict[str, Any]) -> tuple[str, int]:
    if row["verification"] == "file_sha256":
        if not path.is_file():
            raise EvidenceError("file object is not a regular file")
        return sha256_file(path), path.stat().st_size
    manifest_sha256 = row.get("verification_manifest_sha256")
    if row["verification"] == "capsule_manifest_tree_v1" and path.is_dir():
        return _capsule_tree(path, manifest_sha256)
    if row["verification"] == "runtime_sha256sums_tree_v1" and path.is_dir():
        return _runtime_tree(path, manifest_sha256)
    raise EvidenceError("object verification method/path type is unsupported")


def _physical_nodes(path: Path, row: dict[str, Any]) -> frozenset[tuple[int, int]]:
    """Return the physical filesystem nodes that substantiate one verified copy.

    Remote names and failure-domain labels are assertions, not physical identity.
    Canonical roots catch path aliases; device/inode identities additionally keep
    hard-linked files or trees from being counted as independent copies.
    """
    members = [path]
    if row["verification"] == "capsule_manifest_tree_v1":
        manifest_path = path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        members = [manifest_path] + [
            _safe_content(path, item["path"]) for item in manifest["files"]
        ]
    elif row["verification"] == "runtime_sha256sums_tree_v1":
        manifest_path = path / "SHA256SUMS"
        members = [manifest_path]
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            match = SHA_LINE.fullmatch(line)
            if match:
                members.append(_safe_content(path, match.group(2).removeprefix("./")))
    return frozenset((member.stat().st_dev, member.stat().st_ino) for member in members)


def _contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if any(word in str(key).lower() for word in ("token", "password", "secret", "credential")):
                return True
            if _contains_secret(child):
                return True
    elif isinstance(value, list):
        return any(_contains_secret(child) for child in value)
    return False


def _overlapping_roots(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _independent_failure_domains(rows: list[dict[str, Any]]) -> list[str]:
    """Return a maximum set with distinct verified devices and declared domains.

    A caller label may correlate otherwise separate devices, but it can never split
    one verified physical device into several independent copies. Unattested remote
    kinds have no physical_domain and therefore cannot contribute to readiness.
    """
    edges: dict[tuple[str, int], set[str]] = {}
    for row in rows:
        physical_domain = row.get("physical_domain")
        if physical_domain is not None:
            edges.setdefault(physical_domain, set()).add(row["failure_domain"])
    label_to_device: dict[str, tuple[str, int]] = {}

    def assign(device: tuple[str, int], visited: set[str]) -> bool:
        for label in sorted(edges[device]):
            if label in visited:
                continue
            visited.add(label)
            prior = label_to_device.get(label)
            if prior is None or assign(prior, visited):
                label_to_device[label] = device
                return True
        return False

    for device in sorted(edges):
        assign(device, set())
    return sorted(label_to_device)


def _validate_receipt_document(receipts: Any, registry: dict[str, Any],
                               objects: dict[str, dict],
                               policy: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Validate the complete receipt claim before considering any copy ready."""
    if type(receipts) is not dict:
        raise EvidenceError("receipt set must be an object")
    if _contains_secret(receipts):
        raise EvidenceError("receipt set may not retain secrets or credentials")
    if set(receipts) != {"schema", "registry_sha256", "remotes", "copies"}:
        raise EvidenceError("receipt top-level field contract mismatch")
    if type(receipts["schema"]) is not str or receipts["schema"] != RECEIPT_SCHEMA:
        raise EvidenceError(f"receipt set must use {RECEIPT_SCHEMA}")
    _hex64(receipts["registry_sha256"], "receipts.registry_sha256")
    if receipts["registry_sha256"] != sha256_bytes(canonical_json(registry)):
        raise EvidenceError("receipt registry identity mismatch")
    remotes_raw = receipts["remotes"]
    copies = receipts["copies"]
    if type(remotes_raw) is not list or not remotes_raw or type(copies) is not list:
        raise EvidenceError("receipt set needs a remote list and a copy list")

    remote_ids: set[str] = set()
    for remote in remotes_raw:
        if type(remote) is not dict or set(remote) != {
                "id", "root", "kind", "public", "failure_domain"}:
            raise EvidenceError("remote declaration field contract mismatch")
        remote_id = remote["id"]
        if type(remote_id) is not str or not remote_id or remote_id in remote_ids:
            raise EvidenceError("remote IDs must be non-empty strings and unique")
        remote_ids.add(remote_id)
        if type(remote["root"]) is not str or not remote["root"]:
            raise EvidenceError("remote root must be a non-empty string")
        if type(remote["kind"]) is not str or \
                remote["kind"] not in policy["allowed_remote_kinds"]:
            raise EvidenceError("only declared private/offline remote kinds are allowed")
        if type(remote["public"]) is not bool or remote["public"] is not False:
            raise EvidenceError("only declared private/offline remote kinds are allowed")
        if type(remote["failure_domain"]) is not str or not remote["failure_domain"].strip():
            raise EvidenceError("each remote needs a named failure domain")

    seen: set[tuple[str, str]] = set()
    for copy_row in copies:
        if type(copy_row) is not dict or set(copy_row) != {
                "object_id", "remote_id", "relative_path", "sha256", "bytes"}:
            raise EvidenceError("copy receipt field contract mismatch")
        object_id = copy_row["object_id"]
        remote_id = copy_row["remote_id"]
        if type(object_id) is not str or type(remote_id) is not str or \
                object_id not in objects or remote_id not in remote_ids or \
                (object_id, remote_id) in seen:
            raise EvidenceError("copy references unknown/duplicate object or remote")
        seen.add((object_id, remote_id))
        obj = objects[object_id]
        if type(copy_row["relative_path"]) is not str or \
                copy_row["relative_path"] != content_relative(obj["sha256"]):
            raise EvidenceError("copy is outside the content-addressed layout")
        _hex64(copy_row["sha256"], f"receipt.{object_id}.sha256")
        if copy_row["sha256"] != obj["sha256"]:
            raise EvidenceError("copy receipt hash differs from registry")
        if type(copy_row["bytes"]) is not int or copy_row["bytes"] < 0:
            raise EvidenceError("copy receipt byte count is invalid")
        if obj["bytes"] is not None and copy_row["bytes"] != obj["bytes"]:
            raise EvidenceError("copy receipt byte count differs from registry")
    return remotes_raw, copies


def verify_receipts(registry: dict[str, Any], receipts: dict[str, Any],
                    policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = load_policy() if policy is None else _validate_policy(policy)
    objects = validate_registry(registry, policy)
    remotes_raw, copies = _validate_receipt_document(receipts, registry, objects, policy)
    remotes: dict[str, dict] = {}
    canonical_roots: set[Path] = set()
    physical_roots: set[tuple[int, int]] = set()
    for remote in remotes_raw:
        remote_id = remote["id"]
        resolved_root = _safe_remote_root(remote["root"])
        stat = resolved_root.stat()
        physical_root = (stat.st_dev, stat.st_ino)
        if resolved_root in canonical_roots or physical_root in physical_roots:
            raise EvidenceError("remote declarations resolve to a duplicate physical root")
        if any(_overlapping_roots(resolved_root, prior) for prior in canonical_roots):
            raise EvidenceError("remote declarations have overlapping physical roots")
        canonical_roots.add(resolved_root)
        physical_roots.add(physical_root)
        verified_kinds = set(policy["physical_domain_policy"]["verified_local_kinds"])
        physical_domain = ("st_dev", stat.st_dev) if remote["kind"] in verified_kinds else None
        remotes[remote_id] = {
            **remote, "resolved_root": resolved_root,
            "physical_domain": physical_domain,
        }
    seen: set[tuple[str, str]] = set()
    verified: dict[str, list[dict]] = {object_id: [] for object_id in objects}
    verified_physical_nodes: dict[str, set[tuple[int, int]]] = {
        object_id: set() for object_id in objects
    }
    failures: list[dict] = []
    for copy_row in copies:
        object_id, remote_id = copy_row["object_id"], copy_row["remote_id"]
        seen.add((object_id, remote_id))
        obj = objects[object_id]
        try:
            path = _safe_content(remotes[remote_id]["resolved_root"], copy_row["relative_path"])
            actual_hash, actual_bytes = verify_object(path, obj)
            expected_bytes = obj["bytes"]
            if actual_hash != obj["sha256"] or actual_bytes != copy_row["bytes"] or \
                    (expected_bytes is not None and actual_bytes != expected_bytes):
                raise EvidenceError("copy byte/hash identity mismatch")
            physical_nodes = _physical_nodes(path, obj)
        except (OSError, EvidenceError) as exc:
            failures.append({"object_id": object_id, "remote_id": remote_id,
                             "reason": type(exc).__name__})
            continue
        if verified_physical_nodes[object_id].intersection(physical_nodes):
            raise EvidenceError("object copies share a physical content source")
        verified_physical_nodes[object_id].update(physical_nodes)
        verified[object_id].append({"remote_id": remote_id,
                                    "failure_domain": remotes[remote_id]["failure_domain"],
                                    "physical_domain": remotes[remote_id]["physical_domain"]})
    object_status = []
    fully_replicated = 0
    for object_id, obj in sorted(objects.items()):
        failure_domains = _independent_failure_domains(verified[object_id])
        ready = len(failure_domains) >= obj["required_copies"]
        fully_replicated += int(ready)
        object_status.append({"id": object_id, "verified_copies": len(verified[object_id]),
                              "independent_failure_domains": failure_domains,
                              "unattested_domain_copies": sum(
                                  row["physical_domain"] is None
                                  for row in verified[object_id]),
                              "required_copies": obj["required_copies"], "ready": ready})
    return {
        "schema": "abl-phase4-external-evidence-verification/1",
        "registry_sha256": sha256_bytes(canonical_json(registry)),
        "remotes": [{"id": row["id"], "kind": row["kind"],
                     "failure_domain": row["failure_domain"], "public": False,
                     "physical_domain_verified":
                         remotes[row["id"]]["physical_domain"] is not None}
                    for row in remotes_raw],
        "objects": object_status,
        "failures": failures,
        "summary": {"objects": len(objects), "fully_replicated": fully_replicated,
                    "preservation_ready": fully_replicated == len(objects) and not failures},
        "authority": policy["authority"],
    }


def annex_plan(registry: dict[str, Any], policy: dict[str, Any] | None = None) -> dict:
    policy = load_policy() if policy is None else _validate_policy(policy)
    objects = validate_registry(registry, policy)
    file_objects = [row["id"] for row in objects.values() if row["identity_kind"] == "file_sha256"]
    tree_objects = [row["id"] for row in objects.values() if row["identity_kind"] == "tree_sha256"]
    return {
        "schema": "abl-phase4-private-annex-plan/1",
        "execute_automatically": False,
        "public_remote_allowed": False,
        "repository_initialization_performed": False,
        "steps": [
            "Create a private external annex repository outside ABL.",
            "Configure at least two offline remotes in distinct failure domains.",
            "For local/removable roots, require distinct verified filesystem devices.",
            "Do not count private-annex roots without immutable remote attestation.",
            "Package tree objects with their validation manifests before annex ingestion.",
            "Import file objects by content hash and emit an external receipt set.",
            "Run this tool's verify command before claiming availability.",
        ],
        "file_objects_ready_for_annex": sorted(file_objects),
        "tree_objects_require_external_packaging": sorted(tree_objects),
    }


def _synthetic_registry(blobs: dict[str, bytes], policy: dict[str, Any]) -> dict:
    policy = _validate_policy(policy)
    objects = [_object(name, "offline_reader", "file_sha256", sha256_bytes(value), len(value),
                       "synthetic pilot object", policy["minimum_independent_copies"])
               for name, value in sorted(blobs.items())]
    return {
        "schema": REGISTRY_SCHEMA, "source": {"synthetic": True},
        "policy": {"minimum_independent_copies": policy["minimum_independent_copies"],
                   "public_remotes_allowed": False, "repository_bytes_allowed": False,
                   "content_layout": policy["content_layout"]},
        "objects": objects,
        "summary": {"objects": len(objects), "declared_bytes": sum(map(len, blobs.values())),
                    "unknown_size_objects": [], "fully_replicated": 0,
                    "preservation_ready": False},
        "authority": policy["authority"], "source_dependencies": {},
    }


def build_pilot() -> dict[str, Any]:
    policy = load_policy()
    blobs = {"synthetic:alpha": b"alpha evidence\n", "synthetic:beta": b"beta evidence\n"}
    registry = _synthetic_registry(blobs, policy)
    with tempfile.TemporaryDirectory(prefix="abl-phase4-evidence-") as temp:
        base = Path(temp)
        remotes = []
        copies = []
        for index in (1, 2):
            root = base / f"remote-{index}"
            root.mkdir()
            remotes.append({"id": f"remote-{index}", "root": str(root),
                            "kind": "offline_local", "public": False,
                            "failure_domain": f"synthetic-device-{index}"})
            for object_id, blob in blobs.items():
                digest = sha256_bytes(blob)
                relative = content_relative(digest)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
                copies.append({"object_id": object_id, "remote_id": f"remote-{index}",
                               "relative_path": relative, "sha256": digest,
                               "bytes": len(blob)})
        receipts = {"schema": RECEIPT_SCHEMA,
                    "registry_sha256": sha256_bytes(canonical_json(registry)),
                    "remotes": remotes, "copies": copies}
        same_device = verify_receipts(registry, receipts, policy)
        distinct_device_model = _independent_failure_domains([
            {"failure_domain": "synthetic-device-1",
             "physical_domain": ("st_dev", 101)},
            {"failure_domain": "synthetic-device-2",
             "physical_domain": ("st_dev", 202)},
        ])
        duplicate_root_rejected = False
        duplicate_root = copy.deepcopy(receipts)
        duplicate_root["remotes"][1]["root"] = duplicate_root["remotes"][0]["root"]
        try:
            verify_receipts(registry, duplicate_root, policy)
        except EvidenceError:
            duplicate_root_rejected = True
        hardlink_rejected = False
        linked_path = Path(remotes[1]["root"]) / copies[-1]["relative_path"]
        source_path = Path(remotes[0]["root"]) / copies[-1]["relative_path"]
        linked_path.unlink()
        linked_path.hardlink_to(source_path)
        try:
            verify_receipts(registry, receipts, policy)
        except EvidenceError:
            hardlink_rejected = True
        linked_path.unlink()
        linked_path.write_bytes(blobs[copies[-1]["object_id"]])
        tampered_path = Path(remotes[1]["root"]) / copies[-1]["relative_path"]
        tampered_path.write_bytes(b"tampered\n")
        tampered = verify_receipts(registry, receipts, policy)
        public_rejected = False
        public = copy.deepcopy(receipts)
        public["remotes"][0]["public"] = True
        try:
            verify_receipts(registry, public, policy)
        except EvidenceError:
            public_rejected = True
        symlink_rejected = False
        tampered_path.unlink()
        tampered_path.symlink_to(Path(remotes[0]["root"]) / copies[-1]["relative_path"])
        try:
            symlink_result = verify_receipts(registry, receipts, policy)
            symlink_rejected = (not symlink_result["summary"]["preservation_ready"] and
                                bool(symlink_result["failures"]))
        except EvidenceError:
            symlink_rejected = True
    failures = []
    if same_device["summary"]["preservation_ready"] or \
            same_device["summary"]["fully_replicated"]:
        failures.append("same_device_directories_counted_as_independent")
    if distinct_device_model != ["synthetic-device-1", "synthetic-device-2"]:
        failures.append("distinct_physical_domain_model_failed")
    if not duplicate_root_rejected:
        failures.append("duplicate_physical_root_not_rejected")
    if not hardlink_rejected:
        failures.append("shared_physical_content_not_rejected")
    if tampered["summary"]["preservation_ready"] or not tampered["failures"]:
        failures.append("tamper_not_detected")
    if not public_rejected:
        failures.append("public_remote_not_rejected")
    if not symlink_rejected:
        failures.append("symlink_not_rejected")
    return {
        "schema": PILOT_SCHEMA, "runtime_evidence": False, "synthetic_only": True,
        "cases": {
            "same_device_directories": same_device["summary"],
            "distinct_physical_domain_model": {
                "independent_failure_domains": distinct_device_model,
                "ready_at_two": len(distinct_device_model) >= 2,
            },
            "duplicate_physical_root_rejected": duplicate_root_rejected,
            "shared_physical_content_rejected": hardlink_rejected,
            "tampered_copy": tampered["summary"],
            "public_remote_rejected": public_rejected,
            "symlink_rejected": symlink_rejected,
        },
        "summary": {"objects": len(blobs), "failures": failures},
        "annex": annex_plan(registry, policy),
        "production_contract": {
            "registry_is_hash_only": True, "availability_requires_external_receipts": True,
            "minimum_independent_copies": policy["minimum_independent_copies"],
            "local_physical_identity": "st_dev",
            "private_annex_counts_without_attestation": False,
            "public_remote_allowed": False, "annex_execution_automatic": False,
            "campaign_promotion": False,
        },
        "source_dependencies": {
            "tools/phase4_external_evidence.py": sha256_file(Path(__file__)),
            "config/phase4_external_evidence.yaml": sha256_file(POLICY_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--capsule-set", type=Path, default=CAPSULE_SET_PATH)
    verify = sub.add_parser("verify")
    verify.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    verify.add_argument("--receipts", type=Path, required=True)
    annex = sub.add_parser("annex-plan")
    annex.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    sub.add_parser("pilot")
    args = parser.parse_args()
    if args.command == "generate":
        capsule_set = json.loads(args.capsule_set.read_text(encoding="utf-8"))
        registry = build_registry(capsule_set, capsule_set_path=args.capsule_set)
        REGISTRY_PATH.write_bytes(canonical_json(registry))
        print(f"[phase4-external-evidence] registered {len(registry['objects'])} hash-only objects")
        return 0
    if args.command == "verify":
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        receipts = json.loads(args.receipts.read_text(encoding="utf-8"))
        result = verify_receipts(registry, receipts)
        print(json.dumps(result, indent=1, sort_keys=True))
        return 0 if result["summary"]["preservation_ready"] else 1
    if args.command == "annex-plan":
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        print(json.dumps(annex_plan(registry), indent=1, sort_keys=True))
        return 0
    pilot = build_pilot()
    if pilot["summary"]["failures"]:
        raise EvidenceError(f"external-evidence pilot failed: {pilot['summary']['failures']}")
    PILOT_PATH.write_bytes(canonical_json(pilot))
    print("[phase4-external-evidence] synthetic physical-domain/alias/hardlink/tamper/public/symlink pilot; OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
