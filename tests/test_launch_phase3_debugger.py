"""The Phase-3 launcher recovers and stops only exact config-owned processes."""
import os
from pathlib import Path

from tools import launch_phase3_debugger as launcher


def _fake_process(tmp_path: Path, *, pid: int = 4242, state: str = "S",
                  config_env: Path | None = None):
    proc_root = tmp_path / "proc"
    proc = proc_root / str(pid)
    (proc / "fd").mkdir(parents=True)
    binary = tmp_path / "duckstation-qt"
    binary.write_bytes(b"binary")
    config = tmp_path / "config"
    (config / "runtime").mkdir(parents=True)
    log = config / "console.log"
    log.write_text("owned")
    (proc / "exe").symlink_to(binary)
    (proc / "fd/1").symlink_to(log)
    env_config = config if config_env is None else config_env
    environment = (f"XDG_CONFIG_HOME={env_config}\0"
                   f"XDG_RUNTIME_DIR={env_config / 'runtime'}\0")
    (proc / "environ").write_bytes(environment.encode())
    (proc / "stat").write_text(f"{pid} (duckstation-qt) {state} 1 1 1\n")
    return proc_root, config, binary, pid


def test_exact_config_executable_environment_and_fd_identify_one_owner(tmp_path):
    proc_root, config, binary, pid = _fake_process(tmp_path)
    assert launcher.owned_processes(
        config, binary, proc_root=proc_root) == [pid]


def test_same_binary_with_wrong_xdg_environment_is_not_adopted(tmp_path):
    wrong = tmp_path / "wrong-config"
    (wrong / "runtime").mkdir(parents=True)
    proc_root, config, binary, _ = _fake_process(
        tmp_path, config_env=wrong)
    assert launcher.owned_processes(config, binary, proc_root=proc_root) == []


def test_zombie_is_stopped_even_before_proc_reaping(tmp_path):
    proc_root, _, _, pid = _fake_process(tmp_path, state="Z")
    assert launcher.process_state(pid, proc_root=proc_root) == "Z"
    assert launcher.process_stopped(pid, proc_root=proc_root) is True
    os.unlink(proc_root / str(pid) / "stat")
    assert launcher.process_stopped(pid, proc_root=proc_root) is True
