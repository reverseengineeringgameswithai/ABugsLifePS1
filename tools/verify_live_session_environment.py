#!/usr/bin/env python3
"""Verify the pinned DuckStation binary and effective live-replay settings.

The generic fork launcher intentionally creates a minimal fresh config.  Timing
keys omitted from that file therefore resolve through the exact binary's pinned
defaults.  The movie launcher writes its timing-sensitive keys explicitly.
This guard handles both cases, rejects conflicting overrides, and prints the
effective profile used by a Phase-3 live generator.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
from pathlib import Path


PROFILES = {
    "isolated-defaults-v1": {
        "CPU.ExecutionMode": "Recompiler",
        "CPU.OverclockEnable": "false",
        "CPU.OverclockNumerator": "1",
        "CPU.OverclockDenominator": "1",
        "CDROM.ReadSpeedup": "1",
        "CDROM.SeekSpeedup": "1",
        "Main.RewindEnable": "false",
        "Main.RunaheadFrameCount": "0",
        "Console.Region": "Auto",
        "Console.Enable8MBRAM": "false",
    },
    "movie-replay-v1": {
        "CPU.ExecutionMode": "CachedInterpreter",
        "CPU.OverclockEnable": "false",
        "CPU.OverclockNumerator": "1",
        "CPU.OverclockDenominator": "1",
        "CDROM.ReadSpeedup": "1",
        "CDROM.SeekSpeedup": "1",
        "Main.RewindEnable": "false",
        "Main.RunaheadFrameCount": "0",
        "Console.Region": "Auto",
        "Console.Enable8MBRAM": "false",
        "BIOS.PatchFastBoot": "false",
        "Pad1.Type": "AnalogController",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _same_value(actual: str, expected: str) -> bool:
    if expected.lower() in {"true", "false"}:
        return actual.lower() == expected.lower()
    return actual == expected


def verify_environment(*, config_dir: Path, binary: Path, binary_sha256: str,
                       port: int, profile: str) -> dict:
    config_dir = config_dir.expanduser().resolve()
    binary = binary.expanduser().resolve()
    if not config_dir.is_absolute() or not str(config_dir).startswith("/tmp/"):
        raise SystemExit("live-settings guard: config must be an absolute /tmp path")
    settings_path = config_dir / "duckstation/settings.ini"
    if not settings_path.is_file():
        raise SystemExit(f"live-settings guard: missing {settings_path}")
    if not binary.is_file():
        raise SystemExit(f"live-settings guard: missing binary {binary}")
    actual_binary_sha256 = sha256(binary)
    if actual_binary_sha256 != binary_sha256:
        raise SystemExit(
            "live-settings guard: binary SHA-256 mismatch: "
            f"{actual_binary_sha256} != {binary_sha256}")

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(settings_path)
    external = {
        "Enabled": "true",
        "Port": str(port),
        "BindAddress": "127.0.0.1",
    }
    errors: list[str] = []
    for key, expected in external.items():
        actual = parser.get("ExternalDebugger", key, fallback="")
        if not _same_value(actual, expected):
            errors.append(f"ExternalDebugger.{key}={actual!r}, expected {expected!r}")

    effective = {}
    for dotted, expected in PROFILES[profile].items():
        section, key = dotted.split(".", 1)
        explicit = parser.has_option(section, key)
        actual = parser.get(section, key, fallback=expected)
        if not _same_value(actual, expected):
            errors.append(f"{dotted}={actual!r}, expected {expected!r}")
        effective[dotted] = {
            "value": actual,
            "source": "settings.ini" if explicit else "pinned_binary_default",
        }
    bios_dir = parser.get("BIOS", "SearchDirectory", fallback="")
    if not bios_dir:
        errors.append("BIOS.SearchDirectory is absent")
    if errors:
        raise SystemExit("live-settings guard: " + "; ".join(errors))
    return {
        "profile": profile,
        "config_dir": str(config_dir),
        "settings_path": str(settings_path),
        "binary_path": str(binary),
        "binary_sha256": actual_binary_sha256,
        "port": port,
        "bios_search_directory": bios_dir,
        "effective": effective,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    args = parser.parse_args()
    print(json.dumps(verify_environment(
        config_dir=args.config_dir, binary=args.binary,
        binary_sha256=args.binary_sha256, port=args.port,
        profile=args.profile), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
