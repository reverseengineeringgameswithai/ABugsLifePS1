#!/usr/bin/env python3
"""Non-promoting Phase-4 reuse measurement for the unsigned index prover.

The universe is derived row-agnostically: every STORE access row in every
resident static-index record is classified at its exact PC by the rebuilt C
verifier, and the measurement universe is the exact subset whose every
observable base definition is a direct ``table_address`` definition.  The same
``indexdom@IMAGE:START:END:REG:PC`` machinery used by F01 then proves or rejects
the non-constant addend at TABLE+INDEX.  No row status or campaign artifact is
an output of this tool.

Usage:
  tools/phase4_index_interval_demo.py \
      --output analysis/phase4_index_interval_non_f01_demo.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_typed_state as ts  # noqa: E402

SCHEMA = "abl-phase4-index-interval-non-f01-demo/1"
IMAGE = "SCUS_942_88"
WINDOW_LO = 0x800A657E
WINDOW_HI = 0x800A6580
RA_RATCHET_BASELINE_COMMIT = "05bc6b8a251b613cf6c25b6c6bdf351fdf32b7e4"
RA_RATCHET_BASELINE_ARTIFACT = "analysis/phase4_index_interval_non_f01_demo.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _int(value: Any) -> int:
    return ts._int(value)


def _instruction_word(verifier: ts.Verifier, index: dict,
                      image: str, pc: int) -> str | None:
    record = next((row for row in index["records"]
                   if row.get("entry") and row["image_id"] == image
                   and _int(row["entry"]) <= pc < _int(row["end"])), None)
    if record is None:
        return None
    answer = verifier.ask(
        f"indexdom@{image}:{record['entry']}:{record['end']}:zero:0x{pc:08x}")[0]
    return answer.get("site_word")


def _source_stores(index: dict) -> list[dict]:
    raw: list[dict] = []
    for record in index["records"]:
        if (record["image_id"] != IMAGE or not record.get("entry")
                or not record.get("end")):
            continue
        for access in record.get("memory_accesses") or []:
            if access.get("access") != "write":
                continue
            raw.append({
                "image": IMAGE,
                "function": str(record.get("name") or ""),
                "extent": [record["entry"], record["end"]],
                "pc": access["pc"],
                "base_register": access["base_register"],
                "displacement": int(access.get("offset") or 0),
                "width": int(access.get("width") or 4),
                "mnemonic": access.get("mnemonic"),
            })
    raw.sort(key=lambda row: (
        _int(row["extent"][0]), _int(row["pc"]), row["base_register"],
        row["displacement"], row["width"], row["function"]))
    bases = [
        (f"resident-store:{row['function']}@{row['extent'][0]}:"
         f"{row['pc']}:{row['base_register']}:{row['displacement']}:{row['width']}")
        for row in raw]
    counts = {base: bases.count(base) for base in set(bases)}
    seen: dict[str, int] = {}
    for row, base in zip(raw, bases):
        seen[base] = seen.get(base, 0) + 1
        row["id"] = (base if counts[base] == 1
                     else f"{base}:occurrence-{seen[base]}")
    return raw


def _ask_base_queries_fail_closed(
        verifier: ts.Verifier, specs: list[str], batch_size: int = 128,
) -> tuple[list[dict | None], dict[int, str]]:
    """Keep the source census exact when the C verifier rejects a stale row.

    A normal batch fails as a unit. Recursive bisection identifies the exact
    static-index row whose claimed base is not the base decoded by C; that row
    is retained as an explicit source-universe rejection, never silently
    dropped or queried as an arbitrary non-access point.
    """
    answers: list[dict | None] = [None] * len(specs)
    failures: dict[int, str] = {}

    def run(indices: list[int]) -> None:
        if not indices:
            return
        try:
            batch = verifier.ask(*(specs[index] for index in indices))
        except ts.TypedStateError as exc:
            if len(indices) == 1:
                failures[indices[0]] = str(exc)
                return
            middle = len(indices) // 2
            run(indices[:middle])
            run(indices[middle:])
            return
        for index, answer in zip(indices, batch):
            answers[index] = answer

    for offset in range(0, len(specs), batch_size):
        run(list(range(offset, min(offset + batch_size, len(specs)))))
    return answers, failures


def build() -> dict:
    index_raw = ts.INDEX_PATH.read_bytes()
    index = json.loads(index_raw)
    verifier = ts.Verifier(index)
    transfer_closure = ts._indirect_transfer_closure(index)
    stores = _source_stores(index)

    base_specs = [
        (f"{row['image']}:{row['extent'][0]}:{row['extent'][1]}:"
         f"{row['base_register']}:{row['pc']}")
        for row in stores]
    base_answers, base_failures = _ask_base_queries_fail_closed(
        verifier, base_specs)
    class_tally: dict[str, int] = {}
    candidates: list[tuple[dict, dict, list[dict]]] = []
    for position, (row, answer) in enumerate(zip(stores, base_answers)):
        if answer is None:
            label = "c_rejected_static_index_base_or_access"
            class_tally[label] = class_tally.get(label, 0) + 1
            continue
        observable = [item for item in answer["definitions"]
                      if item["observable"]]
        classes = sorted({item["class"] for item in observable})
        label = "+".join(classes) if classes else "no_observable_definition"
        class_tally[label] = class_tally.get(label, 0) + 1
        if (not answer["entry_reachable_uses"] and observable
                and all(ts._proved_table_address_definition(item)
                        for item in observable)):
            candidates.append((row, answer, observable))

    index_specs: dict[str, None] = {}
    for row, _base, definitions in candidates:
        for definition in definitions:
            index_specs[
                f"indexdom@{row['image']}:{row['extent'][0]}:{row['extent'][1]}:"
                f"{definition['index']}:{definition['pc']}"] = None
    spec_list = list(index_specs)
    index_answers = dict(zip(spec_list, ts._ask_batched(verifier, spec_list)))

    convention = verifier.region_provenance(IMAGE, WINDOW_LO, WINDOW_HI - WINDOW_LO)
    exclusions: dict[tuple[int, str], list[dict]] = {}
    for exclusion in convention.get("exclusions") or []:
        exclusions.setdefault(
            (_int(exclusion["pc"]), str(exclusion.get("function") or "")),
            []).append(exclusion)
    hit_pcs = {_int(pc) for pc in convention.get("hit_pcs") or []}

    external_cache: dict[tuple[str, int, int], list[dict]] = {}
    external_entry_sets: dict[str, dict] = {}
    rows: list[dict] = []
    interval_decided: set[str] = set()
    interval_unproved: set[str] = set()
    interval_not_excluding: set[str] = set()
    interval_entry_unclosed: set[str] = set()
    interval_address_decided_before_entry_gate: set[str] = set()
    convention_any: set[str] = set()
    convention_assumption: set[str] = set()
    convention_alignment: set[str] = set()
    convention_hits: set[str] = set()

    for source, base_answer, definitions in candidates:
        image = source["image"]
        entry, end = (_int(source["extent"][0]), _int(source["extent"][1]))
        ext_key = (image, entry, end)
        if ext_key not in external_cache:
            external_cache[ext_key] = ts._external_interior_entries(
                index, image, entry, end, transfer_closure)
        external = external_cache[ext_key]
        external_payload = json.dumps(
            external, sort_keys=True, separators=(",", ":")).encode()
        external_set_id = "external-entry-set:" + _sha(external_payload)
        external_entry_sets.setdefault(external_set_id, {
            "id": external_set_id,
            "entry_count": len(external),
            "entries": external,
        })

        derivations = []
        breaker = None
        excludes = True
        for definition in definitions:
            spec = (f"indexdom@{image}:{source['extent'][0]}:{source['extent'][1]}:"
                    f"{definition['index']}:{definition['pc']}")
            query = index_answers[spec]
            if not query.get("verdict") and breaker is None:
                breaker = query.get("breaking_instruction")
            interval = query.get("interval")
            effective = None
            mode = "unproved"
            no_wrap = False
            if interval is not None:
                table = _int(definition["table"])
                low = table + int(interval["min"]) + source["displacement"]
                high = (table + int(interval["max"]) + source["displacement"]
                        + source["width"])
                no_wrap = (0 <= low <= 0xffffffff
                           and 0 <= high <= 0x100000000)
                if no_wrap:
                    effective = [f"0x{low:08x}", f"0x{high:08x}"]
                    alias_check = ts._ps1_ram_window_exclusion(
                        low, high, WINDOW_LO, WINDOW_HI)
                    mode = alias_check["mode"]
                    if not alias_check["excluded"]:
                        excludes = False
                else:
                    alias_check = None
                    mode = "address_wrap_possible"
                    excludes = False
            else:
                alias_check = None
                excludes = False
            derivations.append({
                "table_address_definition": {
                    key: definition.get(key) for key in
                    ("pc", "word", "table", "index", "hops",
                     "table_base_register", "table_base_proof")},
                "index_domain_query_id": spec,
                "effective_address_interval": effective,
                "no_32bit_wrap": no_wrap,
                "window_exclusion_mode": mode,
                "ps1_ram_alias_check": alias_check,
            })
        if breaker is not None:
            outcome = "interval_unproved"
            interval_unproved.add(source["id"])
        elif not excludes:
            outcome = "proved_interval_does_not_exclude_window"
            interval_not_excluding.add(source["id"])
        elif external:
            interval_address_decided_before_entry_gate.add(source["id"])
            edge = dict(external[0])
            edge["word"] = _instruction_word(
                verifier, index, str(edge["image"]), _int(edge["pc"]))
            breaker = {
                "pc": edge["pc"], "word": edge.get("word"),
                "reason": (edge.get("reason") or
                           "external edge enters interval-query extent interior")}
            outcome = "interval_address_decided_but_external_entry_unclosed"
            interval_entry_unclosed.add(source["id"])
        else:
            outcome = "interval_decided"
            interval_decided.add(source["id"])
            interval_address_decided_before_entry_gate.add(source["id"])

        site_exclusions = exclusions.get(
            (_int(source["pc"]), source["function"]), [])
        kinds = sorted({item["kind"] for item in site_exclusions})
        if kinds:
            convention_any.add(source["id"])
        if set(kinds) & {"EXCLUDED_NEGATIVE_INDEX", "EXCLUDED_OUT_OF_BOUND"}:
            convention_assumption.add(source["id"])
        if "EXCLUDED_ALIGNMENT" in kinds:
            convention_alignment.add(source["id"])
        if _int(source["pc"]) in hit_pcs:
            convention_hits.add(source["id"])
        rows.append({
            **source,
            "base_provenance": {
                "query_form": (
                    f"{image}:{source['extent'][0]}:{source['extent'][1]}:"
                    f"{source['base_register']}:{source['pc']}"),
                "entry_reachable_uses": base_answer["entry_reachable_uses"],
                "observable_definitions": [
                    {key: definition.get(key) for key in
                     ("pc", "word", "class", "table", "index", "hops",
                      "observable")}
                    for definition in definitions],
            },
            "external_interior_entry_set_id": external_set_id,
            "external_interior_entry_count": len(external),
            "interval_outcome": outcome,
            "breaking_instruction": breaker,
            "derivations": derivations,
            "convention_comparison": {
                "region_provenance_exclusion_kinds": kinds,
                "depends_on_index_sign_or_loop_bound_convention": bool(
                    set(kinds) & {"EXCLUDED_NEGATIVE_INDEX",
                                  "EXCLUDED_OUT_OF_BOUND"}),
                "reported_hit": _int(source["pc"]) in hit_pcs,
            },
        })

    universe_ids = {source[0]["id"] for source in candidates}
    classified_total = sum(class_tally.values())
    if classified_total != len(stores):
        raise RuntimeError("base-class tally does not cover the resident store rows")
    if universe_ids != {row["id"] for row in rows}:
        raise RuntimeError("table-address universe was not processed exactly once")

    def exact(values: set[str]) -> dict:
        return {"count": len(values), "site_ids": sorted(values)}

    result = {
        "schema": SCHEMA,
        "question": (
            "On the non-F01 resident slot [0x800A657E,0x800A6580), how many "
            "table-address-class STORE sites are decided by instruction-derived "
            "unsigned intervals, compared with region_provenance conventions?"),
        "window": {
            "start": f"0x{WINDOW_LO:08x}", "end": f"0x{WINDOW_HI:08x}",
            "width": WINDOW_HI - WINDOW_LO,
            "not_f01": True,
        },
        "inputs": {
            "static_index": str(ts.INDEX_PATH.relative_to(ROOT)),
            "static_index_sha256": _sha(index_raw),
            "verifier_source": ts.VERIFIER_SRC,
            "verifier_source_sha256": verifier.source_sha,
            "verifier_binary_sha256": verifier.binary_sha,
            "verifier_image_map_sha256": verifier.image_map_sha,
            "region_provenance_source": ts.REGION_PROVENANCE_SRC,
            "region_provenance_source_sha256": verifier._rp_source_sha,
            "region_provenance_binary_sha256": verifier._rp_binary_sha,
        },
        "universe": {
            "source_definition": (
                "every memory_accesses row with access=write in every "
                "SCUS_942_88 static-index record carrying an extent"),
            "source_store_access_rows": len(stores),
            "base_definition_class_tally": dict(sorted(class_tally.items())),
            "c_rejected_source_rows": [
                {"id": stores[position]["id"], "error": error}
                for position, error in sorted(base_failures.items())],
            "selection": (
                "no entry-reachable use; every observable exact-PC base "
                "definition is table_address with hops=0 and names TABLE, INDEX, PC"),
            "table_address_class_store_rows": len(rows),
            "table_address_class_store_site_ids": sorted(universe_ids),
            "every_selected_site_processed": len(rows) == len(universe_ids),
        },
        "interval_measurement": {
            "decided": exact(interval_decided),
            "unproved": exact(interval_unproved),
            "proved_but_does_not_exclude_window": exact(interval_not_excluding),
            "address_decided_but_external_entry_unclosed": exact(
                interval_entry_unclosed),
        },
        "pre_external_entry_gate_measurement": {
            "address_decided": exact(
                interval_address_decided_before_entry_gate),
            "meaning": (
                "diagnostic only: C interval plus no-wrap and complete PS1 RAM "
                "alias exclusion passed, before the mandatory external-entry "
                "closure gate; these are not proof decisions"),
        },
        "external_indirect_transfer_closure": transfer_closure,
        "external_entry_sets": [external_entry_sets[key]
                                for key in sorted(external_entry_sets)],
        "convention_measurement_on_same_universe": {
            "any_region_provenance_exclusion": exact(convention_any),
            "index_sign_or_loop_bound_convention_exclusion": exact(
                convention_assumption),
            "unconditional_alignment_exclusion": exact(convention_alignment),
            "reported_hit": exact(convention_hits),
            "region_provenance_total_context": {
                key: convention[key] for key in
                ("hits", "unresolved_after_region", "exclusions_total",
                 "excluded_alignment", "excluded_negative_index",
                 "excluded_out_of_bound")},
        },
        "comparison_exact_sets": {
            "decided_by_both_interval_and_assumption_convention": exact(
                interval_decided & convention_assumption),
            "decided_by_interval_not_assumption_convention": exact(
                interval_decided - convention_assumption),
            "decided_by_assumption_convention_not_interval": exact(
                convention_assumption - interval_decided),
        },
        "index_domain_queries": [
            {"id": spec, "result": index_answers[spec]}
            for spec in sorted(index_answers)],
        "sites": rows,
        "authority": {
            "capability_measurement_only": True,
            "changes_f01_status": False,
            "changes_demonstration_row_status": False,
            "changes_campaign_registry": False,
            "promotes_any_dimension": False,
        },
    }

    object_name = (f"{RA_RATCHET_BASELINE_COMMIT}:"
                   f"{RA_RATCHET_BASELINE_ARTIFACT}")
    baseline_proc = subprocess.run(
        ["git", "show", object_name], cwd=ROOT, check=False,
        capture_output=True)
    if baseline_proc.returncode:
        raise RuntimeError(
            "cannot read pre-ra-ratchet demonstration receipt: "
            + baseline_proc.stderr.decode(errors="replace").strip())
    baseline_raw = baseline_proc.stdout
    baseline = json.loads(baseline_raw)

    def outcome_sets(document: dict) -> dict[str, set[str]]:
        names = {
            "decided": "decided",
            "unproved": "interval_unproved",
            "proved_but_does_not_exclude_window":
                "proved_interval_does_not_exclude_window",
            "address_decided_but_external_entry_unclosed":
                "external_interior_entry",
        }
        answer: dict[str, set[str]] = {}
        for key, category in names.items():
            answer[category] = set(
                document["interval_measurement"][key]["site_ids"])
        return answer

    result["diagnostic_outcome_movement_from_05bc6b8a251b"] = {
        "baseline_commit": RA_RATCHET_BASELINE_COMMIT,
        "baseline_artifact": RA_RATCHET_BASELINE_ARTIFACT,
        "baseline_artifact_sha256": _sha(baseline_raw),
        "meaning": (
            "exact diagnostic-stage row-id movement caused by rejecting a "
            "locally-defined-ra indirect target; this receipt remains "
            "non-promoting"),
        **ts._movement(outcome_sets(baseline), outcome_sets(result)),
    }
    return result


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT not in output.parents:
        raise RuntimeError("output must stay inside the repository")
    fresh = render(build())
    if args.check:
        if not output.is_file() or output.read_bytes() != fresh:
            raise RuntimeError(f"retained receipt is stale: {output}")
        print("[phase4-index-interval-demo] retained receipt is fresh")
        return 0
    output.write_bytes(fresh)
    result = json.loads(fresh)
    print(f"[phase4-index-interval-demo] wrote {output}")
    print("  table-address STORE universe: "
          f"{result['universe']['table_address_class_store_rows']}")
    print("  interval decided: "
          f"{result['interval_measurement']['decided']['count']}")
    convention_count = result["convention_measurement_on_same_universe"][
        "index_sign_or_loop_bound_convention_exclusion"]["count"]
    print(f"  convention-dependent decided: {convention_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
