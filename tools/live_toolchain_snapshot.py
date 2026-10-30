#!/usr/bin/env python3
"""Create and verify an immutable per-replay DuckStation toolchain snapshot.

The operator's ``~/duckstation`` worktree is an active development checkout.  A
build can replace ``duckstation-qt`` in place while a long movie replay is still
running, leaving ``/proc/<pid>/exe`` on a deleted inode and making final
provenance/cleanup depend on a path that no longer names the running bytes.

This helper first requires the external checkout to match the retained Phase-3
RPC manifest.  It copies the launcher and client into a new verifier-owned
directory under ``/tmp`` and gives the selected executable an exclusive,
read-only sibling copy in its canonical ``build-release/bin`` directory.  That
last detail is required: DuckStation resolves Qt resources from its application
directory and a byte-identical executable relocated under ``/tmp`` does not
finish startup.  The unique sibling is independent of canonical in-place
rebuilds while retaining the correct application directory.  The helper pins
the remaining runtime support tree before and after the replay and removes only
the exact owned sibling after stopping its exact PID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import stat
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import phase3_duckstation_rpc_manifest as rpc_manifest
    import live_session_provenance as live_provenance
except ModuleNotFoundError:
    from tools import phase3_duckstation_rpc_manifest as rpc_manifest
    from tools import live_session_provenance as live_provenance


ROOT = Path(__file__).resolve().parents[1]
RETAINED_MANIFEST = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
LAUNCHER_REL = Path("scripts/debugger-client/launch_debugger_instance.sh")
CLIENT_REL = Path("scripts/debugger-client/duckstation_debug_client.py")
SNAPSHOT_MANIFEST = "snapshot_manifest.json"
PRIVATE_BINARY_PREFIX = "duckstation-qt.phase3-verifier-"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _under_tmp(path: Path, label: str) -> Path:
    path = path.expanduser().resolve()
    if not path.is_absolute() or not str(path).startswith("/tmp/"):
        raise SystemExit(f"toolchain snapshot guard: {label} must be under /tmp: {path}")
    return path


def _retained() -> dict:
    try:
        return json.loads(RETAINED_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"toolchain snapshot guard: cannot read {RETAINED_MANIFEST}: {exc}") from exc


def _expected_row(retained: dict, rel: Path) -> dict:
    key = rel.as_posix()
    if key in retained.get("binaries", {}):
        return retained["binaries"][key]
    if key in retained.get("source", {}).get("files", {}):
        return retained["source"]["files"][key]
    raise SystemExit(f"toolchain snapshot guard: {key} is not pinned by the RPC manifest")


def prepare_snapshot(*, source_root: Path, snapshot_dir: Path,
                     binary_rel: Path) -> Path:
    source_root = source_root.expanduser().resolve()
    snapshot_dir = _under_tmp(snapshot_dir, "--snapshot-dir")
    if snapshot_dir.exists():
        raise SystemExit(
            f"toolchain snapshot guard: refusing existing snapshot directory: {snapshot_dir}")

    retained = _retained()
    before_gaps = rpc_manifest.current_fork_gaps(retained, source_root)
    if before_gaps:
        raise SystemExit("toolchain snapshot guard: external fork is stale: "
                         + "; ".join(before_gaps))
    if binary_rel.as_posix() not in retained.get("binaries", {}):
        raise SystemExit(
            f"toolchain snapshot guard: binary is not retained: {binary_rel.as_posix()}")

    runtime_root_rel = binary_rel.parent
    runtime_source = (source_root / runtime_root_rel).resolve()
    source_binary = (source_root / binary_rel).resolve()
    expected_binary = _expected_row(retained, binary_rel)
    if (not source_binary.is_file() or source_binary.is_symlink()
            or source_binary.parent != runtime_source):
        raise SystemExit(
            f"toolchain snapshot guard: source binary is absent, symlinked, "
            f"or outside its runtime directory: {source_binary}")
    actual_binary = {
        "sha256": sha256(source_binary), "size": source_binary.stat().st_size,
    }
    if actual_binary != {
            "sha256": expected_binary["sha256"], "size": expected_binary["size"]}:
        raise SystemExit(
            f"toolchain snapshot guard: source binary identity drifted: "
            f"actual={actual_binary} expected={expected_binary}")
    retained_runtime_identity = retained.get("runtime_trees", {}).get(
        runtime_root_rel.as_posix())
    runtime_identity = rpc_manifest.runtime_tree_identity(runtime_source)
    if runtime_identity != retained_runtime_identity:
        raise SystemExit(
            "toolchain snapshot guard: release runtime support differs from "
            f"retained identity: {runtime_identity} != {retained_runtime_identity}")

    rels = (LAUNCHER_REL, CLIENT_REL)
    snapshot_dir.mkdir(parents=True, mode=0o700)
    copied: dict[str, dict] = {}
    private_binary: Path | None = None
    try:
        for rel in rels:
            source = source_root / rel
            try:
                expected = _expected_row(retained, rel)
            except SystemExit:  # both paths are centrally pinned; defensive only
                raise
            if not source.is_file() or source.is_symlink():
                raise SystemExit(
                    f"toolchain snapshot guard: source is absent or symlinked: {source}")
            actual = {"sha256": sha256(source), "size": source.stat().st_size}
            if actual != {"sha256": expected["sha256"], "size": expected["size"]}:
                raise SystemExit(
                    f"toolchain snapshot guard: source identity drifted for {rel}: "
                    f"actual={actual} expected={expected}")
            target = snapshot_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            os.chmod(target, 0o555)
            copied[rel.as_posix()] = {
                "sha256": sha256(target),
                "size": target.stat().st_size,
                "source_path": str(source),
            }
            if copied[rel.as_posix()]["sha256"] != expected["sha256"]:
                raise SystemExit(
                    f"toolchain snapshot guard: copied bytes differ for {rel}")

        # A unique sibling preserves applicationDirPath while breaking the
        # mutable canonical path's inode identity.  Exclusive creation and a
        # random owner suffix prevent collision with another verifier.
        private_binary = runtime_source / f"{PRIVATE_BINARY_PREFIX}{uuid.uuid4().hex}"
        with source_binary.open("rb") as src, private_binary.open("xb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
            dst.flush()
            os.fsync(dst.fileno())
        os.chmod(private_binary, 0o555)
        private_row = {
            "path": str(private_binary),
            "source_path": str(source_binary),
            "sha256": sha256(private_binary),
            "size": private_binary.stat().st_size,
        }
        if {key: private_row[key] for key in ("sha256", "size")} != actual_binary:
            raise SystemExit("toolchain snapshot guard: private executable copy differs")

        # Close both copy-time races. The ignored verifier sibling is not part
        # of Git status or the support-tree selection.
        after_gaps = rpc_manifest.current_fork_gaps(retained, source_root)
        if after_gaps:
            raise SystemExit("toolchain snapshot guard: external fork changed during copy: "
                             + "; ".join(after_gaps))
        after_runtime_identity = rpc_manifest.runtime_tree_identity(runtime_source)
        if after_runtime_identity != runtime_identity:
            raise SystemExit(
                "toolchain snapshot guard: release runtime support changed during copy")

        doc = {
            "version": 2,
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "owner": "phase3-verifier-owned-sibling",
            "retained_rpc_manifest": RETAINED_MANIFEST.relative_to(ROOT).as_posix(),
            "retained_rpc_manifest_sha256": sha256(RETAINED_MANIFEST),
            "source": {
                "root": str(source_root),
                "revision": retained["source"]["revision"],
                "status_sha256": retained["source"]["status_sha256"],
                "dispatcher_sha256": retained["source"]["dispatcher_sha256"],
                "method_count": retained["methods"]["counts"]["current"],
            },
            "binary_rel": binary_rel.as_posix(),
            "runtime_tree_rel": runtime_root_rel.as_posix(),
            "runtime_tree": runtime_identity,
            "private_binary": private_row,
            "launcher_rel": LAUNCHER_REL.as_posix(),
            "client_rel": CLIENT_REL.as_posix(),
            "files": copied,
        }
        manifest_path = snapshot_dir / SNAPSHOT_MANIFEST
        manifest_path.write_text(json.dumps(doc, indent=1) + "\n")
        os.chmod(manifest_path, 0o444)
        # The /tmp control files are private and read-only. The executable has
        # its own inode and is read-only; only its canonical parent remains
        # writable, which is why finish/cleanup validates its exact random name
        # and hash before unlinking it.
        for directory in sorted(
                (p for p in snapshot_dir.rglob("*") if p.is_dir()),
                key=lambda p: len(p.parts), reverse=True):
            os.chmod(directory, 0o555)
        os.chmod(snapshot_dir, 0o555)
        verify_snapshot(manifest_path)
        return manifest_path
    except BaseException:
        # This directory was created by this call and has never been accepted.
        # Restore owner write permission only so the incomplete private copy can
        # be removed without touching any caller-owned path.
        for directory in [snapshot_dir, *snapshot_dir.rglob("*")]:
            if directory.is_dir():
                try:
                    os.chmod(directory, 0o700)
                except OSError:
                    pass
        shutil.rmtree(snapshot_dir, ignore_errors=True)
        if private_binary is not None and private_binary.exists():
            try:
                if (private_binary.parent == runtime_source
                        and private_binary.name.startswith(PRIVATE_BINARY_PREFIX)):
                    private_binary.unlink()
            except OSError:
                pass
        raise


def verify_snapshot(manifest_path: Path) -> dict:
    manifest_path = _under_tmp(manifest_path, "--toolchain-snapshot")
    if manifest_path.name != SNAPSHOT_MANIFEST or not manifest_path.is_file():
        raise SystemExit(
            f"toolchain snapshot guard: invalid snapshot manifest: {manifest_path}")
    snapshot_dir = manifest_path.parent.resolve()
    try:
        doc = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"toolchain snapshot guard: malformed manifest: {exc}") from exc
    if (doc.get("version") != 2
            or doc.get("owner") != "phase3-verifier-owned-sibling"):
        raise SystemExit("toolchain snapshot guard: unsupported/unowned snapshot manifest")
    if doc.get("retained_rpc_manifest_sha256") != sha256(RETAINED_MANIFEST):
        raise SystemExit("toolchain snapshot guard: retained RPC manifest changed")
    retained = _retained()
    source = doc.get("source") or {}
    expected_source = {
        "revision": retained["source"]["revision"],
        "status_sha256": retained["source"]["status_sha256"],
        "dispatcher_sha256": retained["source"]["dispatcher_sha256"],
        "method_count": retained["methods"]["counts"]["current"],
    }
    if any(source.get(key) != value for key, value in expected_source.items()):
        raise SystemExit("toolchain snapshot guard: source identity differs from retained RPC manifest")

    resolved: dict[str, Path] = {}
    for rel, row in (doc.get("files") or {}).items():
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise SystemExit(f"toolchain snapshot guard: unsafe relative path: {rel}")
        path = snapshot_dir / rel_path
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"toolchain snapshot guard: missing/symlinked private file: {path}")
        if sha256(path) != row.get("sha256") or path.stat().st_size != row.get("size"):
            raise SystemExit(f"toolchain snapshot guard: private file drifted: {path}")
        if stat.S_IMODE(path.stat().st_mode) & 0o222:
            raise SystemExit(f"toolchain snapshot guard: private file remains writable: {path}")
        resolved[rel] = path
    required = (doc.get("launcher_rel"), doc.get("client_rel"))
    if any(rel not in resolved for rel in required):
        raise SystemExit("toolchain snapshot guard: launcher/client copy is incomplete")
    runtime_tree_rel = doc.get("runtime_tree_rel")
    source_root = Path(source.get("root") or "").expanduser().resolve()
    binary_rel = Path(doc.get("binary_rel") or "")
    if (not runtime_tree_rel or binary_rel.is_absolute()
            or ".." in binary_rel.parts):
        raise SystemExit("toolchain snapshot guard: invalid binary/runtime declaration")
    runtime_root = (source_root / runtime_tree_rel).resolve()
    if (runtime_root != (source_root / binary_rel).resolve().parent
            or rpc_manifest.runtime_tree_identity(runtime_root) != doc.get("runtime_tree")):
        raise SystemExit("toolchain snapshot guard: release runtime support identity drifted")

    private_row = doc.get("private_binary") or {}
    private_binary = Path(private_row.get("path") or "").resolve()
    if (private_binary.parent != runtime_root
            or not private_binary.name.startswith(PRIVATE_BINARY_PREFIX)
            or not private_binary.is_file() or private_binary.is_symlink()):
        raise SystemExit(
            f"toolchain snapshot guard: private executable is absent or unowned: "
            f"{private_binary}")
    if (sha256(private_binary) != private_row.get("sha256")
            or private_binary.stat().st_size != private_row.get("size")):
        raise SystemExit("toolchain snapshot guard: private executable drifted")
    if stat.S_IMODE(private_binary.stat().st_mode) & 0o222:
        raise SystemExit("toolchain snapshot guard: private executable remains writable")
    source_binary = (source_root / binary_rel).resolve()
    if private_row.get("source_path") != str(source_binary):
        raise SystemExit("toolchain snapshot guard: private executable source path drifted")
    if stat.S_IMODE(snapshot_dir.stat().st_mode) & 0o222:
        raise SystemExit("toolchain snapshot guard: private snapshot directory remains writable")

    return {
        "verified": True,
        "path": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "retained_rpc_manifest_sha256": doc["retained_rpc_manifest_sha256"],
        "source": source,
        "source_binary_path": private_row["source_path"],
        "binary_sha256": private_row["sha256"],
        "runtime_tree": doc["runtime_tree"],
        "files": {rel: {"sha256": row["sha256"], "size": row["size"]}
                  for rel, row in doc["files"].items()},
        "_paths": {
            "binary": str(private_binary),
            "launcher": str(resolved[doc["launcher_rel"]]),
            "client": str(resolved[doc["client_rel"]]),
        },
    }


def cleanup_snapshot_binary(manifest_path: Path) -> dict:
    """Remove only the exact verified executable sibling owned by a snapshot."""
    snapshot = verify_snapshot(manifest_path)
    private_binary = Path(snapshot["_paths"]["binary"])
    private_binary.unlink()
    return {
        "private_binary_removed": not private_binary.exists(),
        "private_binary_path": str(private_binary),
        "private_binary_sha256": snapshot["binary_sha256"],
    }


def _owned_snapshot_process(config: Path, expected_binary: Path) -> tuple[int, Path]:
    """PID/config ownership guard that accepts the verifier's suffixed name."""
    pidfile = config / "instance.pid"
    if not pidfile.is_file():
        raise SystemExit(f"isolated-instance guard: no launcher pidfile at {pidfile}")
    try:
        pid = int(pidfile.read_text().strip())
    except ValueError as exc:
        raise SystemExit(f"isolated-instance guard: invalid PID file {pidfile}") from exc
    proc = Path("/proc") / str(pid)
    exe = proc / "exe"
    if pid <= 1 or not proc.is_dir() or not exe.exists():
        raise SystemExit(f"isolated-instance guard: PID {pid} is not live")
    binary = Path(os.readlink(exe)).resolve()
    if binary != expected_binary.resolve():
        raise SystemExit(
            f"isolated-instance guard: PID {pid} runs {binary}, expected {expected_binary}")
    owns_config = False
    for fd in (proc / "fd").iterdir():
        try:
            Path(os.readlink(fd)).resolve().relative_to(config)
            owns_config = True
            break
        except (OSError, ValueError):
            continue
    if not owns_config:
        raise SystemExit(
            f"isolated-instance guard: PID {pid} has no open file under {config}")
    return pid, binary


def _stop_owned_snapshot_process(config: Path, pid: int,
                                 expected_binary: Path) -> dict:
    """Terminate one revalidated PID; never select by executable name."""
    def process_state() -> str | None:
        try:
            fields = (Path("/proc") / str(pid) / "stat").read_text().split()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            return None
        return fields[2] if len(fields) >= 3 else "?"

    def stopped() -> bool:
        # A zombie has exited and cannot own emulator state even if init has not
        # reaped its transient /proc entry yet.
        return process_state() in (None, "Z", "X")

    checked_pid, _ = _owned_snapshot_process(config, expected_binary)
    if checked_pid != pid:
        raise SystemExit(
            f"isolated-instance guard: pidfile changed from {pid} to {checked_pid}")
    os.kill(pid, signal.SIGTERM)
    for _ in range(100):
        if stopped():
            break
        time.sleep(0.1)
    forced = False
    if not stopped():
        # Revalidate immediately before the only forced kill path so PID reuse
        # cannot redirect cleanup to another process.
        checked_pid, _ = _owned_snapshot_process(config, expected_binary)
        if checked_pid != pid:
            raise SystemExit("isolated-instance guard: PID changed before SIGKILL")
        os.kill(pid, signal.SIGKILL)
        forced = True
        for _ in range(50):
            if stopped():
                break
            time.sleep(0.1)
    final_state = process_state()
    alive = not stopped()
    pidfile = config / "instance.pid"
    if not alive and pidfile.is_file() and pidfile.read_text().strip() == str(pid):
        pidfile.unlink()
    return {
        "owned_pid_stopped": not alive,
        "signal": "SIGKILL" if forced else "SIGTERM",
        "process_final_state": final_state,
    }


def finish_snapshot_run(args, *, generator: str, anchor: dict, timing: dict,
                        source_dependencies: tuple[str, ...]) -> dict:
    """Bank provenance and stop through the immutable private launcher."""
    snapshot = verify_snapshot(Path(args.toolchain_snapshot))
    paths = snapshot.pop("_paths")
    config = _under_tmp(Path(args.config_dir), "--config-dir")
    expected_binary = Path(paths["binary"]).resolve()
    pid, binary = _owned_snapshot_process(config, expected_binary)
    proc_exe = Path("/proc") / str(pid) / "exe"
    running_sha256 = sha256(proc_exe)
    if running_sha256 != snapshot["binary_sha256"]:
        raise SystemExit(
            f"toolchain snapshot guard: running inode hash {running_sha256} differs "
            f"from private binary {snapshot['binary_sha256']}")
    settings = config / "duckstation/settings.ini"
    settings_text = settings.read_text() if settings.is_file() else ""
    if f"Port={args.port}" not in settings_text:
        raise SystemExit("isolated-instance guard: requested port does not match config settings")

    dependencies = {
        rel: live_provenance._sha256(ROOT / rel) for rel in source_dependencies
    }
    before_stop = {
        "command": live_provenance._redacted_command(args.token),
        "generator_sha256": live_provenance._sha256(ROOT / generator),
        "provenance_helper_sha256": live_provenance._sha256(
            ROOT / "tools/live_session_provenance.py"),
        "source_dependencies": dependencies,
        "repository_head": live_provenance._git("rev-parse", "HEAD", cwd=ROOT),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "duckstation": {
            "revision": snapshot["source"]["revision"],
            "status": f"sha256:{snapshot['source']['status_sha256']}",
            "binary_path": str(expected_binary),
            "binary_sha256": running_sha256,
        },
        "toolchain_snapshot": snapshot,
        "debugger": {
            "config_dir": str(config),
            "port": args.port,
            "transport": "ws",
            "token_sha256": hashlib.sha256(args.token.encode()).hexdigest(),
            "recreated": args.instance_state == "recreated",
            "owned_pid": pid,
        },
        "anchor": anchor,
        "timing": timing,
    }
    cleanup = _stop_owned_snapshot_process(config, pid, expected_binary)
    if not cleanup["owned_pid_stopped"]:
        raise SystemExit(f"owned-PID cleanup failed: {cleanup}")
    cleanup.update(cleanup_snapshot_binary(Path(args.toolchain_snapshot)))
    if not cleanup["private_binary_removed"]:
        raise SystemExit(f"private binary cleanup failed: {cleanup}")
    before_stop["cleanup"] = cleanup
    return before_stop


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-root", type=Path,
                        default=Path.home() / "duckstation")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--snapshot-dir", type=Path)
    action.add_argument("--cleanup-manifest", type=Path,
                        help="remove the exact verified sibling after a failed run")
    parser.add_argument("--binary-rel", type=Path,
                        default=Path("build-release/bin/duckstation-qt"))
    args = parser.parse_args()
    if args.cleanup_manifest:
        print(json.dumps(cleanup_snapshot_binary(args.cleanup_manifest), indent=1))
        return 0
    manifest = prepare_snapshot(
        source_root=args.source_root,
        snapshot_dir=args.snapshot_dir,
        binary_rel=args.binary_rel,
    )
    snapshot = verify_snapshot(manifest)
    paths = snapshot.pop("_paths")
    print(json.dumps({"manifest": str(manifest), **paths,
                      "binary_sha256": snapshot["binary_sha256"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
