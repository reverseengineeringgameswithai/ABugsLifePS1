#!/usr/bin/env python3
"""Race-safe, PID-owned wrapper for the external DuckStation launcher.

The external launcher can inspect ``$!`` before ``setsid`` has completed its
``exec`` into ``duckstation-qt``.  In that narrow window it reports
``Instance exited during startup`` and removes the pidfile even though the exact
requested process is live.  This wrapper never selects a process by name alone:
it recovers only one process whose executable, XDG config/runtime environment,
and open file descriptors all belong to the fresh requested config directory,
then proves the authenticated API is stable before restoring the pidfile.

Stop delegates to the fork launcher's PID-scoped stop and then treats a reaped
process or a dead zombie as stopped.  It never uses a broad process-name kill.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

DUCK = Path.home() / "duckstation"
DEFAULT_LAUNCHER = DUCK / "scripts/debugger-client/launch_debugger_instance.sh"
DEFAULT_CLIENT = DUCK / "scripts/debugger-client/duckstation_debug_client.py"


def _under_tmp(path: Path) -> Path:
    path = path.resolve()
    if not path.is_absolute() or not str(path).startswith("/tmp/"):
        raise SystemExit("--config-dir must be an absolute path below /tmp")
    return path


def process_state(pid: int, *, proc_root: Path = Path("/proc")) -> str | None:
    """Return the Linux process state, or ``None`` once the PID is reaped."""
    try:
        fields = (proc_root / str(pid) / "stat").read_text().split()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    return fields[2] if len(fields) >= 3 else "?"


def process_stopped(pid: int, *, proc_root: Path = Path("/proc")) -> bool:
    """A zombie is dead even if its transient /proc entry has not been reaped."""
    return process_state(pid, proc_root=proc_root) in (None, "Z", "X")


def wait_stopped(pid: int, *, timeout: float = 8.0,
                 proc_root: Path = Path("/proc")) -> tuple[bool, str | None, int]:
    started = time.monotonic()
    while True:
        state = process_state(pid, proc_root=proc_root)
        if state in (None, "Z", "X"):
            return True, state, round((time.monotonic() - started) * 1000)
        if time.monotonic() - started >= timeout:
            return False, state, round((time.monotonic() - started) * 1000)
        time.sleep(0.05)


def _environment(pid: int, *, proc_root: Path = Path("/proc")) -> dict[str, str]:
    try:
        raw = (proc_root / str(pid) / "environ").read_bytes()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return {}
    result = {}
    for item in raw.split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        result[key.decode(errors="replace")] = value.decode(errors="replace")
    return result


def _owns_config(pid: int, config: Path, *, proc_root: Path = Path("/proc")) -> bool:
    fd_root = proc_root / str(pid) / "fd"
    try:
        fds = list(fd_root.iterdir())
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return False
    for fd in fds:
        try:
            Path(os.readlink(fd)).resolve().relative_to(config)
            return True
        except (OSError, ValueError):
            continue
    return False


def owned_processes(config: Path, binary: Path, *,
                    proc_root: Path = Path("/proc")) -> list[int]:
    """Find exact config owners for startup-race recovery; never kill from this scan."""
    config = config.resolve()
    binary = binary.resolve()
    found = []
    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        pid = int(proc.name)
        try:
            exe = Path(os.readlink(proc / "exe")).resolve()
        except (OSError, RuntimeError):
            continue
        if exe != binary or process_stopped(pid, proc_root=proc_root):
            continue
        env = _environment(pid, proc_root=proc_root)
        if Path(env.get("XDG_CONFIG_HOME", "/")).resolve() != config:
            continue
        if Path(env.get("XDG_RUNTIME_DIR", "/")).resolve() != config / "runtime":
            continue
        if _owns_config(pid, config, proc_root=proc_root):
            found.append(pid)
    return sorted(found)


def _api_ready(client: Path, port: int, token: str) -> bool:
    return subprocess.run(
        [sys.executable, str(client), "--quiet", "--port", str(port),
         "--token", token, "status"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def _stable_api(client: Path, port: int, token: str, pid: int) -> bool:
    for _ in range(3):
        if process_stopped(pid) or not _api_ready(client, port, token):
            return False
        time.sleep(0.25)
    return True


def start(args) -> int:
    config = _under_tmp(args.config_dir)
    binary = args.binary.resolve()
    if not binary.is_file():
        raise SystemExit(f"requested binary is absent: {binary}")
    if not args.disc.resolve().is_file():
        raise SystemExit(f"requested disc is absent: {args.disc.resolve()}")
    command = [
        str(args.fork_launcher), "start", "--config-dir", str(config),
        "--port", str(args.port), "--token", args.token,
        "--binary", str(binary), "--disc", str(args.disc.resolve()),
    ]
    if args.display:
        command.extend(("--display", args.display))
    proc = subprocess.run(command, capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        if output:
            print(output)
        return 0

    # Recover only the exact exec-before-inspection race.  Any other launcher
    # failure remains a failure; this does not weaken media/API validation.
    deadline = time.monotonic() + 8.0
    candidates: list[int] = []
    while time.monotonic() < deadline:
        candidates = owned_processes(config, binary)
        if len(candidates) == 1 and _stable_api(args.client, args.port, args.token,
                                                candidates[0]):
            break
        if len(candidates) > 1:
            break
        time.sleep(0.1)
    if len(candidates) != 1 or not _stable_api(
            args.client, args.port, args.token, candidates[0]):
        if output:
            print(output, file=sys.stderr)
        if len(candidates) == 1:
            # The exact owner is known but its API never stabilized. Restore the
            # pidfile solely so the fork launcher's config/PID guard can stop
            # that one process; never strand a failed-start orphan.
            failed_pid = candidates[0]
            (config / "instance.pid").write_text(f"{failed_pid}\n")
            stopped = subprocess.run(
                [str(args.fork_launcher), "stop", "--config-dir", str(config),
                 "--binary", str(binary)], capture_output=True, text=True)
            dead, state, waited_ms = wait_stopped(failed_pid)
            print((stopped.stdout + stopped.stderr).strip(), file=sys.stderr)
            print(f"failed-start owned cleanup: pid={failed_pid} "
                  f"stopped={dead} final_state={state!r} waited_ms={waited_ms}",
                  file=sys.stderr)
        print(f"launcher recovery refused: exact config owners={candidates}",
              file=sys.stderr)
        return proc.returncode or 1

    pid = candidates[0]
    pidfile = config / "instance.pid"
    pidfile.write_text(f"{pid}\n")
    print(output)
    print(f"RECOVERED startup ownership race: pid={pid} port={args.port} "
          f"config={config}")
    return 0


def stop(args) -> int:
    config = _under_tmp(args.config_dir)
    pidfile = config / "instance.pid"
    try:
        pid = int(pidfile.read_text().strip())
    except (FileNotFoundError, ValueError):
        print(f"no valid pidfile at {pidfile}; refusing to select a process")
        return 1
    command = [str(args.fork_launcher), "stop", "--config-dir", str(config),
               "--binary", str(args.binary.resolve())]
    proc = subprocess.run(command, capture_output=True, text=True)
    stopped, state, waited_ms = wait_stopped(pid)
    output = (proc.stdout + proc.stderr).strip()
    if output:
        print(output)
    print(f"owned cleanup: pid={pid} stopped={str(stopped).lower()} "
          f"final_state={state!r} waited_ms={waited_ms}")
    return 0 if proc.returncode == 0 and stopped else 1


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("start", "stop"))
    ap.add_argument("--config-dir", type=Path, required=True)
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--fork-launcher", type=Path, default=DEFAULT_LAUNCHER)
    ap.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    ap.add_argument("--port", type=int)
    ap.add_argument("--token")
    ap.add_argument("--disc", type=Path)
    ap.add_argument("--display")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.action == "start" and (
            args.port is None or not args.token or args.disc is None):
        raise SystemExit("start requires --port, --token, and --disc")
    return start(args) if args.action == "start" else stop(args)


if __name__ == "__main__":
    raise SystemExit(main())
