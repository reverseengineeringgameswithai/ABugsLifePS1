import importlib.util
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "analysis/phase4_f01_oracle_breadth_verification.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


VERIFY = load_module(
    ROOT / "tools/phase4_f01_oracle_breadth_verification.py",
    "phase4_f01_oracle_breadth_verification",
)
BREADTH = load_module(
    ROOT / "tools/phase4_f01_breadth_assert.py",
    "phase4_f01_breadth_assert",
)
EVIDENCE = load_module(
    ROOT / "tools/phase4_f01_evidence.py",
    "phase4_f01_evidence",
)


def consolidate(tmp_path: Path, rows: list[dict]):
    results = tmp_path / "results"
    results.mkdir()
    for index, row in enumerate(rows):
        (results / f"row-{index}.json").write_text(json.dumps(row))
    out = tmp_path / "out.json"
    rc = BREADTH.consolidate(SimpleNamespace(workdir=str(tmp_path), out=str(out)))
    return rc, json.loads(out.read_text())


def valid_decision() -> dict:
    return {
        "frame": 100,
        "cycle": 1000,
        "request": 1,
        "gp4c4": 0,
        "law_predicts_finalizer": True,
        "finalizer_observed": True,
        "delta_cycles": 28,
        "law_holds": True,
        "self_certification": {
            "pc": "0x8004FF28",
            "instruction_word": BREADTH.DECISION_IMAGE_WORD,
            "pristine_instruction_word": BREADTH.DECISION_IMAGE_WORD,
            "passed": True,
        },
    }


def valid_breadth_rows() -> list[dict]:
    rows = []
    for level in sorted(BREADTH.DECLARED_LEVELS):
        envelope = BREADTH.declared_fixture_envelopes()[level]
        rows.append({
            "level": level,
            "movie": envelope["movie"],
            "movie_sha256": envelope["movie_sha256"],
            "movie_size": envelope["movie_size"],
            "start_state": {
                "identity": envelope["state"],
                "sha256": envelope["state_sha256"],
            },
            "frames": envelope["frames"],
            "from_boot": False,
            "runtime": {
                "execution_mode": "Interpreter",
                "media": valid_media_identity(),
            },
            "reproducible": True,
            "playback_completed": True,
            "exec_trace": {"total": 3, "returned": 3, "truncated": False},
            "exec_trace_truncated": False,
            "counts": {"consumer": 1, "decisions": 1, "finalizer": 1},
            "preload_rejected": {"consumer": 0, "decision": 0, "finalizer": 0},
            "decisions": [valid_decision()],
            "law_failures": [],
            "law_holds_for_every_decision": True,
        })
    return rows


def valid_media_identity() -> dict:
    return {
        "has_media": True,
        "serial": EVIDENCE.PRISTINE_SERIAL,
        "title": EVIDENCE.PRISTINE_TITLE,
        "cue": {"identity": EVIDENCE.PRISTINE_CUE_NAME,
                "sha256": EVIDENCE.PRISTINE_CUE_SHA256},
        "track": {"identity": EVIDENCE.PRISTINE_BIN_NAME,
                  "sha256": EVIDENCE.PRISTINE_BIN_SHA256},
        "executable": {"identity": EVIDENCE.PRISTINE_EXE_NAME,
                       "sha256": EVIDENCE.PRISTINE_EXE_SHA256},
    }


def valid_oracle_envelope() -> dict:
    movie_identity = (
        "movies/Phase4/Interpreter/Any% Runs/"
        "LEVEL01_AntHill_FromBoot.movie.json"
    )
    return {
        "movie_identity": movie_identity,
        "movie_doc": {
            "game_serial": EVIDENCE.PRISTINE_SERIAL,
            "start_state": {
                "from_boot": True,
                "path": "",
                "file_size": 0,
                "sha256": None,
                "loaded_before_recording": False,
                "reproducible_only_from_state": False,
                "game_serial": EVIDENCE.PRISTINE_SERIAL,
            },
        },
        "movie_sha256": (
            "b29ae83945aaea1d59c03095867376130a3ac3eefcf4b6042a2c36b8369e2e24"
        ),
        "movie_size": 5062842,
        "central_pin": {
            "sha256": (
                "b29ae83945aaea1d59c03095867376130a3ac3eefcf4b6042a2c36b8369e2e24"
            ),
            "size": 5062842,
            "media_class": "pristine_serial",
            "preservation_required": True,
        },
        "media_identity": valid_media_identity(),
        "trace_truncated": False,
        "playback_reproducible": True,
        "playback_completed": True,
        "declared_identities": {movie_identity},
    }


def failed_oracle_checks(kwargs: dict) -> set[str]:
    return {
        row["id"] for row in EVIDENCE.oracle_provenance_checks(**kwargs)
        if not row["passed"]
    }


def test_offline_adjudication_recomputes_exactly():
    retained = json.loads(VERDICT.read_text())
    assert retained["offline_recomputed"] == VERIFY.build_offline()


def test_preserved_absolute_save_identity_is_checkout_independent():
    breadth = json.loads((ROOT / "analysis/phase4_f01_breadth_assertions.json").read_text())
    first = next(iter(breadth["results"].values()))
    movie = json.loads((ROOT / first["movie"]).read_text())
    recorded = movie["start_state"]["path"]
    fixtures = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text()
    )["entries"]
    identity = VERIFY.external_identity(recorded, set(fixtures))
    assert identity.startswith("movies/")
    assert identity in fixtures
    assert VERIFY.provisioned_path(identity) == ROOT / identity


def test_all_six_formal_oracle_assertions_reject_adverse_mutations():
    offline = VERIFY.build_offline()["original_oracle"]
    assert offline["formal_assertions_passing"] == offline["formal_assertions"] == 6
    assert offline["formal_mutations_rejected"] == 6


def test_historical_oracle_verdict_names_every_repair_gap():
    offline = json.loads(VERDICT.read_text())["offline_recomputed"]["original_oracle"]
    receipt = json.loads(VERDICT.read_text())
    verdict = receipt["dimensions"]["original_oracle"]
    assert offline["movie_metadata_from_boot"] is True
    assert offline["generator_derives_from_boot_from_movie"] is False
    assert offline["generator_gates_trace_truncation"] is False
    assert offline["movie_central_pin_present"] is False
    assert offline["natural_request_values"] == [1]
    assert offline["prior_request2_witness_is_injected"] is True
    assert receipt["offline_recomputed"]["source_shape_witnesses"][
        "oracle_media_path_is_not_normalized"
    ] is True
    assert receipt["replay_verification"]["original_oracle"]["byte_identical"] is False
    assert verdict["verdict"] == "NOT MET"
    assert {gap["id"] for gap in verdict["missing_elements"]} >= {
        "natural_request2_skip_control",
        "fail_closed_oracle_provenance",
        "fresh_detached_oracle_regeneration",
    }


def test_repaired_breadth_consolidator_rejects_an_empty_corpus(tmp_path):
    rc, doc = consolidate(tmp_path, [])
    assert rc == 1
    assert doc["levels_asserted"] == 0
    assert doc["law_holds_everywhere"] is False


def test_repaired_breadth_consolidator_rejects_zero_decisions(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["counts"]["decisions"] = 0
    rows[0]["decisions"] = []
    rows[0]["law_holds_for_every_decision"] = False
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["law_holds_everywhere"] is False


def test_repaired_breadth_consolidator_rejects_truncation(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["exec_trace_truncated"] = True
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["law_holds_everywhere"] is False


def test_repaired_breadth_consolidator_accepts_only_the_valid_exact_corpus(tmp_path):
    rc, doc = consolidate(tmp_path, valid_breadth_rows())
    assert rc == 0
    assert doc["levels_asserted"] == 19
    assert doc["total_decisions_checked"] == 19
    assert doc["law_holds_everywhere"] is True
    assert all(row["passed"] for row in doc["corpus_gate"])


def test_repaired_breadth_consolidator_rejects_missing_level(tmp_path):
    rows = valid_breadth_rows()[:-1]
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["corpus_gate"][0]["passed"] is False


def test_repaired_breadth_consolidator_rejects_extra_level(tmp_path):
    rows = valid_breadth_rows()
    extra = copy.deepcopy(rows[0])
    extra["level"] = "LEVEL99_OUT_OF_UNIVERSE"
    rows.append(extra)
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["corpus_gate"][0]["passed"] is False


def test_repaired_breadth_consolidator_rejects_duplicate_or_renamed_level(tmp_path):
    rows = valid_breadth_rows()
    rows[-1]["level"] = rows[0]["level"]
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["corpus_gate"][0]["passed"] is False
    assert doc["corpus_gate"][0]["detail"]["duplicates"]


def test_repaired_breadth_consolidator_rejects_missing_certificate(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["decisions"][0]["self_certification"].pop("instruction_word")
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["law_holds_everywhere"] is False


def test_repaired_breadth_consolidator_rejects_mismatched_certificate(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["decisions"][0]["self_certification"]["instruction_word"] = "0x00000000"
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["law_holds_everywhere"] is False


def test_repaired_breadth_consolidator_rejects_missing_branch_operands(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["decisions"][0].pop("request")
    rows[0]["decisions"][0].pop("gp4c4")
    rows[0]["decisions"][0]["law_predicts_finalizer"] = False
    rows[0]["decisions"][0]["finalizer_observed"] = False
    rows[0]["decisions"][0]["delta_cycles"] = None
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert any("captured" in failure for failure in doc["law_failures"])


def test_repaired_breadth_consolidator_rejects_missing_trace_coordinates(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["decisions"][0]["cycle"] = None
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert any("coordinates" in failure for failure in doc["law_failures"])


def test_repaired_breadth_consolidator_rejects_boolean_cycle_delta(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["decisions"][0]["delta_cycles"] = True
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert any("cycle attribution" in failure for failure in doc["law_failures"])


def test_repaired_breadth_consolidator_derives_hidden_law_failure(tmp_path):
    rows = valid_breadth_rows()
    decision = rows[0]["decisions"][0]
    decision["finalizer_observed"] = False
    decision["delta_cycles"] = None
    # Deliberately retain every submitted summary as a lie.  The gate must derive
    # failure from request/gp/observation rather than trust these fields.
    decision["law_holds"] = True
    rows[0]["law_failures"] = []
    rows[0]["law_holds_for_every_decision"] = True
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    assert doc["law_failures"]


def test_repaired_breadth_consolidator_rejects_error_or_incomplete_playback(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["error"] = "mutated early stop"
    rows[1]["playback_completed"] = False
    rows[2]["reproducible"] = False
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    by_id = {row["id"]: row for row in doc["corpus_gate"]}
    assert by_id["zero_errors"]["passed"] is False
    assert by_id["all_playbacks_reproducible_and_completed"]["passed"] is False


def test_repaired_breadth_consolidator_rejects_unknown_truncation(tmp_path):
    rows = valid_breadth_rows()
    rows[0]["exec_trace_truncated"] = None
    rows[1].pop("exec_trace_truncated")
    rc, doc = consolidate(tmp_path, rows)
    assert rc == 1
    by_id = {row["id"]: row for row in doc["corpus_gate"]}
    assert by_id["all_exec_traces_nontruncated"]["passed"] is False


def test_repaired_breadth_consolidator_rejects_fixture_runtime_and_page_mutations(tmp_path):
    mutations = (
        lambda row: row.__setitem__("movie_sha256", "0" * 64),
        lambda row: row["start_state"].__setitem__("sha256", "0" * 64),
        lambda row: row["runtime"].__setitem__("execution_mode", "CachedInterpreter"),
        lambda row: row["runtime"]["media"]["track"].__setitem__("sha256", "0" * 64),
        lambda row: row["exec_trace"].__setitem__("returned", 2),
        lambda row: row["exec_trace"].update({"total": 4, "returned": 4}),
        lambda row: row.pop("counts"),
        lambda row: row.pop("preload_rejected"),
    )
    for index, mutate in enumerate(mutations):
        rows = valid_breadth_rows()
        mutate(rows[0])
        case_path = tmp_path / str(index)
        case_path.mkdir()
        rc, doc = consolidate(case_path, rows)
        assert rc == 1
        gate = next(
            row for row in doc["corpus_gate"]
            if row["id"] == "all_fixture_and_runtime_provenance_exact"
        )
        assert gate["passed"] is False


def test_valid_breadth_rows_use_the_exact_producer_count_schema():
    for row in valid_breadth_rows():
        assert set(row["counts"]) == {"consumer", "decisions", "finalizer"}
        assert set(row["preload_rejected"]) == {"consumer", "decision", "finalizer"}


def test_oracle_provenance_accepts_the_exact_complete_envelope():
    assert failed_oracle_checks(valid_oracle_envelope()) == set()


# 2026-08-10 fresh-verifier re-pin: `consumers` gained
# analysis/phase2_fixture_audit.json when the fixture audit was regenerated at
# commit 7c85a8a to register the natural-death movie -- a machinery-derived
# field change (the audit genuinely references this movie; the same consumer
# appears on every audited entry), not a hand edit. Exact-entry pinning kept
# deliberately: any future drift in this entry must fail here and be re-pinned
# intentionally.
def test_oracle_movie_is_centrally_pinned_without_committing_its_bytes():
    envelope = valid_oracle_envelope()
    entries = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text()
    )["entries"]
    assert entries[envelope["movie_identity"]] == {
        **envelope["central_pin"],
        "consumers": [
            "analysis/phase2_fixture_audit.json",
            "analysis/phase4_f01_original_oracle.json",
        ],
        "generator_references": [
            "tools/knowledge_closure_audit.py",
            "tools/phase4_f01_original_oracle.py",
        ],
        "capture_origin": "repo_generator_or_replay_tool",
        "copyrighted_or_operator_owned": True,
    }


def test_natural_death_movie_is_centrally_pinned_without_committing_its_bytes():
    entries = json.loads(
        (ROOT / "analysis/phase0_2_external_fixture_set.json").read_text()
    )["entries"]
    assert entries[
        "movies/Phase4/Interpreter/F01_natural_death_FromBoot.movie.json"
    ] == {
        "sha256": (
            "766a7a87892b56b6ed916a9e96561cfe0410805becfb8c62d30670d2677fd0b8"
        ),
        "size": 4678121,
        "media_class": "pristine_serial",
        "consumers": ["analysis/phase2_fixture_audit.json"],
        "generator_references": ["tools/phase4_f01_request2_probe.py"],
        "capture_origin": "repo_generator_or_replay_tool",
        "preservation_required": True,
        "copyrighted_or_operator_owned": True,
    }


def test_oracle_provenance_rejects_anchor_metadata_mutations():
    mutations = {
        "movie_metadata_from_boot": ("from_boot", False),
        "movie_metadata_start_path_empty": ("path", "mutated.sav"),
        "movie_metadata_start_size_zero": ("file_size", 1),
        "movie_metadata_start_hash_absent": ("sha256", "f" * 64),
        "movie_metadata_not_loaded_before_recording": ("loaded_before_recording", True),
        "movie_metadata_not_state_only": ("reproducible_only_from_state", True),
    }
    for expected_id, (field, value) in mutations.items():
        envelope = valid_oracle_envelope()
        envelope["movie_doc"]["start_state"][field] = value
        assert expected_id in failed_oracle_checks(envelope)


def test_oracle_provenance_rejects_movie_pin_hash_and_size_mutations():
    for field, expected_id in (
        ("sha256", "movie_hash_matches_central_pin"),
        ("size", "movie_size_matches_central_pin"),
    ):
        envelope = valid_oracle_envelope()
        envelope["central_pin"][field] = 0 if field == "size" else "0" * 64
        assert expected_id in failed_oracle_checks(envelope)


def test_oracle_provenance_rejects_declaration_and_central_pin_mutations():
    envelope = valid_oracle_envelope()
    envelope["declared_identities"] = set()
    assert "movie_identity_declared" in failed_oracle_checks(envelope)

    envelope = valid_oracle_envelope()
    envelope["central_pin"] = None
    failures = failed_oracle_checks(envelope)
    assert {
        "movie_hash_matches_central_pin",
        "movie_size_matches_central_pin",
        "movie_media_class_is_pristine",
        "movie_preservation_required",
    } <= failures

    for field, value, expected_id in (
        ("media_class", "non_pristine", "movie_media_class_is_pristine"),
        ("preservation_required", False, "movie_preservation_required"),
    ):
        envelope = valid_oracle_envelope()
        envelope["central_pin"][field] = value
        assert expected_id in failed_oracle_checks(envelope)


def test_oracle_provenance_rejects_movie_serial_mutations():
    for location, expected_id in (
        ("start_state", "movie_metadata_serial"),
        ("top_level", "movie_top_level_serial"),
    ):
        envelope = valid_oracle_envelope()
        if location == "start_state":
            envelope["movie_doc"]["start_state"]["game_serial"] = "WRONG"
        else:
            envelope["movie_doc"]["game_serial"] = "WRONG"
        assert expected_id in failed_oracle_checks(envelope)


def test_oracle_provenance_rejects_every_pristine_media_identity_mutation():
    mutations = [
        (("has_media",), False, "pristine_media_has_media"),
        (("serial",), "WRONG", "pristine_media_serial"),
        (("title",), "WRONG", "pristine_media_title"),
        (("cue", "identity"), "wrong.cue", "pristine_media_cue_identity"),
        (("cue", "sha256"), "0" * 64, "pristine_media_cue_sha256"),
        (("track", "identity"), "wrong.bin", "pristine_media_track_identity"),
        (("track", "sha256"), "0" * 64, "pristine_media_track_sha256"),
        (("executable", "identity"), "wrong.exe",
         "pristine_media_executable_identity"),
        (("executable", "sha256"), "0" * 64,
         "pristine_media_executable_sha256"),
    ]
    for path, value, expected_id in mutations:
        envelope = valid_oracle_envelope()
        target = envelope["media_identity"]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        assert expected_id in failed_oracle_checks(envelope)


def test_oracle_provenance_rejects_truncation_and_playback_mutations():
    for field, value, expected_id in (
        ("trace_truncated", True, "exec_trace_not_truncated"),
        ("trace_truncated", None, "exec_trace_not_truncated"),
        ("playback_reproducible", False, "playback_reproducible"),
        ("playback_completed", False, "playback_completed"),
    ):
        envelope = valid_oracle_envelope()
        envelope[field] = value
        assert expected_id in failed_oracle_checks(envelope)


def test_cycle_window_sensitivity_is_stable_at_2000():
    window = VERIFY.build_offline()["campaign_breadth"]["window_sensitivity"]
    assert window["windows_evaluated"] == 10001
    assert window["transitions_through_10000"] == [
        {"window": 0, "law_failures": 19},
        {"window": 28, "law_failures": 0},
    ]
    assert window["stable_passing_interval"] == [28, 1164325800]
    assert window["retained_window"] == 2000
    assert window["retained_window_inside_stable_interval"] is True


def test_compiled_c_direct_entry_universe_is_unique_and_pinned(tmp_path):
    binary = tmp_path / "f01-entry"
    subprocess.run([
        "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
        "-o", str(binary),
        str(ROOT / "tools/phase4_f01_finalizer_entry_probe.c"),
    ], check=True)
    selftest = subprocess.run(
        [str(binary), "--selftest"], check=True, capture_output=True, text=True)
    assert json.loads(selftest.stdout)["selftest"] == "PASS"

    specs = [
        "REBUILD/files/SCUS_942.88:0x80010000",
        "REBUILD/files/BITS/MEMORY.BIN:0x800b5788",
        "REBUILD/files/LEVEL00/LEVEL.BIN:0x800b39a0",
    ]
    for level in range(1, 10):
        specs.extend([
            f"REBUILD/files/LEVEL{level:02d}/LEVEL.BIN:0x800b39a0",
            f"REBUILD/files/LEVEL{level:02d}/LEVEL1.BIN:0x800b39a0",
        ])
    specs.append("REBUILD/files/LEVEL10/LEVEL.BIN:0x800b39a0")
    assert len(specs) == len(set(specs)) == 22

    run = subprocess.run(
        [str(binary), "0x8004ff14", "0x8004ff50", *specs],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    result = json.loads(run.stdout)
    assert result["images_scanned"] == 22
    assert result["words_scanned"] == 143060
    assert result["indirect_sites_total"] == 1246
    assert result["direct_entry_count"] == 0
    assert result["images"][0]["words"] == 117248
    assert result["images"][0]["indirect_sites"] == 1094
    assert result["images"][2]["words"] == 1
    assert 143060 + 117248 - 1 == 260307
    assert 1246 + 1094 == 2340
    assert hashlib.sha256(run.stdout.encode()).hexdigest() == (
        "bd847bb7473163799a35b654390499c28bf59bc4d9a3b6a6896ebc5653c6021c"
    )


def test_breadth_verdict_requires_mapping_and_fail_closed_corpus():
    offline = VERIFY.build_offline()["campaign_breadth"]
    verdict = json.loads(VERDICT.read_text())["dimensions"]["campaign_breadth"]
    assert offline["levels"] == offline["levels_with_at_least_one_decision"] == 19
    assert offline["predicted_call"] == 19
    assert offline["predicted_skip"] == 16
    assert offline["structured_level_type_mapping_present"] is False
    assert offline["structured_applicability_matrix_present"] is False
    assert verdict["verdict"] == "NOT MET"
    assert {gap["id"] for gap in verdict["missing_elements"]} >= {
        "preoutcome_applicability_matrix",
        "predeclared_level_type_mapping",
        "fail_closed_corpus_gate",
        "fresh_detached_regeneration",
    }


def test_breadth_layer_audit_fails_closed_on_unknown_denominators():
    audit = json.loads(VERDICT.read_text())["campaign_breadth_layer_audit"]
    assert list(audit) == [
        "applicability_universe", "stages", "objectives", "variants", "modes",
        "exceptional_paths", "required_taxonomy", "coverage_controls",
    ]
    assert audit["applicability_universe"]["status"] == "ABSENT"
    assert audit["stages"]["denominator"] == "unknown"
    assert audit["objectives"]["status"] == "NOT DEMONSTRATED"
    assert audit["variants"]["status"] == "NOT DEMONSTRATED"
    assert audit["modes"]["status"] == "NOT DEMONSTRATED"
    assert audit["exceptional_paths"]["status"] == "NOT DEMONSTRATED"
    assert audit["required_taxonomy"]["assigned_sessions"] == "0/19"
    assert audit["coverage_controls"]["invalid_mutations_rejected"] == "0/3"


def test_registry_was_not_edited_for_rejected_dimensions():
    verdict = json.loads(VERDICT.read_text())
    assert verdict["registry_action"] == {
        "analysis/mechanics_baseline.yaml": "UNCHANGED: neither dimension met its bar"
    }


def test_all_six_named_work_order_attacks_have_explicit_results():
    checks = json.loads(VERDICT.read_text())["work_order_attack_results"]
    assert list(checks) == ["4a", "4b", "4c", "4d", "4e", "4f"]
    assert all(checks[key]["result"] in {"SURVIVED", "FAILED"} for key in checks)
