"""Hard guards for the deterministic Phase-4 static and overlay indexes."""

import copy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_static_frontier as frontier  # noqa: E402


def retained(path: Path) -> dict:
    return json.loads(path.read_text())


def test_all_static_outputs_recompute_byte_identically():
    documents = frontier.build_all()
    paths = (frontier.INDEX_OUTPUT, frontier.OVERLAY_OUTPUT,
             frontier.PILOT_OUTPUT, frontier.TOOLCHAIN_OUTPUT)
    assert all(path.read_bytes() == frontier.render(document)
               for path, document in zip(paths, documents))


def test_full_census_identity_gp_and_non_code_contracts():
    document = retained(frontier.INDEX_OUTPUT)
    assert document["valid"] is True and document["errors"] == []
    # Re-pinned 2026-08-06: the decoded target-root island 0x8004C898 was
    # promoted from a side list to a census record, so records went 1190 -> 1191
    # (resident 998 -> 999, resident code 900 -> 901). The canonical source and
    # the island contribution are pinned separately so a moved canonical census
    # and a moved island set stay distinguishable.
    assert document["summary"] == {
        "canonical_source_records": 1190,
        "census_records": 1191,
        "content_verified_range_accesses": 29,
        "data_records": 78,
        "duplicate_keys": 0,
        "expected_census_records": 1191,
        "fatal_analysis_errors": 0,
        "overlay_code_functions": 158,
        "resident_code_records": 901,
        "resident_records": 999,
        "target_root_island_records": 1,
        "thunk_records": 54,
    }
    assert len(document["images"]) == 21
    assert all(row["identity_verified"] for row in document["images"])
    data = [row for row in document["records"] if row["range_type"] == "data"]
    assert len(data) == 78
    assert {row["analysis_status"] for row in data} == {"not_applicable"}
    code = [row for row in document["records"] if row["range_type"] != "data"]
    assert all(len(row["basic_blocks"]) == row["basic_block_count"] for row in code)
    assert all(block["terminator"] is None or "delay_slot" in block["terminator"]
               for row in code for block in row["basic_blocks"])
    gp_accesses = [access for row in document["records"]
                   for access in row.get("memory_accesses", [])
                   if access["base_register"] == "gp" and access["address"]]
    # ⚠️ This pin was stale long before it moved here. It was set to 854 when the
    # workbench landed (caf22652b2eb) and never tracked two index re-baselines:
    # a clean checkout at the preceding commit already read 901, so the assertion
    # was red on master independently of this change. The whole-image direct-edge
    # CFG recovery then made 14 more $gp-relative accesses reachable -> 915.
    # Re-pinned with that history recorded rather than silently bumped; what the
    # assertion is FOR -- that $gp accesses resolve and join semantic state -- is
    # the line below and is unaffected.
    assert len(gp_accesses) == 915
    assert any(access["state_joins"] for access in gp_accesses)


def test_f01_c_reader_ranges_reconcile_as_an_exact_set():
    document = retained(frontier.INDEX_OUTPUT)
    proof = document["f01_content_verified_reader_ranges"]
    assert proof["verified"] is True
    assert proof["reader_count"] == proof["indexed_reader_count"] == 29
    assert proof["receipt_only"] == proof["index_only"] == []
    assert document["source_dependencies"][proof["source"]] == \
        proof["artifact_sha256"]
    rows = [access for record in document["records"]
            for access in record.get("memory_accesses") or []
            if access.get("resolved_address_range")]
    assert len(rows) == 29
    assert {row["address_resolution"] for row in rows} == {"bounded_static_range"}
    assert all(row["address"] is None for row in rows), (
        "a bounded dynamic range must not be collapsed to a fabricated point")


def test_overlay_identities_clusters_and_non_promotion_boundary():
    document = retained(frontier.OVERLAY_OUTPUT)
    assert document["valid"] is True and document["errors"] == []
    assert document["summary"] == {
        "additional_region_b_modules": 1,
        "automatic_owner_promotions": 0,
        "exact_multi_image_clusters": 6,
        "overlay_code_functions": 158,
        "overlay_images": 20,
        "structural_candidate_clusters": 13,
        "unique_function_keys": 158,
    }
    keys = [(image["image_id"], function["entry"])
            for image in document["images"] for function in image["functions"]]
    assert len(keys) == len(set(keys)) == 158
    same_va = [key for key in keys if key[1] == "0x800B39A4"]
    assert len(same_va) > 1 and len({key[0] for key in same_va}) == len(same_va)
    assert all(function["semantic_owner"] is None
               for image in document["images"] for function in image["functions"])
    assert all(image["header_rule"] == {"bytes": 4, "code_entry": "base_plus_header"}
               for image in document["images"] if image["role"] == "region_a_level")
    assert all(image["header_value"] == image["expected_header_value"]
               and image["lifetime"] == "swapped_region_a_level"
               for image in document["images"] if image["role"] == "region_a_level")
    fmv = document["additional_region_b_modules"]
    assert len(fmv) == 1 and fmv[0]["image_id"] == "FMV_BIN"
    assert fmv[0]["identity_verified"] is True
    assert fmv[0]["lifetime"] == "exclusive_region_b_fmv"
    assert (fmv[0]["typed_address_rows"], fmv[0]["exact_xrefs"]) == (30, 99)
    assert fmv[0]["semantic_owner"] is None


def test_e15_e08_and_c13_pilots_are_exact_and_non_promoting():
    document = retained(frontier.PILOT_OUTPUT)
    assert document["valid"] is True and document["errors"] == []
    assert document["E15_fmv"]["actual"] == {
        "absolute_xrefs": 99, "player_xrefs": 58,
        "region_b_address_rows": 30, "unclassified_xrefs": 0,
    }
    assert document["E15_fmv"]["all_instruction_words_verified"] is True
    assert document["E15_fmv"]["all_cross_joins_verified"] is True
    assert document["E08_props_movers_gates"]["actual"] == {
        "automatic_owner_promotions": 0, "callbacks": 10,
        "priority_slices": 5, "selectors": 40, "uncontrolled_classes": 28,
    }
    assert all(row["semantic_owner"] is None
               for row in document["E08_props_movers_gates"]["priority_slices"])
    assert document["E08_props_movers_gates"]["program_joins_verified"] is True
    assert all(row["extent_verified"] and row["source_verified"]
               for row in document["E08_props_movers_gates"]["callback_joins"])
    callback_joins = document["E08_props_movers_gates"]["callback_joins"]
    external = [row for row in callback_joins
                if row["source"].startswith("asm/hand_written/")]
    tracked = [row for row in callback_joins
               if row["source"].startswith("src/main/")]
    assert len(external) == 4 and len(tracked) == 6
    # ⚠️ `source_bytes_present` is None for external assembly ON PURPOSE.
    # `asm/hand_written/` is deliberately outside git, so whether its bytes sit
    # on this disk is not a property of the commit -- recording it made the
    # retained artifact regenerate differently in the operator's tree and in a
    # clean checkout, so the document simply does not assert it. What IS a
    # property of the commit is the manifest pin, and that is asserted.
    assert all(row["source_bytes_present"] is None
               and row["source_manifest_pinned"] is True
               and row["source_verification_method"] == "repro_manifest_sha256"
               for row in external)
    assert all(row["source_bytes_present"] is True
               and row["source_verification_method"] == "tracked_file_sha256"
               for row in tracked)
    assert document["E08_props_movers_gates"]["frontier"]["summary"][
        "visited_functions"] > 10
    c13 = document["C13_grain_harvester"]
    assert len(c13["function_roots"]) == 6 and c13["missing_roots"] == []
    assert c13["open_boundaries"] == [
        "causal controls", "lifecycle and breadth", "original oracle"]
    assert c13["state_contract"]["powerup_flags"]["reader_signedness"] == ["unsigned"]
    assert c13["state_contract"]["powerup_flags"]["selected_writer"]["pc"] == "0x80051EB0"
    assert c13["state_contract"]["health_true"]["reader_signedness"] == ["signed"]
    assert c13["state_contract"]["health_true"]["selected_writer"]["pc"] == "0x80055124"
    assert c13["slice_hashes_verified"] is True
    assert c13["frontier"]["closure_claimed"] is False
    assert all(row["owner"] is not None or row["unresolved"] is True
               for row in c13["frontier"]["boundary_edges"])
    assert c13["dimension_promoted"] is False


def test_wrong_resident_base_fails_closed(monkeypatch):
    config = copy.deepcopy(frontier.load_yaml(frontier.CONFIG_PATH))
    config["resident"]["file_va_base"] += 4
    original = frontier.load_yaml
    monkeypatch.setattr(frontier, "load_yaml", lambda path: config
                        if Path(path) == frontier.CONFIG_PATH else original(path))
    document = frontier.build_index()
    assert document["valid"] is False
    assert any("independent address binding drift resident.file_va_base" in error
               for error in document["errors"])


def test_hash_drift_and_duplicate_census_fail_closed(monkeypatch):
    baseline = copy.deepcopy(frontier.load_json(frontier.BUILD_BASELINES_PATH))
    baseline["staged_inputs"]["SCUS_942.88"]["sha256"] = "0" * 64
    functions = copy.deepcopy(frontier.load_json(frontier.FUNCTIONS_PATH))
    functions["functions"].append(copy.deepcopy(functions["functions"][0]))
    original = frontier.load_json

    def mutated(path):
        if Path(path) == frontier.BUILD_BASELINES_PATH:
            return baseline
        if Path(path) == frontier.FUNCTIONS_PATH:
            return functions
        return original(path)

    monkeypatch.setattr(frontier, "load_json", mutated)
    document = frontier.build_index()
    assert document["valid"] is False
    assert document["summary"]["duplicate_keys"] == 1
    assert any("unverified staged image identity" in error for error in document["errors"])
    assert any("duplicate census key" in error for error in document["errors"])


def test_cfg_dataflow_does_not_join_unreachable_or_call_clobbered_constants():
    import struct

    state = {0x800A6590: [{"id": "sentinel"}]}
    branch_words = [0x10000002, 0, 0x3C08800A, 0x8D026590]
    branch = frontier.analyze_code(
        b"".join(struct.pack("<I", word) for word in branch_words),
        0x80010000, "synthetic_branch", state, 0x800A0000)
    assert branch["unreachable_instruction_count"] == 1
    assert not any(row["state_joins"] for row in branch["memory_accesses"])

    call_words = [0x3C08800A, 0x0C004000, 0, 0x8D026590]
    call = frontier.analyze_code(
        b"".join(struct.pack("<I", word) for word in call_words),
        0x80010000, "synthetic_call", state, 0x800A0000)
    assert not any(row["state_joins"] for row in call["memory_accesses"])


def test_census_type_size_header_and_count_mutations_fail_closed(monkeypatch):
    config = copy.deepcopy(frontier.load_yaml(frontier.CONFIG_PATH))
    config["overlays"]["region_a_code_offset"] = 0
    original_yaml = frontier.load_yaml
    monkeypatch.setattr(frontier, "load_yaml", lambda path: config
                        if Path(path) == frontier.CONFIG_PATH else original_yaml(path))
    document = frontier.build_index()
    assert any("region_a_code_offset" in error for error in document["errors"])
    monkeypatch.undo()

    functions = copy.deepcopy(frontier.load_json(frontier.FUNCTIONS_PATH))
    code = next(row for row in functions["functions"]
                if row["space"] == "resident" and row["range_type"] == "code")
    code["range_type"] = "data"
    code["size"] += 4
    original_json = frontier.load_json
    monkeypatch.setattr(frontier, "load_json", lambda path: functions
                        if Path(path) == frontier.FUNCTIONS_PATH else original_json(path))
    document = frontier.build_index()
    assert any("resident_code census" in error for error in document["errors"])
    assert any("census size mismatch" in error for error in document["errors"])


def test_e15_e08_and_c13_provenance_mutations_fail_pilots(monkeypatch):
    index = retained(frontier.INDEX_OUTPUT)
    fmv = copy.deepcopy(frontier.load_json(frontier.FMV_PATH))
    fmv["player_typed_state"]["fields"][0]["address"] = "0xDEADBEEF"
    original = frontier.load_json
    monkeypatch.setattr(frontier, "load_json", lambda path: fmv
                        if Path(path) == frontier.FMV_PATH else original(path))
    assert frontier.build_pilots(index)["E15_fmv"]["valid"] is False
    monkeypatch.undo()

    e08 = copy.deepcopy(frontier.load_json(frontier.E08_PATH))
    e08["frontier"][5]["semantic_owner"] = "invented.owner"
    e08["callback_census"][0]["end"] = "0x80049E8C"
    original = frontier.load_json
    monkeypatch.setattr(frontier, "load_json", lambda path: e08
                        if Path(path) == frontier.E08_PATH else original(path))
    assert frontier.build_pilots(index)["E08_props_movers_gates"]["valid"] is False
    monkeypatch.undo()

    config = copy.deepcopy(frontier.load_yaml(frontier.CONFIG_PATH))
    config["targets"]["C13_grain_harvester"]["state_roots"][1] = "0xDEADBEEF"
    original_yaml = frontier.load_yaml
    monkeypatch.setattr(frontier, "load_yaml", lambda path: config
                        if Path(path) == frontier.CONFIG_PATH else original_yaml(path))
    assert frontier.build_pilots(index)["C13_grain_harvester"]["valid"] is False


def test_e08_external_source_manifest_mutations_fail_closed(monkeypatch, tmp_path):
    index = retained(frontier.INDEX_OUTPUT)
    callback = next(row for row in frontier.load_json(frontier.E08_PATH)["callback_census"]
                    if row["source"].startswith("asm/hand_written/"))
    manifest = frontier.SOURCE_MANIFEST_PATH.read_text()

    bad_pin = tmp_path / "bad-pin.sha256"
    bad_pin.write_text(manifest.replace(callback["source_sha256"], "0" * 64, 1))
    monkeypatch.setattr(frontier, "SOURCE_MANIFEST_PATH", bad_pin)
    assert frontier.build_pilots(index)["E08_props_movers_gates"]["valid"] is False

    duplicate = tmp_path / "duplicate.sha256"
    duplicate.write_text(manifest + f"{callback['source_sha256']}  {callback['source']}\n")
    monkeypatch.setattr(frontier, "SOURCE_MANIFEST_PATH", duplicate)
    assert frontier.build_pilots(index)["E08_props_movers_gates"]["valid"] is False


def test_the_jr_input_is_pinned_and_retained_as_an_exact_set():
    """A CFG universe consuming an unpinned input is an unpinned index.

    "36 sites, 408 targets" is a shape, not an identity, and a wrong table with
    the same shape would pass. The artifact hash is pinned among the index's
    dependencies and the exact (site, target) map is retained so a verifier can
    difference it rather than compare counts.
    """
    document = retained(frontier.INDEX_OUTPUT)
    assert "analysis/phase3_jr_tables.json" in document["source_dependencies"]
    provenance = document["indirect_jump_targets"]
    assert provenance["verified"] is True
    assert provenance["artifact_sha256"] == document["source_dependencies"][
        "analysis/phase3_jr_tables.json"]
    identities = provenance["site_targets"]
    assert len(identities) == provenance["sites"] == 36
    assert sum(len(v) for v in identities.values()) == provenance["targets"] == 408
    digest = hashlib.sha256(
        json.dumps(identities, sort_keys=True).encode()).hexdigest()
    assert provenance["identity_digest"] == digest, (
        "the digest must cover the exact identities, so one moved target changes "
        "a visible value even when the counts hold")


def test_the_cfg_universe_is_not_quoted_as_the_gates():
    """This walk follows verified jr targets; the gate follows direct edges only."""
    document = retained(frontier.INDEX_OUTPUT)
    universe = document["cfg_universe"]
    assert "jr-table targets" in universe
    assert "NOT the static-ASM" in universe
    gate = ROOT / "analysis/phase4_static_asm_prerequisites.json"
    if gate.is_file():
        assert json.loads(gate.read_bytes())["direct_cfg"][
            "indirect_edges_followed"] is False


def test_the_gate_jr_identities_are_imported_as_an_exact_superset():
    """51 proved target sets sat unused while the index consumed only phase3."""
    document = retained(frontier.INDEX_OUTPUT)
    gate = document["indirect_jump_targets_from_gate"]
    assert gate["verified"] is True
    assert gate["sites"] == 87 and gate["sites_added"] == 51
    assert len(gate["site_targets"]) == gate["sites"]
    assert sum(len(v) for v in gate["site_targets"].values()) == gate["targets"]
    # phase3 must be a SUBSET, checked rather than assumed: a gate that had
    # dropped a phase3 site would be a disagreement, not a silent merge.
    assert gate["phase3_sites_not_in_gate"] == []
    phase3 = document["indirect_jump_targets"]["site_targets"]
    for site, targets in phase3.items():
        assert set(targets) <= set(gate["site_targets"][site]), site


def test_a_target_root_island_is_decoded_without_widening_any_extent():
    """A proved target in unclaimed bytes is invisible to an extent-built walk.

    Importing more jr identities cannot fix that on its own; the bytes have to
    become a separately evidenced island, and NOT by stretching a neighbour.
    """
    document = retained(frontier.INDEX_OUTPUT)
    islands = document["target_root_islands"]
    assert islands, "the mover-dispatch arm must be recovered"
    island = next(row for row in islands if row["start"] == "0x8004C898")
    assert island["end"] == "0x8004C8AC" and island["instruction_count"] == 5
    assert island["reached_by"] == ["0x8004C868"]
    assert island["widened_an_existing_extent"] is False
    assert "fallthrough reaches the gap end" in island["stopping_proof"]
    # Neither neighbouring extent moved: the island is a NEW record between
    # them, not a stretched boundary.
    records = {(row["image_id"], row["entry"]): row for row in document["records"]}
    assert records[("SCUS_942_88", "0x8004C818")]["end"] == "0x8004C898"
    assert records[("SCUS_942_88", "0x8004C8AC")]["end"] == "0x8004D224"


def test_the_island_IS_a_census_record_and_its_stores_are_per_record_visible():
    """The expected-count pin is a change detector, not a hiding place.

    Keeping the island out of `records` to preserve the pinned count made its
    two register-based stores invisible to every per-record consumer -- the F01
    blocker ledger and the writer-census resolver alike -- so "the falsifier
    ran over the island" was unbankable. The pin was re-pinned intentionally
    and the island promoted; the side list keeps only discovery provenance.
    """
    document = retained(frontier.INDEX_OUTPUT)
    island = next(row for row in document["target_root_islands"]
                  if row["start"] == "0x8004C898")
    assert island["is_a_census_record"] is True
    assert island["census_record"] == "SCUS_942_88:0x8004C898"
    # ONE authoritative universe: the code facts live on the record, and the
    # provenance entry does not carry a second copy of the accesses.
    assert "memory_accesses" not in island
    record = next(row for row in document["records"]
                  if row.get("source") == "target_root_island")
    assert (record["image_id"], record["entry"], record["end"]) == \
        ("SCUS_942_88", "0x8004C898", "0x8004C8AC")
    assert record["range_type"] == "code"
    assert record["analysis_status"] == "ok"
    assert record["island_provenance"]["stopping_proof"] == island["stopping_proof"]
    # Its two stores are through a register base, so they are BLOCKERS, not
    # writers, and they are now in the same memory-access universe as every
    # other record's accesses.
    accesses = record["memory_accesses"]
    assert [row["mnemonic"] for row in accesses] == ["sh", "sw"]
    assert all(row["address"] is None for row in accesses)
    assert all(row["base_register"] == "s0" for row in accesses)
    # Exact-set identity between decoded islands and island records, both ways.
    decode_keys = {(row["image"], row["start"], row["end"])
                   for row in document["target_root_islands"]}
    record_keys = {(row["image_id"], row["entry"], row["end"])
                   for row in document["records"]
                   if row.get("source") == "target_root_island"}
    assert decode_keys == record_keys
    # The re-pinned identity holds: canonical + islands = records.
    summary = document["summary"]
    assert summary["census_records"] == summary["expected_census_records"]
    assert summary["census_records"] == (summary["canonical_source_records"]
                                         + summary["target_root_island_records"])


def test_the_resident_header_rule_is_derived_from_the_image():
    document = retained(frontier.INDEX_OUTPUT)
    images = {row["image_id"]: row for row in document["images"]}
    assert images["SCUS_942_88"]["header_rule"] == {
        "bytes": 0x800, "code_entry": "base_plus_header"}
    assert images["MEMORY"]["header_rule"] == {"bytes": 0, "code_entry": "base"}
    assert images["LEVEL01_LEVEL"]["header_rule"] == {
        "bytes": 4, "code_entry": "base_plus_header"}
