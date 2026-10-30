#!/usr/bin/env python3
"""The locally-computed-base campaign for F01, in the bankable shape.

The 2026-08-06 review's planning correction: a "<~N sites decided, stop" rule
is a cost/yield heuristic, not evidence of exhaustion. A boundary is bankable
only as ``bounded_exhausted_<named method>`` over an EXACTLY defined eligible
universe, with EVERY eligible site processed, a per-site failure reason
retained, and reopening falsifiers named. This tool is that shape.

ELIGIBLE UNIVERSE (derived, not declared)
-----------------------------------------
The acceptance-fixture stores (chosen by the resolver, never by this tool)
joined to the blocker ledger's ``still_unresolved`` verdicts in the retained
typed-state artifact -- i.e. exactly the fixture stores that every existing
analysis (constant propagation, ABI accelerator, typed-pointer loads, the
proved-jr chain, and the convention-tier second opinion) has already failed to
decide. Cross-overlay joins that are ambiguous by pc are processed for every
candidate and listed, never collapsed.

METHOD (per site, all from the rebuilt C verifier's instruction facts)
----------------------------------------------------------------------
1. Classify the base register's observable reaching definitions at the site.
2. Attempt the one recovery per class that existing machinery supports:
   * call_result       -> per-SITE return typing: every observable def must be
                          a call to a NAMED callee; each callee's return is
                          typed with returns@, chasing exactly ONE pure-copy
                          hop at the return point (v0 = sN -> what sN holds
                          there). Deeper interprocedural chains are out of this
                          method's scope BY DEFINITION and are named as such.
   * entry_value       -> the site is reachable with the register's ENTRY
                          value (callee-saved, ungoverned): recover what every
                          exact direct call/jump/branch or already-proved jr
                          edge carries. Non-call delay slots are checked for a
                          redefining write. No established entry edge remains
                          a named blocker; return-address attribution is never
                          treated as an edge.
   * global_load       -> the base is loaded from one fixed cell: the chain to
                          a region exists but is GATED on the same
                          table-writer-universe exhaustiveness the island
                          binding is gated on. Named, not silently converted.
   * table_address     -> query the exact non-constant addend at the forming
                          addu with indexdom@. Every reaching definition must
                          be in the unsigned-interval whitelist. A proved
                          lower bound decides only when 32-bit address addition
                          cannot wrap and [TABLE+min+disp,RAM_HI) misses both
                          windows; otherwise the exact breaking instruction is
                          the refined wall. Return-table rows use the same query
                          at the recovered return definition.
   * self_adjust (sp)  -> stack displacement from a caller-dependent entry sp:
                          stack-region membership is a convention, not proved.
   * anything else     -> the raw definition list IS the failure reason.
3. A site is DECIDED only if a proof-grade interval excludes both windows.
   Everything else keeps a named, machine-derived failure reason.

The output stages the campaign verdict
``bounded_exhausted_locally_computed_base_recovery`` with its falsifiers; it
does NOT bank it -- only a fresh detached verifier may.

Usage:
  tools/phase4_f01_local_base_recovery.py \
      --output analysis/phase4_f01_local_base_recovery.json [--check]
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
import phase4_static_frontier as frontier  # noqa: E402

RESOLVE_PATH = ROOT / "analysis/phase4_f01_frontier_resolve.json"
TYPED_STATE_PATH = ROOT / "analysis/phase4_f01_typed_state.json"
HARD_TRUTH_PATH = ROOT / "analysis/phase4_f01_static_hard_truth.json"
BASELINE_PATH = ROOT / "analysis/phase4_f01_local_base_recovery_1bba2487_outcomes.json"
BASELINE_SOURCE_COMMIT = "1bba2487b1b6f3e9d7669947de494ba649b99b70"
BASELINE_SOURCE_ARTIFACT = "analysis/phase4_f01_local_base_recovery.json"
PREREQUISITE_COMMIT = "b6cb61d35f9da0c890f9318d1b4a0122f2e6e084"
PREREQUISITE_ARTIFACT = "analysis/phase4_f01_local_base_recovery.json"
RA_RATCHET_BASELINE_COMMIT = "05bc6b8a251b613cf6c25b6c6bdf351fdf32b7e4"
RA_RATCHET_BASELINE_ARTIFACT = "analysis/phase4_f01_local_base_recovery.json"
SCHEMA = "abl-phase4-f01-local-base-recovery/1"
BASELINE_SCHEMA = "abl-phase4-f01-local-base-outcome-baseline/1"
WINDOWS = ((0x800823A0, 0x800823A2), (0x80082470, 0x80082472))
RAM_HI = 0x80200000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def derive_universe(resolve: dict, typed: dict, index: dict) -> tuple[list[dict], list[dict]]:
    """Fixture stores x still_unresolved, joined exactly; ambiguities listed."""
    records: dict[tuple[str, str], dict] = {}
    for r in index["records"]:
        if r.get("entry"):
            records[(r["image_id"], str(r.get("name") or ""))] = r
    still: dict[int, list[dict]] = {}
    for row in typed["still_unresolved"]:
        try:
            still.setdefault(_int(row["pc"]), []).append(row)
        except (KeyError, ValueError):
            continue
    sites, ambiguous = [], []
    for s in resolve["unresolved_sites"]:
        if not s.get("store"):
            continue
        pc = _int(s["pc"])
        joins = []
        for row in still.get(pc, []):
            image = str(row.get("function", "")).split(":", 1)[0]
            if image.startswith(s["image"]) or s["image"].startswith(image):
                joins.append((image, row))
        if not joins:
            continue                    # decided or absent -- not eligible
        if len(joins) > 1:
            ambiguous.append({"pc": s["pc"], "fixture_image": s["image"],
                              "candidates": sorted(i for i, _ in joins)})
        for image, row in joins:
            name = str(row["function"]).split(":", 1)[1].split("@")[0]
            record = records.get((image, name))
            if record is None:
                ambiguous.append({"pc": s["pc"], "fixture_image": s["image"],
                                  "error": f"no index record for {image}:{name}"})
                continue
            sites.append({
                "image": image, "function": name,
                "extent": [record["entry"], record["end"]],
                "pc": f"0x{pc:08x}",
                "base_register": str(row["base_register"]),
                "offset": int(row.get("offset", 0)),
                "mnemonic": str(row.get("mnemonic", "")),
            })
    sites.sort(key=lambda r: (r["image"], r["pc"], r["base_register"],
                              r["function"], r["offset"]))
    bases = [f"{row['image']}:0x{_int(row['pc']):08X}:{row['base_register']}"
             for row in sites]
    seen_ids: dict[str, int] = {}
    for row, base in zip(sites, bases):
        seen_ids[base] = seen_ids.get(base, 0) + 1
        row["id"] = (base if bases.count(base) == 1
                     else f"{base}:occurrence-{seen_ids[base]}")
    return sites, ambiguous


def established_entry_sources(index: dict, image: str, entry: int) -> list[dict]:
    """Every named static edge entering ENTRY, exact-set deduplicated.

    Direct branch/jump/call edges come from the index records. Proved jr edges
    come from both pinned imports; when phase3 and the gate name the same edge,
    it remains one source with both provenances rather than two callers.
    """
    sources: dict[tuple[str, int, str], dict] = {}
    resident = next((row["image_id"] for row in index["images"]
                     if row.get("role") == "resident"), "SCUS_942_88")
    for record in index["records"]:
        if not record.get("entry") or record["image_id"] not in (image, resident):
            continue
        for edge in record.get("direct_calls") or []:
            if _int(edge["target"]) == entry:
                key = (record["image_id"], _int(edge["pc"]), "call")
                sources[key] = {"kind": "call", "pc": edge["pc"],
                                "image": record["image_id"],
                                "function": record.get("name"),
                                "extent": [record["entry"], record["end"]],
                                "provenance": ["direct_call"]}
        for edge in record.get("direct_jumps") or []:
            if _int(edge["target"]) == entry:
                key = (record["image_id"], _int(edge["pc"]), "jump")
                sources[key] = {"kind": "jump", "pc": edge["pc"],
                                "image": record["image_id"],
                                "function": record.get("name"),
                                "extent": [record["entry"], record["end"]],
                                "provenance": ["direct_jump"]}
        for edge in record.get("branches") or []:
            if entry in {_int(value) for value in edge.get("successors") or []}:
                key = (record["image_id"], _int(edge["pc"]), "branch")
                sources[key] = {"kind": "branch", "pc": edge["pc"],
                                "image": record["image_id"],
                                "function": record.get("name"),
                                "extent": [record["entry"], record["end"]],
                                "provenance": ["direct_branch"]}
    for source_name in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        for pc, targets in ((index.get(source_name) or {}).get("site_targets") or {}).items():
            if entry not in {_int(value) for value in targets}:
                continue
            source_pc = _int(pc)
            record = next((row for row in index["records"]
                           if row["image_id"] == resident and row.get("entry")
                           and _int(row["entry"]) <= source_pc < _int(row["end"])), None)
            if record is None:
                raise RuntimeError(f"proved jr source {pc} lies in no resident record")
            key = (resident, source_pc, "proved_jr")
            if key not in sources:
                sources[key] = {"kind": "proved_jr", "pc": pc,
                                "image": resident, "function": record.get("name"),
                                "extent": [record["entry"], record["end"]],
                                "provenance": []}
            sources[key]["provenance"].append(source_name)
    rows = list(sources.values())
    for row in rows:
        row["provenance"] = sorted(set(row["provenance"]))
    return sorted(rows, key=lambda row: (row["image"], _int(row["pc"]), row["kind"]))


def recover_entry_value(row: dict, site: dict, verifier: ts.Verifier,
                        index: dict, transfer_closure: dict) -> dict:
    """Type a callee-saved entry value at every established transfer edge."""
    sources = established_entry_sources(index, site["image"], _int(site["extent"][0]))
    row["established_entry_sources"] = sources
    if not sources:
        row["outcome"] = "blocked_no_direct_caller"
        row["reason"] = ("reachable with the callee-saved entry value, but the "
                         "index has no direct call/jump/branch or proved-jr edge "
                         "to the function entry")
        return row

    facts = []
    base_reg = frontier.REG_NAMES.index(site["base_register"])
    image_meta = {item["image_id"]: item for item in index["images"]}
    for source in sources:
        pc = _int(source["pc"])
        # Non-call transfers also execute one delay slot. defsat deliberately
        # advances calls past it; for branch/jump/jr we prove the delay slot
        # does not redefine the register before querying at the control PC.
        delay_writes_base = False
        if source["kind"] != "call":
            meta = image_meta[source["image"]]
            raw = (ROOT / meta["path"]).read_bytes()
            off = pc + 4 - _int(meta["file_va_base"])
            delay_word = int.from_bytes(raw[off:off + 4], "little")
            delay_writes_base = frontier.written_register(delay_word) == base_reg
        fact = {**source, "delay_slot_writes_base": delay_writes_base}
        if delay_writes_base:
            fact["blocked"] = "delay slot redefines the entry base"
            facts.append(fact)
            continue
        lo, hi = source["extent"]
        q = verifier.ask(
            f"defsat@{source['image']}:{lo}:{hi}:{site['base_register']}:{source['pc']}")[0]
        observable = [d for d in q["definitions"] if d["observable"]]
        fact.update({
            "definition_classes": sorted({d["class"] for d in observable}),
            "definitions": observable,
            "entry_reachable": q["entry_reachable_uses"],
        })
        facts.append(fact)
    row["entry_value_typing"] = facts
    if any(f.get("delay_slot_writes_base") or f.get("entry_reachable")
           for f in facts):
        row["outcome"] = "blocked_dispatch_entry_value_unrecovered"
        row["reason"] = ("at least one established entry edge has an untyped "
                         "base value or a redefining delay slot")
        return row
    failed_table_defs = [
        (fact, definition)
        for fact in facts for definition in fact.get("definitions") or []
        if definition.get("table_address_failure")]
    if failed_table_defs:
        candidates = [
            {"image": fact["image"], "extent": fact["extent"],
             "definition": definition,
             "context": f"established_{fact['kind']}_entry_edge@{fact['pc']}"}
            for fact, definition in failed_table_defs]
        return decide_index_interval(
            row, site, verifier, index, transfer_closure, candidates,
            "blocked_index_sign_needs_convention")
    classes = sorted({cls for fact in facts for cls in fact["definition_classes"]})
    if classes == ["global_load"]:
        cells = sorted({d["address"] for fact in facts for d in fact["definitions"]
                        if d.get("address")})
        if len(cells) == 1:
            row["outcome"] = "blocked_writer_universe_exhaustiveness"
            row["cells"] = cells
            row["reason"] = ("every established entry edge carries the base from "
                             f"fixed cell {cells[0]}; its content typing remains "
                             "gated on the non-exhaustive table-writer universe")
            return row
    if (classes == ["table_address"]
            and all(ts._proved_table_address_definition(definition)
                    for fact in facts for definition in fact["definitions"])):
        tables = sorted({d["table"] for fact in facts for d in fact["definitions"]
                         if d.get("table")})
        if len(tables) == 1:
            candidates = [
                {"image": fact["image"], "extent": fact["extent"],
                 "definition": definition,
                 "context": f"established_{fact['kind']}_entry_edge@{fact['pc']}"}
                for fact in facts for definition in fact["definitions"]
                if definition.get("class") == "table_address"]
            return decide_index_interval(
                row, site, verifier, index, transfer_closure, candidates,
                "blocked_index_sign_needs_convention")
    row["outcome"] = "blocked_dispatch_entry_value_unrecovered"
    row["reason"] = ("the exact established entry-edge set does not reduce to one "
                     "proof-grade global cell or bounded table-address domain")
    return row


def window_free(lo: int, hi: int) -> bool:
    return all(hi <= w_lo or lo >= w_hi for w_lo, w_hi in WINDOWS)


def type_return(verifier: ts.Verifier, index: dict, image: str,
                callee: int) -> dict:
    """Type one callee's return, chasing exactly ONE pure-copy hop."""
    record = next((r for r in index["records"]
                   if r["image_id"] == image and r.get("entry")
                   and _int(r["entry"]) == callee), None)
    if record is None:
        resident = next((r for r in index["records"]
                         if r["image_id"] == "SCUS_942_88" and r.get("entry")
                         and _int(r["entry"]) == callee), None)
        if resident is None:
            return {"callee": f"0x{callee:08x}", "outcome": "no_index_record"}
        image, record = "SCUS_942_88", resident
    q = verifier.ask(f"returns@{image}:{record['entry']}:{record['end']}")[0]
    if q.get("no_return_site"):
        return {"callee": f"0x{callee:08x}", "name": record.get("name"),
                "outcome": "no_return_site"}
    observable = [d for d in q["definitions"] if d["observable"]]
    classes = sorted({d["class"] for d in observable})
    result = {"callee": f"0x{callee:08x}", "name": record.get("name"),
              "return_def_classes": classes}
    if classes == ["register_copy"] and len(observable) == 1:
        # ONE copy hop: what does the copied register hold at the return?
        src = observable[0].get("from")
        pc = observable[0]["pc"]
        if src:
            q2 = verifier.ask(
                f"defsat@{image}:{record['entry']}:{record['end']}:{src}:{pc}")[0]
            obs2 = [d for d in q2["definitions"] if d["observable"]]
            result["copy_hop"] = {
                "register": src, "at": pc,
                "image": image,
                "extent": [record["entry"], record["end"]],
                "def_classes": sorted({d["class"] for d in obs2}),
                "definitions": obs2,
                "table_base_proved": bool(obs2) and all(
                    ts._proved_table_address_definition(d) for d in obs2),
                "tables": sorted({d.get("table") for d in obs2 if d.get("table")}),
                "addresses": sorted({d.get("address") for d in obs2
                                     if d.get("address")}),
                "entry_reachable": q2["entry_reachable_uses"],
            }
    if classes == ["global_load"] and q.get("loaded_from"):
        result["loaded_from"] = q["loaded_from"]
    return result


def record_has_external_interior_entries(
        index: dict, image: str, lo: int, hi: int,
        transfer_closure: dict,
) -> list[dict]:
    """Campaign spelling of the shared proved-or-unknown entry closure."""
    return ts._external_interior_entries(
        index, image, lo, hi, transfer_closure)


def instruction_word(verifier: ts.Verifier, index: dict,
                     image: str, pc: int) -> str | None:
    """Read one instruction through the C image/query path, never in Python."""
    record = next((item for item in index["records"]
                   if item.get("entry") and item["image_id"] == image
                   and _int(item["entry"]) <= pc < _int(item["end"])), None)
    if record is None:
        return None
    query = verifier.ask(
        f"indexdom@{image}:{record['entry']}:{record['end']}:zero:0x{pc:08x}")[0]
    return query.get("site_word")


def _access_width(site: dict) -> int:
    """Instruction width for the fixture row (the C ledger omits it sometimes)."""
    if site.get("width") is not None:
        return int(site["width"])
    return {"sb": 1, "sh": 2, "sw": 4, "swl": 4, "swr": 4}.get(
        str(site.get("mnemonic") or "").lower(), 4)


def decide_index_interval(row: dict, site: dict, verifier: ts.Verifier,
                          index: dict, transfer_closure: dict,
                          candidates: list[dict],
                          prior_outcome: str) -> dict:
    """Run indexdom@ for every table-address definition feeding one site.

    The queried register is the exact non-constant addend at the `addu` that
    formed TABLE+INDEX, and the query point is that `addu` itself (before it
    executes).  A proof is accepted only when every definition has an
    instruction-derived unsigned interval, the extent has no external interior
    entry, and adding the interval to the table cannot wrap 32-bit address
    arithmetic.  The lower bound then excludes the F01 windows without a loop
    bound or an upper-bound convention.  Every failure retains the C query's
    exact breaker PC, word, and reason.
    """
    attempts: list[dict] = []
    for candidate in candidates:
        definition = candidate["definition"]
        image = candidate["image"]
        lo, hi = candidate["extent"]
        attempt = {
            "context": candidate["context"],
            "image": image,
            "extent": [lo, hi],
            "table": definition.get("table"),
            "table_address_definition_pc": definition.get("pc"),
            "table_address_definition_word": definition.get("word"),
            "index_register": definition.get("index"),
            "table_base_register": definition.get("table_base_register"),
            "table_base_proof": definition.get("table_base_proof"),
            "classification_hops": definition.get("hops"),
        }
        if not ts._proved_table_address_definition(definition):
            attempt["verdict"] = False
            attempt["breaking_instruction"] = (
                definition.get("table_address_failure") or {
                    "pc": definition.get("pc"), "word": definition.get("word"),
                    "reason": "table-address constant operand lacks a "
                              "path-complete reaching-definition proof"})
            attempts.append(attempt)
            continue
        if (definition.get("hops") or 0) != 0:
            attempt["verdict"] = False
            attempt["breaking_instruction"] = {
                "pc": definition.get("pc"), "word": definition.get("word"),
                "reason": "table-address definition is hidden behind a copy; "
                          "the index-use PC is not exact"}
            attempts.append(attempt)
            continue
        index_reg = definition.get("index")
        use_pc = definition.get("pc")
        if not index_reg or not use_pc or not definition.get("table"):
            attempt["verdict"] = False
            attempt["breaking_instruction"] = {
                "pc": definition.get("pc"), "word": definition.get("word"),
                "reason": "table-address classification lacks table/index/use PC"}
            attempts.append(attempt)
            continue
        external = record_has_external_interior_entries(
            index, image, _int(lo), _int(hi), transfer_closure)
        query = verifier.ask(
            f"indexdom@{image}:{lo}:{hi}:{index_reg}:{use_pc}")[0]
        attempt["external_interior_entries"] = external
        attempt["index_domain"] = query
        attempt["c_interval_verdict"] = bool(query.get("verdict"))
        attempt["external_entry_domain_closed"] = not external
        attempt["verdict"] = bool(query.get("verdict")) and not external
        if not query.get("verdict"):
            attempt["breaking_instruction"] = query.get("breaking_instruction")
        elif external:
            edge = dict(external[0])
            edge["word"] = instruction_word(
                verifier, index, str(edge["image"]), _int(edge["pc"]))
            attempt["breaking_instruction"] = {
                "pc": edge.get("pc"), "word": edge.get("word"),
                "reason": (edge.get("reason") or
                           "external edge enters the interval-query extent interior")}
        else:
            attempt["breaking_instruction"] = None
        attempts.append(attempt)

    row["prior_outcome"] = prior_outcome
    row["index_interval_attempts"] = attempts
    if not attempts or any(not attempt["verdict"] for attempt in attempts):
        breakers = [attempt.get("breaking_instruction") for attempt in attempts
                    if not attempt.get("verdict")]
        row["outcome"] = "blocked_index_interval_unproved_instruction"
        row["breaking_instructions"] = [b for b in breakers if b]
        if row["breaking_instructions"]:
            first = row["breaking_instructions"][0]
            row["reason"] = (
                "the instruction/entry closure rejects at least one interval "
                f"attempt: {first.get('pc')} word {first.get('word')} "
                f"({first.get('reason')}); no convention is substituted")
        else:
            row["reason"] = (
                "no exact table-address index use was available to the C prover")
        return row

    width = _access_width(site)
    effective: list[dict] = []
    arithmetic_ok = True
    for attempt in attempts:
        interval = attempt["index_domain"]["interval"]
        table = _int(attempt["table"])
        lo64 = table + int(interval["min"]) + int(site["offset"])
        hi64 = table + int(interval["max"]) + int(site["offset"]) + width
        no_wrap = 0 <= lo64 <= 0xffffffff and 0 <= hi64 <= 0x100000000
        arithmetic_ok = arithmetic_ok and no_wrap
        alias_checks = ([ts._ps1_ram_window_exclusion(
            lo64, hi64, w_lo, w_hi) for w_lo, w_hi in WINDOWS]
            if no_wrap else [])
        effective.append({
            "table": f"0x{table:08x}",
            "index_interval": interval,
            "displacement": int(site["offset"]),
            "width": width,
            "effective_address_interval": (
                [f"0x{lo64:08x}", f"0x{hi64:08x}"] if no_wrap else None),
            "no_32bit_wrap": no_wrap,
            "ps1_ram_alias_checks": alias_checks,
        })
    row["effective_intervals"] = effective
    if not arithmetic_ok:
        limiting = attempts[0]["index_domain"]
        row["outcome"] = "blocked_index_interval_address_wrap_possible"
        row["breaking_instructions"] = [{
            "pc": limiting["site_pc"], "word": limiting["site_word"],
            "reason": "proved index interval can wrap TABLE+INDEX address arithmetic"}]
        row["reason"] = (
            "the index interval itself is proved, but TABLE+INDEX can wrap; a "
            "numeric lower bound on the effective address would be unsound")
        return row

    alias_overlaps = sorted({
        tuple(alias)
        for item in effective
        for check in item["ps1_ram_alias_checks"]
        for alias in check["overlapping_aliases"]})
    if alias_overlaps:
        limiting = attempts[0]["index_domain"]
        row["outcome"] = "blocked_index_interval_ps1_ram_alias_overlap"
        row["breaking_instructions"] = [{
            "pc": limiting["site_pc"], "word": limiting["site_word"],
            "reason": "proved numeric interval overlaps a PS1 2 MiB RAM mirror "
                      "of a watched window"}]
        row["overlapping_ps1_ram_aliases"] = [list(row) for row in alias_overlaps]
        row["reason"] = (
            "virtual-address non-overlap is insufficient: the proved interval "
            "contains a mirrored physical alias of watched state")
        return row

    lower = min(_int(item["effective_address_interval"][0]) for item in effective)
    if not window_free(lower, RAM_HI):
        limiting = attempts[0]["index_domain"]
        row["outcome"] = "blocked_index_interval_lower_bound_reaches_window"
        row["breaking_instructions"] = [{
            "pc": limiting["site_pc"], "word": limiting["site_word"],
            "reason": (f"proved lower bound 0x{lower:08x} does not exclude "
                       "both watched windows")}]
        row["reason"] = (
            f"the interval is instruction-proved, but [0x{lower:08x}, "
            f"0x{RAM_HI:08x}) overlaps a watched window; no upper-bound "
            "convention is attempted")
        return row

    row["outcome"] = "decided_index_interval_lower_bound"
    row["proof"] = {
        "kind": "instruction_derived_unsigned_index_interval",
        "every_reaching_definition_whitelisted": True,
        "full_derivations": [attempt["index_domain"]["derivations"]
                             for attempt in attempts],
        "effective_intervals": effective,
        "valid_ram_store_interval": [f"0x{lower:08x}", f"0x{RAM_HI:08x}"],
        "windows": [[f"0x{lo:08x}", f"0x{hi:08x}"] for lo, hi in WINDOWS],
        "windows_excluded_because": (
            "both canonical windows lie below the lower bound and the complete "
            "effective intervals miss every direct/KSEG0/KSEG1 PS1 RAM alias"),
        "uses_loop_bound": False,
        "uses_index_sign_convention": False,
        "uses_upper_bound_convention": False,
    }
    row["reason"] = (
        "every table-address index has a C-proved unsigned interval and "
        f"[0x{lower:08x}, 0x{RAM_HI:08x}) misses both windows")
    return row


def try_anchored_progression(row: dict, observable: list[dict], site: dict,
                             index: dict, transfer_closure: dict) -> dict | None:
    """DECIDED path: every observable def is an agreeing anchor or a uniform
    positive self-adjustment, the site is governed, and no external edge enters
    the record's interior -- then the base is >= anchor on the anchor's
    lattice, and [anchor+disp, RAM_HI) either misses both windows or it does
    not. Rests on the DELAY-SLOT-CORRECTED reach walk (the prior blind spot is
    fixed and pinned by test) plus the cross-extent guard; the standing jalr
    caveat travels with it like every binding.
    """
    anchors = {_int(d["value"]) for d in observable
               if d["class"] == "materialised_constant" and d.get("value")}
    deltas = {int(d.get("delta", 0)) for d in observable
              if d["class"] == "self_adjust"}
    others = [d for d in observable
              if d["class"] not in ("materialised_constant", "self_adjust")]
    if others or len(anchors) != 1 or not deltas:
        return None
    if any(d <= 0 for d in deltas) or len(deltas) != 1:
        row["outcome"] = "blocked_progression_delta_not_uniform_positive"
        row["reason"] = (f"anchor {sorted(anchors)} with self-adjust deltas "
                        f"{sorted(deltas)}; a non-positive or mixed stride "
                        "gives no lower bound")
        return row
    lo, hi = _int(site["extent"][0]), _int(site["extent"][1])
    external = record_has_external_interior_entries(
        index, site["image"], lo, hi, transfer_closure)
    if external:
        row["outcome"] = "blocked_external_interior_entry"
        row["external_entries"] = external[:10]
        row["reason"] = ("the record's interior is entered from outside its "
                        "extent, so extent-local reachability does not bound "
                        "the register state")
        return row
    anchor = anchors.pop()
    span_lo = anchor + int(site["offset"])
    if window_free(span_lo, RAM_HI):
        row["outcome"] = "decided_anchored_progression_lower_bound"
        row["proof"] = {
            "anchor": f"0x{anchor:08x}", "stride": sorted(deltas)[0],
            "value_domain": "anchor + k*stride, k >= 0 (no upper bound)",
            "store_interval": [f"0x{span_lo:08x}", f"0x{RAM_HI:08x}"],
            "windows_excluded_because": "both windows lie below the interval",
            "rests_on": [
                "delay-slot-corrected reachability (pinned by test)",
                "zero external interior entries (index + both jr maps)",
                "callee-saved discipline across calls (standing assumption)",
                "unbounded jalr entries not excluded (standing Item-2 blocker)",
            ],
        }
        return row
    row["outcome"] = "blocked_progression_interval_reaches_a_window"
    row["reason"] = (f"anchor 0x{anchor:08x} + disp {site['offset']} gives "
                    f"[0x{span_lo:08x}, RAM_HI) which overlaps a window; the "
                    "lower bound alone cannot exclude it")
    return row


def process_site(site: dict, verifier: ts.Verifier, index: dict,
                 transfer_closure: dict) -> dict:
    """One eligible site -> a decided bound or a NAMED machine-derived reason."""
    image, lo, hi = site["image"], site["extent"][0], site["extent"][1]
    base, pc = site["base_register"], site["pc"]
    q = verifier.ask(f"{image}:{lo}:{hi}:{base}:{pc}")[0]
    observable = [d for d in q["definitions"] if d["observable"]]
    classes = sorted({d["class"] for d in observable})
    row = {**site, "base_def_classes": classes,
           "entry_reachable": q["entry_reachable_uses"]}

    # ---- one COPY hop, site-level: s0 = pure copy of X -> ask about X -------
    # The C chase stops at a basic-block wall; defsat at the copy's pc crosses
    # it CFG-aware. Exactly one hop, recorded; deeper chains stay a named
    # further method.
    if (classes == ["register_copy"] and observable
            and not q["entry_reachable_uses"]
            and len({d.get("from") for d in observable}) == 1
            and observable[0].get("from")):
        src = observable[0]["from"]
        hopped: list[dict] = []
        for d in observable:
            q2 = verifier.ask(f"defsat@{image}:{lo}:{hi}:{src}:{d['pc']}")[0]
            hopped.extend(x for x in q2["definitions"] if x["observable"])
            if q2["entry_reachable_uses"]:
                hopped.append({"class": "entry_value", "pc": d["pc"]})
        row["copy_hop"] = {"register": src,
                           "classes": sorted({x["class"] for x in hopped})}
        observable = hopped
        classes = row["copy_hop"]["classes"]
        row["base_def_classes"] = [f"register_copy->{c}" for c in classes]

    if q["entry_reachable_uses"] and base in ("s0", "s1", "s2", "s3", "s4",
                                              "s5", "s6", "s7", "fp"):
        # The site can execute with the register's ENTRY value. Recover it at
        # every established direct or proved-jr entry edge, including branches
        # and tail dispatches; a return-address heuristic is not an edge.
        return recover_entry_value(
            row, site, verifier, index, transfer_closure)

    if classes == ["call_result"]:
        callees = sorted({_int(d["callee"]) for d in observable
                          if d.get("callee")})
        indirect = any(d.get("indirect") for d in observable)
        if indirect or not callees:
            row["outcome"] = "blocked_indirect_call_result"
            row["reason"] = ("the base is the result of an INDIRECT call; no "
                            "callee to type -- the enumerated jalr blocker")
            return row
        typed_returns = [type_return(verifier, index, image, c) for c in callees]
        row["return_typing"] = typed_returns
        tables = sorted({t for r in typed_returns
                         for t in (r.get("copy_hop", {}).get("tables") or [])})
        if (len(typed_returns) == len(callees)
                and all(r.get("copy_hop", {}).get("def_classes") == ["table_address"]
                        and r.get("copy_hop", {}).get("table_base_proved") is True
                        for r in typed_returns)
                and len(tables) == 1
                and all(not r.get("copy_hop", {}).get("entry_reachable")
                        for r in typed_returns)):
            candidates = []
            for result in typed_returns:
                callee = _int(result["callee"])
                record = next((record for record in index["records"]
                               if record["image_id"] == image and record.get("entry")
                               and _int(record["entry"]) == callee), None)
                result_image = image
                if record is None:
                    result_image = "SCUS_942_88"
                    record = next(record for record in index["records"]
                                  if record["image_id"] == result_image
                                  and record.get("entry")
                                  and _int(record["entry"]) == callee)
                hop = result["copy_hop"]
                q2 = verifier.ask(
                    f"defsat@{result_image}:{record['entry']}:{record['end']}:"
                    f"{hop['register']}:{hop['at']}")[0]
                candidates.extend(
                    {"image": result_image,
                     "extent": [record["entry"], record["end"]],
                     "definition": definition,
                     "context": f"return_from_{result.get('name')}@{result['callee']}"}
                    for definition in q2["definitions"]
                    if definition["observable"]
                    and ts._proved_table_address_definition(definition))
            return decide_index_interval(
                row, site, verifier, index, transfer_closure, candidates,
                "blocked_return_domain_needs_index_convention")
        failed_return_defs = [
            (result, definition)
            for result in typed_returns
            for definition in (result.get("copy_hop", {}).get("definitions") or [])
            if definition.get("table_address_failure")]
        if failed_return_defs:
            candidates = [
                {"image": result["copy_hop"]["image"],
                 "extent": result["copy_hop"]["extent"],
                 "definition": definition,
                 "context": (f"return_from_{result.get('name')}"
                             f"@{result['callee']}")}
                for result, definition in failed_return_defs]
            return decide_index_interval(
                row, site, verifier, index, transfer_closure, candidates,
                "blocked_return_domain_needs_index_convention")
        row["outcome"] = "blocked_return_domain_unrecovered"
        row["reason"] = ("callee return values do not reduce to one typed "
                        "domain within one copy hop; deeper interprocedural "
                        "return-domain propagation is a further method")
        return row

    if classes and set(classes) <= {"global_load", "table_load"}:
        # A direct element-0 load and an indexed load are two spellings of the
        # same table dependency when every recovered address agrees. Keep the
        # exact definition classes, but do not misfile their mixture as "no
        # method": both require the same content-domain/writer-universe proof.
        cells = sorted(
            {d["address"] for d in observable
             if d["class"] == "global_load" and d.get("address")} |
            {d["table"] for d in observable
             if d["class"] == "table_load" and d.get("table")})
        if len(cells) == 1:
            row["outcome"] = "blocked_writer_universe_exhaustiveness"
            row["cells"] = cells
            row["reason"] = (
                f"every recovered base definition loads from table {cells[0]} "
                "(direct element-0 and/or indexed spelling); its content "
                "domain is the same chain both table-backed bindings are "
                "GATED on -- the writer universe is a corroborated lower "
                "bound, not a census (5,012 undecided stores measured "
                "corpus-wide)")
            return row

    if (classes == ["table_address"]
            and all(ts._proved_table_address_definition(definition)
                    for definition in observable)):
        tables = sorted({d.get("table") for d in observable if d.get("table")})
        if len(tables) == 1:
            candidates = [
                {"image": image, "extent": [lo, hi], "definition": definition,
                 "context": f"site_base_definition@{definition['pc']}"}
                for definition in observable]
            return decide_index_interval(
                row, site, verifier, index, transfer_closure, candidates,
                "blocked_index_sign_needs_convention")

    failed_table_defs = [
        definition for definition in observable
        if definition.get("table_address_failure")]
    if failed_table_defs:
        # The stricter shared CFG may reject the TABLE operand before the
        # unsigned-index query can run.  This is still an interval-campaign
        # result: retain the exact C breaker rather than degrading the row to a
        # generic no-method bucket or reviving its convention.
        cells = sorted(
            {d["address"] for d in observable
             if d["class"] == "global_load" and d.get("address")} |
            {d["table"] for d in observable
             if d["class"] == "table_load" and d.get("table")})
        if cells:
            row["coexisting_writer_universe_cells"] = cells
            row["coexisting_writer_universe_exhaustive"] = False
        candidates = [
            {"image": image, "extent": [lo, hi], "definition": definition,
             "context": f"site_base_definition@{definition['pc']}"}
            for definition in failed_table_defs]
        return decide_index_interval(
            row, site, verifier, index, transfer_closure, candidates,
            "blocked_index_sign_needs_convention")

    if classes == ["self_adjust"] and base == "sp":
        row["outcome"] = "blocked_stack_entry_value_caller_dependent"
        row["reason"] = ("sp-relative after a frame adjustment; the entry sp "
                        "is the caller's, so stack-region membership is a "
                        "convention about the runtime layout, not an "
                        "instruction-derived bound")
        return row

    progression = try_anchored_progression(
        row, observable, site, index, transfer_closure)
    if progression is not None:
        return progression

    row["outcome"] = "blocked_no_recovery_method"
    row["definitions"] = [{k: d.get(k) for k in
                           ("pc", "class", "value", "address", "table", "from",
                            "callee", "word", "table_address_failure")
                           if d.get(k) is not None}
                          for d in observable]
    row["reason"] = ("no method in this campaign's definition applies to this "
                    "definition shape; the raw observable definitions are "
                    "retained as the failure reason")
    return row


def outcome_movement(before_rows: list[dict], after_rows: list[dict]) -> dict:
    """Exact outcome-set movement for one stable campaign-row universe."""
    before = {row["id"]: row["outcome"] for row in before_rows}
    after = {row["id"]: row["outcome"] for row in after_rows}
    if len(before) != len(before_rows) or len(after) != len(after_rows):
        raise RuntimeError("campaign row ids are not unique")
    before_ids = set(before)
    after_ids = set(after)
    shared_ids = before_ids & after_ids
    baseline_only_ids = sorted(before_ids - after_ids)
    current_only_ids = sorted(after_ids - before_ids)
    changed = [{"id": site_id, "before": before[site_id], "after": after[site_id]}
               for site_id in sorted(shared_ids)
               if before[site_id] != after[site_id]]
    outcomes = sorted(set(before.values()) | set(after.values()))
    set_movement = {
        outcome: {
            "gained_ids": sorted(site_id for site_id in after
                                 if after[site_id] == outcome and
                                 before.get(site_id) != outcome),
            "lost_ids": sorted(site_id for site_id in before
                               if before[site_id] == outcome and
                               after.get(site_id) != outcome),
        }
        for outcome in outcomes
        if (any(after[site_id] == outcome and before.get(site_id) != outcome
                for site_id in after) or
            any(before[site_id] == outcome and after.get(site_id) != outcome
                for site_id in before))
    }
    return {
        "comparison": (
            "exact row-id sets in both directions; changed_outcomes is "
            "restricted to shared ids, while one-sided ids and outcome "
            "gains/losses are listed explicitly"),
        "baseline_site_rows": len(before),
        "current_site_rows": len(after),
        "shared_site_rows": len(shared_ids),
        "baseline_only_ids": baseline_only_ids,
        "current_only_ids": current_only_ids,
        "baseline_only_outcomes": [
            {"id": site_id, "outcome": before[site_id]}
            for site_id in baseline_only_ids],
        "current_only_outcomes": [
            {"id": site_id, "outcome": after[site_id]}
            for site_id in current_only_ids],
        "changed_outcome_count": len(changed),
        "changed_outcomes": changed,
        "outcome_site_set_movement": set_movement,
    }


def breaker_movement(before_rows: list[dict], after_rows: list[dict]) -> dict:
    """Exact before/after breaker arrays for a stable campaign universe."""
    before = {str(row["id"]): row.get("breaking_instructions") or []
              for row in before_rows}
    after = {str(row["id"]): row.get("breaking_instructions") or []
             for row in after_rows}
    if len(before) != len(before_rows) or len(after) != len(after_rows):
        raise RuntimeError("campaign row ids are not unique")
    before_ids, after_ids = set(before), set(after)
    changed_ids = sorted(
        site_id for site_id in before_ids & after_ids
        if before[site_id] != after[site_id])
    return {
        "comparison": (
            "exact row-id universe in both directions and full ordered "
            "breaker arrays before and after for every changed shared id"),
        "baseline_site_rows": len(before),
        "current_site_rows": len(after),
        "baseline_only_ids": sorted(before_ids - after_ids),
        "current_only_ids": sorted(after_ids - before_ids),
        "changed_breaker_count": len(changed_ids),
        "changed_breaker_ids": changed_ids,
        "changed_breakers": [
            {"id": site_id, "before": before[site_id],
             "after": after[site_id]}
            for site_id in changed_ids],
    }


def build() -> dict:
    resolve_raw = RESOLVE_PATH.read_bytes()
    typed_raw = TYPED_STATE_PATH.read_bytes()
    index_raw = ts.INDEX_PATH.read_bytes()
    hard_truth_raw = HARD_TRUTH_PATH.read_bytes()
    baseline_raw = BASELINE_PATH.read_bytes()
    resolve = json.loads(resolve_raw)
    typed = json.loads(typed_raw)
    index = json.loads(index_raw)
    hard_truth = json.loads(hard_truth_raw)
    baseline = json.loads(baseline_raw)
    if (hard_truth.get("verdicts") or {}).get("requested_dispatch_sites_proved"):
        raise RuntimeError("hard-truth receipt unexpectedly proves the claimed jalr sites")
    if int((hard_truth.get("verdicts") or {}).get(
            "new_indirect_target_sets_to_register", -1)) != 0:
        raise RuntimeError("hard-truth receipt requires an unregistered dispatch set")
    verifier = ts.Verifier(index)
    transfer_closure = ts._indirect_transfer_closure(index)

    sites, ambiguous = derive_universe(resolve, typed, index)
    rows = [process_site(site, verifier, index, transfer_closure)
            for site in sites]
    decided = [r for r in rows if r["outcome"].startswith("decided")]
    tally: dict[str, int] = {}
    for r in rows:
        tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1

    legacy_movement = outcome_movement(baseline.get("outcomes") or [], rows)
    prerequisite_object = f"{PREREQUISITE_COMMIT}:{PREREQUISITE_ARTIFACT}"
    prerequisite_proc = subprocess.run(
        ["git", "show", prerequisite_object], cwd=ROOT, capture_output=True)
    if prerequisite_proc.returncode:
        raise RuntimeError(
            f"cannot read prerequisite campaign {prerequisite_object}: "
            + prerequisite_proc.stderr.decode(errors="replace").strip())
    prerequisite_raw = prerequisite_proc.stdout
    prerequisite = json.loads(prerequisite_raw)
    prerequisite_by_id = {
        item["id"]: item["outcome"] for item in prerequisite.get("sites") or []}
    for row in rows:
        if ("prior_outcome" in row
                and row["id"] in prerequisite_by_id):
            row["prior_outcome"] = prerequisite_by_id[row["id"]]
    prerequisite_movement = outcome_movement(
        prerequisite.get("sites") or [], rows)
    ratchet_object = (f"{RA_RATCHET_BASELINE_COMMIT}:"
                      f"{RA_RATCHET_BASELINE_ARTIFACT}")
    ratchet_proc = subprocess.run(
        ["git", "show", ratchet_object], cwd=ROOT, capture_output=True)
    if ratchet_proc.returncode:
        raise RuntimeError(
            f"cannot read pre-ra-ratchet campaign {ratchet_object}: "
            + ratchet_proc.stderr.decode(errors="replace").strip())
    ratchet_raw = ratchet_proc.stdout
    ratchet = json.loads(ratchet_raw)
    ratchet_breaker_movement = breaker_movement(
        ratchet.get("sites") or [], rows)

    table_attest = next(
        (binding.get("attestation") for binding in typed["bindings"]
         if (binding.get("attestation") or {}).get("known_writer_identity")), None)
    if table_attest is None:
        raise RuntimeError("typed-state artifact lacks corrected writer attestation")
    writer_universe = table_attest["table_writer_universe"]

    return {
        "schema": SCHEMA,
        "question": ("Can any of the acceptance fixture's still-unresolved "
                     "stores be decided by recovering its locally computed "
                     "base -- with proof, not convention?"),
        "inputs": {
            "fixture": str(RESOLVE_PATH.relative_to(ROOT)),
            "fixture_sha256": _sha(resolve_raw),
            "typed_state": str(TYPED_STATE_PATH.relative_to(ROOT)),
            "typed_state_sha256": _sha(typed_raw),
            "static_index_sha256": _sha(index_raw),
            "static_hard_truth": str(HARD_TRUTH_PATH.relative_to(ROOT)),
            "static_hard_truth_sha256": _sha(hard_truth_raw),
            "outcome_baseline": str(BASELINE_PATH.relative_to(ROOT)),
            "outcome_baseline_sha256": _sha(baseline_raw),
            "outcome_baseline_source_commit": baseline["source_commit"],
            "outcome_baseline_source_artifact_sha256":
                baseline["source_artifact_sha256"],
            "prerequisite_commit": PREREQUISITE_COMMIT,
            "prerequisite_artifact": PREREQUISITE_ARTIFACT,
            "prerequisite_artifact_sha256": _sha(prerequisite_raw),
            "verifier_source": ts.VERIFIER_SRC,
            "verifier_source_sha256": verifier.source_sha,
            "verifier_binary_sha256": verifier.binary_sha,
        },
        "eligible_universe": {
            "definition": ("every acceptance-fixture STORE whose ledger "
                           "verdict in the retained typed-state artifact is "
                           "still_unresolved -- i.e. undecided by constant "
                           "propagation, the ABI accelerator, typed-pointer "
                           "loads, the proved-jr chain, AND the convention-"
                           "tier second opinion"),
            "site_rows": len(rows),
            "ambiguous_joins": ambiguous,
            "note": ("site_rows counts (image, pc) rows; a pc shared by two "
                     "overlays contributes a row per candidate image and the "
                     "ambiguity is listed above, never collapsed"),
        },
        "sites": rows,
        "every_eligible_site_processed": len(rows) == len(sites),
        "tally": dict(sorted(tally.items())),
        "decided_by_proof": len(decided),
        "movement_from_1bba2487": legacy_movement,
        "movement_from_b6cb61d35f9d": {
            "baseline_commit": PREREQUISITE_COMMIT,
            "baseline_artifact": PREREQUISITE_ARTIFACT,
            "baseline_artifact_sha256": _sha(prerequisite_raw),
            **prerequisite_movement,
        },
        "breaker_movement_from_05bc6b8a251b": {
            "baseline_commit": RA_RATCHET_BASELINE_COMMIT,
            "baseline_artifact": RA_RATCHET_BASELINE_ARTIFACT,
            "baseline_artifact_sha256": _sha(ratchet_raw),
            "meaning": (
                "the campaign outcomes do not move; this exact receipt pins "
                "which machine breaker changed under the local-ra ratchet"),
            **ratchet_breaker_movement,
        },
        "dispatch_hard_truth": {
            "requested_sites": hard_truth["c_probe"]["requested_dispatch_sites"],
            "new_indirect_target_sets_registered": [],
            "actual_entry_edges_consumed": {
                "seed_plant_trampoline_handler": ["0x8005C108 proved jr"],
                "berry_tough_damage_dispatch": [
                    "0x80058EE8 direct branch", "0x80058F08 direct branch"],
            },
            "meaning": ("the claimed jalr PCs failed closed; campaign movement "
                        "comes from consuming the real already-registered jr edge "
                        "and the two direct branch entry edges"),
        },
        "external_indirect_transfer_closure": transfer_closure,
        "writer_falsifier_remeasurement": {
            "known_writer_identity": table_attest["known_writer_identity"],
            "recognizer_residual": table_attest["writer_recognizer_residual"],
            "corpus_undecided_stores": writer_universe["corpus_undecided_stores"],
            "resolved_write_hit_pcs": writer_universe["resolved_write_hit_pcs"],
            "resolved_writers_not_previously_enumerated":
                writer_universe["resolved_writers_not_previously_enumerated"],
            "known_writer_set_gained": writer_universe["known_writer_set_gained"],
            "known_writer_set_lost": writer_universe["known_writer_set_lost"],
            "exhaustive": writer_universe["exhaustive"],
        },
        "campaign": {
            "proposed_disposition": "bounded_exhausted_locally_computed_base_recovery",
            "method_definition": ("per-site base-definition classification by "
                                  "the rebuilt C verifier (delay-slot-"
                                  "corrected reachability); ONE site-level "
                                  "copy hop across a basic-block wall; "
                                  "per-site return typing with exactly ONE "
                                  "copy hop at the return; callee-saved "
                                  "entry-value recovery over every exact direct "
                                  "call/jump/branch and already-proved jr edge, "
                                  "with non-call delay slots checked for base "
                                  "redefinition; the anchored-progression "
                                  "lower-bound proof (agreeing constant "
                                  "anchor + uniform positive self-adjust, "
                                  "governed site, zero external interior "
                                  "entries); no convention is relabelled as "
                                  "proof; exact table-address indices at direct "
                                  "and one-hop return sites are queried with "
                                  "indexdom@, whose lbu/lhu/andi/srl/sltiu/"
                                  "constant/sll/addu/addiu whitelist rejects "
                                  "any unclassified reaching definition and "
                                  "accepts a lower bound only after a no-wrap "
                                  "check"),
            "banked": False,
            "banking_authority": "a fresh detached verifier only",
            "reopening_falsifiers": [
                "a direct or proved indirect entry edge appears for a function "
                "still filed under blocked_no_direct_caller",
                "any jalr site's target set is bounded (gate or otherwise), "
                "unlocking the blocked_indirect_call_result and "
                "blocked_no_direct_caller classes",
                "the table-writer universe for any cell named here is proved "
                "exhaustive, unlocking blocked_writer_universe_exhaustiveness",
                "one of the exact breaking instructions retained by an "
                "blocked_index_interval_unproved_instruction indexdom attempt "
                "is independently proved by a new general "
                "method (never by weakening the whitelist for a wanted site), "
                "or an external-interior-entry boundary is eliminated",
                "a deeper interprocedural return-domain method is built and "
                "verified, unlocking blocked_return_domain_unrecovered",
            ],
        },
        "authority": {
            "changes_campaign_registry": False,
            "promotes_dimension": False,
            "closes_item_2": False,
            "banks_the_disposition": False,
        },
    }


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


def build_outcome_baseline() -> dict:
    """Rebuild the pinned 1bba2487 outcome snapshot from its Git object.

    This is deliberately a separate generator mode: the historical snapshot
    is an input to the current campaign comparison, never an output inferred
    from the current campaign.  The full source commit and source-artifact
    bytes are pinned in the rendered document.
    """
    object_name = f"{BASELINE_SOURCE_COMMIT}:{BASELINE_SOURCE_ARTIFACT}"
    proc = subprocess.run(
        ["git", "show", object_name], cwd=ROOT, capture_output=True)
    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="replace").strip()
        raise RuntimeError(
            f"cannot read pinned baseline object {object_name}: {detail}")
    source_raw = proc.stdout
    try:
        source = json.loads(source_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"pinned baseline object {object_name} is not JSON: {exc}") from exc
    sites = source.get("sites")
    if not isinstance(sites, list):
        raise RuntimeError(f"pinned baseline object {object_name} has no site list")

    bases = [
        f"{row['image']}:0x{_int(row['pc']):08X}:{row['base_register']}"
        for row in sites
    ]
    seen: dict[str, int] = {}
    outcomes = []
    for row, base in zip(sites, bases):
        seen[base] = seen.get(base, 0) + 1
        site_id = (base if bases.count(base) == 1
                   else f"{base}:occurrence-{seen[base]}")
        outcome = str(row.get("outcome") or "")
        if not outcome.startswith(("decided", "blocked")):
            raise RuntimeError(
                f"pinned baseline site {site_id} lacks a named outcome")
        outcomes.append({"id": site_id, "outcome": outcome})
    outcomes.sort(key=lambda row: row["id"])
    if len({row["id"] for row in outcomes}) != len(outcomes):
        raise RuntimeError("pinned baseline reconstruction produced duplicate ids")
    return {
        "schema": BASELINE_SCHEMA,
        "source_commit": BASELINE_SOURCE_COMMIT,
        "source_artifact": BASELINE_SOURCE_ARTIFACT,
        "source_artifact_sha256": _sha(source_raw),
        "site_count": len(outcomes),
        "outcomes": outcomes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument(
        "--baseline-output", type=Path,
        help=("rebuild the pinned 1bba2487 outcome snapshot from the exact "
              "source artifact stored in Git"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    baseline_mode = args.baseline_output is not None
    output = args.baseline_output if baseline_mode else args.output
    payload = render(build_outcome_baseline() if baseline_mode else build())
    if args.check:
        if not output.is_file() or output.read_bytes() != payload:
            print(f"[local-base-recovery] STALE: {output}", file=sys.stderr)
            return 1
        print(f"[local-base-recovery] {output}: fresh")
        return 0
    output.write_bytes(payload)
    document = json.loads(payload)
    print(f"[local-base-recovery] wrote {output}")
    if baseline_mode:
        print(f"  pinned source {document['source_commit']} "
              f"| site rows {document['site_count']} "
              f"| source sha256 {document['source_artifact_sha256']}")
        return 0
    print(f"  eligible site rows {document['eligible_universe']['site_rows']} "
          f"| processed {document['every_eligible_site_processed']} "
          f"| decided by proof {document['decided_by_proof']}")
    for outcome, count in document["tally"].items():
        print(f"    {count:3d}  {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
