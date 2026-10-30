#!/usr/bin/env python3
"""Shared isolation/provenance closure for Phase-3 live generators.

The helper refuses a non-/tmp config, verifies the launcher's PID really owns an
open file under that config, records fork/binary identity without the token, and
stops only that launcher-owned PID when the generator is finished.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUCK = Path.home() / "duckstation"
FORK_LAUNCHER = DUCK / "scripts/debugger-client/launch_debugger_instance.sh"
LAUNCHER = ROOT / "tools/launch_phase3_debugger.py"
FIXTURE_SET = ROOT / "analysis/phase0_2_external_fixture_set.json"
RPC_MANIFEST = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
STRICT_PRISTINE_MEDIA_CLASS = "pristine"

# These fields identify a particular replay process, not its semantic result.
# They are retained in the committed artifact for auditability, but a replay with
# identical hashes/observations must not dirty a clean checkout merely because it
# used a fresh port, token, PID, timestamp, or absolute isolation path.
VOLATILE_EVIDENCE_KEYS = {
    "generated", "command", "repository_head", "recorded_utc", "config_dir",
    "port", "token_sha256", "owned_pid", "launcher_output", "game_path",
    "path", "media_path", "mounted_path", "isolated_card_path", "seed_path",
    # emulator.getStateInfo reports the save file's filesystem mtime here, not
    # a timestamp stored in the emulated state.  The clean-checkout provisioner
    # deliberately verifies/copies bytes without treating host metadata as part
    # of a fixture pin, so this value changes for a byte-identical provisioned
    # save.  The fixture SHA-256, size, state format/version, embedded media and
    # observations remain semantic and are retained below.
    "timestamp",
    # Cleanup may observe a dead zombie for a few milliseconds before init
    # reaps it.  Both states prove the owned process stopped; retain the exact
    # observation without making replay freshness depend on host scheduling.
    "process_final_state", "cleanup_wait_ms",
}

# These are volatile only at their exact snapshot-run locations.  A blanket
# key-name exclusion would be unsafe: for example, runtime_tree.manifest_sha256
# is a decisive support-tree identity and must remain semantic.
VOLATILE_EVIDENCE_PATHS = {
    ("run_provenance", "duckstation", "binary_path"),
    ("run_provenance", "toolchain_snapshot", "manifest_sha256"),
    ("run_provenance", "cleanup", "private_binary_path"),
}


def add_required_live_args(parser, *, optional: bool = False) -> None:
    kwargs = {} if optional else {"required": True}
    parser.add_argument("--port", type=int, **kwargs)
    parser.add_argument("--token", **kwargs)
    parser.add_argument("--config-dir", type=Path, **kwargs)
    parser.add_argument("--instance-state", choices=("recreated", "reused"), **kwargs)


def require_optional_live_args(args) -> None:
    missing = [name for name in ("port", "token", "config_dir", "instance_state")
               if getattr(args, name, None) in (None, "")]
    if missing:
        raise SystemExit(f"live mode requires explicit arguments: {missing}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _fixture_entries(fixture_set: Path = FIXTURE_SET) -> dict[str, dict]:
    try:
        doc = json.loads(fixture_set.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"save-state origin guard: cannot read fixture set {fixture_set}: {exc}") from exc
    entries = doc.get("entries")
    if not isinstance(entries, dict):
        raise SystemExit(
            f"save-state origin guard: fixture set has no entries mapping: {fixture_set}")
    return entries


def verify_declared_save_fixture(
        path: Path, *, root: Path = ROOT,
        fixture_entries: dict[str, dict] | None = None,
        allowed_media_classes: set[str] | None = None) -> dict:
    """Verify the central pin and origin class for one external save.

    A save-state serial is not an origin proof: ALLMODS retains ``SCUS-94288``.
    This guard therefore joins the exact repo-relative fixture against the central
    preservation manifest and verifies its bytes before any caller may load it.
    ``allowed_media_classes=None`` validates the declaration without accepting it;
    anchor selectors use that mode to retain explicit rejected rows.
    """
    root = Path(root).resolve()
    path = Path(path).resolve()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise SystemExit(
            f"save-state origin guard: fixture is outside the checkout: {path}") from exc
    entries = fixture_entries if fixture_entries is not None else _fixture_entries()
    entry = entries.get(rel)
    if not isinstance(entry, dict):
        raise SystemExit(
            f"save-state origin guard: {rel} is not centrally declared in {FIXTURE_SET}")
    if not path.is_file():
        raise SystemExit(f"save-state origin guard: declared fixture is absent: {path}")
    actual_size = path.stat().st_size
    expected_size = entry.get("size")
    if actual_size != expected_size:
        raise SystemExit(
            f"save-state origin guard: size mismatch for {rel}: "
            f"actual={actual_size} expected={expected_size}")
    actual_sha256 = _sha256(path)
    expected_sha256 = entry.get("sha256")
    if actual_sha256 != expected_sha256:
        raise SystemExit(
            f"save-state origin guard: SHA-256 mismatch for {rel}: "
            f"actual={actual_sha256} expected={expected_sha256}")
    media_class = entry.get("media_class")
    if allowed_media_classes is not None and media_class not in allowed_media_classes:
        raise SystemExit(
            f"save-state origin guard: {rel} has media_class={media_class!r}; "
            f"required one of {sorted(allowed_media_classes)}")
    return {
        "path": rel,
        "sha256": actual_sha256,
        "size": actual_size,
        "media_class": media_class,
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
    }


def select_pristine_save_anchors(
        baseline: dict, *, root: Path = ROOT,
        fixture_entries: dict[str, dict] | None = None) -> tuple[list[tuple[str, str]], dict]:
    """Select strict-pristine save anchors and retain every refusal explicitly."""
    accepted: list[tuple[str, str]] = []
    accepted_rows: list[dict] = []
    rejected_rows: list[dict] = []
    seen: set[str] = set()
    for label, row in (baseline.get("stages") or {}).items():
        save = row.get("save")
        if not save:
            continue
        if save in seen:
            raise SystemExit(f"save-state origin guard: duplicate baseline save: {save}")
        seen.add(save)
        declaration = verify_declared_save_fixture(
            Path(root) / save, root=root, fixture_entries=fixture_entries,
            allowed_media_classes=None)
        selected = declaration["media_class"] == STRICT_PRISTINE_MEDIA_CLASS
        result = {"label": label, "save": save, **declaration}
        if selected:
            accepted.append((label, save))
            accepted_rows.append(result)
        else:
            rejected_rows.append({
                **result,
                "reason": "not strict pristine; never load as original-game authority",
            })
    if not accepted:
        raise SystemExit("save-state origin guard: baseline has no strict-pristine anchors")
    selection = {
        "source": "analysis/phase2_stage_baseline.json",
        "required_media_class": STRICT_PRISTINE_MEDIA_CLASS,
        "anchors_requested": len(accepted_rows) + len(rejected_rows),
        "anchors_accepted": len(accepted_rows),
        "anchors_rejected": len(rejected_rows),
        "accepted": accepted_rows,
        "rejected": rejected_rows,
    }
    return accepted, selection


def retained_pristine_save_gaps(
        doc: dict, *, fixture_entries: dict[str, dict] | None = None,
        require_selection: bool = False) -> list[str]:
    """Recompute retained save-origin predicates from low-level artifact rows.

    This deliberately ignores any artifact-level ``passes`` or ``pristine``
    boolean. It joins each save pin against the central fixture set, checks every
    pre-load inspection's embedded media name against the pristine retail pins,
    and (for aggregate sweeps) proves the selection ledger is complete.
    """
    gaps: list[str] = []
    run = doc.get("run_provenance") or {}
    anchor = run.get("anchor") or {}
    saves = list(anchor.get("saves") or [])
    if anchor.get("save"):
        saves.append(anchor["save"])
    if not saves:
        return gaps
    entries = fixture_entries if fixture_entries is not None else _fixture_entries()
    pins = {
        **(doc.get("fixture_sha256") or {}),
        **(anchor.get("fixture_sha256") or {}),
    }
    try:
        from build_identity import load_baselines
    except ModuleNotFoundError:
        from tools.build_identity import load_baselines
    pristine_names = set((load_baselines().get("pristine_media") or {}))
    inspections = anchor.get("state_inspections") or []
    by_fixture = {}
    for row in inspections:
        declaration = row.get("fixture_declaration") or {}
        rel = declaration.get("path")
        if not rel and row.get("path"):
            rel = Path(row["path"]).name
        if rel:
            by_fixture[rel] = row
            by_fixture[Path(rel).name] = row

    for save in saves:
        entry = entries.get(save)
        if not isinstance(entry, dict):
            gaps.append(f"{save}: absent from central fixture set")
            continue
        if entry.get("media_class") != STRICT_PRISTINE_MEDIA_CLASS:
            gaps.append(
                f"{save}: media_class={entry.get('media_class')!r}, not strict pristine")
        if pins.get(save) != entry.get("sha256"):
            gaps.append(
                f"{save}: retained SHA-256 does not match the central fixture pin")
        inspection = by_fixture.get(save) or by_fixture.get(Path(save).name)
        if not inspection:
            gaps.append(f"{save}: no matching pre-load state inspection")
            continue
        if inspection.get("serial") != "SCUS-94288":
            gaps.append(f"{save}: inspected serial is not SCUS-94288")
        media_path = inspection.get("media_path")
        if not media_path or Path(media_path).name not in pristine_names:
            gaps.append(
                f"{save}: embedded media path is not a pinned pristine-media name: "
                f"{media_path!r}")
        declaration = inspection.get("fixture_declaration")
        if declaration:
            if declaration.get("media_class") != STRICT_PRISTINE_MEDIA_CLASS:
                gaps.append(f"{save}: inspection declaration is not strict pristine")
            if declaration.get("sha256") != entry.get("sha256"):
                gaps.append(f"{save}: inspection declaration hash differs from central pin")
        origin = inspection.get("state_media_hash_verification")
        if origin is not None and origin.get("pristine_verified") is not True:
            gaps.append(f"{save}: embedded media hash verification did not pass")

    if len(inspections) != len(saves):
        gaps.append(
            f"state inspection count {len(inspections)} != save count {len(saves)}")
    if doc.get("anchors_used") is not None and doc.get("anchors_used") != len(saves):
        gaps.append(
            f"anchors_used={doc.get('anchors_used')} != retained save count {len(saves)}")

    selection = doc.get("anchor_selection") or anchor.get("selection")
    if require_selection and not isinstance(selection, dict):
        gaps.append("strict-pristine aggregate has no anchor-selection ledger")
    if isinstance(selection, dict):
        accepted = selection.get("accepted") or []
        rejected = selection.get("rejected") or []
        accepted_saves = [row.get("save") for row in accepted]
        if accepted_saves != saves:
            gaps.append("anchor-selection accepted saves differ from loaded saves")
        if selection.get("anchors_requested") != len(accepted) + len(rejected):
            gaps.append("anchor-selection requested count is inconsistent")
        if selection.get("anchors_accepted") != len(accepted):
            gaps.append("anchor-selection accepted count is inconsistent")
        if selection.get("anchors_rejected") != len(rejected):
            gaps.append("anchor-selection rejected count is inconsistent")
        for row in accepted:
            entry = entries.get(row.get("save")) or {}
            if entry.get("media_class") != STRICT_PRISTINE_MEDIA_CLASS:
                gaps.append(f"selection accepted non-pristine save {row.get('save')}")
        for row in rejected:
            entry = entries.get(row.get("save")) or {}
            if entry.get("media_class") == STRICT_PRISTINE_MEDIA_CLASS:
                gaps.append(f"selection rejected strict-pristine save {row.get('save')}")
    return gaps


@lru_cache(maxsize=8)
def _verify_pristine_state_media(path: str) -> dict:
    try:
        from build_identity import verify_pristine_media_path
    except ModuleNotFoundError:
        from tools.build_identity import verify_pristine_media_path
    return verify_pristine_media_path(path)


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def _redacted_command(token: str) -> str:
    argv = list(sys.argv)
    for i, item in enumerate(argv[:-1]):
        if item == "--token":
            argv[i + 1] = "<redacted-token>"
    return shlex.join([sys.executable, *argv])


def _rpc_manifest_identity(binary: Path) -> dict:
    """Bind a live run to the exact current external source and binary.

    A Git revision plus ``status --short`` path list is not enough for a dirty
    fork: file contents can change while the same paths remain dirty.  Recompute
    every source/support hash retained by the Phase-3 RPC manifest and require
    the selected executable to be one of its exact binary rows.  The separate
    manifest generator still validates method extraction; this join prevents a
    retained live artifact from silently surviving a current-toolchain change.
    """
    try:
        retained = json.loads(RPC_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"live toolchain guard: cannot read {RPC_MANIFEST}: {exc}") from exc

    source = retained.get("source") or {}
    revision = _git("rev-parse", "HEAD", cwd=DUCK)
    status_raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1"], cwd=DUCK)
    status_sha256 = hashlib.sha256(status_raw).hexdigest()
    if revision != source.get("revision"):
        raise SystemExit(
            "live toolchain guard: DuckStation revision differs from retained RPC manifest")
    if status_sha256 != source.get("status_sha256"):
        raise SystemExit(
            "live toolchain guard: DuckStation dirty status differs from retained RPC manifest")

    for rel, row in (source.get("files") or {}).items():
        path = DUCK / rel
        if (not path.is_file() or path.stat().st_size != row.get("size")
                or _sha256(path) != row.get("sha256")):
            raise SystemExit(
                f"live toolchain guard: retained source/support identity drifted: {rel}")

    binary = Path(binary).resolve()
    selected_rel = None
    selected_row = None
    for rel, row in (retained.get("binaries") or {}).items():
        if binary == (DUCK / rel).resolve():
            selected_rel, selected_row = rel, row
            break
    if selected_row is None:
        raise SystemExit(
            f"live toolchain guard: running binary is not declared by the RPC manifest: {binary}")
    if (binary.stat().st_size != selected_row.get("size")
            or _sha256(binary) != selected_row.get("sha256")):
        raise SystemExit(
            f"live toolchain guard: running binary drifted from RPC manifest: {selected_rel}")

    semantic = dict(retained)
    semantic.pop("generated", None)
    semantic_sha256 = hashlib.sha256(json.dumps(
        semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "path": RPC_MANIFEST.relative_to(ROOT).as_posix(),
        "semantic_sha256": semantic_sha256,
        "source": {
            "revision": source["revision"],
            "status_sha256": source["status_sha256"],
            "dispatcher_sha256": source["dispatcher_sha256"],
            "method_count": retained["methods"]["counts"]["current"],
        },
        "binary": {
            "path": f"~/duckstation/{selected_rel}",
            "sha256": selected_row["sha256"],
            "size": selected_row["size"],
        },
    }


def _owned_process(config: Path) -> tuple[int, Path]:
    pidfile = config / "instance.pid"
    if not pidfile.is_file():
        raise SystemExit(f"isolated-instance guard: no launcher pidfile at {pidfile}")
    try:
        pid = int(pidfile.read_text().strip())
    except ValueError as exc:
        raise SystemExit(f"isolated-instance guard: invalid PID file {pidfile}") from exc
    proc = Path("/proc") / str(pid)
    exe = proc / "exe"
    if not proc.is_dir() or not exe.exists():
        raise SystemExit(f"isolated-instance guard: PID {pid} is not live")
    binary = Path(os.readlink(exe)).resolve()
    if binary.name != "duckstation-qt":
        raise SystemExit(f"isolated-instance guard: PID {pid} is {binary}, not duckstation-qt")
    owns_config = False
    for fd in (proc / "fd").iterdir():
        try:
            target = Path(os.readlink(fd))
            target.resolve().relative_to(config)
            owns_config = True
            break
        except (OSError, ValueError):
            continue
    if not owns_config:
        raise SystemExit(
            f"isolated-instance guard: PID {pid} has no open file under {config}")
    return pid, binary


def verified_media_identity(client, status: dict) -> dict:
    """Hash the exact mounted media and reject a swap during verification."""
    before = client.call("emulator.getMediaInfo", {})
    if not before.get("has_media") or not before.get("path"):
        raise SystemExit(f"mounted-media guard: no media is mounted: {before}")
    if status.get("game_serial") != "SCUS-94288" or \
            before.get("game_serial") != status.get("game_serial"):
        raise SystemExit(
            f"mounted-media guard: debugger/media serial mismatch: {status} / {before}")
    try:
        from build_identity import verify_pristine_media_path
    except ModuleNotFoundError:
        from tools.build_identity import verify_pristine_media_path
    verification = verify_pristine_media_path(before["path"])
    after = client.call("emulator.getMediaInfo", {})
    stable = ("has_media", "path", "game_serial", "subimage_count", "subimage_index")
    if any(before.get(key) != after.get(key) for key in stable):
        raise SystemExit(
            f"mounted-media guard: media changed while hashing: {before} -> {after}")
    return {
        "game_serial": status.get("game_serial"),
        "game_title": status.get("game_title"),
        "game_path": before["path"],
        "rpc_before_hash": before,
        "rpc_after_hash": after,
        "hash_verification": verification,
    }


def inspect_state_before_load(client, path: Path, media_identity: dict) -> dict:
    """Inspect and validate a save-state before any mutating load.

    ``loadState`` validates the disc too, but Phase 3 banks the non-mutating
    ``getStateInfo`` result so a corrupt, incompatible, or foreign-media anchor
    cannot become an invisible prerequisite.  Callers retain the returned row in
    ``run_provenance.anchor.state_inspections``.
    """
    path = Path(path).resolve()
    if not path.is_absolute():  # resolve() is defensive; keep the contract clear.
        raise SystemExit(f"save-state inspection requires an absolute path: {path}")
    info = client.call("emulator.getStateInfo", {"path": str(path)})
    if info.get("exists") is not True or info.get("valid") is not True:
        raise SystemExit(f"save-state inspection failed for {path}: {info}")
    expected_serial = media_identity.get("game_serial")
    state_serial = info.get("serial")
    if expected_serial != "SCUS-94288" or state_serial != expected_serial:
        raise SystemExit(
            f"save-state/media mismatch before load: state={info} "
            f"mounted_serial={expected_serial!r}")
    declaration = verify_declared_save_fixture(
        path, allowed_media_classes={STRICT_PRISTINE_MEDIA_CLASS})
    state_media_path = info.get("media_path")
    if not state_media_path:
        raise SystemExit(
            f"save-state origin guard: getStateInfo returned no media_path for {path}")
    mounted_path = media_identity.get("game_path")
    if mounted_path and Path(state_media_path).resolve() == Path(mounted_path).resolve():
        origin_verification = media_identity.get("hash_verification") or {}
    else:
        origin_verification = _verify_pristine_state_media(str(Path(state_media_path).resolve()))
    if origin_verification.get("pristine_verified") is not True:
        raise SystemExit(
            f"save-state origin guard: embedded media is not pristine: "
            f"{state_media_path} -> {origin_verification}")
    return {
        "path": str(path),
        "exists": True,
        "valid": True,
        "serial": state_serial,
        "title": info.get("title"),
        "media_path": info.get("media_path"),
        "media_subimage_index": info.get("media_subimage_index"),
        "version": info.get("version"),
        "file_size": info.get("file_size"),
        "timestamp": info.get("timestamp"),
        "has_screenshot": info.get("has_screenshot"),
        "fixture_declaration": declaration,
        "state_media_hash_verification": origin_verification,
    }


def _semantic_evidence(value, trail=()):
    """Drop only per-run identity while retaining hashes and observations."""
    if isinstance(value, dict):
        return {
            key: _semantic_evidence(item, (*trail, key))
            for key, item in value.items()
            if (key not in VOLATILE_EVIDENCE_KEYS
                and (*trail, key) not in VOLATILE_EVIDENCE_PATHS)
        }
    if isinstance(value, list):
        return [_semantic_evidence(item, trail) for item in value]
    return value


def write_live_evidence(path: Path, doc: dict) -> bool:
    """Write a live artifact only when its semantic evidence changed.

    The complete fresh-run provenance remains available in the file whenever a
    substantive result, generator hash, fixture inspection, fork revision, or
    binary hash changes.  A semantically identical replay returns ``False`` and
    deliberately preserves the retained bytes, making clean-checkout validation
    independent of fresh ports/tokens/PIDs and absolute worktree paths.
    """
    path = Path(path)
    if path.exists():
        try:
            retained = json.loads(path.read_text())
        except json.JSONDecodeError:
            retained = None
        if retained is not None and _semantic_evidence(retained) == _semantic_evidence(doc):
            print(f"[evidence] semantic replay matched {path}; retained bytes unchanged")
            return False
    path.write_text(json.dumps(doc, indent=1) + "\n")
    return True


def finish_run(args, *, generator: str, anchor: dict, timing: dict) -> dict:
    config = Path(args.config_dir)
    if not config.is_absolute() or not str(config).startswith("/tmp/"):
        raise SystemExit("isolated-instance guard: --config-dir must be an absolute /tmp path")
    config = config.resolve()
    pid, binary = _owned_process(config)
    settings = config / "duckstation/settings.ini"
    settings_text = settings.read_text() if settings.is_file() else ""
    if f"Port={args.port}" not in settings_text:
        raise SystemExit("isolated-instance guard: requested port does not match config settings")

    fork_status = _git("status", "--short", cwd=DUCK)
    before_stop = {
        "command": _redacted_command(args.token),
        "generator_sha256": _sha256(ROOT / generator),
        "provenance_helper_sha256": _sha256(Path(__file__)),
        "launcher_helper_sha256": _sha256(LAUNCHER),
        "repository_head": _git("rev-parse", "HEAD", cwd=ROOT),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "duckstation": {
            "revision": _git("rev-parse", "HEAD", cwd=DUCK),
            "status": fork_status if fork_status else "clean",
            "binary_path": str(binary),
            "binary_sha256": _sha256(binary),
        },
        "rpc_manifest": _rpc_manifest_identity(binary),
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
    stopped = subprocess.run(
        [sys.executable, str(LAUNCHER), "stop", "--config-dir", str(config),
         "--binary", str(binary), "--fork-launcher", str(FORK_LAUNCHER)],
        capture_output=True, text=True,
    )
    try:
        from launch_phase3_debugger import process_state, process_stopped
    except ModuleNotFoundError:
        from tools.launch_phase3_debugger import process_state, process_stopped
    final_state = process_state(pid)
    cleanup = {
        "owned_pid_stopped": stopped.returncode == 0 and process_stopped(pid),
        "launcher_returncode": stopped.returncode,
        "launcher_output": (stopped.stdout + stopped.stderr).strip(),
        "process_final_state": final_state,
    }
    if not cleanup["owned_pid_stopped"]:
        raise SystemExit(f"owned-PID cleanup failed: {cleanup}")
    before_stop["cleanup"] = cleanup
    return before_stop
