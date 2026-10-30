"""Falsification guards for the active Phase-4 C15 lifecycle campaign."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_checkpoint_respawn as c15  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import ps1_scenario  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_checkpoint_respawn.json"
ARTIFACT_SHA256 = "fc71182a5ffeb1acc15a305d4c707ac2f2846ebc173497d48a4bbc3fd1fc0660"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_c15_evidence_recomputes_exact_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert doc["campaign_state"] == "active_partial"
    assert c15.evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_checkpoint_respawn.py").read_bytes()).hexdigest()
    assert run["duckstation"]["revision"] == \
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5"
    assert run["duckstation"]["binary_sha256"] == \
        "91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6"
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_and_static_census_recompute_from_hash_pins():
    retained = load_artifact()
    assert c15.build_fixture_census() == retained["fixture_census"]
    assert c15.build_static_census() == retained["static_census"]
    words = retained["static_census"]["instructions"]
    assert words["anchor_x_store"]["instruction_word"] == "0xAC236550"
    assert words["respawn_anchor_x_load"]["instruction_word"] == "0x8CC66550"
    assert words["respawn_live_x_store"]["instruction_word"] == "0xACA60000"
    assert words["respawn_lives_decrement"]["instruction_word"] == "0xA02665A0"
    overlay = retained["static_census"]["overlay_safe_anchor_selector"]
    assert overlay["sha256"] == \
        "1fdeb0da151050edbde73a082b5951ae4326ec133979ca5bae2f0198bd8cfbf9"
    assert overlay["instructions"]["selected_anchor_x_store"] == {
        "address": "0x800B3D24", "instruction_word": "0xAC830000",
        "file_offset": "0x384"}
    writers = retained["static_census"]["pit_transition_writers"]
    assert writers["scene_10_pit"]["path"] == \
        "REBUILD/files/LEVEL10/LEVEL.BIN"
    assert writers["scene_10_pit"]["sha256"] == \
        "97e72e5e4bf8c1029cabc98cfcef43d5077666edeb39617d012769f01285c4b8"
    assert writers["scene_10_pit"]["instructions"]["safe_x_store"] == {
        "address": "0x800B3BAC", "instruction_word": "0xAC830000",
        "file_offset": "0x20C"}
    assert writers["scene_4_pit"]["path"] == \
        "REBUILD/files/LEVEL04/LEVEL.BIN"
    assert writers["scene_4_pit"]["sha256"] == \
        "8494bef9a426a6b2ceea0bb57a634c5520a12abb89c493ce4b88ab3d992764ba"
    assert writers["scene_4_pit"]["instructions"]["safe_heading_store"] == {
        "address": "0x800B3CB0", "instruction_word": "0xA4226578",
        "file_offset": "0x310"}
    breadth = {row["id"]: row for row in retained["fixture_census"]["pit_breadth"]}
    assert breadth["scene_10_pit"]["movie"]["sha256"] == \
        "c049d9b8075f458f87301134a3cb9998137ae0a82fa5d8d5516dd05b69c99e24"
    assert breadth["scene_10_pit"]["save"]["sha256"] == \
        "959bf87da9deb91fbdb1633175aebefc9de329d5aa4d7ef9ce18df0f34bc6a06"
    assert breadth["scene_4_pit"]["movie"]["sha256"] == \
        "a06c81943700db5bd4e570165d54b098e54c67644cb116fde826bf75db8fee99"
    assert breadth["scene_4_pit"]["save"]["sha256"] == \
        "9e2cee6d4847c758ad6bae1e396fd7de31830f5b55220e63719a50cc1806973a"


def test_single_variable_and_convergence_mutations_turn_the_c15_proof_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["live"]["neutral_input_control"]["recipe"]["changed_frames"].pop()
    assert "neutral control changed" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    guards = mutated["live"]["counterfactuals"]["single_variable_guards"]
    guards["anchor_only_changed_byte_addresses"].append("0x800A6554")
    assert "not confined" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    branch = mutated["live"]["counterfactuals"]["branch_recipes"] \
        ["anchor_x_plus_4096"]["post_reset"]
    branch["cycle_neutral_trace"]["control"]["ram_sha256"] = "00" * 32
    assert "did not converge" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    branch = mutated["live"]["counterfactuals"]["branch_recipes"] \
        ["stores_nopped_anchor_x_plus_4096"]["post_reset"]
    branch["snapshot"]["anchor_store_words"]["0x80054E70"] = "0xAC236550"
    assert "suppressed writer" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    owner = mutated["live"]["reset_owner"]
    owner["single_variable_guard"]["changed_byte_addresses"].append(
        "0x8015E6D4")
    assert "not confined" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    owner = mutated["live"]["reset_owner"]
    owner["branches"]["selected_x_source_plus_128"]["post_reset"] \
        ["snapshot"]["live_xyz"][0] += 1
    assert "scaled reset outcome" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    owner = mutated["live"]["reset_owner"]
    owner["selector_denial_single_variable_guard"][
        "changed_byte_addresses"].append("0x800A6591")
    assert "not confined to the status word" in \
        " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    owner = mutated["live"]["reset_owner"]
    denial_coverage = owner["branches"]["selector_status_bit_cleared"] \
        ["post_reset"]["cycle_neutral_trace"]["coverage"]
    selector = next(row for row in denial_coverage
                    if row["label"] == "overlay_safe_anchor_selector")
    selector["pcs"].append("0x800b3d24")
    assert "exact pre-store gate" in " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    contact = mutated["live"]["contact_death_anchor_control"]
    contact["single_variable_guard"]["changed_byte_addresses"] = [
        "0x800A6550"]
    assert "contact-death branch is not confined" in \
        " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    contact = mutated["live"]["contact_death_anchor_control"]
    contact["branches"]["safe_anchor_x_plus_4096"] \
        ["first_completed_respawn_boundary"]["snapshot"]["live_xyz"][0] += 1
    assert "contact-death respawn outcome changed" in \
        " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    breadth = mutated["live"]["pit_breadth"][0]
    breadth["causal_result"]["classification"] = \
        "resident_handler_consumed_retained_safe_anchor"
    assert "scene_10_pit causal classification changed" in \
        " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    breadth = mutated["live"]["pit_breadth"][1]
    coverage = breadth["branches"]["safe_anchor_x_plus_4096"] \
        ["post_reset"]["cycle_neutral_trace"]["coverage"]
    handler = next(row for row in coverage
                   if row["label"] == "respawn_transition_state_handler")
    handler["pcs"].remove("0x8005b348")
    assert "scene_4_pit mutation lost the exact respawn chain" in \
        " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    attribution = mutated["live"]["pit_writer_attribution"][0]
    attribution["access_log"]["events"][0]["instruction_pc"] = "0x800b3bb0"
    assert "scene_10_pit transition-writer attribution changed" in \
        " ".join(c15.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    writer = mutated["static_census"]["pit_transition_writers"]["scene_4_pit"]
    writer["sha256"] = "00" * 32
    assert "scene_4_pit pristine writer identity changed" in \
        " ".join(c15.evidence_gaps(mutated))


def test_c15_registry_is_active_without_promoting_coverage():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "safe_respawn_anchor")
    assert campaign["status"] == "active"
    for assertions in campaign["evidence"].values():
        for assertion in assertions:
            assert common.audit_assertion(assertion) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "safe_respawn_anchor: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C15_checkpoints"]["state"] == "open"
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["families"]["player_lifecycle"]["derived_status"] == "active"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_c15_schema_record_and_semantic_correction_keep_unknowns_visible():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_checkpoint_respawn.yaml").read_text())
    assert schema["schema"] == "abl-phase4-checkpoint-respawn/2"
    assert schema["campaign_state"] == "active_partial"
    assert schema["reproduced_controls"]["natural_post_reset"] == {
        "movie_frame": 160,
        "live_xyz": [501696, 30215, 494013],
        "safe_anchor_xyz": [501696, 30092, 494016],
        "true_health": 4, "lives": 4,
    }
    assert set(schema["ownership_boundaries"]["still_open"]) == {
        "Source and general activation policy of status mask 0x0010, denial behavior in other row-selecting variants, plus reset scope.",
        "Indirect/additional overlay variants, actor, scripted and exceptional death classes plus remaining-stage, save/load and scene-transition breadth.",
    }
    source = schema["pristine_frontier"]["authored_row_source"]
    assert source["dat_path"] == "REBUILD/files/LEVEL03/LEVEL.DAT"
    assert source["type_01_record"] == {
        "file_offset": 0x458, "runtime_pointer": 0x8015E684,
        "count": 18, "size": 220,
        "sha256": "6adbdd60b3935d76caf6b929cb108fd4b338d39c1888a2ad4abe92d21416fee3"}
    activation = schema["pristine_frontier"]["level06_runtime_activation"]
    assert activation["exact_call"] == {
        "address": 0x8005B194, "instruction_word": 0x0C02CEBB,
        "target": 0x800B3AEC, "return": 0x8005B19C,
    }
    assert activation["fixed_safe_tuple"] == {
        "x": 35329, "y": -85228, "z": -154696, "heading": 3063}
    activation = schema["pristine_frontier"]["level08_runtime_activation"]
    assert activation["exact_call"] == {
        "address": 0x8005B1A4, "instruction_word": 0x0C02CEBA,
        "target": 0x800B3AE8, "return": 0x8005B1AC,
    }
    assert activation["fixed_safe_and_live_tuple"] == {
        "x": -157682, "y": 5744, "z": -12845, "heading": 352}
    assert activation["coverage"] == {
        "initializer_hits": 27, "initializer_distinct_pcs": 27,
        "response_only_hits": 0, "truncated": False,
        "cycle_neutral": True}
    assert schema["reproduced_controls"]["contact_death_safe_anchor_control"] \
        ["mutated_post"]["live_xyz"] == [-19395, -112966, -142999]
    assert schema["reproduced_controls"]["exact_reset_boundary"] == {
        "pre_movie_frame": 156,
        "pre_live_xyz": [508193, 153067, 517418],
        "pre_safe_anchor_xyz": [507900, 31787, 503976],
        "reset_movie_frame": 157,
        "reset_live_xyz": [501696, 30092, 494016],
        "reset_safe_anchor_xyz": [501696, 30092, 494016],
        "true_health": 4, "lives": 4,
    }
    assert schema["reproduced_controls"]["level03_selector_denial"] == {
        "pre_movie_frame": 156,
        "mutation": {
            "address": 0x800A6590, "before": 0x0014,
            "after": 0x0004, "cleared_mask": 0x0010,
            "changed_bytes": [0x800A6590]},
        "post_movie_frame": 157,
        "post_live_xyz": [507900, 31787, 503976],
        "post_safe_anchor_xyz": [507900, 31787, 503976],
        "true_health": 4, "lives": 4,
        "selector_coverage": {
            "total_hits": 17, "distinct_pcs": 17,
            "safe_xyz_store_pcs_present": [], "cycle_neutral": True},
        "resident_handler_coverage": {
            "total_hits": 768, "distinct_pcs": 138,
            "matches_natural_control": True},
        "boundary": (
            "one exact LEVEL03 boundary proves status mask 0x0010 is necessary "
            "for authored-row selection; it does not identify who sets the mask "
            "or generalize denial policy"),
    }
    pit_breadth = {row["id"]: row for row in
                   schema["reproduced_controls"]["pit_stage_breadth"]}
    assert pit_breadth["scene_10_pit"]["boundary"] == {
        "scene": 10, "pre_frame": 144, "reset_frame": 145,
        "pre_health": 0, "pre_lives": 1,
        "post_health": 4, "post_lives": 0}
    assert pit_breadth["scene_4_pit"]["boundary"] == {
        "scene": 4, "pre_frame": 204, "reset_frame": 205,
        "pre_health": 4, "pre_lives": 6,
        "post_health": 4, "post_lives": 5}
    assert pit_breadth["scene_10_pit"]["exact_transition_writer"] == {
        "path": "REBUILD/files/LEVEL10/LEVEL.BIN",
        "function_bounds": [0x800B3ADC, 0x800B3C18],
        "complete_access_events": 4,
        "decisive_stores": [0x800B3BAC, 0x800B3BBC, 0x800B3BC8,
                            0x800B3BDC]}
    assert pit_breadth["scene_4_pit"]["exact_transition_writer"] == {
        "path": "REBUILD/files/LEVEL04/LEVEL.BIN",
        "function_bounds": [0x800B3C5C, 0x800B3CD4],
        "complete_access_events": 5,
        "decisive_stores": [0x800B3C94, 0x800B3C9C, 0x800B3CA8,
                            0x800B3CB0, 0x800B3CC4]}

    records = yaml.safe_load((ROOT / "config/record_types.yaml").read_text())
    player = next(row for row in records["records"] if row["id"] == "player_block")
    fields = {row["offset"]: row for row in player["fields"]}
    assert [fields[offset]["name"] for offset in (0x50, 0x54, 0x58, 0x78)] == [
        "safe_respawn_anchor_x", "safe_respawn_anchor_y",
        "safe_respawn_anchor_z", "safe_respawn_anchor_heading"]

    semantic = yaml.safe_load((ROOT / "config/semantic_state.yaml").read_text())
    entry = next(row for row in semantic["entries"]
                 if row["id"] == "original.setpiece_record_index")
    assert entry["address"] == 0x800823CC
    assert [row["address"] for row in entry["writers"]] == [0x8005456C, 0x8005B9D8]
    assert all(row["id"] != "original.checkpoint_fp_save"
               for row in semantic["entries"])
    xrefs = json.loads((ROOT / "analysis/phase3_xrefs.json").read_text())
    row = xrefs["entries"]["original.setpiece_record_index"]
    assert [item["pc"] for item in row["readers"]] == ["0x8004D69C", "0x8004D8CC"]
    assert [item["pc"] for item in row["writers"]] == ["0x8005456C", "0x8005B9D8"]


def test_declarative_scenarios_retain_exact_reset_boundary_assertions():
    scenario_dir = ROOT / "tools/scenarios/duckstation"
    expected = {
        "pristine_checkpoint_respawn.yaml": ({100, 157}, 18),
        "pristine_c15_authored_row_denial.yaml": ({156, 157}, 19),
        "pristine_contact_respawn_safe_anchor.yaml": ({350, 355}, 18),
        "pristine_scene10_pit_respawn.yaml": ({144, 145}, 15),
        "pristine_scene4_pit_respawn.yaml": ({204, 205}, 15),
        "pristine_scene6_level06_respawn_initializer.yaml": ({487, 489}, 16),
        "pristine_scene8_level08_respawn_initializer.yaml": (
            {223793, 223853, 223973}, 18),
    }
    for name, (targets, count) in expected.items():
        scenario = yaml.safe_load((scenario_dir / name).read_text())
        assertions = [item for phase in scenario["phases"]
                      for item in phase["assertions"]]
        assert len(assertions) == count
        assert {phase["trigger"]["target"]
                for phase in scenario["phases"]} == targets

    contact = yaml.safe_load(
        (scenario_dir / "pristine_contact_respawn_safe_anchor.yaml").read_text())
    assert contact["setup"] == [{
        "type": "rpc", "id": "select_ordinary_respawn",
        "method": "debugger.writeU8",
        "params": {"address": 0x800A65A0, "value": 1}}]
    assert contact["phases"][0]["after"] == [{
        "type": "rpc", "id": "change_only_fatal_safe_x",
        "method": "debugger.writeU32",
        "params": {"address": 0x800A6550, "value": 0xFFFFB43D}}]
    denial = yaml.safe_load(
        (scenario_dir / "pristine_c15_authored_row_denial.yaml").read_text())
    assert denial["phases"][0]["after"] == [{
        "type": "rpc", "id": "clear_only_respawn_selector_status_bit",
        "method": "debugger.writeU16",
        "params": {"address": 0x800A6590, "value": 4}}]
    fixture_rel, fixture = ps1_scenario.central_state_fixture(
        ROOT / "movies/Phase4/C16_gameover_continue.movie.sav")
    assert fixture_rel == "movies/Phase4/C16_gameover_continue.movie.sav"
    assert fixture["sha256"] == \
        "e9c7a3b6545dffc8bc5455317b43bc58a6a1a6012e393768b64d81e22e1c1592"

    for name, fixture_sha, mutation in (
            ("pristine_scene10_pit_respawn.yaml",
             "959bf87da9deb91fbdb1633175aebefc9de329d5aa4d7ef9ce18df0f34bc6a06",
             0xFFFE7BF4),
            ("pristine_scene4_pit_respawn.yaml",
             "9e2cee6d4847c758ad6bae1e396fd7de31830f5b55220e63719a50cc1806973a",
             0x000B6E18)):
        scenario = yaml.safe_load((scenario_dir / name).read_text())
        movie_path = Path(scenario["playback"]["movie"])
        save_path = movie_path.with_suffix(".sav")
        state_rel, state_fixture = ps1_scenario.central_state_fixture(
            ROOT / save_path)
        assert state_rel == save_path.as_posix()
        assert state_fixture["sha256"] == fixture_sha
        assert scenario["phases"][0]["after"][0]["params"] == {
            "address": 0x800A6550, "value": mutation}
