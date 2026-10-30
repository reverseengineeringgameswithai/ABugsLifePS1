"""Falsifiable guards for the Phase-4 movie-ready work-order policy."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_movie_priority as priority  # noqa: E402
import phase4_scheduler_policy as scheduler  # noqa: E402


CONTROLLER = ROOT / "tools/flik_phase4_method_ratchet.sh"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sources() -> dict:
    return {
        "policy": common.load_yaml(priority.POLICY_PATH),
        "debt": load(priority.DEBT_PATH),
        "offline": load(priority.OFFLINE_PATH),
        "fixture_audit": load(priority.FIXTURE_AUDIT_PATH),
        "fixture_set": load(priority.FIXTURE_SET_PATH),
        "movie_inventory": load(priority.MOVIE_INVENTORY_PATH),
        "capsule": load(priority.CAPSULE_PATH),
        "derived": load(priority.DERIVED_PATH),
        "ownership": load(priority.OWNERSHIP_PATH),
    }


@pytest.fixture(scope="module")
def document() -> dict:
    return load(priority.OUTPUT)


def rebuild(sources: dict, **changes: dict) -> dict:
    inputs = {key: deepcopy(value) for key, value in sources.items()}
    inputs.update(changes)
    return priority.build(**inputs)


def row(document: dict, row_id: str) -> dict:
    return next(item for item in document["rows"] if item["row_id"] == row_id)


def test_retained_queue_recomputes_all_rows_and_current_eligibility(document):
    expected = priority.build()
    assert priority.validate_retained(document, expected) == []
    assert document["schema"] == priority.SCHEMA
    assert document["selection_policy"] == "movie-ready"
    assert document["valid"] is True
    assert document["errors"] == []
    assert len(document["rows"]) == len({
        item["row_id"] for item in document["rows"]}) == \
        len(common.baseline_rows()) == 107
    assert document["counts"]["eligible"] == sum(
        item["eligibility"]["eligible"] for item in document["rows"])
    assert document["counts"]["selectable"] == sum(
        item["selection"]["selectable"] for item in document["rows"])
    assert document["counts"]["eligible"] > 0
    assert all(
        item["eligibility"]["requirements"]["remaining_debt_positive"]
        for item in document["rows"] if item["eligibility"]["eligible"])


def test_completed_rows_cannot_reenter_and_completion_label_is_not_trusted(
        sources, document):
    for row_id in ("A04_kick", "A16_swinging"):
        target = row(document, row_id)
        assert target["derived_remaining"] == 0
        assert target["eligibility"]["eligible"] is False

    debt = deepcopy(sources["debt"])
    target = next(item for item in debt["rows"]
                  if item["row_id"] == "A04_kick")
    target["completion_state"] = "open"
    mutated = rebuild(sources, debt=debt)
    assert mutated["valid"] is True
    assert row(mutated, "A04_kick")["eligibility"]["eligible"] is False
    c15 = row(document, "C15_checkpoints")
    assert "Safe respawn anchor" in c15["name"]
    assert "no player-facing checkpoint mechanic" in c15["name"]


def test_every_eligible_row_has_exact_verified_movie_and_start_state(document):
    fixture = load(priority.FIXTURE_SET_PATH)["entries"]
    for item in document["rows"]:
        if not item["eligibility"]["eligible"]:
            continue
        assert item["movie_anchors"]
        for anchor in item["movie_anchors"]:
            assert anchor["verified"] is True
            for kind in ("movie", "start_state"):
                pinned = anchor[kind]
                assert pinned["path"].startswith("movies/Phase4/")
                assert pinned["central_pin_verified"] is True
                assert pinned["preservation_required"] is True
                assert fixture[pinned["path"]]["sha256"] == pinned["sha256"]
                assert common.sha256(ROOT / pinned["path"]) == pinned["sha256"]


def test_movie_pin_and_start_state_pin_mutations_invalidate_generation(sources,
                                                                     document):
    anchor = next(item for item in document["rows"]
                  if item["eligibility"]["eligible"])["movie_anchors"][0]
    for kind in ("movie", "start_state"):
        fixture_set = deepcopy(sources["fixture_set"])
        path = anchor[kind]["path"]
        fixture_set["entries"][path]["sha256"] = "0" * 64
        mutated = rebuild(sources, fixture_set=fixture_set)
        assert mutated["valid"] is False
        assert any(path in error for error in mutated["errors"])


def test_capsule_manifest_without_exact_payload_tree_is_rejected(
        sources, tmp_path):
    capsule = deepcopy(sources["capsule"]["capsules"][0])
    original = Path(capsule["capsule_directory"]) / "manifest.json"
    fake = tmp_path / "capsule"
    fake.mkdir()
    (fake / "manifest.json").write_bytes(original.read_bytes())
    capsule["capsule_directory"] = str(fake)
    start = capsule["start_state"]
    result, errors = priority._capsule_status(
        capsule, capsule["movie"], capsule["movie_sha256"], start["path"],
        start["sha256"], {})
    assert errors
    assert any("payload" in error or "tree" in error for error in errors)
    assert result["preservation_verified"] is False
    assert result["verified_domains"] == []
    assert result["independent_control_verified"] is False


def test_capsule_positive_result_is_not_reused_after_payload_drift(tmp_path):
    directory = tmp_path / "capsule"
    payload = directory / "chunks/0.bin"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"exact capsule payload")
    payload_sha = hashlib.sha256(payload.read_bytes()).hexdigest()
    tree = hashlib.sha256()
    tree.update(b"chunks/0.bin\0")
    tree.update(payload_sha.encode())
    tree.update(b"\0")
    fingerprint = {
        "registers_sha256": "1" * 64,
        "ram_sha256": "2" * 64,
        "vram_sha256": "3" * 64,
        "spu_ram_sha256": "4" * 64,
    }
    manifest_doc = {
        "complete": True,
        "capture": {"status": {
            "complete": True,
            "truncated": False,
            "error": "",
            "blocks": 1,
            "checkpoints": [],
        }},
        "control": {
            "capsule_fingerprint": fingerprint,
            "control_fingerprint": deepcopy(fingerprint),
            "mismatches": {},
        },
        "files": [{
            "path": "chunks/0.bin",
            "sha256": payload_sha,
            "bytes": payload.stat().st_size,
        }],
    }
    manifest = directory / "manifest.json"
    manifest.write_text(json.dumps(manifest_doc), encoding="utf-8")
    capsule = {
        "capsule_directory": str(directory),
        "capsule_manifest_sha256": common.sha256(manifest),
        "capsule_tree_sha256": tree.hexdigest(),
        "capsule_file_count": 1,
        "capsule_bytes": payload.stat().st_size,
        "preservation_required": True,
        "movie": "movies/Phase4/test.pxm",
        "movie_sha256": "5" * 64,
        "start_state": {
            "path": "movies/Phase4/test.state",
            "sha256": "6" * 64,
        },
        "control_match": True,
        "frames": 1,
    }
    cache = {}
    first, first_errors = priority._capsule_status(
        capsule, capsule["movie"], capsule["movie_sha256"],
        capsule["start_state"]["path"],
        capsule["start_state"]["sha256"], cache)
    assert first_errors == []
    assert first["preservation_verified"] is True

    payload.unlink()
    second, second_errors = priority._capsule_status(
        capsule, capsule["movie"], capsule["movie_sha256"],
        capsule["start_state"]["path"],
        capsule["start_state"]["sha256"], cache)
    assert second_errors
    assert second["preservation_verified"] is False
    assert second["verified_domains"] == []
    assert second["independent_control_verified"] is False


def test_queue_authority_fingerprint_tracks_derived_index_payload(tmp_path):
    external = tmp_path / "derived-index.json"
    external.write_bytes(b"synthetic derived index")
    documents = {
        "fixture_set": {"entries": {}},
        "movie_inventory": {"files": []},
        "capsule": {"capsules": []},
        "derived": {"external_indexes": [{
            "absolute_path": str(external),
        }]},
    }
    before = priority.authority_runtime_fingerprint(
        documents["fixture_set"], documents["movie_inventory"],
        documents["capsule"], documents["derived"])
    external.unlink()
    after = priority.authority_runtime_fingerprint(
        documents["fixture_set"], documents["movie_inventory"],
        documents["capsule"], documents["derived"])
    assert before != after


def test_dimension_leaf_mutation_cannot_hide_behind_authored_counts(sources):
    debt = deepcopy(sources["debt"])
    target = next(item for item in debt["rows"]
                  if item["row_id"] == "A04_kick")
    dimension = next(iter(target["dimensions"].values()))
    dimension["state"] = "gap"
    mutated = rebuild(sources, debt=debt)
    assert mutated["valid"] is False
    assert any(
        "A04_kick: authored remaining count disagrees" in error
        for error in mutated["errors"])


def test_e15_is_deferred_until_other_movie_ready_work_is_exhausted(
        sources, document):
    e15 = row(document, "E15_fmv")
    assert e15["eligibility"]["eligible"] is True
    assert e15["selection"]["deferred"] is True
    assert e15["selection"]["selectable"] is False
    assert document["counts"]["selectable"] > 0

    policy = deepcopy(sources["policy"])
    policy["defer_while_other_eligible"] = []
    mutated = rebuild(sources, policy=policy)
    assert mutated["valid"] is False
    assert any("defer exactly E15_fmv" in error for error in mutated["errors"])


def test_scores_are_auditable_and_movie_quantity_adds_no_points(document):
    maxima = {
        key: value["maximum"]
        for key, value in next(item for item in document["rows"]
                               if item["score"])["score"]["components"].items()
    }
    assert list(document["score_component_order"]) == \
        list(priority.EXPECTED_SCORE_COMPONENTS)
    for item in document["rows"]:
        if item["score"] is None:
            continue
        components = item["score"]["components"]
        assert set(components) == set(priority.EXPECTED_SCORE_COMPONENTS)
        assert item["score"]["total"] == sum(
            components[key]["points"]
            for key in document["score_component_order"])
        assert all(0 <= components[key]["points"] <= maxima[key]
                   for key in components)
        controls = components["control_quality"]
        assert "movie_count_not_scored" in controls["inputs"]
        assert "movie quantity" in \
            components["retained_evidence"]["rationale"]


def test_score_input_mutation_changes_regeneration_and_fails_retained_guard(
        sources, document):
    target = next(
        item for item in document["rows"]
        if item["eligibility"]["eligible"]
        and item["score"]["components"]["static_ownership"]["points"]
        < item["score"]["components"]["static_ownership"]["maximum"])
    ownership = deepcopy(sources["ownership"])
    ownership["rows"][target["row_id"]].setdefault("functions", []).append({
        "function_start": "0x8ffff000",
        "name": "mutation_only_score_input",
    })
    mutated = rebuild(sources, ownership=ownership)
    assert mutated["valid"] is True
    assert row(mutated, target["row_id"])["score"] != target["score"]
    assert priority.validate_retained(document, mutated) == [
        "retained movie-priority artifact differs from regeneration"]


def test_candidate_batches_are_small_coherent_and_selected_batch_is_guarded(
        document):
    assert document["candidate_batches"]
    for batch in document["candidate_batches"]:
        assert 1 <= len(batch["rows"]) <= 3
        if len(batch["rows"]) > 1:
            assert all(
                item["reasons"] for item in batch["coupling"])
        assert "movie-ready:" in batch["batch_id"]

    mutated = deepcopy(document)
    mutated["selected_batch"]["rows"] = ["E15_fmv"]
    assert "retained movie-priority artifact differs from regeneration" in \
        priority.validate_retained(mutated, document)


def test_one_no_reduction_iteration_rotates_to_a_disjoint_batch(document):
    first = priority.packet(document)
    before = load(priority.DEBT_PATH)
    before["scheduler"]["selected_campaigns"] = [{
        "campaign_id": first["selected_batch"]["batch_id"],
        "rows": deepcopy(first["selected_batch"]["rows"]),
    }]
    before_raw = scheduler.json_bytes(before)
    after_raw = scheduler.json_bytes(deepcopy(before))
    no_reduction = scheduler.derive_progress(before_raw, after_raw, 1)
    rotated = priority.packet(
        document, first, no_reduction, document, before_raw, after_raw)
    assert rotated["rotation"] == {
        "required": True,
        "applied": True,
        "reason": (
            "Previous completed executor iteration reduced no row or dimension "
            "debt; reviewed policy rotates to a disjoint batch."),
    }
    assert set(first["selected_batch"]["rows"]).isdisjoint(
        rotated["selected_batch"]["rows"])
    reduced_after = deepcopy(before)
    target = next(item for item in reduced_after["rows"]
                  if item["row_id"] == first["selected_batch"]["rows"][0])
    dimension = next(name for name, detail in target["dimensions"].items()
                     if detail["state"] in {"gap", "partial"})
    target["dimensions"][dimension]["state"] = "met"
    states = [detail["state"] for detail in target["dimensions"].values()]
    target["counts"] = {
        "met": states.count("met"),
        "not_applicable": 0,
        "remaining": states.count("gap") + states.count("partial"),
    }
    reduced_after["counts"]["dimensions"] = {
        state: sum(
            detail["state"] == state for item in reduced_after["rows"]
            for detail in item["dimensions"].values())
        for state in ("gap", "partial", "met")
    }
    reduced_after_raw = scheduler.json_bytes(reduced_after)
    reduced_progress = scheduler.derive_progress(
        before_raw, reduced_after_raw, 1)
    reduced = priority.packet(
        document, first, reduced_progress, document, before_raw,
        reduced_after_raw)
    assert reduced["rotation"]["required"] is False
    assert reduced["selected_batch"] == document["candidate_batches"][0]


def controller_contract_errors(source: str) -> list[str]:
    errors = []
    required = {
        "default": 'SELECTION_POLICY="closure-debt"',
        "CLI": "closure-debt|movie-ready",
        "detached": 'child=("$SCRIPT_PATH" --internal-run "$@")',
        "dry-run": (
            "dry run passed with selection policy $SELECTION_POLICY"),
        "metadata": '"selection_policy": "$SELECTION_POLICY"',
        "packet prompt": "authoritative generated work packet",
        "phase": '"phase": {"type": "integer", "const": 4}',
    }
    for label, fragment in required.items():
        if fragment not in source:
            errors.append(f"missing {label} propagation")

    reseed = source[source.index("automatic_reseed()"):
                    source.index("stop_requested_at_boundary()")]
    for fragment in (
        '--selection-policy "$SELECTION_POLICY"',
        '--previous-movie-ready-packet "$packet"',
        '--previous-movie-ready-progress "$progress"',
        '--previous-movie-ready-queue "$queue"',
        '--previous-movie-ready-debt-before "$debt_before"',
        '--previous-movie-ready-debt-after "$debt_after"',
    ):
        if fragment not in reseed:
            errors.append(f"automatic reseed loses {fragment}")
    if "movie-ready automatic reseed requires the complete five-snapshot" not in reseed:
        errors.append("automatic reseed does not fail closed on missing snapshots")
    prepare = source[source.index("prepare_movie_ready_packet()"):
                     source.index("phase4_progress_record()")]
    if "movie-ready continuation is missing a required prior snapshot" not in prepare:
        errors.append("normal continuation does not fail closed on missing snapshots")

    loop = source[source.index("for ((iteration = 1;"):]
    cadence = (
        'if [[ "$SELECTION_POLICY" == "movie-ready" ]] || \\\n'
        '       [[ "$row_transitions"')
    if cadence not in loop:
        errors.append("movie-ready open iteration does not force campaign verifier")
    if ('if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then\n'
            '    if ! run_campaign_verifier' not in loop):
        errors.append("movie-ready terminal claim does not run campaign verifier")
    if "exact gaps feed the next executor" not in loop:
        errors.append("campaign verifier gaps are not handed forward")
    return errors


def test_controller_threads_movie_ready_through_every_continuation():
    source = CONTROLLER.read_text(encoding="utf-8")
    assert controller_contract_errors(source) == []
    assert "--selection-policy movie-ready" in source
    assert "rotation required but no disjoint batch remains" not in source
    assert 'phase4_scheduler_policy.py" \\' in source
    assert '--derive-progress --before "$before" --after "$after"' in source
    assert '--previous-queue "$previous_queue"' in source
    assert '--previous-debt-before "$previous_debt_before"' in source
    assert '--previous-debt-after "$previous_debt_after"' in source


def test_controller_policy_propagation_and_verifier_cadence_are_mutation_guarded():
    source = CONTROLLER.read_text(encoding="utf-8")
    reseed_fragment = '--selection-policy "$SELECTION_POLICY"'
    reseed_start = source.index("automatic_reseed()")
    reseed_end = source.index("stop_requested_at_boundary()")
    mutated_reseed = (
        source[:reseed_start]
        + source[reseed_start:reseed_end].replace(
            reseed_fragment, "--phase-only", 1)
        + source[reseed_end:]
    )
    assert any("automatic reseed loses" in error
               for error in controller_contract_errors(mutated_reseed))

    mutated_missing = source.replace(
        "movie-ready automatic reseed requires the complete five-snapshot",
        "movie-ready reseed silently resets to genesis", 1)
    assert "automatic reseed does not fail closed on missing snapshots" in \
        controller_contract_errors(mutated_missing)

    cadence = (
        'if [[ "$SELECTION_POLICY" == "movie-ready" ]] || \\\n'
        '       [[ "$row_transitions"')
    mutated_cadence = source.replace(
        cadence,
        'if [[ "$row_transitions" != "[]" ]] || \\\n'
        '       [[ "$row_transitions"',
        1,
    )
    assert "movie-ready open iteration does not force campaign verifier" in \
        controller_contract_errors(mutated_cadence)
