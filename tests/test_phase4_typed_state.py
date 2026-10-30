"""The typed-state compiler must refuse to certify its own input.

Every test here is a way the compiler could have been made to agree with a claim
it was supposed to check. The F01 numbers are asserted too, so a change that
quietly moves them has to be looked at.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_typed_state as ts  # noqa: E402

SCHEMA = ROOT / "config/phase4_f01_typed_state.yaml"
RETAINED = ROOT / "analysis/phase4_f01_typed_state.json"


@pytest.fixture(scope="module")
def index() -> dict:
    return json.loads(ts.INDEX_PATH.read_bytes())


@pytest.fixture(scope="module")
def verifier(index) -> ts.Verifier:
    return ts.Verifier(index)


@pytest.fixture(scope="module")
def compiled(verifier) -> dict:
    doc, sha = ts.load_schema(SCHEMA)
    return ts.compile_typed_state(doc, sha, verifier)


def test_retained_output_is_fresh():
    """The checked-in result must be what the tool produces today."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_typed_state.py"), str(SCHEMA),
         "--output", str(RETAINED), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_authority_is_not_promotion(compiled):
    """Bounding sites is evidence for dimension 3, not a promotion of it."""
    assert compiled["authority"]["promotes_dimension"] is False
    assert compiled["authority"]["declaration_is_not_evidence"] is True
    assert compiled["authority"]["fresh_verifier_required"] is True


def test_indirect_control_flow_blockers_are_untouched(compiled):
    """Typing a base says nothing about where control flow can go."""
    ledger = json.loads((ROOT / "analysis/phase4_f01_frontier_blockers.json").read_bytes())
    carried = compiled["indirect_control_flow_blockers_untouched"]
    assert carried["indirect_jumps"] == len(ledger.get("indirect_jumps") or [])
    assert carried["unanalysed_extents"] == len(ledger.get("unanalysed_extents") or [])
    assert carried["indirect_jumps"] > 0, "F01 still has indirect jumps; this must not read as zero"


def test_f01_acceptance_fixture(compiled):
    """45 of the resolver's 238 stores remain convention-decided; none is proof.

    238, and it got there in two corrections that both went UP -- which is what an
    honest re-baseline looks like. First the resolver's extent ENDS were hand-typed
    and 20 of 29 stopped short of the real function (106 -> 231). Then a fresh
    verifier found the extent SET was also a subset: the tool's own criterion
    admits 37 functions and it listed 29, omitting scene_flow_dispatcher, which is
    where this row's entire lifecycle argument lives (231 -> 238). Both the set and
    the ends are now generated from the static index.
    """
    fixture = compiled["acceptance_fixture"]
    assert fixture["sites"] == 238
    assert fixture["verdicts"].get("bounded_by_proof", 0) == 0
    assert fixture["verdicts"].get("bounded_by_index_convention") == 45
    assert fixture["verdicts"].get("still_unresolved") == 96
    decided = (fixture["verdicts"].get("bounded_by_proof", 0)
               + fixture["verdicts"]["bounded_by_index_convention"])
    assert decided == 45, "all 45 remain convention-only after entry/alias gates"
    assert fixture["sites"] - decided == 193, (
        "193 of the 238 remain UNDISPOSED -- 96 unresolved plus 97 absent from "
        "the ledger. Never quote 0+45+96 as though 141 were the denominator.")
    # Every site is accounted for -- joined, absent, or ambiguous. A fixture that
    # quietly loses rows would make coverage look better than it is.
    assert (fixture["joined_to_ledger"] + fixture["absent_from_ledger_count"]
            + len(fixture["ambiguous_join"])) == fixture["sites"]
    assert fixture["absent_from_ledger_count"] == len(fixture["absent_from_ledger"])


def test_fixture_absences_are_listed_not_counted_as_bounded(compiled):
    """Sites the ledger never saw stay the resolver's problem."""
    fixture = compiled["acceptance_fixture"]
    assert fixture["absent_from_ledger_count"] == 97
    for row in fixture["absent_from_ledger"]:
        assert row["pc"].startswith("0x")


def test_index_bound_exclusions_are_kept_out_of_proof(compiled):
    """The second opinion's tiers rest on a convention, so they get their own bucket."""
    so = compiled["second_opinion"]
    assert so["regenerated_here"] is True
    assert "convention" in so["soundness"]
    assert "every image carrying an unresolved site" in so["scope"]
    # nothing in the convention bucket may be counted as proof
    proof = {r["id"] for r in compiled["bounded_by_proof"]}
    conv = {r["id"] for r in compiled["bounded_by_index_convention"]}
    assert not (proof & conv)
    assert compiled["counts"]["bounded_by_index_convention"] == len(conv)


def test_instruction_intervals_fail_closed_on_cfg_alias_and_entry_gates(compiled):
    """No interval row promotes while any machine boundary remains open."""
    receipt = compiled["second_opinion"]["instruction_interval_upgrade"]
    movement = compiled["movement_from_b6cb61d35f9d"]
    assert receipt["query_form"] == "indexdom@IMAGE:START:END:REG:PC"
    assert receipt["convention_site_universe"] == 2769
    assert receipt["upgraded_site_count"] == 0
    upgraded = set(receipt["upgraded_site_ids"])
    assert upgraded == set()
    assert movement["ledger"]["categories"]["bounded_by_proof"][
        "gained_ids"] == []
    assert movement["ledger"]["categories"][
        "bounded_by_index_convention"]["lost_ids"] == []
    assert receipt["outcomes"] == {
        "external_interior_entry": 27,
        "interval_unproved": 97,
        "proved_interval_does_not_exclude_every_window": 3,
    }
    assert receipt["exact_table_address_candidates"] == 127
    assert receipt["unique_index_queries"] == 94
    assert receipt["base_classification_failure_count"] == 2642
    exact_base_failures = [
        row for row in receipt["base_classification_failures"]
        if row["base_definition_failures"]]
    assert len(exact_base_failures) == 1708
    assert sum(len(row["base_definition_failures"])
               for row in exact_base_failures) == 1721
    for row in exact_base_failures:
        for definition in row["base_definition_failures"]:
            breaker = definition["table_address_failure"]
            assert breaker["pc"] and breaker["word"] and breaker["reason"]
    alias_rows = {
        row["id"] for row in receipt["attempts_for_exact_table_address_candidates"]
        if "ps1_ram_alias_overlap" in row.get("failure_modes", [])}
    assert len(alias_rows) == 3
    ratchet = compiled["diagnostic_outcome_movement_from_05bc6b8a251b"]
    assert ratchet["baseline_universe_count"] == 1598
    assert ratchet["current_universe_count"] == 127
    assert len(ratchet["baseline_only_ids"]) == 1471
    assert ratchet["current_only_ids"] == []
    categories = ratchet["categories"]
    assert len(categories["external_interior_entry"]["lost_ids"]) == 133
    assert categories["external_interior_entry"]["gained_ids"] == []
    assert len(categories["proved_interval_does_not_exclude_every_window"][
        "lost_ids"]) == 33
    assert categories["proved_interval_does_not_exclude_every_window"][
        "gained_ids"] == []
    assert categories["interval_unproved"]["gained_ids"] == []
    assert len(categories["interval_unproved"]["lost_ids"]) == 1305
    external = receipt["external_indirect_transfer_closure"]
    assert external["site_count"] == 247
    assert external["complete_indirect_jump_site_count"] == 87
    assert external["unknown_indirect_jump_site_count"] == 20
    assert external["unknown_indirect_call_site_count"] == 140
    assert len(external["unknown_transfer_site_ids"]) == 160
    assert external["target_domains_complete"] is False


def test_fixture_and_ledger_movements_are_exact_stable_sets(compiled):
    movement = compiled["movement_from_b6cb61d35f9d"]
    assert movement["baseline_commit"] == ts.INDEX_INTERVAL_BASELINE_COMMIT
    assert movement["ledger"]["baseline_universe_count"] == 20431
    assert movement["ledger"]["current_universe_count"] == 20431
    assert movement["ledger"]["baseline_only_ids"] == []
    assert movement["ledger"]["current_only_ids"] == []
    fixture = movement["acceptance_fixture"]
    assert fixture["baseline_universe_count"] == 238
    assert fixture["current_universe_count"] == 238
    assert fixture["baseline_only_ids"] == fixture["current_only_ids"] == []
    for section in (movement["ledger"], fixture):
        for category in section["categories"].values():
            assert category["gained_ids"] == []
            assert category["lost_ids"] == []


def test_no_blocking_site_is_reported_as_reaching_a_window(compiled):
    """A HIT here would be a real writer the frontier missed. Escalate, never file."""
    so = compiled["second_opinion"]
    assert so["sites_reported_as_reaching_a_window"] == [], (
        "region_provenance says an unresolved site REACHES a watched window")
    # and the check is not vacuous: it does find hits elsewhere in the image
    assert so["site_verdicts"], "no verdicts at all means the join silently failed"


def test_second_opinion_covers_every_image_not_just_the_resident_one(compiled):
    """Overlays are raw images; extending to them is what decided 29 more sites."""
    so = compiled["second_opinion"]
    assert len(so["images_analysed"]) == 21, so["images_analysed"]
    assert so["images_unavailable"] == {}
    assert RESIDENT_IMAGE_ID in so["images_analysed"]
    overlays = {str(r["function"]).split(":", 1)[0]
                for r in compiled["bounded_by_index_convention"]}
    assert overlays - {RESIDENT_IMAGE_ID}, "no overlay site was decided at all"
    # nothing may be filed as out-of-scope for want of an image any more
    assert so["site_verdicts"].get("image_unavailable", 0) == 0


def test_unanchored_regions_may_only_use_alignment(compiled):
    """The tier rule has to survive being pointed at a new class of image.

    An unanchored region is an arithmetic progression whose first element the
    analyser could not prove. Alignment is invariant to which element is called
    the anchor; the negative-index and out-of-bound tiers are not. The compiler
    fails closed on a violation, so this asserts the invariant actually holds on
    the data rather than merely that the guard exists.
    """
    assert compiled["second_opinion"]["unanchored_regions_restricted_to_alignment"] is True
    unanchored = 0
    for row in compiled["bounded_by_index_convention"]:
        for verdict in row["region_provenance"].values():
            if verdict.get("verified_anchor"):
                continue
            unanchored += 1
            assert verdict["verdict"] == "EXCLUDED_ALIGNMENT", (
                f"{row['function']} {row['pc']}: {verdict['verdict']} on an "
                "unanchored region")
    assert unanchored > 0, "no unanchored region in the data; the rule is untested"


def test_consumes_the_whole_ledger_not_the_fixture(compiled):
    """A shrinking acceptance fixture must not shrink the reported universe."""
    ledger = json.loads((ROOT / "analysis/phase4_f01_frontier_blockers.json").read_bytes())
    assert compiled["counts"]["unresolved_sites_in_ledger"] == len(ledger["unresolved_accesses"])
    assert compiled["counts"]["unresolved_sites_in_ledger"] > 16000
    assert compiled["counts"]["still_unresolved_stores"] > 5000


def test_binding_rejected_when_the_table_is_wrong(index, verifier):
    """Naming a different table must not still verify."""
    doc, _ = ts.load_schema(SCHEMA)
    ledger = json.loads((ROOT / "analysis/phase4_f01_frontier_blockers.json").read_bytes())
    binding = copy.deepcopy(next(b for b in doc["region_bindings"]
                                 if b["provenance"] == "typed_pointer_load"))
    binding["pointer_table"] = "0x80090750"
    ok, why, _ = ts.verify_typed_pointer_load(binding, index, ledger, verifier,
                                             _schema_regions())
    assert ok is False and "not the declared table" in why


def test_binding_rejected_for_a_register_with_mixed_definitions(index, verifier):
    """a0 in the same function is written 39 ways; it must not pass."""
    doc, _ = ts.load_schema(SCHEMA)
    ledger = json.loads((ROOT / "analysis/phase4_f01_frontier_blockers.json").read_bytes())
    binding = copy.deepcopy(next(b for b in doc["region_bindings"]
                                 if b["provenance"] == "typed_pointer_load"))
    binding["register"] = "a0"
    ok, why, _ = ts.verify_typed_pointer_load(binding, index, ledger, verifier,
                                             _schema_regions())
    assert ok is False and "do not all load from one address" in why


def test_many_callers_are_judged_on_agreement_not_counted(index, ledger, verifier,
                                                          regions):
    """Caller COUNT is not the question; whether they agree is.

    The old check rejected any function with more than one caller and accepted
    any function with exactly one, without ever looking at what was passed. A
    multi-caller function must now fail (if at all) for a reason about VALUES.
    """
    multi = None
    for record in index["records"]:
        if not record.get("entry"):
            continue
        entry = ts._int(record["entry"])
        n = sum(1 for other in index["records"]
                for e in other.get("direct_calls") or []
                if ts._int(e["target"]) == entry) if record["image_id"] else 0
        if n > 1 and any(
                ts._names_function(str(s.get("function", "")), record["image_id"], entry)
                for s in ledger["unresolved_accesses"]):
            multi = (record["image_id"], entry)
            break
    if multi is None:
        pytest.skip("no multi-caller function carries a ledger blocker")
    image, entry = multi
    reg = next(str(s["base_register"]) for s in ledger["unresolved_accesses"]
               if ts._names_function(str(s.get("function", "")), image, entry))
    ok, why, _ = ts.verify_caller_argument(
        {"image": image, "function": f"0x{entry:08x}", "register": reg,
         "region": "player_actor", "provenance": "caller_argument",
         "detail": "probe", "pointer_table": None},
        index, ledger, verifier, regions)
    assert "direct callers, so the argument is not single-valued" not in why, (
        "rejection must not be based on caller count alone")


def test_schema_may_not_relax_the_authority_contract():
    doc = yaml.safe_load(SCHEMA.read_bytes())
    doc["authority"]["promotes_dimension"] = True
    tmp = ROOT / "analysis/_authority_probe.yaml"
    tmp.write_text(yaml.safe_dump(doc))
    try:
        with pytest.raises(ts.TypedStateError, match="authority"):
            ts.load_schema(tmp)
    finally:
        tmp.unlink()


def test_pointer_table_belongs_only_to_typed_pointer_load():
    doc = yaml.safe_load(SCHEMA.read_bytes())
    caller = next(b for b in doc["region_bindings"] if b["provenance"] == "caller_argument")
    caller["pointer_table"] = "0x80090748"
    tmp = ROOT / "analysis/_pointer_table_probe.yaml"
    tmp.write_text(yaml.safe_dump(doc))
    try:
        with pytest.raises(ts.TypedStateError, match="pointer_table"):
            ts.load_schema(tmp)
    finally:
        tmp.unlink()


def test_verifier_is_rebuilt_here(compiled):
    """The reported hash must be of the binary that actually ran."""
    inputs = compiled["inputs"]
    src = (ROOT / ts.VERIFIER_SRC).read_bytes()
    assert inputs["verifier_source_sha256"] == ts._sha(src)
    assert inputs["verifier_images"] == len(json.loads(ts.INDEX_PATH.read_bytes())["images"])
    attest = next(b["attestation"] for b in compiled["bindings"]
                  if b["provenance"] == "typed_pointer_load")
    assert attest["regenerated_here"] is True
    assert attest["writer_index_crosscheck_no_index_only"] is True
    assert attest["writer_enumeration_corroborated"] is False
    assert attest["known_writer_identity"]["exact_match"] is True
    assert attest["writer_recognizer_residual"]["unclassified_store_words"] > 0


def test_c_verifier_self_test_passes(verifier):
    """The ASM verifier's own counterexamples, run against the built binary."""
    proc = subprocess.run([str(verifier.binary), "--self-test"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAIL" not in proc.stdout
    assert "bindable=0" in proc.stdout, "the bypass counterexample must stay rejected"
    assert "masked index interval" in proc.stdout and "interval=[0,252]" in proc.stdout
    for control in ("dominating table base accepted",
                    "table base join bypass rejected",
                    "entry gp table base accepted",
                    "locally redefined gp rejected",
                    "truncated jump table base rejected",
                    "unresolved jr table base rejected",
                    "overlapping ori uses bitwise value",
                    "call-delay constant clobber rejected",
                    "call-delay argument boundary accepted",
                    "jal link source rejected",
                    "jalr link source rejected",
                    "call-boundary re-entry rejected",
                    "re-entrant direct lui accepted",
                    "call link definition preserved",
                    "signed load rejected", "addu overflow rejected",
                    "definition-bypass path rejected",
                    "converged guard rejected",
                    "indirect interior entry rejected",
                    "scheduled lbu interval",
                    "immediate lbu consumer rejected",
                    "load-before-guard rejected",
                    "aliased sltiu destination rejected",
                    "nonlinear load-before-guard rejected",
                    "cop move-before-guard rejected",
                    "syscall transfer rejected",
                    "break transfer rejected",
                    "cop branch transfer rejected",
                    "regimm link return rejected",
                    "transfer in delay slot rejected",
                    "dead lexical sltiu guard rejected",
                    "dual-context delay slot rejected",
                    "locally-defined ra re-entry rejected",
                    "direct transfer missing delay rejected",
                    "branch missing delay rejected"):
        assert control in proc.stdout


def test_public_base_query_requires_path_complete_table_constant(verifier, tmp_path):
    """A lexical LUI cannot cross a CFG join and become a table proof."""
    base = 0x80010000
    safe_words = [
        0x30A8003F, 0x3C098009, 0x01285021, 0xAD420000,
        0x03E00008, 0x00000000,
    ]
    join_words = [
        0x30A8003F, 0x14800002, 0x00000000, 0x3C098009,
        0x01285021, 0xAD420000, 0x03E00008, 0x00000000,
    ]
    gp_entry_words = [
        0x30A8003F, 0x03885021, 0xAD420000, 0x03E00008, 0x00000000,
    ]
    gp_redefined_words = [
        0x30A8003F, 0x0080E021, 0x03885021, 0xAD420000,
        0x03E00008, 0x00000000,
    ]
    truncated_jump_words = [
        0x30A8003F, 0x3C098009, 0x01285021, 0xAD420000, 0x08004004,
    ]
    unresolved_jr_words = [
        0x30A8003F, 0x3C098009, 0x01285021, 0xAD420000,
        0x01600008, 0x00000000,
    ]
    ori_overlap_words = [
        0x3C098008, 0x352923A0, 0x35292000, 0x30880000,
        0x01285021, 0xAD420000,
    ]
    call_delay_words = [
        0x0C008000, 0x3C098009, 0x3088003F, 0x01285021,
        0xAD420000, 0x0800C000, 0x00000000,
    ]
    rows = []
    cases = (
        ("SAFE_BASE", safe_words),
        ("JOIN_BASE", join_words),
        ("GP_ENTRY", gp_entry_words),
        ("GP_REDEFINED", gp_redefined_words),
        ("TRUNCATED_JUMP", truncated_jump_words),
        ("UNRESOLVED_JR", unresolved_jr_words),
        ("ORI_OVERLAP", ori_overlap_words),
        ("CALL_DELAY", call_delay_words),
    )
    for image, words in cases:
        path = tmp_path / f"{image}.bin"
        path.write_bytes(b"".join(word.to_bytes(4, "little") for word in words))
        rows.append(f"{image} {path} 0x{base:08x}")
    image_map = tmp_path / "images.txt"
    image_map.write_text("\n".join(rows) + "\n")
    queries = [
        (f"SAFE_BASE:0x{base:08x}:0x{base + len(safe_words) * 4:08x}:"
         f"t2:0x{base + 3 * 4:08x}"),
        (f"JOIN_BASE:0x{base:08x}:0x{base + len(join_words) * 4:08x}:"
         f"t2:0x{base + 5 * 4:08x}"),
        (f"GP_ENTRY:0x{base:08x}:0x{base + len(gp_entry_words) * 4:08x}:"
         f"t2:0x{base + 2 * 4:08x}"),
        (f"GP_REDEFINED:0x{base:08x}:"
         f"0x{base + len(gp_redefined_words) * 4:08x}:"
         f"t2:0x{base + 3 * 4:08x}"),
        (f"TRUNCATED_JUMP:0x{base:08x}:"
         f"0x{base + len(truncated_jump_words) * 4:08x}:"
         f"t2:0x{base + 3 * 4:08x}"),
        (f"UNRESOLVED_JR:0x{base:08x}:"
         f"0x{base + len(unresolved_jr_words) * 4:08x}:"
         f"t2:0x{base + 3 * 4:08x}"),
        (f"ORI_OVERLAP:0x{base:08x}:"
         f"0x{base + len(ori_overlap_words) * 4:08x}:"
         f"t2:0x{base + 5 * 4:08x}"),
        (f"CALL_DELAY:0x{base:08x}:"
         f"0x{base + len(call_delay_words) * 4:08x}:"
         f"t2:0x{base + 4 * 4:08x}"),
        (f"defsat@CALL_DELAY:0x{base:08x}:"
         f"0x{base + len(call_delay_words) * 4:08x}:"
         f"t1:0x{base:08x}"),
        (f"indexdom@JOIN_BASE:0x{base:08x}:"
         f"0x{base + len(join_words) * 4:08x}:t0:0x{base + 4 * 4:08x}"),
    ]
    proc = subprocess.run(
        [str(verifier.binary), str(image_map), *queries], cwd=ROOT,
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (safe, joined, gp_entry, gp_redefined, truncated_jump, unresolved_jr,
     ori_overlap, call_delay, call_boundary, index_domain) = \
        json.loads(proc.stdout)["queries"]

    safe_definition = next(
        row for row in safe["definitions"] if row["observable"])
    assert safe_definition["class"] == "table_address"
    assert safe_definition["table"] == "0x80090000"
    assert safe_definition["index"] == "t0"
    assert safe_definition["table_base_register"] == "t1"
    assert safe_definition["table_base_proof"] == ts.TABLE_BASE_PROOF

    joined_definition = next(
        row for row in joined["definitions"] if row["observable"])
    assert joined_definition["class"] == "opaque"
    assert joined_definition["table_address_failure"] == {
        "pc": "0x80010010",
        "word": "0x01285021",
        "reason": "table_base_operand_not_path_invariant",
    }
    gp_entry_definition = next(
        row for row in gp_entry["definitions"] if row["observable"])
    assert gp_entry_definition["class"] == "table_address"
    assert gp_entry_definition["table"] == "0x80081d98"
    assert gp_entry_definition["index"] == "t0"
    assert gp_entry_definition["table_base_register"] == "gp"
    assert gp_entry_definition["table_base_proof"] == ts.TABLE_BASE_PROOF

    ori_definition = next(
        row for row in ori_overlap["definitions"] if row["observable"])
    assert ori_definition["class"] == "table_address"
    assert ori_definition["table"] == "0x800823a0"
    assert ori_definition["index"] == "t0"
    assert ori_definition["table_base_register"] == "t1"
    assert ori_definition["table_base_proof"] == ts.TABLE_BASE_PROOF

    expected_failures = (
        (gp_redefined, "0x80010008", "0x03885021",
         "table_base_operand_not_path_invariant"),
        (truncated_jump, "0x80010010", "0x08004004",
         "control_transfer_delay_slot_outside_query_extent"),
        (unresolved_jr, "0x80010010", "0x01600008",
         "unresolved_indirect_jump_may_enter_query_extent"),
        (call_delay, "0x80010000", "0x0c008000",
         "call_delay_definition_clobbered_before_continuation"),
    )
    for answer, pc, word, reason in expected_failures:
        definition = next(
            row for row in answer["definitions"] if row["observable"])
        assert definition["class"] == "opaque"
        assert definition["table_address_failure"] == {
            "pc": pc, "word": word, "reason": reason,
        }
    boundary_definition = next(
        row for row in call_boundary["definitions"] if row["observable"])
    assert boundary_definition["class"] == "materialised_constant"
    assert boundary_definition["pc"] == "0x80010004"
    assert boundary_definition["value"] == "0x80090000"
    assert boundary_definition["call_boundary"] == \
        "before_callee_execution"
    assert index_domain["verdict"] is True
    assert index_domain["interval"]["min"] == 0
    assert index_domain["interval"]["max"] == 63


def test_call_boundary_preserves_link_writes_and_dynamic_phases(
        verifier, tmp_path):
    """A call boundary may hide a clobber, never the call's own link write.

    JAL writes ``ra`` and JALR writes its named ``rd`` before the delay slot.
    Suppressing either definition exposes a stale pre-call constant.  A
    source-dependent delay value must also reject a continuation that loops to
    the same static call, while a direct delay-slot LUI remains independent of
    invocation history.
    """
    base = 0x80010000
    cases = {
        "JAL_RA": [
            0x3C1F8009,       # stale pre-call: lui ra,0x8009
            0x0C008000,       # jal 0x80020000 (writes ra)
            0x27E40000,       # delay: addiu a0,ra,0 (reads new link)
            0x0800C000, 0x00000000,
        ],
        "JALR_LINK": [
            0x3C108009,       # stale pre-call: lui s0,0x8009
            0x3C198002,       # lui t9,0x8002
            0x03208009,       # jalr s0,t9 (writes link to s0)
            0x26040000,       # delay: addiu a0,s0,0 (reads new link)
            0x0800C000, 0x00000000,
        ],
        "REENTRY_SOURCE": [
            0x3C108009,       # lui s0,0x8009
            0x0C008000,       # jal 0x80020000
            0x26040000,       # delay: addiu a0,s0,0
            0x08004001,       # continuation loops to this same jal
            0x00000000,
        ],
        "REENTRY_DIRECT": [
            0x0C008000,       # jal 0x80020000
            0x3C048009,       # delay: direct, invocation-independent LUI
            0x08004000,       # continuation loops to this same jal
            0x00000000,
        ],
    }
    image_rows = []
    for image, words in cases.items():
        path = tmp_path / f"{image}.bin"
        path.write_bytes(
            b"".join(word.to_bytes(4, "little") for word in words))
        image_rows.append(f"{image} {path} 0x{base:08x}")
    image_map = tmp_path / "call-boundary-images.txt"
    image_map.write_text("\n".join(image_rows) + "\n")

    def query(image, reg, call_word):
        end = base + len(cases[image]) * 4
        return (f"defsat@{image}:0x{base:08x}:0x{end:08x}:"
                f"{reg}:0x{base + call_word * 4:08x}")

    proc = subprocess.run(
        [str(verifier.binary), str(image_map),
         query("JAL_RA", "ra", 1), query("JAL_RA", "a0", 1),
         query("JALR_LINK", "s0", 2), query("JALR_LINK", "a0", 2),
         query("REENTRY_SOURCE", "a0", 1),
         query("REENTRY_DIRECT", "a0", 0)],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (jal_link, jal_argument, jalr_link, jalr_argument,
     reentry_source, reentry_direct) = json.loads(proc.stdout)["queries"]

    for answer, pc in ((jal_link, base + 4), (jalr_link, base + 8)):
        observed = [row for row in answer["definitions"]
                    if row["observable"]]
        assert len(observed) == 1
        assert observed[0]["pc"] == f"0x{pc:08x}"
        assert observed[0]["class"] == "opaque"
        assert observed[0]["reason"] == "call_link_value_not_modelled"
        assert "value" not in observed[0]

    for answer in (jal_argument, jalr_argument, reentry_source):
        observed = [row for row in answer["definitions"]
                    if row["observable"]]
        assert len(observed) == 1
        assert observed[0]["class"] == "opaque"
        assert observed[0]["reason"] == \
            "call_delay_argument_not_a_tracked_constant"
        assert "value" not in observed[0]

    observed = [row for row in reentry_direct["definitions"]
                if row["observable"]]
    assert len(observed) == 1
    assert observed[0]["class"] == "materialised_constant"
    assert observed[0]["value"] == "0x80090000"
    assert observed[0]["call_boundary"] == "before_callee_execution"


def test_full_consumer_rejects_branch_bypassed_table_base(verifier, tmp_path):
    """The real upgrader must keep the convention when TABLE is not proved."""
    base = 0x80010000
    words = [
        0x30A8003F, 0x14800002, 0x00000000, 0x3C098009,
        0x01285021, 0xAD420000, 0x03E00008, 0x00000000,
    ]
    image_path = tmp_path / "JOIN_CONSUMER.bin"
    image_path.write_bytes(
        b"".join(word.to_bytes(4, "little") for word in words))
    image_map = tmp_path / "images-consumer.txt"
    image_map.write_text(f"JOIN_CONSUMER {image_path} 0x{base:08x}\n")

    class MappedVerifier:
        binary = verifier.binary

        def ask(self, *queries):
            proc = subprocess.run(
                [str(self.binary), str(image_map), *queries], cwd=ROOT,
                capture_output=True, text=True)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            return json.loads(proc.stdout)["queries"]

    index = {
        "images": [{
            "image_id": "JOIN_CONSUMER", "role": "resident",
            "identity_verified": True, "file_va_base": "0x80010000",
            "size": len(words) * 4, "path": str(image_path),
        }],
        "records": [{
            "image_id": "JOIN_CONSUMER", "entry": "0x80010000",
            "end": "0x80010020", "name": "join_consumer",
            "direct_jumps": [], "direct_calls": [], "branches": [],
            "indirect_jumps": [], "indirect_calls": [],
        }],
    }
    site = {
        "id": "JOIN_CONSUMER:0x80010014:t2",
        "function": "JOIN_CONSUMER:join_consumer@0x80010000",
        "base_register": "t2", "pc": "0x80010014", "width": 4,
        "offset": 0, "tiers": ["synthetic_convention"],
        "region_provenance": {"synthetic": True},
    }
    verdict_by_pc = {
        base + 5 * 4: [("JOIN_CONSUMER", "bounded_by_index_convention")],
    }
    remaining, upgraded, receipt = ts.upgrade_convention_with_index_intervals(
        [site], [(0x800823A0, 0x800823A2)], MappedVerifier(), index,
        verdict_by_pc)

    assert remaining == [site]
    assert upgraded == []
    assert receipt["exact_table_address_candidates"] == 0
    assert receipt["unique_index_queries"] == 0
    assert receipt["upgraded_site_count"] == 0
    assert verdict_by_pc[base + 5 * 4] == [
        ("JOIN_CONSUMER", "bounded_by_index_convention")]


def test_full_consumer_rejects_locally_redefined_gp_table_base(
        verifier, tmp_path):
    """The pinned entry GP cannot override an explicit reaching GP write."""
    base = 0x80010000
    words = [
        0x30A8003F, 0x0080E021, 0x03885021, 0xAD420000,
        0x03E00008, 0x00000000,
    ]
    image_path = tmp_path / "GP_REDEFINED_CONSUMER.bin"
    image_path.write_bytes(
        b"".join(word.to_bytes(4, "little") for word in words))
    image_map = tmp_path / "images-gp-consumer.txt"
    image_map.write_text(
        f"GP_REDEFINED_CONSUMER {image_path} 0x{base:08x}\n")

    class MappedVerifier:
        binary = verifier.binary

        def ask(self, *queries):
            proc = subprocess.run(
                [str(self.binary), str(image_map), *queries], cwd=ROOT,
                capture_output=True, text=True)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            return json.loads(proc.stdout)["queries"]

    index = {
        "images": [{
            "image_id": "GP_REDEFINED_CONSUMER", "role": "resident",
            "identity_verified": True, "file_va_base": "0x80010000",
            "size": len(words) * 4, "path": str(image_path),
        }],
        "records": [{
            "image_id": "GP_REDEFINED_CONSUMER", "entry": "0x80010000",
            "end": "0x80010018", "name": "gp_redefined_consumer",
            "direct_jumps": [], "direct_calls": [], "branches": [],
            "indirect_jumps": [], "indirect_calls": [],
        }],
    }
    site = {
        "id": "GP_REDEFINED_CONSUMER:0x8001000c:t2",
        "function": (
            "GP_REDEFINED_CONSUMER:gp_redefined_consumer@0x80010000"),
        "base_register": "t2", "pc": "0x8001000c", "width": 4,
        "offset": 0, "tiers": ["synthetic_convention"],
        "region_provenance": {"synthetic": True},
    }
    verdict_by_pc = {
        base + 3 * 4: [
            ("GP_REDEFINED_CONSUMER", "bounded_by_index_convention")],
    }
    remaining, upgraded, receipt = ts.upgrade_convention_with_index_intervals(
        [site], [(0x800823A0, 0x800823A2)], MappedVerifier(), index,
        verdict_by_pc)

    assert remaining == [site]
    assert upgraded == []
    assert receipt["exact_table_address_candidates"] == 0
    assert receipt["unique_index_queries"] == 0
    assert receipt["upgraded_site_count"] == 0
    assert verdict_by_pc[base + 3 * 4] == [
        ("GP_REDEFINED_CONSUMER", "bounded_by_index_convention")]


def test_full_consumer_uses_bitwise_ori_table_value(verifier, tmp_path):
    """Overlapping ORI bits must not turn an in-window table into a miss."""
    base = 0x80010000
    words = [
        0x3C098008, 0x352923A0, 0x35292000, 0x30880000,
        0x01285021, 0xAD420000,
    ]
    image_path = tmp_path / "ORI_OVERLAP_CONSUMER.bin"
    image_path.write_bytes(
        b"".join(word.to_bytes(4, "little") for word in words))
    image_map = tmp_path / "images-ori-overlap-consumer.txt"
    image_map.write_text(
        f"ORI_OVERLAP_CONSUMER {image_path} 0x{base:08x}\n")

    class MappedVerifier:
        binary = verifier.binary

        def ask(self, *queries):
            proc = subprocess.run(
                [str(self.binary), str(image_map), *queries], cwd=ROOT,
                capture_output=True, text=True)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            return json.loads(proc.stdout)["queries"]

    index = {
        "images": [{
            "image_id": "ORI_OVERLAP_CONSUMER", "role": "resident",
            "identity_verified": True, "file_va_base": "0x80010000",
            "size": len(words) * 4, "path": str(image_path),
        }],
        "records": [{
            "image_id": "ORI_OVERLAP_CONSUMER", "entry": "0x80010000",
            "end": "0x80010018", "name": "ori_overlap_consumer",
            "direct_jumps": [], "direct_calls": [], "branches": [],
            "indirect_jumps": [], "indirect_calls": [],
        }],
    }
    site = {
        "id": "ORI_OVERLAP_CONSUMER:0x80010014:t2",
        "function": (
            "ORI_OVERLAP_CONSUMER:ori_overlap_consumer@0x80010000"),
        "base_register": "t2", "pc": "0x80010014", "width": 4,
        "offset": 0, "tiers": ["synthetic_convention"],
        "region_provenance": {"synthetic": True},
    }
    verdict_by_pc = {
        base + 5 * 4: [
            ("ORI_OVERLAP_CONSUMER", "bounded_by_index_convention")],
    }
    remaining, upgraded, receipt = ts.upgrade_convention_with_index_intervals(
        [site], [(0x800823A0, 0x800823A2), (0x80082470, 0x80082472)],
        MappedVerifier(), index, verdict_by_pc)

    assert remaining == [site]
    assert upgraded == []
    assert receipt["exact_table_address_candidates"] == 1
    assert receipt["unique_index_queries"] == 1
    assert receipt["outcomes"] == {
        "proved_interval_does_not_exclude_every_window": 1}
    attempt = receipt["attempts_for_exact_table_address_candidates"][0]
    assert attempt["outcome"] == \
        "proved_interval_does_not_exclude_every_window"
    assert verdict_by_pc[base + 5 * 4] == [
        ("ORI_OVERLAP_CONSUMER", "bounded_by_index_convention")]


def test_full_consumer_rejects_call_delay_table_constant(verifier, tmp_path):
    """A caller-saved value written in a call slot does not survive the call."""
    base = 0x80010000
    words = [
        0x0C008000, 0x3C098009, 0x3088003F, 0x01285021,
        0xAD420000, 0x0800C000, 0x00000000,
    ]
    image_path = tmp_path / "CALL_DELAY_CONSUMER.bin"
    image_path.write_bytes(
        b"".join(word.to_bytes(4, "little") for word in words))
    image_map = tmp_path / "images-call-delay-consumer.txt"
    image_map.write_text(
        f"CALL_DELAY_CONSUMER {image_path} 0x{base:08x}\n")

    class MappedVerifier:
        binary = verifier.binary

        def ask(self, *queries):
            proc = subprocess.run(
                [str(self.binary), str(image_map), *queries], cwd=ROOT,
                capture_output=True, text=True)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            return json.loads(proc.stdout)["queries"]

    index = {
        "images": [{
            "image_id": "CALL_DELAY_CONSUMER", "role": "resident",
            "identity_verified": True, "file_va_base": "0x80010000",
            "size": len(words) * 4, "path": str(image_path),
        }],
        "records": [{
            "image_id": "CALL_DELAY_CONSUMER", "entry": "0x80010000",
            "end": "0x8001001c", "name": "call_delay_consumer",
            "direct_jumps": [{"pc": "0x80010014", "target": "0x80030000"}],
            "direct_calls": [{"pc": "0x80010000", "target": "0x80020000"}],
            "branches": [], "indirect_jumps": [], "indirect_calls": [],
        }],
    }
    site = {
        "id": "CALL_DELAY_CONSUMER:0x80010010:t2",
        "function": "CALL_DELAY_CONSUMER:call_delay_consumer@0x80010000",
        "base_register": "t2", "pc": "0x80010010", "width": 4,
        "offset": 0, "tiers": ["synthetic_convention"],
        "region_provenance": {"synthetic": True},
    }
    verdict_by_pc = {
        base + 4 * 4: [
            ("CALL_DELAY_CONSUMER", "bounded_by_index_convention")],
    }
    remaining, upgraded, receipt = ts.upgrade_convention_with_index_intervals(
        [site], [(0x800823A0, 0x800823A2)], MappedVerifier(), index,
        verdict_by_pc)

    assert remaining == [site]
    assert upgraded == []
    assert receipt["exact_table_address_candidates"] == 0
    assert receipt["unique_index_queries"] == 0
    assert receipt["upgraded_site_count"] == 0
    failure = receipt["base_classification_failures"][0]
    assert failure["id"] == site["id"]
    assert failure["base_definition_failures"][0][
        "table_address_failure"] == {
            "pc": "0x80010000", "word": "0x0c008000",
            "reason": "call_delay_definition_clobbered_before_continuation",
        }
    assert verdict_by_pc[base + 4 * 4] == [
        ("CALL_DELAY_CONSUMER", "bounded_by_index_convention")]


def test_full_consumer_keeps_cross_image_same_pc_indirect_blocker(
        verifier, tmp_path):
    """Only same-image sites are internal, even when numeric PCs collide."""
    base = 0x80010000
    safe_words = [
        0x30A8003F, 0x3C098009, 0x01285021, 0xAD420000,
        0x03E00008, 0x00000000,
    ]
    other_words = [
        0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x01000008, 0x00000000,  # jr t0 at the same numeric PC as A's jr ra
    ]
    safe_path = tmp_path / "SAME_PC_SAFE.bin"
    other_path = tmp_path / "SAME_PC_OTHER.bin"
    safe_path.write_bytes(
        b"".join(word.to_bytes(4, "little") for word in safe_words))
    other_path.write_bytes(
        b"".join(word.to_bytes(4, "little") for word in other_words))
    image_map = tmp_path / "images-same-pc.txt"
    image_map.write_text(
        f"SAME_PC_SAFE {safe_path} 0x{base:08x}\n"
        f"SAME_PC_OTHER {other_path} 0x{base:08x}\n")

    class MappedVerifier:
        binary = verifier.binary

        def ask(self, *queries):
            proc = subprocess.run(
                [str(self.binary), str(image_map), *queries], cwd=ROOT,
                capture_output=True, text=True)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            return json.loads(proc.stdout)["queries"]

    index = {
        "images": [
            {"image_id": "SAME_PC_SAFE", "role": "resident",
             "identity_verified": True, "file_va_base": "0x80010000",
             "size": len(safe_words) * 4, "path": str(safe_path)},
            # A malformed load base cannot prove mutual exclusion.  This image
            # therefore remains possibly co-resident and must block A.
            {"image_id": "SAME_PC_OTHER", "role": "overlay",
             "identity_verified": True, "file_va_base": True,
             "size": len(other_words) * 4, "path": str(other_path)},
        ],
        "records": [
            {"image_id": "SAME_PC_SAFE", "entry": "0x80010000",
             "end": "0x80010018", "name": "safe_table",
             "direct_jumps": [], "direct_calls": [], "branches": [],
             "indirect_jumps": [], "indirect_calls": []},
            {"image_id": "SAME_PC_OTHER", "entry": "0x80010000",
             "end": "0x80010018", "name": "other_dispatch",
             "direct_jumps": [], "direct_calls": [], "branches": [],
             "indirect_jumps": [{"pc": "0x80010010", "register": "t0"}],
             "indirect_calls": []},
        ],
    }
    site = {
        "id": "SAME_PC_SAFE:0x8001000c:t2",
        "function": "SAME_PC_SAFE:safe_table@0x80010000",
        "base_register": "t2", "pc": "0x8001000c", "width": 4,
        "offset": 0, "tiers": ["synthetic_convention"],
        "region_provenance": {"synthetic": True},
    }
    verdict_by_pc = {
        base + 3 * 4: [("SAME_PC_SAFE", "bounded_by_index_convention")],
    }
    remaining, upgraded, receipt = ts.upgrade_convention_with_index_intervals(
        [site], [(0x800923A0, 0x800923A2)], MappedVerifier(), index,
        verdict_by_pc)

    assert remaining == [site]
    assert upgraded == []
    assert receipt["exact_table_address_candidates"] == 1
    assert receipt["unique_index_queries"] == 1
    assert receipt["outcomes"] == {"external_interior_entry": 1}
    attempt = receipt["attempts_for_exact_table_address_candidates"][0]
    assert attempt["outcome"] == "external_interior_entry"
    assert attempt["first_external_entry"] == {
        "kind": "unknown_indirect_jump_target_domain",
        "image": "SAME_PC_OTHER",
        "from": "other_dispatch",
        "pc": "0x80010010",
        "target": None,
        "target_domain_complete": False,
        "reason": (
            "unknown indirect target domain cannot exclude entry into "
            "0x80010000..0x80010018"),
        "source_site_id": "indirect_jump:SAME_PC_OTHER:0x80010010",
        "word": "0x01000008",
    }
    assert verdict_by_pc[base + 3 * 4] == [
        ("SAME_PC_SAFE", "bounded_by_index_convention")]


def test_public_indexdom_rejects_detached_architecture_counterexamples(
        verifier, tmp_path):
    """The ratchets must hold through the public query parser, not only self-test."""
    base = 0x80010000
    cases = {
        "ALIAS": (
            [0x2C840001, 0x10800004, 0, 0xAC820000, 0x08004008,
             0, 0x03E00008, 0, 0x03E00008, 0],
            "a0", 3, "0x2c840001",
            "definition_operation_not_in_interval_whitelist"),
        "NONLINEAR": (
            [0x08004003, 0x84A40000, 0, 0x2C890010, 0x11200004,
             0, 0xAC820000, 0x03E00008, 0, 0x03E00008, 0],
            "a0", 6, "0x84a40000", "load_is_not_unsigned_lbu_or_lhu"),
        "SYSCALL": (
            [0x3088003F, 0x0000000C, 0xAD020000, 0x03E00008, 0],
            "t0", 2, "0x0000000c", "syscall_exception_transfer_not_modelled"),
        "COPBRANCH": (
            [0x3088003F, 0x49010001, 0, 0xAD020000, 0x03E00008, 0],
            "t0", 3, "0x49010001",
            "coprocessor_conditional_branch_not_modelled"),
        "DEADGUARD": (
            [0x08004003, 0, 0x2C890010, 0x15200003, 0,
             0x03E00008, 0, 0xAC820000, 0x03E00008, 0],
            "a0", 7, "0xac820000",
            "path_reaches_query_without_definition_or_guard"),
        "DUALCONTEXT": (
            [0x08004005, 0, 0xAD020000, 0x08004040, 0,
             0x1480FFFB, 0, 0x30A8003F, 0x08004002, 0],
            "t0", 2, "0x00000000",
            "delay_slot_word_has_ordinary_entry_not_modelled"),
        "RAREENTRY": (
            [0x3C1F8001, 0x37FF0028, 0x14800004, 0,
             0x30C8003F, 0x0800400A, 0, 0x03E00008, 0, 0,
             0xAD020000, 0x03E00008, 0],
            "t0", 10, "0x03e00008",
            "locally_defined_ra_indirect_target_not_modelled"),
    }
    map_rows = []
    queries = []
    expected = {}
    for image, (words, register, site, breaker, reason) in cases.items():
        path = tmp_path / f"{image}.bin"
        path.write_bytes(b"".join(word.to_bytes(4, "little") for word in words))
        map_rows.append(f"{image} {path} 0x{base:08x}")
        queries.append(
            f"indexdom@{image}:0x{base:08x}:0x{base + len(words) * 4:08x}:"
            f"{register}:0x{base + site * 4:08x}")
        expected[image] = (breaker, reason)
    image_map = tmp_path / "images.txt"
    image_map.write_text("\n".join(map_rows) + "\n")
    proc = subprocess.run(
        [str(verifier.binary), str(image_map), *queries],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    answers = json.loads(proc.stdout)["queries"]
    assert len(answers) == len(cases)
    for answer in answers:
        assert answer["verdict"] is False
        breaker, reason = expected[answer["image"]]
        assert answer["breaking_instruction"] == {
            "pc": answer["breaking_instruction"]["pc"],
            "word": breaker,
            "reason": reason,
        }


def test_public_indexdom_rejects_transfer_without_in_extent_delay_slot(
        verifier, tmp_path):
    """A truncated transfer must not erase its delay-slot successor paths."""
    base = 0x80010000
    cases = {
        "J_EDGE": ([0x3088003F, 0xAD020000, 0x84A80000,
                    0x08004001, 0], "0x08004001"),
        "B_EDGE": ([0x3088003F, 0xAD020000, 0x84A80000,
                    0x1000FFFD, 0], "0x1000fffd"),
    }
    map_rows = []
    queries = []
    for image, (words, _) in cases.items():
        path = tmp_path / f"{image}.bin"
        path.write_bytes(b"".join(word.to_bytes(4, "little") for word in words))
        map_rows.append(f"{image} {path} 0x{base:08x}")
        # The image contains the delay slot; the declared analysis extent does
        # not. The query must reject the final in-extent transfer itself.
        queries.append(
            f"indexdom@{image}:0x{base:08x}:0x{base + 4 * 4:08x}:"
            f"t0:0x{base + 4:08x}")
    image_map = tmp_path / "images.txt"
    image_map.write_text("\n".join(map_rows) + "\n")
    proc = subprocess.run(
        [str(verifier.binary), str(image_map), *queries],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    answers = json.loads(proc.stdout)["queries"]
    assert len(answers) == len(cases)
    for answer in answers:
        assert answer["verdict"] is False
        assert answer["interval"] is None
        assert answer["breaking_instruction"] == {
            "pc": "0x8001000c",
            "word": cases[answer["image"]][1],
            "reason": "control_transfer_delay_slot_outside_query_extent",
        }


def test_writer_probe_finds_six_known_writers_and_reports_its_residual(verifier):
    writers = verifier.ask("writers@SCUS_942_88:0x80090748")[0]
    assert [row["pc"] for row in writers["writers"]] == [
        "0x8003a49c", "0x80049c10", "0x80049c14",
        "0x8004a4b4", "0x8004d378", "0x8004d43c"]
    assert writers["writer_count"] == 6
    assert writers["computed_base_writers"] == 2
    move = next(row for row in writers["writers"] if row["pc"] == "0x80049c10")
    assert move["address_spelling"] == "materialise_then_scaled_index"
    assert move["value_source_kind"] == "existing_entry_from_same_table_family"
    assert move["value_source_pc"] == "0x80049c08"
    clear = next(row for row in writers["writers"] if row["pc"] == "0x80049c14")
    assert clear["clears_to_null"] is True
    assert writers["enumeration_complete"] is False
    assert writers["recognizer_residual_store_words"] == 10995


# ---------------------------------------------------------------- ABI ----
# Increment 3. These pin the behaviour that distinguishes reading the callers
# from counting them.

def _arg_binding():
    doc, _ = ts.load_schema(SCHEMA)
    return copy.deepcopy(next(b for b in doc["region_bindings"]
                              if b["provenance"] == "caller_argument"))


@pytest.fixture(scope="module")
def ledger() -> dict:
    return json.loads((ROOT / "analysis/phase4_f01_frontier_blockers.json").read_bytes())


@pytest.fixture(scope="module")
def regions() -> dict:
    doc, _ = ts.load_schema(SCHEMA)
    return {r["id"]: (ts._int(r["start"]), ts._int(r["end"])) for r in doc["regions"]}


def test_argument_value_is_read_from_the_callers(index, ledger, verifier, regions):
    """The constant must come from the instructions, not the schema's prose."""
    ok, why, attest = ts.verify_caller_argument(_arg_binding(), index, ledger,
                                                verifier, regions)
    assert ok, why
    assert attest["agreed_value"] == "0x800a6500"
    assert attest["argument"] == "a0"
    assert attest["read_from_instructions"] is True
    # every direct caller is named, with the call site it was read at
    assert attest["callers"], "a verified argument must name its callers"
    for caller in attest["callers"]:
        assert caller["value"] == "0x800a6500"
        assert caller["call_pc"].startswith("0x")


@pytest.mark.parametrize("extent,label", [
    ((0x800A6600, 0x800A6700), "region entirely above the value"),
    ((0x800A6000, 0x800A6100), "region entirely below the value"),
])
def test_argument_rejected_when_the_region_excludes_the_value(
        index, ledger, verifier, regions, extent, label):
    """Move the region off the recovered value and acceptance must collapse.

    This is what proves the verdict is driven by the value read out of the
    callers. A check that merely counted callers would pass all of these.
    """
    probe = {**regions, "player_actor": extent}
    ok, why, _ = ts.verify_caller_argument(_arg_binding(), index, ledger, verifier, probe)
    assert ok is False, label
    assert "outside player_actor" in why


def test_argument_rejected_for_a_register_that_is_not_argument_derived(
        index, ledger, verifier, regions):
    binding = _arg_binding()
    binding["register"] = "v0"
    ok, why, _ = ts.verify_caller_argument(binding, index, ledger, verifier, regions)
    assert ok is False
    assert "neither the incoming argument" in why


def test_argument_rejected_when_the_binding_bounds_nothing(
        index, ledger, verifier, regions):
    """A binding with no site in the ledger is dead weight, not a pass.

    The a0 binding this repo used to carry was exactly this, and the old
    caller-counting check accepted it.
    """
    binding = _arg_binding()
    binding["register"] = "a0"
    ok, why, _ = ts.verify_caller_argument(binding, index, ledger, verifier, regions)
    assert ok is False
    assert "no unresolved site" in why


def test_copy_chase_reaches_the_incoming_argument(verifier):
    """s1 is `addu s1, a0, zero`; the chase has to see through it."""
    q = verifier.ask("SCUS_942_88:0x80048138:0x800498ac:s1")[0]
    observed = [d for d in q["definitions"] if d["observable"]]
    assert any(d["class"] == "register_copy" and d["incoming"] == "a0" for d in observed)


def test_delay_slot_is_where_the_argument_is_set(verifier):
    """MIPS runs the delay slot before the call transfers control.

    Asking at the jal itself sees the jal's own clobber and answers
    `call_result` -- wrong, and confidently so.
    """
    q = verifier.ask("defsat@SCUS_942_88:0x8004ecd4:0x8004f478:a0:0x8004efd8")[0]
    observed = [d for d in q["definitions"] if d["observable"]]
    assert len(observed) == 1
    assert observed[0]["class"] == "materialised_constant"
    assert observed[0]["value"] == "0x800a6500"
    assert observed[0]["pc"] == "0x8004efdc", "the delay slot, not the jal"


def test_return_typing_answers_and_reports_stubs(verifier):
    """`returns@` classifies v0 at the return points, and says so when there are none."""
    sfx, memset_ = verifier.ask(
        "returns@SCUS_942_88:0x80050994:0x80050c40",
        "returns@SCUS_942_88:0x8005f7ac:0x8005f7b8")
    assert sfx["no_return_site"] is False and sfx["targeted_sites"] >= 1
    assert sfx["definitions"], "a function with a return point must classify v0"
    # a thunk with no `jr ra` is an answer, not a crash -- one bad query must not
    # take down a whole batch
    assert memset_["no_return_site"] is True
    assert memset_["targeted_sites"] == 0


SURVEY = ROOT / "analysis/phase4_f01_abi_survey.json"
RESIDENT_IMAGE_ID = ts.RESIDENT_IMAGE


def test_retained_survey_is_fresh():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_typed_state.py"), str(SCHEMA),
         "--output", str(RETAINED), "--survey", str(SURVEY), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_abi_survey_states_the_negative_result_in_numbers():
    """Argument typing does not decide F01's residual, and this says so measurably.

    The ABI accelerator's honest outcome on F01 is that almost every remaining
    blocked base is LOCALLY COMPUTED -- an index, a load, arithmetic -- not an
    argument. A negative result written only in prose rots; this one is
    regenerated from the same check the compiler runs.
    """
    survey = json.loads(SURVEY.read_bytes())
    # every covered store is either already bounded or still open -- no third bucket
    assert (survey["blocking_stores_already_bounded"] + survey["blocking_stores_still_open"]
            == survey["blocking_stores_covered"])
    assert survey["blocking_stores_still_open"] == sum(
        r["blocking_stores_still_open"] for r in survey["rows"])
    by_kind = {}
    for row in survey["rows"]:
        by_kind[row["verdict_kind"]] = (by_kind.get(row["verdict_kind"], 0)
                                        + row["blocking_stores_still_open"])
    assert by_kind["not_argument_derived"] > 0.8 * survey["blocking_stores_still_open"], (
        "if this stops dominating, argument typing has become worth extending")
    # residual is counted per SITE: a group with one bounded store and nine open
    # ones is nine of residual, not zero
    assert survey["blocking_stores_already_bounded"] > 0
    for row in survey["rows"]:
        assert (row["blocking_stores_already_bounded"] + row["blocking_stores_still_open"]
                == row["blocking_stores"])
        assert row["already_bounded_by"] is None or set(row["already_bounded_by"]) <= {
            "proof", "index_convention", "assertion"}


def test_abi_survey_uses_the_widest_region_so_it_measures_recovery_not_placement():
    """A group must fail the survey only when the VALUE cannot be recovered."""
    survey = json.loads(SURVEY.read_bytes())
    assert "widest possible region" in survey["method"]
    for row in survey["rows"]:
        assert "outside" not in row["verdict"], (
            "a region-placement rejection cannot appear in a widest-region survey")


def test_result_does_not_depend_on_where_the_checkout_lives(verifier):
    """An independent verifier recomputes from a DIFFERENT directory.

    The image map handed to the ASM verifier once carried absolute paths, so its
    sha256 -- and therefore the whole artifact -- changed with the checkout
    location. The retained result then failed `--check` in a clean worktree,
    which is exactly the situation the workbench's "recompute from a committed
    clean checkout" rule creates.
    """
    content = verifier.image_map.read_text()
    assert str(ROOT) not in content, (
        "the image map embeds an absolute path; the artifact will not reproduce "
        "from a clean checkout elsewhere")
    for line in content.splitlines():
        path = line.split()[1]
        assert not path.startswith("/"), path
        assert (ROOT / path).is_file(), path


# ------------------------------------------- proved_jr_cluster_argument ----
# The island's two stores were the first sites ever bounded ACROSS a jr edge --
# and then REOPENED by the 2026-08-06 review: "loads from the table" is not
# "points into the region" until the written-value domains are proved (they now
# are) AND the table-writer universe is proved exhaustive (it is NOT -- a
# measured corpus of undecided stores could alias the table, the same open
# problem as Item 2 itself). The binding therefore stays REJECTED on exactly
# that named link, with every other link proved in the attestation.

def _schema_regions():
    doc, _ = ts.load_schema(SCHEMA)
    return {r["id"]: (ts._int(r["start"]), ts._int(r["end"])) for r in doc["regions"]}


def _island_binding():
    doc, _ = ts.load_schema(SCHEMA)
    return copy.deepcopy(next(b for b in doc["region_bindings"]
                              if b["provenance"] == "proved_jr_cluster_argument"))


def test_island_binding_is_rejected_on_the_two_named_writer_links(
        index, ledger, verifier, regions):
    """Structure closes; value induction and writer exhaustiveness stay open.

    accepted must be False while ANY store in ANY image has an undecided
    effective address that could alias the table -- an enumerated writer set
    is a corrected KNOWN LOWER bound, not a census. The new compaction move
    preserves the table domain only conditionally and cannot prove its premise.
    """
    ok, why, attest = ts.verify_proved_jr_cluster_argument(
        _island_binding(), index, ledger, verifier, regions)
    assert ok is False
    assert "not proved exhaustive" in why and "Item 2" in why
    # -- and every structural link IS proved, in the attestation:
    facts = attest["island_facts"]
    assert facts["prologue"] == {"copy_pc": "0x8004c144", "argument": "a0",
                                 "straight_line": True}
    kinds = sorted(w["kind"] for w in facts["writes"])
    assert kinds == ["prologue_argument_copy", "terminal_epilogue_restore"]
    assert attest["proved_edge"]["jr_site"] == "0x8004c868"
    assert attest["writer_index_crosscheck_no_index_only"] is True
    assert attest["writer_enumeration_corroborated"] is False
    assert attest["known_writer_identity"]["exact_match"] is True
    assert attest["known_writer_identity"]["gained_known_writers"] == [
        "0x80049c10", "0x80049c14"]
    ei = attest["cluster_entry_integrity"]
    assert len(ei["images_walked"]) == 21 and ei["intruders"] == []
    assert ei["jr_sources_armed"]["gate"]["verified"] is True
    # finding 1: nulls and the publisher are proved; the move is conditional.
    domains = {d["pc"]: d for d in attest["writer_value_domains"]}
    assert domains["0x8003a49c"]["kind"] == "null"
    assert domains["0x80049c14"]["kind"] == "null"
    assert domains["0x8004a4b4"]["kind"] == "null"
    assert domains["0x8004d43c"]["kind"] == "null"
    move = domains["0x80049c10"]
    assert move["kind"] == "same_table_entry_move"
    assert move["instruction_fact_proved"] is True
    assert move["value_domain_proved"] is False
    assert "least fixed point" in " ".join(move["what_would_prove_the_induction"])
    prog = domains["0x8004d378"]["proof"]
    assert prog["verdict"] is True
    assert ts._int(prog["anchor"]) == 0x8009FD80 and prog["stride"] == 0x84
    # finding 2 measured, not assumed: both residuals are nonzero and the
    # independent resolved-write falsifier is re-run over the six-writer set.
    universe = attest["table_writer_universe"]
    assert universe["exhaustive"] is False
    assert universe["corpus_undecided_stores"] > 0
    assert set(universe["enumerated_writers_missing_from_resolved_hits"]) == {
        "0x80049c10", "0x80049c14", "0x8004d378", "0x8004d43c"}
    assert universe["resolved_writers_not_previously_enumerated"] == []
    assert universe["known_writer_set_gained"] == ["0x80049c10", "0x80049c14"]
    assert universe["writer_recognizer_residual_store_words"] > 0
    assert "jalr" in " ".join(attest["residual_assumptions"])
    assert attest["caller_typing_failures"] == [
        "mover_updater's s0 at 0x8004d5e0 is not uniformly loaded from one "
        "address"]
    mover_defs = attest["caller_typing"][0]["definitions"]
    mover_opaque = next(row for row in mover_defs
                        if row["pc"] == "0x8004d660")
    assert mover_opaque["table_address_failure"] == {
        "pc": "0x8004d690",
        "word": "0x03e00008",
        "reason": "locally_defined_ra_indirect_target_not_modelled",
    }


def test_the_two_island_ids_are_REOPENED_not_proof_bounded(compiled):
    """The exact consequence of the review: both ids back in still_unresolved."""
    reopened = sorted(r["id"] for r in compiled["still_unresolved"]
                      if "jr_target_island" in r["id"])
    assert reopened == [
        "unresolved_access:SCUS_942_88:jr_target_island_8004c898"
        "@0x8004c898@0x8004C8A0",
        "unresolved_access:SCUS_942_88:jr_target_island_8004c898"
        "@0x8004c898@0x8004C8A8",
    ]
    assert not any("jr_target_island" in r["id"] for r in compiled["bounded_by_proof"])
    binding = next(b for b in compiled["bindings"]
                   if b["provenance"] == "proved_jr_cluster_argument")
    assert binding["accepted"] is False
    assert "not proved exhaustive" in binding["verdict"]


def test_typed_pointer_load_is_rejected_on_the_same_two_writer_gates(compiled):
    """No proof bucket may grandfather a premise the fresh verifier falsified."""
    binding = next(b for b in compiled["bindings"]
                   if b["provenance"] == "typed_pointer_load")
    attest = binding["attestation"]
    assert binding["accepted"] is False
    assert "cannot be grandfathered as proof" in binding["verdict"]
    assert attest["writer_value_domains_proved"] is False
    assert "same-table" in attest["writer_value_domains_failure"]
    assert attest["table_writer_universe"]["exhaustive"] is False
    gate = attest["hard_truth_gate"]
    assert gate["required_predicates"] == [
        "writer_value_domains_proved",
        "table_writer_universe.exhaustive",
    ]
    assert gate["writer_value_domains_proved"] is False
    assert gate["table_writer_universe_exhaustive"] is False
    assert gate["accepted"] is False
    assert "cannot be grandfathered" in gate["decision"]
    assert attest["definition_gate_failures"] == [
        "the definitions reaching these sites do not all load from one address"]
    opaque = next(row for row in attest["definitions"]
                  if row["pc"] == "0x8004b698")
    assert opaque["table_address_failure"] == {
        "pc": "0x8004b6d4",
        "word": "0x03e00008",
        "reason": "locally_defined_ra_indirect_target_not_modelled",
    }
    assert not any(r["provenance"] == "typed_pointer_load"
                   for r in compiled["bounded_by_proof"])
    reopened = [r for r in compiled["still_unresolved"]
                if "actor_player_contact_resolver@0x8004abf4" in r["function"]
                and r["base_register"] == "s1"]
    assert len(reopened) == attest["targeted_sites"] == 54


def test_island_binding_rejected_when_the_table_is_wrong(index, ledger, verifier,
                                                         regions):
    """A wrong table must fail on the caller-typing link, before the gate."""
    binding = _island_binding()
    binding["pointer_table"] = "0x80090744"
    ok, why, _ = ts.verify_proved_jr_cluster_argument(binding, index, ledger,
                                                      verifier, regions)
    assert not ok
    assert "0x80090744" in why and "loads from" in why


def test_island_binding_rejected_when_the_prologue_is_cut_off(index, ledger,
                                                              verifier, regions):
    """A cluster that starts past the argument copy proves nothing about s0.

    [0x8004C818, 0x8004D224) tiles exactly onto contiguous records and contains
    both the jr site and the island, so the bookkeeping checks all pass -- the
    rejection has to come from the INSTRUCTIONS or the entry walk, never from
    the exhaustiveness gate (which would mean the unsound cluster sailed
    through every structural check).
    """
    binding = _island_binding()
    binding["cluster"] = {"start": "0x8004C818", "end": "0x8004D224"}
    ok, why, _ = ts.verify_proved_jr_cluster_argument(binding, index, ledger,
                                                      verifier, regions)
    assert not ok, "a cluster with no governing prologue must not pass"
    assert "exhaustive" not in why, "must fail BEFORE the final gate"


def test_island_binding_rejected_when_the_cluster_head_is_cut_off(index, ledger,
                                                                  verifier, regions):
    """Dropping the interpreter head makes its edges EXTERNAL entries.

    [0x8004C228, 0x8004D224) still tiles onto contiguous records, but the head
    it excludes branches/jumps into the op handlers -- now interior addresses
    entered from outside by non-call edges, caught by the whole-image
    seven-successor walk.
    """
    binding = _island_binding()
    binding["cluster"] = {"start": "0x8004C228", "end": "0x8004D224"}
    ok, why, _ = ts.verify_proved_jr_cluster_argument(binding, index, ledger,
                                                      verifier, regions)
    assert not ok
    assert "non-call edge" in why


def test_an_outside_jr_target_landing_at_cluster_start_is_an_untyped_entry(
        index, ledger, verifier, regions):
    """Codex mutation: jr INTO cluster.start must reject, not count as a caller.

    Real data provides the case: declaring the cluster to START at the island
    entry puts the gate-proved jr at 0x8004C868 OUTSIDE the cluster, and its
    proved target lands exactly on the new cluster start. That entry carries no
    typed argument, so it must be an intruder -- if this ever passes, a jr edge
    is being silently treated as a jal.
    """
    binding = _island_binding()
    binding["cluster"] = {"start": "0x8004C898", "end": "0x8004D224"}
    ok, why, attest = ts.verify_proved_jr_cluster_argument(binding, index, ledger,
                                                           verifier, regions)
    assert not ok
    assert "non-call edge" in why or "jr site" in why


def test_a_fabricated_non_null_writer_fails_the_value_domain_proof(index, verifier):
    """Codex mutation: an arbitrary non-null writer must not inherit the region.

    A writer whose value register is v1 at a store where v1 is a loaded field
    (not an anchored progression) must fail `progression@` -- if it passed, any
    store could be declared a pool publisher.
    """
    fake = {"writers": [
        {"pc": "0x8004d378", "value_register": "s2", "clears_to_null": False},
        {"pc": "0x8004d55c", "value_register": "v0", "clears_to_null": False},
    ], "writer_count": 2, "non_null_writers": 2}
    ok, domains, why = ts._prove_writer_value_domains(
        verifier, index, "SCUS_942_88", 0x8009FD80, fake)
    assert ok is False
    assert "NOT an anchored progression" in why or "domain" in why


def test_the_sound_alternative_cluster_reaches_both_final_writer_gates(
        index, ledger, verifier, regions):
    """[0x8004C13C, 0x8004C8AC) is structurally sound; writer gates stop it.

    The motion/chase tail never re-enters that range, so the prologue governs
    every entry and the write census holds. A checker that rejected it EARLIER
    would be pattern-matched to one blessed declaration; a checker that
    ACCEPTED it would be ignoring the writer-universe gate. The only correct
    outcome is rejection at the conditional-move and exhaustiveness links.
    """
    binding = _island_binding()
    binding["cluster"] = {"start": "0x8004C13C", "end": "0x8004C8AC"}
    ok, why, _ = ts.verify_proved_jr_cluster_argument(binding, index, ledger,
                                                      verifier, regions)
    assert ok is False
    assert "not proved exhaustive" in why, (
        "every structural check must pass for this sound declaration; "
        f"got: {why}")
    assert "same-table content invariant" in why
