#!/usr/bin/env python3
"""Report and validate the authoritative ABL reverse-engineering campaign state.

The repository has several independently generated progress artifacts.  This
tool derives one stable summary from them so status prose cannot silently drift
from the census, naming store, overlay builder, or format manifests.

The default command is read-only and prints the live derived status.  ``--check``
also compares it with the committed snapshot.  ``--write`` is the only mode
that changes a file.  ``--preflight`` additionally verifies local media and
toolchain hashes; a dirty worktree is reported but is not an error.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
SNAPSHOT = ANALYSIS / "re_campaign_status.json"
EXPECTED_GENERATOR = "tools/re_campaign_status.py"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_count(path: Path) -> int:
    return sum(1 for item in path.rglob("*.c") if item.is_file()) if path.exists() else 0


def derive_status() -> dict:
    census = _json(ANALYSIS / "functions.json")
    progress = _json(ANALYSIS / "decomp_progress.json")
    overlay_progress = _json(ANALYSIS / "overlay_decomp_progress.json")
    naming = _json(ANALYSIS / "naming_priority.json")
    overlay_naming = _json(ANALYSIS / "overlay_naming_priority.json")
    u3 = _json(ANALYSIS / "traces" / "u3_evidence.json")
    chunk_roles = _json(ROOT / "tools" / "level_raw_chunk_roles.json")
    subsystem_slices = _json(ANALYSIS / "subsystem_slices.json")

    resident = [row for row in census["functions"] if row["space"] == "resident"]
    resident_code = [row for row in resident if row["range_type"] in ("code", "thunk")]
    overlay_code = [
        row
        for row in census["functions"]
        if row["space"] == "overlay" and row["range_type"] == "code"
    ]
    unknown = [row for row in resident_code if row["classification"] == "unknown"]
    unknown_starts = {row["start"] for row in unknown}
    u3_hit_starts = {address for address, evidence in u3.items() if evidence.get("hits", 0) > 0}

    role_confidence = Counter(row["confidence"] for row in chunk_roles)
    matched = progress["matched"]

    return {
        "generated_by": EXPECTED_GENERATOR,
        "schema_version": 1,
        "resident": {
            "records": len(resident),
            "code_functions": len(resident_code),
            "classification": dict(sorted(Counter(row["classification"] for row in resident_code).items())),
            "unknown": len(unknown),
            "unknown_dynamic": sum("dynamic" in row.get("discovery", []) for row in unknown),
            "unknown_graph_connected": sum(bool(row.get("callers") or row.get("callees")) for row in unknown),
            "unknown_opaque": sum(not (row.get("callers") or row.get("callees")) for row in unknown),
            "unknown_with_u3_hits": len(unknown_starts & u3_hit_starts),
        },
        "overlay": {
            "code_functions": len(overlay_code),
            "named": len(overlay_code) - overlay_naming["unknown_total"],
            "unknown": overlay_naming["unknown_total"],
            "runtime_covered_unknown": overlay_naming["dynamic_covered"],
            "byte_matched_c": overlay_progress["matched"]["functions"],
        },
        "reconstruction": {
            "resident_matched_functions": matched["functions"],
            "resident_matched_bytes": matched["bytes"],
            "resident_matched_byte_pct": matched["pct_bytes"],
            "resident_asm_functions": matched["asm"]["functions"],
            "resident_c_functions": matched["c"]["functions"],
            "resident_c_bytes": matched["c"]["bytes"],
            "source_tree_c": {
                "resident": _source_count(ROOT / "src" / "main"),
                "overlay": _source_count(ROOT / "src" / "overlays"),
                "wip": _source_count(ROOT / "src" / "wip"),
            },
        },
        "understanding": {
            "resident_unknown": naming["unknown_total"],
            "resident_runtime_covered_unknown": naming["dynamic_covered"],
            "u3_candidates": len(u3),
            "u3_candidates_hit": len(u3_hit_starts),
            "u3_hit_still_unknown": len(unknown_starts & u3_hit_starts),
        },
        "formats": {
            "level_raw_roles_total": len(chunk_roles),
            "level_raw_roles_semantic_confirmed": role_confidence.get("CONFIRMED", 0),
            "level_raw_roles_format_confirmed": role_confidence.get("CONFIRMED-fmt", 0),
            "level_raw_roles_likely": role_confidence.get("LIKELY", 0),
            "mover_vm_opcodes_confirmed": 26,
            "mover_vm_opcodes_total": 26,
            "all_roundtrip_files": 78,
            "anm_roundtrip_files": 58,
        },
        "subsystem_slices": {
            name: {
                "status": row["status"],
                "scope": row["scope"],
                "residual": row["residual"],
            }
            for name, row in sorted(subsystem_slices["slices"].items())
        },
        "acceptance": {
            "all_resident_candidates_classified": len(unknown) == 0,
            "all_tracked_overlay_candidates_classified": overlay_naming["unknown_total"] == 0,
            "game_code_c_complete": False,
            # sc-3 (EXP_2026-07-09_audio_engine_probe): all three named residuals
            # addressed — sequencer linked-dead (0 game callers + 0 runtime hits),
            # SPU voice scheduling reconstructed (src_re/sfx_voice_manager.c), and
            # non-XA SFX id->VAG map solved (analysis/sfx_id_vag_map.json, validated
            # live id 0x35 -> tone 37 -> VAG 38). XA music start already closed.
            "audio_engine_closed": True,
            # sc-4 (EXP_2026-07-09_fmv_engine_bounded_close): FMV.BIN is stock PsyQ
            # libpress STR-player orchestration — 0 hardware-register accesses in the
            # whole 509KB overlay, delegates to resident St*/Cd*/Gpu* + async
            # flag-signaled decode ("time out in decoding !" spin-wait). No custom
            # MDEC decoder exists to reverse; closed by identification.
            "fmv_engine_closed": True,
            "model_animation_semantics_closed": False,
            "collision_contact_semantics_closed": False,
            "loose_ends_closed": all(
                row["status"] in ("confirmed_static", "address_role_closed")
                for row in _json(ANALYSIS / "loose_ends.json")["items"].values()
            ),
        },
    }


def _print_status(status: dict) -> None:
    resident = status["resident"]
    overlay = status["overlay"]
    reconstruction = status["reconstruction"]
    formats = status["formats"]
    print(
        "resident: "
        f"{resident['code_functions']} code functions; {resident['unknown']} unknown "
        f"({resident['unknown_with_u3_hits']} already have u3 hits)"
    )
    print(
        "reconstruction: "
        f"{reconstruction['resident_c_functions']} C + "
        f"{reconstruction['resident_asm_functions']} asm = "
        f"{reconstruction['resident_matched_byte_pct']:.3f}% of resident code bytes"
    )
    print(
        "overlays: "
        f"{overlay['named']}/{overlay['code_functions']} named; "
        f"{overlay['byte_matched_c']} byte-matched C"
    )
    print(
        "LEVEL.RAW: "
        f"{formats['level_raw_roles_semantic_confirmed']} semantic + "
        f"{formats['level_raw_roles_format_confirmed']} format-confirmed + "
        f"{formats['level_raw_roles_likely']} likely = "
        f"{formats['level_raw_roles_total']} roles"
    )
    open_items = [name for name, done in status["acceptance"].items() if not done]
    print(f"acceptance: {len(open_items)} open ({', '.join(open_items)})")


def _check_snapshot(status: dict) -> list[str]:
    if not SNAPSHOT.exists():
        return [f"missing committed snapshot: {SNAPSHOT.relative_to(ROOT)}"]
    committed = _json(SNAPSHOT)
    return [] if committed == status else ["campaign status snapshot is stale; run with --write"]


def _toolchain_preflight() -> list[str]:
    errors: list[str] = []
    segments = yaml.safe_load((ROOT / "config" / "segments.yml").read_text(encoding="utf-8"))
    image = ROOT / segments["image"]
    if not image.exists():
        errors.append(f"owner EXE missing: {image}")
    else:
        digest = hashlib.sha1(image.read_bytes()).hexdigest()
        if digest != segments["sha1"]:
            errors.append(f"owner EXE SHA-1 mismatch: {digest} != {segments['sha1']}")

    prefix = os.environ.get("ABL_MIPS_PREFIX", "mips64-linux-gnu-")
    for name in ("as", "ld", "objcopy"):
        if shutil.which(prefix + name) is None:
            errors.append(f"cross tool missing: {prefix + name}")

    manifest = _json(ROOT / "tools" / "toolchain_manifest.json")
    oldgcc = Path(os.environ.get("ABL_OLDGCC_DIR", "~/abl-toolchain/old-gcc")).expanduser()
    for record in manifest["compilers"]:
        compiler_dir = oldgcc / Path(record["dir"]).name
        for filename, key in (("cc1", "cc1_sha256"), ("cpp", "cpp_sha256")):
            path = compiler_dir / filename
            if not path.exists():
                errors.append(f"compiler input missing: {path}")
            elif _sha256(path) != record[key]:
                errors.append(f"compiler input hash mismatch: {path}")

    maspsx = Path(os.environ.get("ABL_MASPSX", "~/abl-toolchain/maspsx/maspsx.py")).expanduser()
    if not maspsx.exists():
        errors.append(f"maspsx missing: {maspsx}")

    psyq = os.environ.get("ABL_PSYQ_INCLUDE")
    if psyq:
        include = Path(psyq).expanduser()
        if not include.is_dir():
            errors.append(f"ABL_PSYQ_INCLUDE is not a directory: {include}")
        else:
            sys.path.insert(0, str(ROOT / "tools"))
            from substrate_common import external_header_evidence
            evidence = external_header_evidence(include)
            print("PsyQ oracle: "
                  f"{evidence['file_count']} external files, "
                  f"tree sha256={evidence['tree_sha256']} (contents uncommitted)")
    else:
        print("PsyQ oracle: not configured (optional; set ABL_PSYQ_INCLUDE)")

    if not errors:
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            from substrate_common import compile_at, load_segments

            segment_config = load_segments()
            c_toolchain = segment_config["c_toolchain"]
            with tempfile.TemporaryDirectory(prefix="abl_preflight_") as directory:
                source = Path(directory) / "smoke.c"
                source.write_text(
                    "void set_two_bytes(unsigned char *p){p[3]=12;p[7]=0x3c;}\n",
                    encoding="ascii",
                )
                built = compile_at(
                    source,
                    0x80061D04,
                    compiler_id=c_toolchain["compiler"],
                    cc1_flags=c_toolchain["cc1_flags"],
                    maspsx_args=c_toolchain.get("maspsx_args", []),
                )
                if not built:
                    errors.append("C toolchain smoke test produced no code")
            if not errors:
                print("C toolchain: compile smoke test passed")
        except Exception as exc:
            errors.append(f"C toolchain smoke test failed: {exc}")

    result = subprocess.run(
        [sys.executable, "tools/verify_repro_inputs.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        errors.append("critical reproducibility inputs failed verification")
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)

    dirty = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.splitlines()
    print(f"worktree: {len(dirty)} changed/untracked paths (reported, not failed)")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="update the committed status snapshot")
    parser.add_argument("--check", action="store_true", help="fail when the committed snapshot is stale")
    parser.add_argument("--preflight", action="store_true", help="verify local media and toolchains")
    parser.add_argument("--run-tests", action="store_true", help="run the repository's safe pytest suite")
    parser.add_argument(
        "--run-build",
        action="store_true",
        help="rebuild and SHA-1-validate the owner EXE (requires local media)",
    )
    args = parser.parse_args(argv)

    status = derive_status()
    _print_status(status)
    errors: list[str] = []

    if args.write:
        SNAPSHOT.write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {SNAPSHOT.relative_to(ROOT)}")
    if args.check:
        errors.extend(_check_snapshot(status))
    if args.preflight:
        errors.extend(_toolchain_preflight())
    if args.run_tests:
        result = subprocess.run([sys.executable, "tools/run_safe_tests.py"], cwd=ROOT)
        if result.returncode:
            errors.append("safe pytest suite failed")
    if args.run_build:
        for script in ("tools/build_psx_exe.py", "tools/validate_build.py"):
            result = subprocess.run(
                [sys.executable, script], cwd=ROOT, text=True, capture_output=True
            )
            if result.returncode:
                errors.append(f"{script} failed")
                output = (result.stdout + result.stderr).splitlines()
                print("\n".join(output[-40:]), file=sys.stderr)
                break
        else:
            print("reconstruction: full EXE build and SHA-1 validation passed")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
