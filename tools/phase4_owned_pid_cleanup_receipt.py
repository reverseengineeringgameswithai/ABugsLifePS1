#!/usr/bin/env python3
"""Record a credential-free receipt after an isolated DuckStation PID stops."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import phase4_common as common


RUNTIME_SHA256 = \
    "55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8"
LAUNCHER = Path(
    "~/duckstation/scripts/debugger-client/"
    "launch_debugger_instance.sh")


def build(args: argparse.Namespace) -> dict:
    config_dir = args.config_dir.resolve()
    output = args.output.resolve()
    result = args.result.resolve()
    runtime = args.runtime.resolve()
    if not str(config_dir).startswith("/var/tmp/"):
        raise SystemExit("config directory must be an isolated /var/tmp path")
    if Path(f"/proc/{args.owned_pid}").exists():
        raise SystemExit(f"owned PID {args.owned_pid} is still alive")
    if (config_dir / "instance.pid").exists():
        raise SystemExit("launcher PID file remains after stop")
    stop_path = config_dir / "stop.out"
    expected_stop = f"Stopped isolated instance (pid {args.owned_pid})."
    if not stop_path.is_file() or stop_path.read_text().strip() != expected_stop:
        raise SystemExit("owned launcher stop output is absent or mismatched")
    if not runtime.is_file() or common.sha256(runtime) != RUNTIME_SHA256:
        raise SystemExit("preserved runtime identity drifted")
    if not result.is_file():
        raise SystemExit("external live result is missing")
    if common.ROOT == output or common.ROOT in output.parents:
        raise SystemExit("cleanup receipt must remain outside Git")
    return {
        "schema": "abl-phase4-owned-pid-cleanup/1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "config_dir": str(config_dir),
        "owned_pid": args.owned_pid,
        "launcher": str(LAUNCHER),
        "stop_output": expected_stop,
        "instance_pid_absent_after_stop": True,
        "owned_pid_alive_after_stop": False,
        "runtime_executable_sha256": RUNTIME_SHA256,
        "evidence_result": {
            "absolute_path": str(result),
            "sha256": common.sha256(result),
            "bytes": result.stat().st_size,
        },
        "credentials_retained": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--owned-pid", type=int, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = build(args)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(f"PASS: owned PID {args.owned_pid} cleanup -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
