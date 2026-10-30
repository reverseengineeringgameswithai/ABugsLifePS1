"""Immutable toolchain snapshots keep long live replays independent of rebuilds."""
import json
import os
import shutil
from pathlib import Path

import pytest

import live_toolchain_snapshot as snapshot


def _sha(path: Path) -> str:
    return snapshot.sha256(path)


def _chmod_tree(root: Path, mode: int) -> None:
    for path in [root, *root.rglob("*")]:
        if path.is_dir():
            os.chmod(path, mode)


def test_snapshot_verification_recomputes_private_bytes_and_retained_identity(
        tmp_path, monkeypatch):
    retained_path = tmp_path / "rpc.json"
    private = tmp_path / "private"
    source = tmp_path / "source"
    binary_rel = "build-release/bin/duckstation-qt"
    launcher_rel = "scripts/debugger-client/launch_debugger_instance.sh"
    client_rel = "scripts/debugger-client/duckstation_debug_client.py"
    payloads = {
        launcher_rel: b"#!/bin/sh\n",
        client_rel: b"client-v1\n",
    }
    files = {}
    for rel, payload in payloads.items():
        path = private / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        os.chmod(path, 0o555)
        files[rel] = {
            "sha256": _sha(path), "size": len(payload),
            "source_path": str(Path("/source") / rel),
        }
    runtime = source / "build-release/bin"
    runtime.mkdir(parents=True)
    (runtime / "libsupport.so").write_bytes(b"support-v1")
    source_binary = runtime / "duckstation-qt"
    source_binary.write_bytes(b"binary-v1")
    private_binary = runtime / f"{snapshot.PRIVATE_BINARY_PREFIX}unit"
    private_binary.write_bytes(source_binary.read_bytes())
    os.chmod(private_binary, 0o555)
    retained = {
        "source": {
            "revision": "a" * 40,
            "status_sha256": "b" * 64,
            "dispatcher_sha256": "c" * 64,
        },
        "methods": {"counts": {"current": 203}},
    }
    retained_path.write_text(json.dumps(retained))
    monkeypatch.setattr(snapshot, "RETAINED_MANIFEST", retained_path)
    doc = {
        "version": 2,
        "owner": "phase3-verifier-owned-sibling",
        "retained_rpc_manifest_sha256": _sha(retained_path),
        "source": {
            "root": str(source),
            "revision": "a" * 40,
            "status_sha256": "b" * 64,
            "dispatcher_sha256": "c" * 64,
            "method_count": 203,
        },
        "binary_rel": binary_rel,
        "runtime_tree_rel": "build-release/bin",
        "runtime_tree": snapshot.rpc_manifest.runtime_tree_identity(
            runtime),
        "private_binary": {
            "path": str(private_binary),
            "source_path": str(source_binary),
            "sha256": _sha(private_binary),
            "size": private_binary.stat().st_size,
        },
        "launcher_rel": launcher_rel,
        "client_rel": client_rel,
        "files": files,
    }
    manifest = private / snapshot.SNAPSHOT_MANIFEST
    manifest.write_text(json.dumps(doc))
    os.chmod(manifest, 0o444)
    _chmod_tree(private, 0o555)

    verified = snapshot.verify_snapshot(manifest)
    assert verified["verified"] is True
    assert verified["binary_sha256"] == _sha(private_binary)

    os.chmod(private / client_rel, 0o755)
    (private / client_rel).write_bytes(b"mutated")
    os.chmod(private / client_rel, 0o555)
    with pytest.raises(SystemExit, match="private file drifted"):
        snapshot.verify_snapshot(manifest)


@pytest.mark.local_media
def test_current_fork_can_be_copied_to_a_fresh_read_only_snapshot(tmp_path):
    target = tmp_path / "toolchain"
    manifest = None
    try:
        manifest = snapshot.prepare_snapshot(
            source_root=Path.home() / "duckstation",
            snapshot_dir=target,
            binary_rel=Path("build-release/bin/duckstation-qt"),
        )
        verified = snapshot.verify_snapshot(manifest)
        assert verified["verified"] is True
        assert verified["source_binary_path"].endswith(
            "/duckstation/build-release/bin/duckstation-qt")
        assert Path(verified["_paths"]["binary"]).parent == Path.home() / (
            "duckstation/build-release/bin")
        assert not (target.stat().st_mode & 0o222)
    finally:
        if manifest is not None:
            cleanup = snapshot.cleanup_snapshot_binary(manifest)
            assert cleanup["private_binary_removed"] is True
        if target.exists():
            _chmod_tree(target, 0o700)
            shutil.rmtree(target)
