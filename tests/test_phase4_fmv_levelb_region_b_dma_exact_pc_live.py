from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_exact_pc_live as live  # noqa: E402


RUNTIME = ROOT / "config/phase4_fmv_levelb_region_b_dma_exact_pc_runtime.yaml"


def test_runtime_is_closed_and_exact_plan_joined():
    runtime = live.load_runtime(RUNTIME)
    plan = live.exact_plan(runtime)
    assert runtime["observer_plan"]["direct_command_plan"] == plan
    assert runtime["atomic_anchor"]["target_frame"] == 15816
    assert runtime["execution"]["capture_window"] == {
        "clock": "emulator_frame",
        "start": 15816,
        "stop": 15880,
        "stop_inclusive": False,
    }
    assert [row["control_role"] for row in runtime["variants"]] == [
        "positive", "negative",
    ]


def test_atomic_request_is_one_uninstrumented_cold_boot_anchor():
    runtime = live.load_runtime(RUNTIME)
    request = live._batch_request(runtime)
    assert request["continue_on_error"] is False
    assert len(request["jobs"]) == 1
    [job] = request["jobs"]
    assert job["recipe"] == "bootAndRun"
    assert job["instrumentation"] == []
    assert job["run"] == {"frames": 15815}
    assert job["movie"] == {
        "path": str((ROOT / "movies/100% Runs/LEVEL01.movie.json").resolve()),
    }
    assert Path(job["movie"]["path"]).is_absolute()
    assert job["expected_media"]["tracks"] == runtime["expected_media"]["tracks"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda doc: doc["atomic_anchor"].update(target_frame=15815),
            "atomic anchor",
        ),
        (
            lambda doc: doc["observer_plan"].update(
                schema="abl-phase4-observer-plan/1"),
            "observer plan",
        ),
        (
            lambda doc: doc["variants"][1].update(control_role="positive"),
            "variants",
        ),
    ],
)
def test_runtime_mutations_fail_closed(tmp_path, mutation, message):
    original = live.yaml.safe_load(RUNTIME.read_text())
    changed = copy.deepcopy(original)
    mutation(changed)
    changed_path = tmp_path / "runtime.yaml"
    changed_path.write_text(live.yaml.safe_dump(changed, sort_keys=False))
    with pytest.raises(ValueError, match=message):
        live.load_runtime(changed_path)
