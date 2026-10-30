#!/usr/bin/env python3
"""Build the F01 ABI ledger from pinned extents and a compiled C decoder.

Python owns identity, scope reconciliation, retained-proof joins, and the
receipt.  tools/phase4_f01_abi_probe.c alone reads and decodes instruction
words.

Usage:
  python3 tools/phase4_f01_abi_ledger.py --write
  python3 tools/phase4_f01_abi_ledger.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_f01_abi_ledger.json"
PROBE_SOURCE = ROOT / "tools/phase4_f01_abi_probe.c"
FRONTIER = ROOT / "analysis/phase4_f01_frontier_result.json"
TYPED_STATE = ROOT / "analysis/phase4_f01_typed_state.json"
LOCAL_BASE = ROOT / "analysis/phase4_f01_local_base_recovery.json"
ABI_SURVEY = ROOT / "analysis/phase4_f01_abi_survey.json"
STATIC_INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
HOISTED = ROOT / "analysis/hoisted_load_idiom_scan.json"
DISCIPLINE_PILOT = ROOT / "analysis/phase4_discipline_pilot.json"
TYPED_SCHEMA = ROOT / "config/phase4_f01_typed_state.yaml"
REGION_PROVENANCE_SOURCE = ROOT / "tools/region_provenance.c"

ISSUED_COMMIT = "1de4e4e0eba9020e4f3417631ffe5650d20b78f2"
ISSUED_STATUS_LINES = 117
ISSUED_STATUS_SHA256 = "547e11db97bc156fc7719494f48a8ad416745e5af5a2c335a1516b21c67a1dc2"


class LedgerError(RuntimeError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    return json.loads(raw), raw


def integer(value: int | str) -> int:
    return value if isinstance(value, int) else int(value, 0)


def canonical_id(record: dict) -> str:
    name = record.get("name")
    shown = "<unnamed>" if name is None else str(name)
    return f"{record['image_id']}:{shown}@0x{integer(record['entry']):08x}"


def source_key(text: str) -> tuple[str, int]:
    return text.split(":", 1)[0], integer(text.rsplit("@", 1)[1])


def fraction(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100.0 * numerator / denominator, 3) if denominator else None,
    }


def compile_probe(directory: Path) -> tuple[Path, str, str]:
    binary = directory / "phase4_f01_abi_probe"
    argv = [
        "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
        "-o", str(binary), PROBE_SOURCE.relative_to(ROOT).as_posix(),
    ]
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise LedgerError(f"compiled C probe failed to build:\n{proc.stderr}")
    version = subprocess.run(
        ["cc", "--version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()[0]
    return binary, sha(binary.read_bytes()), version


def scope_from_inputs(frontier: dict, typed: dict, local: dict, index: dict) -> tuple[list[dict], dict]:
    records = {
        (row["image_id"], integer(row["entry"])): row
        for row in index["records"] if row.get("entry") is not None
    }

    frontier_raw = set(frontier["graph"]["reached_functions"])
    roots_raw = set(frontier["graph"]["roots"])
    if frontier_raw != roots_raw:
        raise LedgerError("frontier roots and reached_functions differ")
    frontier_keys = {source_key(value) for value in frontier_raw}

    typed_raw: set[str] = set()
    typed_collections = (
        "bounded_by_proof", "bounded_by_assertion_only",
        "bounded_by_index_convention", "still_unresolved",
    )
    typed_by_collection: dict[str, set[tuple[str, int]]] = {}
    for collection in typed_collections:
        values = {str(row["function"]) for row in typed[collection] if row.get("function")}
        typed_raw |= values
        typed_by_collection[collection] = {source_key(value) for value in values}
    typed_keys = {source_key(value) for value in typed_raw}

    local_keys = {
        (str(row["image"]), integer(row["extent"][0])) for row in local["sites"]
    }
    union = frontier_keys | typed_keys | local_keys
    missing_index = sorted(union - set(records))
    if missing_index:
        raise LedgerError(f"scope keys absent from static index: {missing_index[:4]}")
    selected = [records[key] for key in sorted(union)]
    canonical = {key: canonical_id(records[key]) for key in union}

    def source_receipt(name: str, keys: set[tuple[str, int]], definition: str) -> dict:
        return {
            "source": name,
            "definition": definition,
            "count": len(keys),
            "contributed_to_union": sorted(canonical[key] for key in keys),
            "in_scope_absent_from_source": sorted(canonical[key] for key in union - keys),
            "source_outside_union": sorted(
                f"{image}@0x{entry:08x}" for image, entry in keys - union
            ),
        }

    name_disagreements = []
    for raw in sorted(frontier_raw):
        key = source_key(raw)
        if raw.lower() != canonical[key].lower():
            name_disagreements.append({
                "frontier_identifier": raw,
                "static_index_identifier": canonical[key],
                "same_image_and_entry": True,
            })

    return selected, {
        "definition": (
            "union by exact (image, entry) of frontier reached functions, functions "
            "whose extents occur in the four retained typed-state outcome collections, "
            "and local-base site owner extents; identity/name/end come from the static index"
        ),
        "count": len(union),
        "in_scope": sorted(canonical.values()),
        "sources": [
            source_receipt(
                "analysis/phase4_f01_frontier_result.json::graph.reached_functions",
                frontier_keys,
                "the exact reached-function set; roots are independently required equal",
            ),
            source_receipt(
                "analysis/phase4_f01_typed_state.json::outcome function extents",
                typed_keys,
                "unique function identifiers in bounded_by_proof, bounded_by_assertion_only, "
                "bounded_by_index_convention, and still_unresolved",
            ),
            source_receipt(
                "analysis/phase4_f01_local_base_recovery.json::sites owner extents",
                local_keys,
                "unique exact (image, extent start) owners of all retained site rows",
            ),
        ],
        "typed_state_collection_counts": {
            key: len(value) for key, value in typed_by_collection.items()
        },
        "source_relationships": {
            "frontier_roots_equal_reached_functions": True,
            "typed_state_is_subset_of_frontier": typed_keys <= frontier_keys,
            "local_base_owners_are_subset_of_frontier": local_keys <= frontier_keys,
            "typed_state_only": sorted(canonical[key] for key in typed_keys - frontier_keys),
            "local_base_only": sorted(canonical[key] for key in local_keys - frontier_keys),
            "frontier_absent_from_typed_state_count": len(frontier_keys - typed_keys),
            "frontier_absent_from_local_base_count": len(frontier_keys - local_keys),
        },
        "identifier_name_disagreements": name_disagreements,
        "identifier_rule": (
            "source names are never used to move an extent; the nine historical `fn` "
            "labels agree on image+entry and are replaced by the static-index names"
        ),
    }


EXPECTED_RA_HAZARD_SITES = {
    0x80018F44, 0x8001923C, 0x80019614, 0x80019B3C,
    0x80019F34, 0x8001A0DC, 0x8001A1D4,
}


def ra_hazard_pairs(pilot: dict) -> list[dict]:
    result = []
    sites = set()
    for row in pilot["per_site_outcomes"]:
        targets = (row.get("wall") or {}).get("observed_non_call_successor_targets")
        if not targets:
            continue
        site = integer(row["site_instruction"]["pc"])
        sites.add(site)
        for target in targets:
            result.append({
                "image": row["owner"]["image"],
                "site_pc": site,
                "observed_target": integer(target),
            })
    if sites != EXPECTED_RA_HAZARD_SITES:
        raise LedgerError(
            f"retained general-$ra caution universe moved: {sorted(sites)}"
        )
    if len(result) != 18 or {row["image"] for row in result} != {"SCUS_942_88"}:
        raise LedgerError("retained general-$ra caution pairs moved")
    return sorted(result, key=lambda row: (row["site_pc"], row["observed_target"]))


def write_manifest(
    path: Path, records: list[dict], index: dict, hoisted: dict, hazards: list[dict]
) -> str:
    lines = ["VERSION 1"]
    image_ids = {row["image_id"] for row in records}
    image_meta = {row["image_id"]: row for row in index["images"]}
    entry_call_witnesses: dict[tuple[str, int], list[int]] = defaultdict(list)
    for source in index["records"]:
        image_id = source["image_id"]
        for call in source.get("direct_calls") or []:
            entry_call_witnesses[(image_id, integer(call["target"]))].append(
                integer(call["pc"])
            )
    for image_id in sorted(image_ids):
        row = image_meta[image_id]
        lines.append(
            f"IMAGE {image_id} {row['path']} {integer(row['file_va_base']):08x} "
            f"{integer(row['size'])} {integer(row['runtime_gp']):08x}"
        )
    for row in records:
        name = str(row.get("name") or "<unnamed>").replace(" ", "_")
        witnesses = entry_call_witnesses.get(
            (row["image_id"], integer(row["entry"])), []
        )
        witness = min(witnesses) if witnesses else 0
        lines.append(
            f"FUNC {row['image_id']} {integer(row['entry']):08x} "
            f"{integer(row['end']):08x} {name} {int(bool(witness))} {witness:08x}"
        )
    # The retained hoisted family is resident code. It is deliberately supplied
    # as identities only; C must re-decode and re-match every word sequence.
    for row in hoisted["hits"]:
        lines.append(
            f"HOIST SCUS_942_88 {integer(row['load_pc']):08x} "
            f"{integer(row['logged_pc']):08x}"
        )
    # These retained runtime targets are caution/falsification evidence only.
    # C re-decodes both the exact jr $ra site and the instruction at target-8,
    # which would have created that target under call-link semantics.
    for row in hazards:
        lines.append(
            f"RAHAZARD {row['image']} {row['site_pc']:08x} "
            f"{row['observed_target']:08x}"
        )
    text = "\n".join(lines) + "\n"
    path.write_text(text)
    return sha(text.encode())


def region_names(address: int, regions: list[dict]) -> list[str]:
    return sorted(
        str(region["id"]) for region in regions
        if integer(region["start"]) <= address < integer(region["end"])
    )


def typed_site_map(typed: dict) -> dict[tuple[str, int], dict]:
    result: dict[tuple[str, int], dict] = {}
    for collection in (
        "bounded_by_proof", "bounded_by_assertion_only",
        "bounded_by_index_convention", "still_unresolved",
    ):
        for row in typed[collection]:
            fn = str(row.get("function") or "")
            if ":" not in fn or not row.get("pc"):
                continue
            key = (fn.split(":", 1)[0], integer(row["pc"]))
            value = {
                "typed_state_bucket": collection,
                "region": row.get("region"),
                "bound": row.get("bound"),
                "region_provenance": row.get("region_provenance"),
            }
            old = result.get(key)
            if old is not None and old != value:
                raise LedgerError(f"typed-state site has conflicting outcomes: {key}")
            result[key] = value
    return result


def enrich_rows(
    probe: dict, records: list[dict], typed: dict, index: dict, schema: dict
) -> list[dict]:
    probe_rows = {
        (row["image"], integer(row["entry"])): row for row in probe["rows"]
    }
    index_rows = {
        (row["image_id"], integer(row["entry"])): row for row in records
    }
    if set(probe_rows) != set(index_rows):
        raise LedgerError("C probe row identity differs from scoped static-index identity")
    typed_sites = typed_site_map(typed)
    regions = schema["regions"]
    accepted_argument_domains: dict[tuple[str, int, str], dict] = {}
    for binding in typed["bindings"]:
        attest = binding.get("attestation") or {}
        if not binding.get("accepted") or not attest.get("argument"):
            continue
        accepted_argument_domains[
            (binding["image"], integer(binding["function"]), attest["argument"])
        ] = {
            "kind": "pointer",
            "domain": binding["region"],
            "proof_source": "accepted retained typed-state binding",
            "binding_register": binding["register"],
            "agreed_value": attest.get("agreed_value"),
        }

    result = []
    for key in sorted(index_rows):
        source = index_rows[key]
        raw = probe_rows[key]
        raw["name"] = source.get("name")
        raw["end_exclusive"] = f"0x{integer(source['end']):08x}"
        raw["static_index_analysis_status"] = source["analysis_status"]
        raw["static_index_extent_fingerprint"] = source["exact_fingerprint"]

        arguments = []
        for argument in raw.pop("argument_registers"):
            domain = accepted_argument_domains.get((key[0], key[1], argument["register"]))
            if domain is None and argument["pointer_use_pc"] is not None:
                domain = {
                    "kind": "pointer",
                    "domain": "unknown",
                    "proof_source": (
                        "compiled-C read-before-write memory-base use proves pointer shape; "
                        "no retained region proof establishes its pointee domain"
                    ),
                }
            if domain is None:
                domain = {
                    "kind": "unknown",
                    "domain": "unknown",
                    "proof_source": (
                        "instruction proves consumption but not a stable pointer/scalar/index domain"
                    ),
                }
            arguments.append({**argument, "type_domain": domain})
        for argument in raw["stack_arguments"]:
            argument["type_domain"] = {
                "kind": "unknown", "domain": "unknown",
                "proof_source": "stack read-before-write proves location only",
            }
        raw["arguments"] = arguments

        indexed_accesses = [
            access for access in source.get("memory_accesses") or []
            if access.get("access") == "write"
        ]
        indexed_by_pc = {integer(access["pc"]): access for access in indexed_accesses}
        decoded_store_pcs = {integer(store["pc"]) for store in raw["decoded_stores"]}
        missing_index_stores = sorted(decoded_store_pcs - set(indexed_by_pc))
        if missing_index_stores:
            raise LedgerError(
                f"compiled-C stores absent from static-index access list at {key}: "
                f"{missing_index_stores[:4]}"
            )
        accesses = [indexed_by_pc[pc] for pc in sorted(decoded_store_pcs)]
        resolved, pointer, stack = [], [], []
        gp_by_pc = {integer(row["pc"]): row for row in raw["direct_gp_writes"]}
        for access in accesses:
            pc = integer(access["pc"])
            item = {
                "pc": f"0x{pc:08x}",
                "mnemonic": access["mnemonic"],
                "width": access["width"],
                "base_register": access["base_register"],
                "offset": access["offset"],
            }
            address = access.get("address")
            if address is not None:
                addr = integer(address)
                resolved.append({
                    **item,
                    "address": f"0x{addr:08x}",
                    "named_regions": region_names(addr, regions),
                    "gp_offset": addr - integer(
                        next(image for image in index["images"] if image["image_id"] == key[0])["runtime_gp"]
                    ),
                })
            elif access["base_register"] == "sp":
                stack.append(item)
            elif pc in gp_by_pc:
                # C decodes this directly even if the index did not resolve it.
                gp_item = gp_by_pc[pc]
                addr = integer(gp_item["address"])
                resolved.append({
                    **item,
                    "address": gp_item["address"],
                    "named_regions": region_names(addr, regions),
                    "gp_offset": gp_item["offset"],
                    "address_basis": "compiled-C direct $gp store decode",
                })
            else:
                pointer.append({**item, **(typed_sites.get((key[0], pc)) or {
                    "typed_state_bucket": "not_present_in_typed_state_site_universe",
                    "region": None, "bound": None, "region_provenance": None,
                })})
        raw["memory_side_effects"] = {
            "scope": (
                "direct entry-reachable stores decoded inside this function extent; "
                "transitive memory effects of nested callees are not attributed"
            ),
            "resolved_global_or_gp_writes": resolved,
            "unresolved_pointer_writes": pointer,
            "stack_writes_excluded_from_interface_side_effects": stack,
            "region_provenance_reuse": (
                "typed_state_bucket and region_provenance are joined verbatim by exact "
                "(image, pc) from the retained typed-state output; this ledger does not "
                "re-run or reinterpret tools/region_provenance.c"
            ),
            "all_decoded_store_sites_accounted_for": (
                len(accesses) == len(resolved) + len(pointer) + len(stack)
                == raw["decoded_store_sites"]
            ),
            "static_index_extent_stores_outside_compiled_c_entry_reachability": sorted(
                f"0x{pc:08x}" for pc in set(indexed_by_pc) - decoded_store_pcs
            ),
        }
        raw["abi_row_complete"] = True
        callee_statuses_resolved = all(
            not item["status"].startswith(("not_classified", "unknown_"))
            for item in raw["callee_saved"]
        )
        raw["callee_saved_effects_classified"] = bool(
            raw["mechanically_complete"] and callee_statuses_resolved
        )
        raw["callee_saved_effects_unclassified_reason"] = (
            None if raw["callee_saved_effects_classified"]
            else "compiled_cfg_incomplete"
            if not raw["mechanically_complete"]
            else "no_incoming_ra_continuation_or_ambiguous_save_state"
        )
        raw["fully_resolved"] = bool(
            raw["mechanically_complete"]
            and raw["frame"]["kind"] in {"none", "fixed"}
            and raw["return_convention"]["classification"]
            not in {
                "unknown_return_discipline", "unknown_entry_ra_provenance",
                "unknown_no_proved_normal_return",
            }
            and not any(item["ambiguous_save_slots"] for item in raw["callee_saved"])
            and raw["callee_saved_effects_classified"]
            and not pointer
            and all(arg["type_domain"]["domain"] != "unknown" for arg in arguments)
            and all(arg["type_domain"]["domain"] != "unknown" for arg in raw["stack_arguments"])
        )
        result.append(raw)
    return result


def survey_crosscheck(survey: dict, rows: list[dict]) -> dict:
    ledger = {(row["image"], integer(row["entry"])): row for row in rows}
    output = []
    for source in survey["rows"]:
        key = (source["image"], integer(source["function"]))
        row = ledger.get(key)
        if row is None:
            raise LedgerError(f"ABI survey function absent from ledger: {key}")
        argument = next(
            (arg for arg in row["arguments"] if arg["register"] == source["register"]),
            None,
        )
        ledger_exact_domain = bool(
            argument and argument["type_domain"]["domain"] != "unknown"
        )
        agreement = bool(source["typed"]) == ledger_exact_domain
        output.append({
            "image": source["image"],
            "function": source["function"],
            "register": source["register"],
            "survey_typed": source["typed"],
            "survey_verdict_kind": source["verdict_kind"],
            "survey_verdict": source["verdict"],
            "ledger_register_is_consumed_incoming_argument": argument is not None,
            "ledger_exact_domain_proved": ledger_exact_domain,
            "agreement": agreement,
            "interpretation": (
                "agreement on exact region-domain availability; generic pointer shape "
                "does not contradict the survey's failure to recover a region"
                if agreement else
                "DISAGREEMENT: one derivation claims an exact region domain and the other does not"
            ),
        })
    agreements = sum(row["agreement"] for row in output)
    return {
        "question_difference": (
            "the survey asks whether a blocked store base has an exact argument-derived "
            "region; the ledger first asks whether a0-a3 is consumed, then records only "
            "an independently proved exact domain. Pointer shape alone is not survey typing"
        ),
        "rows_checked": len(output),
        "agreements": agreements,
        "disagreements": len(output) - agreements,
        "every_disagreement": [row for row in output if not row["agreement"]],
        "every_row": output,
    }


def build_receipt() -> dict:
    frontier, frontier_raw = load_json(FRONTIER)
    typed, typed_raw = load_json(TYPED_STATE)
    local, local_raw = load_json(LOCAL_BASE)
    survey, survey_raw = load_json(ABI_SURVEY)
    index, index_raw = load_json(STATIC_INDEX)
    hoisted, hoisted_raw = load_json(HOISTED)
    pilot, pilot_raw = load_json(DISCIPLINE_PILOT)
    schema_raw = TYPED_SCHEMA.read_bytes()
    schema = yaml.safe_load(schema_raw)

    records, scope = scope_from_inputs(frontier, typed, local, index)
    hazards = ra_hazard_pairs(pilot)
    if len(records) != 764:
        raise LedgerError(f"frozen scope moved: {len(records)} != 764")
    if hoisted.get("sites") != 22 or len(hoisted.get("hits") or []) != 22:
        raise LedgerError("retained hoisted-load universe moved")

    images = []
    for row in index["images"]:
        path = ROOT / row["path"]
        raw = path.read_bytes()
        observed = sha(raw)
        if observed != row["sha256"] or observed != row["expected_sha256"]:
            raise LedgerError(f"image identity mismatch: {row['image_id']}")
        if len(raw) != integer(row["size"]):
            raise LedgerError(f"image size mismatch: {row['image_id']}")
        images.append({
            "image": row["image_id"], "path": row["path"],
            "size": len(raw), "sha256": observed,
            "file_va_base": row["file_va_base"], "runtime_gp": row["runtime_gp"],
        })

    with tempfile.TemporaryDirectory(prefix="phase4-f01-abi-") as tmp_text:
        tmp = Path(tmp_text)
        binary, binary_sha, cc_version = compile_probe(tmp)
        manifest = tmp / "manifest.txt"
        manifest_sha = write_manifest(manifest, records, index, hoisted, hazards)
        proc = subprocess.run(
            [str(binary), str(manifest)], cwd=ROOT, capture_output=True, text=True
        )
        if proc.returncode:
            raise LedgerError(f"compiled C probe rejected manifest:\n{proc.stderr}")
        try:
            probe = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"compiled C probe emitted invalid JSON: {exc}") from exc

    if len(probe["rows"]) != len(records):
        raise LedgerError("compiled C probe row count differs from scope")
    if len(probe["hoisted_load_checks"]) != 22:
        raise LedgerError("compiled C probe did not check all hoisted loads")
    if not all(
        row["decoded_as_load"] and row["contiguous_idiom_recognized"]
        for row in probe["hoisted_load_checks"]
    ):
        raise LedgerError("compiled C probe rejected a retained hoisted-load idiom")

    caution_pairs = probe.get("ra_general_jump_caution_pairs") or []
    if len(caution_pairs) != len(hazards):
        raise LedgerError("compiled C probe did not check all general-$ra caution pairs")
    if not all(
        row["site_is_jr_ra"] and not row["target_minus_8_is_call"]
        for row in caution_pairs
    ):
        raise LedgerError("compiled C probe rejected a general-$ra caution witness")
    caution_sites = {integer(row["site_pc"]) for row in caution_pairs}
    if caution_sites != EXPECTED_RA_HAZARD_SITES:
        raise LedgerError("compiled C general-$ra caution site set differs from pin")
    scoped_extents = [
        (row["image_id"], integer(row["entry"]), integer(row["end"]))
        for row in records
    ]
    if any(
        image == "SCUS_942_88" and lo <= site < hi
        for site in caution_sites for image, lo, hi in scoped_extents
    ):
        raise LedgerError("general-$ra caution site unexpectedly entered ABI ledger scope")

    rows = enrich_rows(probe, records, typed, index, schema)
    crosscheck = survey_crosscheck(survey, rows)
    arguments = [argument for row in rows for argument in row["arguments"]]
    stack_arguments = [argument for row in rows for argument in row["stack_arguments"]]
    mechanically_closed = sum(
        row["mechanically_complete"]
        and row["frame"]["kind"] in {"none", "fixed"}
        and row["return_convention"]["classification"]
        not in {
            "unknown_return_discipline", "unknown_entry_ra_provenance",
            "unknown_no_proved_normal_return",
        }
        and not any(item["ambiguous_save_slots"] for item in row["callee_saved"])
        and row["memory_side_effects"]["all_decoded_store_sites_accounted_for"]
        for row in rows
    )
    return_known = sum(
        row["return_convention"]["classification"]
        not in {
            "unknown_return_discipline", "unknown_entry_ra_provenance",
            "unknown_no_proved_normal_return",
        }
        for row in rows
    )
    pointer_closed = sum(
        not row["memory_side_effects"]["unresolved_pointer_writes"] for row in rows
    )
    known_argument_domains = sum(
        argument["type_domain"]["domain"] != "unknown" for argument in arguments
    )
    known_stack_domains = sum(
        argument["type_domain"]["domain"] != "unknown" for argument in stack_arguments
    )
    fully_resolved = sum(row["fully_resolved"] for row in rows)
    callee_saved_classified = sum(
        row["callee_saved_effects_classified"] for row in rows
    )

    input_hashes = {
        FRONTIER.relative_to(ROOT).as_posix(): sha(frontier_raw),
        TYPED_STATE.relative_to(ROOT).as_posix(): sha(typed_raw),
        LOCAL_BASE.relative_to(ROOT).as_posix(): sha(local_raw),
        ABI_SURVEY.relative_to(ROOT).as_posix(): sha(survey_raw),
        STATIC_INDEX.relative_to(ROOT).as_posix(): sha(index_raw),
        HOISTED.relative_to(ROOT).as_posix(): sha(hoisted_raw),
        DISCIPLINE_PILOT.relative_to(ROOT).as_posix(): sha(pilot_raw),
        TYPED_SCHEMA.relative_to(ROOT).as_posix(): sha(schema_raw),
        REGION_PROVENANCE_SOURCE.relative_to(ROOT).as_posix(): sha(
            REGION_PROVENANCE_SOURCE.read_bytes()
        ),
    }
    retained_rp = typed["second_opinion"]
    if retained_rp["source_sha256"] != input_hashes[
        REGION_PROVENANCE_SOURCE.relative_to(ROOT).as_posix()
    ]:
        raise LedgerError("typed-state region-provenance source pin is stale")

    coverage = {
        "functions_in_scope": len(rows),
        "complete_abi_rows": fraction(sum(row["abi_row_complete"] for row in rows), len(rows)),
        "mechanically_closed_rows": fraction(mechanically_closed, len(rows)),
        "fully_resolved_rows": fraction(fully_resolved, len(rows)),
        "return_convention_known_rows": fraction(return_known, len(rows)),
        "callee_saved_effects_classified_rows": fraction(
            callee_saved_classified, len(rows)
        ),
        "pointer_write_set_fully_resolved_rows": fraction(pointer_closed, len(rows)),
        "consumed_argument_domains_known": fraction(known_argument_domains, len(arguments)),
        "stack_argument_domains_known": fraction(known_stack_domains, len(stack_arguments)),
        "unknown_reasons": {
            "context_sensitive_delay_slot_entry_rows": sum(
                bool(row["cfg_context_sensitive_delay_entries"]) for row in rows
            ),
            "reachable_unsupported_instruction_rows": sum(
                bool(row["decoder_unknown_pcs"]) for row in rows
            ),
            "variable_or_unknown_frame_rows": sum(
                row["frame"]["kind"] == "variable_or_unknown" for row in rows
            ),
            "inherited_or_unbalanced_entry_frame_rows": sum(
                row["frame"]["kind"] == "inherited_or_unbalanced" for row in rows
            ),
            "unclassified_entry_relative_stack_loads": sum(
                len(row["unclassified_entry_relative_stack_loads"])
                for row in rows
            ),
            "unclassified_stack_loads_without_entry_call_proof": sum(
                len(row["unclassified_entry_relative_stack_loads"])
                for row in rows
                if row["stack_argument_analysis"]["classification"]
                == "unknown_entry_sp_provenance"
            ),
            "unknown_or_inconsistent_return_rows": len(rows) - return_known,
            "unproved_entry_ra_provenance_rows": sum(
                row["return_convention"]["classification"]
                == "unknown_entry_ra_provenance"
                for row in rows
            ),
            "no_proved_normal_return_but_exit_provenance_open_rows": sum(
                row["return_convention"]["classification"]
                == "unknown_no_proved_normal_return"
                for row in rows
            ),
            "ambiguous_callee_save_rows": sum(
                any(item["ambiguous_save_slots"] for item in row["callee_saved"])
                for row in rows
            ),
            "callee_saved_effects_unclassified_rows": (
                len(rows) - callee_saved_classified
            ),
            "callee_saved_effects_rejected_for_incomplete_cfg_rows": sum(
                row["callee_saved_effects_unclassified_reason"]
                == "compiled_cfg_incomplete"
                and all(
                    not item["status"].startswith(("not_classified", "unknown_"))
                    for item in row["callee_saved"]
                )
                for row in rows
            ),
            "consumed_register_arguments_with_unknown_domain": (
                len(arguments) - known_argument_domains
            ),
            "stack_arguments_with_unknown_domain": len(stack_arguments) - known_stack_domains,
            "rows_with_unresolved_pointer_writes": len(rows) - pointer_closed,
        },
        "complete_row_definition": (
            "structural: every in-scope function has every requested field and explicit "
            "unknowns; mechanically_closed and fully_resolved are stricter non-vacuous fractions"
        ),
    }

    eligible = fully_resolved == len(rows) and mechanically_closed == len(rows)
    return {
        "schema": "abl-phase4-f01-abi-ledger/2",
        "status": "partial",
        "execution_freeze": {
            "issued_baseline_commit": ISSUED_COMMIT,
            "issued_baseline_status_short_line_count": ISSUED_STATUS_LINES,
            "issued_baseline_status_short_sha256": ISSUED_STATUS_SHA256,
            "operator_wip_preserved": True,
        },
        "scope": scope,
        "inputs": {
            "artifacts": input_hashes,
            "images": images,
            "compiled_probe": {
                "source": PROBE_SOURCE.relative_to(ROOT).as_posix(),
                "source_sha256": sha(PROBE_SOURCE.read_bytes()),
                "binary_sha256": binary_sha,
                "compiler": cc_version,
                "flags": ["-std=c99", "-O2", "-Wall", "-Wextra", "-Werror"],
                "manifest_sha256": manifest_sha,
                "instruction_decoding_owned_by": "compiled C",
            },
            "region_provenance_reuse": {
                "retained_output": TYPED_STATE.relative_to(ROOT).as_posix(),
                "tool": retained_rp["tool"],
                "source_sha256": retained_rp["source_sha256"],
                "binary_sha256": retained_rp["binary_sha256"],
                "windows_queried": retained_rp["windows_queried"],
                "site_verdicts": retained_rp["site_verdicts"],
                "rerun_by_this_ledger": False,
            },
        },
        "method": {
            "argument_rule": (
                "entry value reaches an instruction read on at least one entry-reachable "
                "CFG path before any write; nested calls kill surviving a0-a3 only after "
                "their delay slot"
            ),
            "stack_argument_rule": (
                "load from entry-SP offset >=16 on a path where the same canonical slot "
                "has not been written, but only when C proves a call-entry-SP anchor: "
                "a same-image static-index direct-call witness re-decodes in C as an exact "
                "call target, with no unknown SP state and no positive pop of an unobserved "
                "frame. All other candidate loads remain explicit unclassified evidence"
            ),
            "return_rule": (
                "dataflow may prove that jr $ra uses the incoming entry value or an "
                "unambiguous paired frame-slot reload, but that is only an incoming-$ra "
                "continuation; absent external call-link provenance it is not promoted "
                "to a normal return. Conversely, absence of such a jr $ra does not prove "
                "no normal return because a copied link or other indirect exit remains "
                "possible. Both cases keep the return convention unknown"
            ),
            "callee_save_rule": (
                "a canonical save candidate stores a value proved unchanged from entry "
                "and has a matching reload before any overwrite of that entry-SP slot; "
                "outgoing/local stores and ambiguous paired slots cannot close the row"
            ),
            "delay_slot_rule": (
                "transfers execute their delay instruction first; direct entries into a "
                "physical delay word require context splitting and are reported unknown"
            ),
            "hoisted_load_rule": (
                "all 22 retained sites are re-decoded as contiguous slt/sltu, add/addu, "
                "load, beq/bne idioms by C; the load read is not moved behind the guard"
            ),
            "type_rule": (
                "memory-base use proves pointer shape only; exact domains require an "
                "accepted retained typed-state binding; call-site constants alone never type"
            ),
            "memory_rule": (
                "direct entry-reachable body stores only: resolved static-index addresses "
                "and C-decoded direct $gp stores are named, unresolved sites reuse exact "
                "retained region-provenance outcomes, and nested-callee effects are not "
                "silently attributed"
            ),
        },
        "coverage": coverage,
        "abi_survey_crosscheck": crosscheck,
        "hoisted_load_crosscheck": {
            "expected": 22,
            "checked": len(probe["hoisted_load_checks"]),
            "all_recognized": True,
            "rows": probe["hoisted_load_checks"],
        },
        "ra_general_jump_caution_crosscheck": {
            "scope_relationship": (
                "all seven exact GTE/clip sites are outside every one of the 764 ABI "
                "ledger extents; this is a global caution control, not row coverage"
            ),
            "runtime_authority": "retained corroboration/falsification only; never proof",
            "source": DISCIPLINE_PILOT.relative_to(ROOT).as_posix(),
            "unique_sites_expected": 7,
            "unique_sites_checked": len(caution_sites),
            "site_target_pairs_checked": len(caution_pairs),
            "all_sites_decode_as_jr_ra": all(
                row["site_is_jr_ra"] for row in caution_pairs
            ),
            "all_observed_targets_lack_call_at_target_minus_8": all(
                not row["target_minus_8_is_call"] for row in caution_pairs
            ),
            "all_sites_outside_ledger_scope": True,
            "pairs": caution_pairs,
        },
        "rows": rows,
        "original_interfaces_eligible_for_promotion": eligible,
        "status_statement": (
            f"{fully_resolved}/{len(rows)} rows are fully resolved; original_interfaces "
            "remains partial and is not eligible for promotion."
        ),
        "authority": {
            "promotes_dimension": False,
            "f01_status_remains": "partial",
            "fresh_detached_verifier_required_to_bank": True,
            "runtime_replay_used": False,
        },
        "reproduction": {
            "write": "python3 tools/phase4_f01_abi_ledger.py --write",
            "check": "python3 tools/phase4_f01_abi_ledger.py --check",
        },
    }


def render(receipt: dict) -> str:
    return json.dumps(receipt, indent=1, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    expected = render(build_receipt())
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(expected)
        receipt = json.loads(expected)
        print(
            f"[phase4-f01-abi-ledger] wrote {output.relative_to(ROOT)}: "
            f"{receipt['coverage']['fully_resolved_rows']['fraction']} fully resolved"
        )
        return 0
    if not output.exists():
        print(f"[phase4-f01-abi-ledger] missing {output}", file=__import__("sys").stderr)
        return 1
    if output.read_text() != expected:
        print("[phase4-f01-abi-ledger] STALE: rerun with --write", file=__import__("sys").stderr)
        return 1
    receipt = json.loads(expected)
    print(
        "[phase4-f01-abi-ledger] PASS: "
        f"{receipt['coverage']['complete_abi_rows']['fraction']} rows, "
        f"{receipt['coverage']['fully_resolved_rows']['fraction']} fully resolved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
