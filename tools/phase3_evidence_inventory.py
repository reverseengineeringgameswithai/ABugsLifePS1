#!/usr/bin/env python3
"""Inventory every Phase-3 generator, artifact, guard, note, and fixture edge.

The acceptance contract requires a complete regeneration inventory before any
closure summary.  This tool keeps the declaration surface next to the code and
then discovers omissions from the filesystem.  Live tools are recorded as live
even when their retained artifact happens to exist; retained JSON does not turn a
runtime experiment into a static generator.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import retained_pristine_save_gaps
    import phase3_duckstation_rpc_manifest as rpc_manifest
except ModuleNotFoundError:
    from tools.live_session_provenance import retained_pristine_save_gaps
    from tools import phase3_duckstation_rpc_manifest as rpc_manifest

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROVENANCE_HELPER = "tools/live_session_provenance.py"
LIVE_LAUNCHER_HELPER = "tools/launch_phase3_debugger.py"
RPC_MANIFEST_PATH = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
CURRENT_RPC_MANIFEST = json.loads(RPC_MANIFEST_PATH.read_text())


def mode(command: str, classification: str) -> dict:
    return {"command": command, "classification": classification}


LIVE_ARGS = "--port <port> --token <token> --config-dir </tmp/config> --instance-state <recreated|reused>"
PRISTINE_CUE = "<operator-root>/Disney-Pixar A Bug's Life (v1.0).cue"
PRISTINE_MEDIA = {
    "pin_source": "tools/build_baselines.json",
    "cue": {
        "path": PRISTINE_CUE,
        "sha1": "25adb139e50ba28c2d9c1ecab4528e9cf004b1d5",
    },
    "tracks": [{
        "path": "<operator-root>/Disney-Pixar A Bug's Life (v1.0).bin",
        "sha1": "0bc1a29748d4bd608d076495d085e825574880d1",
    }],
}
BINARY_PROFILES = {
    "normal": {
        "path": "~/duckstation/build/bin/duckstation-qt",
        "sha256": CURRENT_RPC_MANIFEST[
            "binaries"]["build/bin/duckstation-qt"]["sha256"],
    },
    "release": {
        "path": "~/duckstation/build-release/bin/duckstation-qt",
        "sha256": CURRENT_RPC_MANIFEST[
            "binaries"]["build-release/bin/duckstation-qt"]["sha256"],
    },
    # The long transition replay uses the same current release identity through
    # an owned immutable sibling snapshot. The sibling prevents an in-place
    # canonical rebuild from changing the running inode during the 16-stage run.
    "release_current": {
        "path": "~/duckstation/build-release/bin/duckstation-qt",
        "sha256": CURRENT_RPC_MANIFEST[
            "binaries"]["build-release/bin/duckstation-qt"]["sha256"],
    },
}


def live_mode(command: str, *, binary: str = "release",
              settings_profile: str = "isolated-defaults-v1",
              immutable_snapshot: bool = False) -> dict:
    """Declare the complete environment needed before a live generator runs."""
    selected = BINARY_PROFILES[binary]
    if immutable_snapshot:
        snapshot = "</tmp/config>/toolchain"
        private_binary = "<owned-sibling-path-from-snapshot-helper>"
        private_launcher = (
            f"{snapshot}/scripts/debugger-client/launch_debugger_instance.sh")
        private_client = f"{snapshot}/scripts/debugger-client/duckstation_debug_client.py"
        prepare = (
            "python3 tools/live_toolchain_snapshot.py "
            f"--snapshot-dir {snapshot} "
            "--binary-rel build-release/bin/duckstation-qt"
        )
        launcher = (
            f"{prepare}\n"
            "tools/launch_repro_playback.sh --config-dir </tmp/config> "
            "--port <port> --token <token> "
            f"--binary {private_binary} --fork-launcher {private_launcher} "
            f"--client {private_client} --disc \"{PRISTINE_CUE}\" "
            "--card-seed ~/.cache/abl/abl_card_seed.mcd --bootstrap-fastboot"
        )
        settings_binary = private_binary
    elif settings_profile == "movie-replay-v1":
        launcher = (
            "tools/launch_repro_playback.sh --config-dir </tmp/config> "
            "--port <port> --token <token> "
            f"--binary {selected['path']} --disc \"{PRISTINE_CUE}\" "
            "--card-seed ~/.cache/abl/abl_card_seed.mcd"
        )
        settings_binary = selected["path"]
    else:
        launcher = (
            "python3 tools/launch_phase3_debugger.py start "
            "--config-dir </tmp/config> --port <port> --token <token> "
            f"--binary {selected['path']} "
            "--fork-launcher ~/duckstation/scripts/debugger-client/launch_debugger_instance.sh "
            "--client ~/duckstation/scripts/debugger-client/duckstation_debug_client.py "
            f"--disc \"{PRISTINE_CUE}\""
        )
        settings_binary = selected["path"]
    settings = (
        "python3 tools/verify_live_session_environment.py "
        "--config-dir </tmp/config> --port <port> "
        f"--binary {settings_binary} --binary-sha256 {selected['sha256']} "
        f"--profile {settings_profile}"
    )
    return {
        "command": command,
        "classification": "live",
        "reproduction": {
            "launcher_command": launcher,
            "settings_command": settings,
            "settings_profile": settings_profile,
            "immutable_snapshot_required": immutable_snapshot,
            "binary": selected,
            "media": PRISTINE_MEDIA,
        },
    }


GENERATOR_SPECS = {
    "tools/phase3_asset_provenance.py": {
        "modes": [mode("python3 tools/phase3_asset_provenance.py", "local_media")],
        "outputs": ["analysis/phase3_asset_provenance.json"],
    },
    "tools/phase3_camera_record.py": {
        "modes": [live_mode(f"python3 tools/phase3_camera_record.py {LIVE_ARGS}")],
        "outputs": ["analysis/phase3_camera_record.json"],
    },
    "tools/phase3_call_graph.py": {
        "modes": [mode("python3 tools/phase3_call_graph.py", "static")],
        "outputs": ["analysis/phase3_call_graph.json"],
    },
    "tools/phase3_cfg_liveness.py": {
        "modes": [mode("library consumed by tools/phase3_hook_contract.py", "static")],
        "outputs": [],
    },
    "tools/phase3_coverage_matrix.py": {
        "modes": [mode("python3 tools/phase3_coverage_matrix.py", "static")],
        "outputs": ["analysis/phase3_coverage_matrix.json"],
    },
    "tools/phase3_contradictions.py": {
        "modes": [mode("python3 tools/phase3_contradictions.py", "static")],
        "outputs": ["analysis/phase3_contradictions.json"],
    },
    "tools/phase3_dispatch_map.py": {
        "modes": [mode("python3 tools/phase3_dispatch_map.py", "local_media")],
        "outputs": ["analysis/phase3_dispatch_map.json"],
    },
    "tools/phase3_duckstation_rpc_manifest.py": {
        "modes": [mode(
            "python3 tools/phase3_duckstation_rpc_manifest.py --check",
            "local_media",
        )],
        "outputs": [
            "analysis/phase3_duckstation_rpc_manifest.json",
            "tools/duckstation_rpc_method_manifest.md",
        ],
    },
    "tools/phase3_evidence_inventory.py": {
        "modes": [mode("python3 tools/phase3_evidence_inventory.py", "static")],
        "outputs": ["analysis/phase3_evidence_inventory.json"],
    },
    "tools/phase3_fn_ptr_fields.py": {
        "modes": [live_mode(f"python3 tools/phase3_fn_ptr_fields.py {LIVE_ARGS}",
                            binary="normal")],
        "outputs": ["analysis/phase3_fn_ptr_fields.json"],
    },
    "tools/phase3_gate_audit.py": {
        "modes": [mode("python3 tools/phase3_gate_audit.py", "static")],
        "outputs": ["analysis/phase3_gate_audit.json"],
    },
    "tools/phase3_hook_contract.py": {
        "modes": [mode("python3 tools/phase3_hook_contract.py", "local_media")],
        "outputs": ["analysis/phase3_hook_contracts.json"],
    },
    "tools/phase3_jalr_callbacks.py": {
        "modes": [
            mode("python3 tools/phase3_jalr_callbacks.py --no-live", "local_media"),
            live_mode(f"python3 tools/phase3_jalr_callbacks.py {LIVE_ARGS}"),
        ],
        "outputs": ["analysis/phase3_jalr_callbacks.json"],
    },
    "tools/phase3_jr_tables.py": {
        "modes": [mode("python3 tools/phase3_jr_tables.py", "local_media")],
        "outputs": ["analysis/phase3_jr_tables.json"],
    },
    "tools/phase3_native_domains.py": {
        "modes": [mode("python3 tools/phase3_native_domains.py", "static")],
        "outputs": ["analysis/phase3_native_domains.json"],
    },
    "tools/phase3_knowledge_audit.py": {
        "modes": [mode("python3 tools/phase3_knowledge_audit.py", "static")],
        "outputs": ["analysis/phase3_knowledge_audit.json"],
    },
    "tools/phase3_overlay_map.py": {
        "modes": [mode("python3 tools/phase3_overlay_map.py", "static")],
        "outputs": ["analysis/phase3_overlay_map.json"],
    },
    "tools/phase3_ownership_graph.py": {
        "modes": [mode("python3 tools/phase3_ownership_graph.py", "static")],
        "outputs": ["analysis/phase3_ownership_graph.json"],
    },
    "tools/phase3_record_types.py": {
        "modes": [
            mode("python3 tools/phase3_record_types.py", "static"),
            live_mode(f"python3 tools/phase3_record_types.py --probe {LIVE_ARGS}",
                      binary="normal"),
        ],
        "outputs": ["analysis/phase3_record_types.json", "analysis/phase3_record_probe.json"],
        "live_outputs": ["analysis/phase3_record_probe.json"],
    },
    "tools/phase3_render_descriptors.py": {
        "modes": [live_mode(f"python3 tools/phase3_render_descriptors.py {LIVE_ARGS}",
                            binary="normal")],
        "outputs": ["analysis/phase3_render_descriptors.json"],
    },
    "tools/phase3_scene_asset_graph.py": {
        "modes": [mode("python3 tools/phase3_scene_asset_graph.py", "local_media")],
        "outputs": ["analysis/phase3_scene_asset_graph.json"],
    },
    "tools/phase3_semantic_lifetime.py": {
        "modes": [live_mode(f"python3 tools/phase3_semantic_lifetime.py {LIVE_ARGS} --stage stage01_anthill")],
        "outputs": ["analysis/phase3_semantic_lifetime.json"],
    },
    "tools/phase3_sfx_interface.py": {
        "modes": [live_mode(f"python3 tools/phase3_sfx_interface.py {LIVE_ARGS} --lo -24 --hi 48")],
        "outputs": ["analysis/phase3_sfx_interface.json"],
    },
    "tools/phase3_spin_functional.py": {
        "modes": [live_mode(f"python3 tools/phase3_spin_functional.py {LIVE_ARGS}")],
        "outputs": ["analysis/phase3_spin_functional.json"],
    },
    "tools/phase3_thud_trace.py": {
        "modes": [live_mode(f"python3 tools/phase3_thud_trace.py {LIVE_ARGS}")],
        "outputs": ["analysis/phase3_thud.json"],
    },
    "tools/phase3_training_anchor_fixture.py": {
        "modes": [live_mode(f"python3 tools/phase3_training_anchor_fixture.py --output "
                            f"phase3_pristine_training_gameplay_i5.sav {LIVE_ARGS}",
                            binary="normal")],
        "outputs": ["analysis/phase3_training_anchor_fixture.json"],
    },
    "tools/phase3_transition_reset.py": {
        "modes": [live_mode(
            f"python3 tools/phase3_transition_reset.py --all {LIVE_ARGS} "
            "--toolchain-snapshot </tmp/config>/toolchain/snapshot_manifest.json "
            "--card-seed ~/.cache/abl/abl_card_seed.mcd",
            binary="release_current", settings_profile="movie-replay-v1",
            immutable_snapshot=True)],
        "outputs": ["analysis/phase3_transition_reset.json"],
        "extra_dependencies": [
            "tools/live_toolchain_snapshot.py",
            "tools/launch_repro_playback.sh",
        ],
    },
    "tools/phase3_unknown_fields.py": {
        "modes": [live_mode(f"python3 tools/phase3_unknown_fields.py {LIVE_ARGS}")],
        "outputs": ["analysis/phase3_unknown_fields.json"],
    },
    "tools/phase3_xrefs.py": {
        "modes": [mode("python3 tools/phase3_xrefs.py", "local_media")],
        "outputs": ["analysis/phase3_xrefs.json"],
    },
}

INVENTORY_OUTPUT = "analysis/phase3_evidence_inventory.json"
NON_HASHED_OUTPUTS = {
    INVENTORY_OUTPUT,
    # The contradiction ledger consumes this inventory and records its hash.
    # Hashing the ledger here would create the reciprocal artifact cycle
    # inventory -> contradictions -> inventory, for which no byte-stable pair
    # can exist. Its full semantic document is independently recomputed by
    # phase3_contradictions.py/tests and consumed by the coverage/gate audits.
    "analysis/phase3_contradictions.json",
    # The gate consumes this inventory and records its freshness. Hashing the
    # gate output here would create a two-artifact cycle with no stable fixed
    # point. Its semantic freshness is recomputed by phase3_gate_audit.py/tests.
    "analysis/phase3_gate_audit.json",
}
SELF_REGENERATING_AUDIT_OUTPUTS = {
    INVENTORY_OUTPUT,
    "analysis/phase3_gate_audit.json",
}
STRICT_PRISTINE_AGGREGATES = {
    "analysis/phase3_record_probe.json",
    "analysis/phase3_render_descriptors.json",
    "analysis/phase3_fn_ptr_fields.json",
}

PATH_LITERAL = re.compile(
    r"(?:analysis|config|mod|tools|tests|ObsidianVault|REBUILD|build|movies)/"
    r"[A-Za-z0-9_ ./,'()+-]+\.(?:json|ya?ml|csv|sym|md|sav|movie)", re.IGNORECASE
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rpc_manifest_semantic_sha256(doc: dict = CURRENT_RPC_MANIFEST) -> str:
    semantic = dict(doc)
    semantic.pop("generated", None)
    return hashlib.sha256(json.dumps(
        semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def tracked_input_mutations() -> list[str]:
    """Return tracked changes that make a closure verdict non-durable.

    The inventory and gate outputs are excluded because each audit necessarily
    rewrites its own verdict while falsification tests are running.  They retain
    independent semantic-freshness comparisons.  Every other tracked path is an
    upstream closure input and must match HEAD before the inventory may report
    closure-ready.
    """
    proc = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", "-z",
         "HEAD", "--"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    changed = proc.stdout.decode(errors="surrogateescape").split("\0")
    return sorted(
        rel for rel in changed
        if rel and rel not in SELF_REGENERATING_AUDIT_OUTPUTS
    )


def current_provenance_helper_sha256() -> str:
    """Hash the shared live helper every retained live generator imports.

    A generator can remain byte-identical while this helper gains a stronger
    media/provenance guard. The retained artifact is stale in that case and
    must be replayed; checking only ``generator_sha256`` misses that dependency.
    """
    return sha256(ROOT / LIVE_PROVENANCE_HELPER)


def current_launcher_helper_sha256() -> str:
    return sha256(ROOT / LIVE_LAUNCHER_HELPER)


def retained_source_dependency_gaps(doc: dict, *, generator: str,
                                    requires_launcher_helper: bool = False,
                                    extra_dependencies: list[str] | None = None) -> list[str]:
    """Join retained live evidence to its generator and shared helper bytes."""
    run = doc.get("run_provenance") or {}
    gaps = []
    if run.get("generator_sha256") != sha256(ROOT / generator):
        gaps.append(
            "retained generator SHA-256 differs from the current generator")
    if run.get("provenance_helper_sha256") != current_provenance_helper_sha256():
        gaps.append(
            "retained provenance-helper SHA-256 differs from the current shared helper")
    if requires_launcher_helper and run.get("launcher_helper_sha256") != \
            current_launcher_helper_sha256():
        gaps.append(
            "retained launcher-helper SHA-256 differs from the current owned launcher")
    retained_extra = run.get("source_dependencies") or {}
    for rel in extra_dependencies or []:
        if retained_extra.get(rel) != sha256(ROOT / rel):
            gaps.append(f"retained dependency SHA-256 differs for {rel}")
    return gaps


def training_regeneration_gaps(doc: dict) -> list[str]:
    """Recompute the strict Training recipe from retained low-level observations."""
    gaps = []
    output = doc.get("output")
    entries = json.loads((ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())[
        "entries"]
    expected = entries.get(output) or {}
    playback = doc.get("playback_generation")
    if not isinstance(playback, dict):
        return ["playback_generation is absent; the fixture was only existence-checked"]
    exact = {
        "reproduction_verified": True,
        "candidate_generated_in_this_run": True,
        "requested_start_frame": 0,
        "start_playback_index": 0,
        "advance_start_playback_index": 0,
        "target_movie_frame": 6904,
        "observed_playback_index": 6904,
        "observed_emulator_frame": 6905,
        "observed_cycle": 3909055795,
        "observed_pc": "0x8004fea4",
        "loaded_frame_count": 9299,
        "reproducible": True,
        "matches_provisioned_fixture": True,
    }
    for key, value in exact.items():
        if playback.get(key) != value:
            gaps.append(f"playback_generation.{key}={playback.get(key)!r}, expected {value!r}")
    if playback.get("generated_sha256") != expected.get("sha256"):
        gaps.append("generated Training hash differs from the central fixture pin")
    if playback.get("generated_size") != expected.get("size"):
        gaps.append("generated Training size differs from the central fixture pin")
    if doc.get("output_size") != expected.get("size"):
        gaps.append("retained Training output_size differs from the central fixture pin")
    if (doc.get("fixture_sha256") or {}).get(output) != expected.get("sha256"):
        gaps.append("retained Training fixture hash differs from the central fixture pin")
    timing = (doc.get("run_provenance") or {}).get("timing") or {}
    if timing.get("movie_frame") != 6904 or timing.get("emulator_frame") != 6905:
        gaps.append("run timing does not retain the deterministic movie/emulator boundary")
    if timing.get("candidate_generated_in_this_run") is not True:
        gaps.append("run timing does not prove that a transient candidate was regenerated")
    return gaps


def required_state_media_provenance_gaps(
        doc: dict, *, require_selection: bool = False) -> list[str]:
    """Require central fixture and embedded-media hashes on every loaded save.

    ``retained_pristine_save_gaps`` validates fields when present. Closure also
    requires the fresh helper's fields to be present, otherwise old same-serial
    evidence can survive a stronger provenance contract without replay.
    """
    gaps = retained_pristine_save_gaps(doc, require_selection=require_selection)
    run = doc.get("run_provenance") or {}
    anchor = run.get("anchor") or {}
    saves = list(anchor.get("saves") or [])
    if anchor.get("save"):
        saves.append(anchor["save"])
    if not saves:
        return gaps
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
        inspection = by_fixture.get(save) or by_fixture.get(Path(save).name)
        if not isinstance(inspection, dict):
            continue
        declaration = inspection.get("fixture_declaration")
        if not isinstance(declaration, dict):
            gaps.append(f"{save}: pre-load inspection has no central fixture declaration")
        else:
            if declaration.get("manifest") != \
                    "analysis/phase0_2_external_fixture_set.json":
                gaps.append(f"{save}: inspection declaration names the wrong manifest")
            if not isinstance(declaration.get("size"), int):
                gaps.append(f"{save}: inspection declaration has no exact size")
        origin = inspection.get("state_media_hash_verification")
        if not isinstance(origin, dict):
            gaps.append(f"{save}: embedded media hash verification is absent")
            continue
        if origin.get("pin_source") != "tools/build_baselines.json":
            gaps.append(f"{save}: embedded media verification names the wrong pin source")
        files = origin.get("files") or {}
        if not files or any(
                row.get("matches_pin") is not True
                or row.get("actual_sha1") != row.get("expected_sha1")
                for row in files.values()):
            gaps.append(f"{save}: embedded media file hashes are incomplete or mismatched")
    return gaps


def artifact_fixtures(outputs: list[str]) -> dict[str, dict]:
    fixtures = {}
    for rel in outputs:
        path = ROOT / rel
        if not path.is_file() or path.suffix != ".json":
            continue
        try:
            doc = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        for field in ("fixture_sha256", "patched_fixture_sha256"):
            for fixture, digest in (doc.get(field) or {}).items():
                fixtures[fixture] = {"sha256": digest, "declared_in": rel, "field": field}
    return fixtures


def references_in_tree(needles: list[str], root: Path, suffix: str) -> list[str]:
    hits = []
    for path in sorted(root.rglob(f"*{suffix}")):
        text = path.read_text(errors="replace")
        if any(needle in text for needle in needles):
            hits.append(path.relative_to(ROOT).as_posix())
    return hits


def live_mode_declaration_gaps(tool: str, row: dict) -> list[str]:
    """Reject live commands that rely on launcher or emulator defaults implicitly."""
    gaps = []
    reproduction = row.get("reproduction")
    if not isinstance(reproduction, dict):
        return [f"{tool}: missing reproduction declaration"]
    for field in ("launcher_command", "settings_command", "settings_profile",
                  "binary", "media"):
        if not reproduction.get(field):
            gaps.append(f"{tool}: missing reproduction.{field}")
    launch = reproduction.get("launcher_command") or ""
    settings = reproduction.get("settings_command") or ""
    for flag in ("--config-dir", "--port", "--token", "--binary", "--disc"):
        if flag not in launch:
            gaps.append(f"{tool}: launcher omits {flag}")
    if reproduction.get("settings_profile") == "isolated-defaults-v1":
        for token in (LIVE_LAUNCHER_HELPER, "--fork-launcher", "--client"):
            if token not in launch:
                gaps.append(f"{tool}: owned launcher omits {token}")
    for flag in ("--config-dir", "--port", "--binary", "--binary-sha256", "--profile"):
        if flag not in settings:
            gaps.append(f"{tool}: settings guard omits {flag}")
    binary = reproduction.get("binary") or {}
    if not binary.get("path") or not re.fullmatch(r"[0-9a-f]{64}", binary.get("sha256", "")):
        gaps.append(f"{tool}: binary path/SHA-256 is not exact")
    else:
        binary_path = Path(binary["path"]).expanduser()
        if not binary_path.is_file():
            gaps.append(f"{tool}: declared binary is absent: {binary_path}")
        elif sha256(binary_path) != binary["sha256"]:
            gaps.append(f"{tool}: declared binary SHA-256 differs from current bytes")
    if reproduction.get("immutable_snapshot_required"):
        for token in ("tools/live_toolchain_snapshot.py", "--snapshot-dir",
                      "--fork-launcher", "--client"):
            if token not in launch:
                gaps.append(f"{tool}: immutable launcher omits {token}")
    media = reproduction.get("media") or {}
    if media.get("pin_source") != "tools/build_baselines.json":
        gaps.append(f"{tool}: pristine media does not name build_baselines pin source")
    cue = media.get("cue") or {}
    tracks = media.get("tracks") or []
    if not cue.get("path") or not re.fullmatch(r"[0-9a-f]{40}", cue.get("sha1", "")):
        gaps.append(f"{tool}: CUE path/SHA-1 is not exact")
    if not tracks or any(not track.get("path") or
                         not re.fullmatch(r"[0-9a-f]{40}", track.get("sha1", ""))
                         for track in tracks):
        gaps.append(f"{tool}: track path/SHA-1 is not exact")
    return gaps


def retained_environment_gaps(doc: dict, live_modes: list[dict]) -> list[str]:
    """Join a retained live artifact to its declared binary and retail media."""
    run = doc.get("run_provenance") or {}
    actual_binary = run.get("duckstation") or {}
    media = ((run.get("anchor") or {}).get("media_identity") or {})
    verification = media.get("hash_verification") or {}
    declarations = [mode["reproduction"] for mode in live_modes
                    if isinstance(mode.get("reproduction"), dict)]
    if not declarations:
        return ["no declared live environment"]
    snapshot = run.get("toolchain_snapshot") or {}
    expected_source = CURRENT_RPC_MANIFEST["source"]
    matched_binary = any(
        actual_binary.get("binary_sha256") == row["binary"].get("sha256")
        and (
            Path(actual_binary.get("binary_path") or "").resolve()
            == Path(row["binary"].get("path") or "").expanduser().resolve()
            or (
                row.get("immutable_snapshot_required") is True
                and snapshot.get("verified") is True
                and snapshot.get("binary_sha256") == row["binary"].get("sha256")
                and Path(snapshot.get("source_binary_path") or "").resolve()
                == Path(row["binary"].get("path") or "").expanduser().resolve()
            )
        )
        for row in declarations
    )
    gaps = []
    if not matched_binary:
        gaps.append("retained binary path/SHA-256 differs from every declared live mode")
    if any(row.get("immutable_snapshot_required") for row in declarations):
        if snapshot.get("verified") is not True:
            gaps.append("retained run lacks a verified immutable toolchain snapshot")
        snapshot_source = snapshot.get("source") or {}
        expected_snapshot_source = {
            "revision": expected_source["revision"],
            "status_sha256": expected_source["status_sha256"],
            "dispatcher_sha256": expected_source["dispatcher_sha256"],
            "method_count": CURRENT_RPC_MANIFEST["methods"]["counts"]["current"],
        }
        if any(snapshot_source.get(key) != value
               for key, value in expected_snapshot_source.items()):
            gaps.append("retained immutable snapshot differs from current RPC source identity")
    else:
        retained_rpc = run.get("rpc_manifest") or {}
        expected_rpc_source = {
            "revision": expected_source["revision"],
            "status_sha256": expected_source["status_sha256"],
            "dispatcher_sha256": expected_source["dispatcher_sha256"],
            "method_count": CURRENT_RPC_MANIFEST["methods"]["counts"]["current"],
        }
        if retained_rpc.get("path") != RPC_MANIFEST_PATH.relative_to(ROOT).as_posix():
            gaps.append("retained run does not name the Phase-3 RPC manifest")
        if retained_rpc.get("semantic_sha256") != rpc_manifest_semantic_sha256():
            gaps.append("retained run differs from current RPC manifest semantic identity")
        if retained_rpc.get("source") != expected_rpc_source:
            gaps.append("retained run differs from current RPC source identity")
        retained_rpc_binary = retained_rpc.get("binary") or {}
        if not any(
                retained_rpc_binary.get("sha256") == row["binary"].get("sha256")
                and Path(retained_rpc_binary.get("path") or "").expanduser().resolve()
                == Path(row["binary"].get("path") or "").expanduser().resolve()
                for row in declarations):
            gaps.append("retained RPC binary identity differs from every declared live mode")
    expected_files = {
        Path(row["media"]["cue"]["path"]).name: row["media"]["cue"]["sha1"]
        for row in declarations
    }
    for row in declarations:
        expected_files.update({
            Path(track["path"]).name: track["sha1"]
            for track in row["media"].get("tracks", [])
        })
    observed_files = verification.get("files") or {}
    for name, expected in expected_files.items():
        observed = observed_files.get(name) or {}
        if observed.get("actual_sha1") != expected or observed.get("matches_pin") is not True:
            gaps.append(f"retained media pin mismatch: {name}")
    return gaps


def build_inventory() -> dict:
    tracked_mutations = tracked_input_mutations()
    current_live_toolchain_gaps = rpc_manifest.current_fork_gaps(
        CURRENT_RPC_MANIFEST)
    discovered_generators = sorted(
        path.relative_to(ROOT).as_posix() for path in (ROOT / "tools").glob("phase3_*.py")
    )
    discovered_artifacts = sorted([
        *(path.relative_to(ROOT).as_posix()
          for path in (ROOT / "analysis").glob("phase3_*.json")),
        *(path.relative_to(ROOT).as_posix()
          for path in [ROOT / "tools/duckstation_rpc_method_manifest.md"]
          if path.is_file()),
    ])
    declared_outputs = sorted(
        output for spec in GENERATOR_SPECS.values() for output in spec["outputs"]
    )
    rows = {}
    for rel, spec in sorted(GENERATOR_SPECS.items()):
        path = ROOT / rel
        source = path.read_text()
        outputs = spec["outputs"]
        fixtures = artifact_fixtures(outputs)
        literals = sorted(set(PATH_LITERAL.findall(source)) - set(outputs))
        classifications = sorted({row["classification"] for row in spec["modes"]})
        declared_live_modes = [row for row in spec["modes"]
                               if row["classification"] == "live"]
        requires_launcher_helper = any(
            LIVE_LAUNCHER_HELPER in (row.get("reproduction", {}).get(
                "launcher_command") or "")
            for row in declared_live_modes
        )
        live_output_paths = set(spec.get("live_outputs", outputs)) if "live" in classifications else set()
        live_outputs = []
        for output in outputs:
            out_path = ROOT / output
            if out_path.is_file() and out_path.suffix == ".json":
                try:
                    doc = json.loads(out_path.read_text())
                except ValueError:
                    continue
                if output in live_output_paths:
                    run = doc.get("run_provenance") or {}
                    anchor = run.get("anchor") or {}
                    saves = ([anchor["save"]] if anchor.get("save") else
                             list(anchor.get("saves") or []))
                    inspections = anchor.get("state_inspections") or []
                    inspected = {
                        Path(row.get("path") or "").name
                        for row in inspections
                        if row.get("exists") is True and row.get("valid") is True
                        and row.get("serial") == "SCUS-94288"
                    }
                    state_inspections_complete = (
                        not saves or
                        {Path(save).name for save in saves}.issubset(inspected)
                    )
                    origin_gaps = required_state_media_provenance_gaps(
                        doc, require_selection=output in STRICT_PRISTINE_AGGREGATES)
                    environment_gaps = retained_environment_gaps(doc, declared_live_modes)
                    dependency_gaps = retained_source_dependency_gaps(
                        doc, generator=rel,
                        requires_launcher_helper=requires_launcher_helper,
                        extra_dependencies=spec.get("extra_dependencies"))
                    reproduction_guard_gaps = (
                        training_regeneration_gaps(doc)
                        if output == "analysis/phase3_training_anchor_fixture.json"
                        else []
                    )
                    live_outputs.append({
                        "artifact": output,
                        "run_provenance_present": isinstance(doc.get("run_provenance"), dict),
                        "save_anchors": saves,
                        "state_inspections_complete": state_inspections_complete,
                        "pristine_save_origin_gaps": origin_gaps,
                        "declared_environment_gaps": environment_gaps,
                        "source_dependency_gaps": dependency_gaps,
                        "reproduction_guard_gaps": reproduction_guard_gaps,
                    })
        needles = [Path(rel).name, *outputs]
        rows[rel] = {
            "tool_sha256": sha256(path),
            "shared_dependencies": (([{
                "path": LIVE_PROVENANCE_HELPER,
                "sha256": current_provenance_helper_sha256(),
            }] + ([{
                "path": LIVE_LAUNCHER_HELPER,
                "sha256": current_launcher_helper_sha256(),
            }] if requires_launcher_helper else []) +
                [{"path": rel, "sha256": sha256(ROOT / rel)}
                  for rel in spec.get("extra_dependencies", [])])
                if "live" in classifications else []),
            "modes": spec["modes"],
            "outputs": [
                {"path": output,
                 "tracked": bool((ROOT / output).is_file()),
                 # An inventory cannot embed its own content hash without an
                 # impossible self-referential fixed point. Freshness is checked
                 # by recomputing its semantic content instead.
                 "sha256": (sha256(ROOT / output)
                            if (ROOT / output).is_file() and output not in NON_HASHED_OUTPUTS
                            else None)}
                for output in outputs
            ],
            "source_path_literals": literals,
            "artifact_fixtures": fixtures,
            "guards": references_in_tree(needles, ROOT / "tests", ".py"),
            "notes": references_in_tree(needles, ROOT / "ObsidianVault", ".md"),
            "live_artifact_provenance": live_outputs,
            "uses_hardcoded_default_token": 'default="debugger-1000"' in source,
            "accepts_config_dir": bool(re.search(
                r"add_argument\(\s*[\"']--config-dir[\"']", source)
                or "add_required_live_args(" in source),
        }

    missing_declarations = sorted(set(discovered_generators) - set(GENERATOR_SPECS))
    stale_declarations = sorted(set(GENERATOR_SPECS) - set(discovered_generators))
    orphan_artifacts = sorted(set(discovered_artifacts) - set(declared_outputs))
    missing_outputs = sorted(set(declared_outputs) - set(discovered_artifacts))
    live_provenance_gaps = sorted(
        item["artifact"]
        for row in rows.values()
        for item in row["live_artifact_provenance"]
        if not item["run_provenance_present"]
    )
    live_state_inspection_gaps = sorted(
        item["artifact"]
        for row in rows.values()
        for item in row["live_artifact_provenance"]
        if item["save_anchors"] and not item["state_inspections_complete"]
    )
    live_save_origin_gaps = sorted(
        item["artifact"]
        for row in rows.values()
        for item in row["live_artifact_provenance"]
        if item["pristine_save_origin_gaps"]
    )
    hardcoded_token_tools = sorted(
        rel for rel, row in rows.items()
        if "live" in {mode["classification"] for mode in row["modes"]}
        and row["uses_hardcoded_default_token"]
    )
    missing_config_dir_tools = sorted(
        rel for rel, row in rows.items()
        if "live" in {mode["classification"] for mode in row["modes"]}
        and not row["accepts_config_dir"]
    )
    live_mode_environment_declaration_gaps = sorted(
        gap
        for tool, spec in GENERATOR_SPECS.items()
        for row in spec["modes"]
        if row["classification"] == "live"
        for gap in live_mode_declaration_gaps(tool, row)
    )
    live_artifact_environment_mismatches = sorted(
        f"{item['artifact']}: {gap}"
        for row in rows.values()
        for item in row["live_artifact_provenance"]
        for gap in item["declared_environment_gaps"]
    )
    live_artifact_source_dependency_mismatches = sorted(
        f"{item['artifact']}: {gap}"
        for row in rows.values()
        for item in row["live_artifact_provenance"]
        for gap in item["source_dependency_gaps"]
    )
    live_artifact_reproduction_guard_failures = sorted(
        f"{item['artifact']}: {gap}"
        for row in rows.values()
        for item in row["live_artifact_provenance"]
        for gap in item["reproduction_guard_gaps"]
    )
    return {
        "_comment": "Complete Phase-3 evidence generator/artifact inventory. "
                    "Classifications are declared per command mode; filesystem "
                    "discovery rejects silent generator/artifact omissions. "
                    "Regenerate: python3 tools/phase3_evidence_inventory.py",
        "generated": date.today().isoformat(),
        "generators": rows,
        "summary": {
            "generators_discovered": len(discovered_generators),
            "generators_declared": len(GENERATOR_SPECS),
            "artifacts_discovered": len(discovered_artifacts),
            "artifacts_declared": len(declared_outputs),
            "missing_generator_declarations": missing_declarations,
            "stale_generator_declarations": stale_declarations,
            "orphan_artifacts": orphan_artifacts,
            "missing_outputs": missing_outputs,
            "live_artifacts_without_run_provenance": live_provenance_gaps,
            "live_save_artifacts_without_preload_state_inspection":
                live_state_inspection_gaps,
            "live_save_artifacts_with_non_pristine_origin": live_save_origin_gaps,
            "live_tools_with_hardcoded_default_token": hardcoded_token_tools,
            "live_tools_without_config_dir_argument": missing_config_dir_tools,
            "live_mode_environment_declaration_gaps":
                live_mode_environment_declaration_gaps,
            "live_artifact_environment_mismatches":
                live_artifact_environment_mismatches,
            "live_artifact_source_dependency_mismatches":
                live_artifact_source_dependency_mismatches,
            "live_artifact_reproduction_guard_failures":
                live_artifact_reproduction_guard_failures,
            "current_live_toolchain_gaps": current_live_toolchain_gaps,
            "tracked_input_mutations": tracked_mutations,
        },
        "closure_ready": not any((
            missing_declarations, stale_declarations, orphan_artifacts, missing_outputs,
            live_provenance_gaps, live_state_inspection_gaps,
            live_save_origin_gaps,
            hardcoded_token_tools, missing_config_dir_tools,
            live_mode_environment_declaration_gaps,
            live_artifact_environment_mismatches,
            live_artifact_source_dependency_mismatches,
            live_artifact_reproduction_guard_failures,
            current_live_toolchain_gaps,
            tracked_mutations,
        )),
    }


def main() -> int:
    doc = build_inventory()
    path = ROOT / INVENTORY_OUTPUT
    path.write_text(json.dumps(doc, indent=1) + "\n")
    summary = doc["summary"]
    print(f"[phase3-inventory] {summary['generators_declared']}/"
          f"{summary['generators_discovered']} generators declared; "
          f"{summary['artifacts_declared']}/{summary['artifacts_discovered']} artifacts owned")
    print(f"[phase3-inventory] {'CLOSURE-READY' if doc['closure_ready'] else 'OPEN'}")
    for key, value in summary.items():
        if isinstance(value, list) and value:
            print(f"  {key}: {value}")
    return 0 if doc["closure_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
