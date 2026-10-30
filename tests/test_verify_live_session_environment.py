"""Guards for exact Phase-3 DuckStation binary/settings declarations."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.verify_live_session_environment import verify_environment


def _fixture(tmp_path: Path, settings: str) -> tuple[Path, Path, str]:
    config = tmp_path / "isolated"
    (config / "duckstation").mkdir(parents=True)
    (config / "duckstation/settings.ini").write_text(settings)
    binary = tmp_path / "duckstation-qt"
    binary.write_bytes(b"pinned debugger binary")
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    return config, binary, digest


def test_generic_profile_resolves_timing_keys_from_the_pinned_binary(tmp_path):
    config, binary, digest = _fixture(tmp_path, """
[BIOS]
SearchDirectory=/operator/bios
[ExternalDebugger]
Enabled=true
Port=24901
BindAddress=127.0.0.1
AuthToken=redacted
""")
    result = verify_environment(
        config_dir=config, binary=binary, binary_sha256=digest,
        port=24901, profile="isolated-defaults-v1")
    assert result["effective"]["CPU.ExecutionMode"] == {
        "value": "Recompiler", "source": "pinned_binary_default"}
    assert result["effective"]["CDROM.ReadSpeedup"]["value"] == "1"
    assert result["effective"]["Main.RewindEnable"]["value"] == "false"


def test_movie_profile_rejects_a_timing_override(tmp_path):
    config, binary, digest = _fixture(tmp_path, """
[BIOS]
SearchDirectory=/operator/bios
PatchFastBoot=false
[CPU]
ExecutionMode=CachedInterpreter
OverclockEnable=true
[Console]
Region=Auto
Enable8MBRAM=false
[Pad1]
Type=AnalogController
[ExternalDebugger]
Enabled=true
Port=24902
BindAddress=127.0.0.1
""")
    with pytest.raises(SystemExit, match="CPU.OverclockEnable"):
        verify_environment(
            config_dir=config, binary=binary, binary_sha256=digest,
            port=24902, profile="movie-replay-v1")
