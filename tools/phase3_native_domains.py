#!/usr/bin/env python3
"""Build an independently bounded fixed-width native-domain/consumer census.

The semantic-state registry is one representation, not its own proof of
exhaustiveness. WP3 is joined from three independent machine layers:

* the exhaustive campaign-state scope manifest (what state campaigns require);
* every fixed-width typed record field (including pointer-relative fields);
* every statically decoded bounded jr selector table and its consumer site.

The generator rejects scalar semantic entries omitted from the campaign manifest
and campaign IDs omitted from the semantic registry. Removing a curated registry
row can no longer leave an exhaustive artifact green.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = {"u8", "s8", "u16", "s16", "u32", "s32"}


def sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def domain_text(entry: dict) -> str | None:
    if entry.get("domain"):
        return str(entry["domain"])
    invariants = entry.get("invariants") or []
    if invariants:
        return "; ".join(
            ", ".join(f"{key}={value}" for key, value in row.items())
            for row in invariants
        )
    return None


def classify_domain(identifier: str, domain: str | None) -> str:
    text = f"{identifier} {domain or ''}".lower()
    if any(word in text for word in ("selector", "state", "type", "kind", "opcode")):
        return "selector"
    if "flag" in text or "bit" in text:
        return "flags"
    if "coordinate" in text or "world " in text or "pos_" in text:
        return "coordinate"
    if any(word in text for word in ("counter", "timer", "count", "ttl")):
        return "counter_or_timer"
    return "scalar"


def scope_semantic_gaps(semantic: dict, scope: dict) -> tuple[list[str], list[str]]:
    """Return (unknown scope IDs, semantic scalars absent from scope)."""
    by_id = {entry["id"]: entry for entry in semantic["entries"]
             if entry.get("namespace") == "original"
             and isinstance(entry.get("address"), int)}
    scope_ids = {
        state_id for campaign in scope.get("campaigns") or []
        for state_id in campaign.get("state_ids") or []
    }
    unknown = sorted(scope_ids - set(by_id))
    scalars = {
        eid for eid, entry in by_id.items() if entry.get("width") in WIDTHS
    }
    unscoped = sorted(scalars - scope_ids)
    return unknown, unscoped


def _bounded_blocker(evidence: list[str], next_experiment: str) -> dict:
    return {
        "missing_link": "valid native value domain is not empirically bounded",
        "evidence": "; ".join(evidence),
        "next_experiment": next_experiment,
    }


def build() -> dict:
    sem_rel = "config/semantic_state.yaml"
    scope_rel = "config/phase3_campaign_state_scope.yaml"
    rec_rel = "config/record_types.yaml"
    xr_rel = "analysis/phase3_xrefs.json"
    jr_rel = "analysis/phase3_jr_tables.json"
    sem = yaml.safe_load((ROOT / sem_rel).read_text())
    scope = yaml.safe_load((ROOT / scope_rel).read_text())
    records = yaml.safe_load((ROOT / rec_rel).read_text())
    xrefs = json.loads((ROOT / xr_rel).read_text())
    jr = json.loads((ROOT / jr_rel).read_text())

    unknown_scope_ids, unscoped_scalars = scope_semantic_gaps(sem, scope)
    scope_ids = {
        state_id for campaign in scope["campaigns"]
        for state_id in campaign.get("state_ids") or []
    }
    semantic_entries = {
        entry["id"]: entry for entry in sem["entries"]
        if entry.get("namespace") == "original"
        and entry.get("width") in WIDTHS
        and isinstance(entry.get("address"), int)
    }

    state_rows = []
    for eid, entry in semantic_entries.items():
        xr = xrefs["entries"].get(eid, {})
        consumers = list(xr.get("readers") or [])
        if not consumers:
            consumers = [{
                "status": "bounded_static_method_limit",
                "reason": xr.get("no_static_xref_because")
                          or "no direct static reader is attributable",
                "next_experiment": "trace reads after the owning fixture is loaded",
            }]
        domain = domain_text(entry)
        evidence = list(entry.get("evidence") or []) + [scope_rel, xr_rel]
        row = {
            "id": eid,
            "source_kind": "campaign_state",
            "address": f"0x{entry['address']:08X}",
            "width": entry["width"],
            "classification": classify_domain(eid, domain),
            "domain": domain or "unknown",
            "consumers": consumers,
            "evidence": evidence,
            "status": "resolved" if domain else "bounded",
            "required_by_campaign_scope": eid in scope_ids,
        }
        if not domain:
            row["blocker"] = _bounded_blocker(
                evidence, "establish nonzero/edge preconditions and trace every consumer branch")
        state_rows.append(row)

    # Typed record fields are independent: most record accesses are
    # pointer-relative and cannot be discovered by the absolute-address xref pass.
    record_rows = []
    semantic_by_address = {
        entry["address"]: eid for eid, entry in semantic_entries.items()
    }
    for record in records["records"]:
        rec_evidence = [rec_rel, *(record.get("evidence") or [])]
        for field in record["fields"]:
            if field["width"] not in WIDTHS:
                continue
            address = record["base"] + field["offset"]
            semantic_id = semantic_by_address.get(address)
            readers = list((xrefs["entries"].get(semantic_id, {}) if semantic_id else {})
                           .get("readers") or [])
            consumers = readers or [{
                "status": "bounded_pointer_relative_consumer",
                "reason": "record field is reached through an instance pointer; "
                          "the absolute xref scan cannot enumerate dynamic bases",
                "next_experiment": "trace this record-relative offset across the "
                                   "owning campaign and attribute instruction PCs",
            }]
            domain = str(field.get("note") or "") or None
            evidence = rec_evidence + [xr_rel]
            row = {
                "id": f"record.{record['id']}.{field['name']}",
                "source_kind": "typed_record_field",
                "record": record["id"],
                "field": field["name"],
                "offset": f"0x{field['offset']:02X}",
                "address_first_instance": f"0x{address:08X}",
                "width": field["width"],
                "classification": classify_domain(field["name"], domain),
                "domain": domain or "unknown",
                "consumers": consumers,
                "evidence": evidence,
                "status": "resolved" if domain else "bounded",
                "semantic_state_id": semantic_id,
            }
            if not domain:
                row["blocker"] = _bounded_blocker(
                    evidence, "exercise nonzero and edge values for this field and "
                              "trace every pointer-relative reader branch")
            record_rows.append(row)

    # Each decoded jr table has a statically recovered bound, selector consumer,
    # and complete target domain. This universe is independent of semantic_state.
    dispatch_rows = []
    for pc, table in sorted(jr["decoded"].items()):
        count = int(table["entries"])
        dispatch_rows.append({
            "id": f"dispatch.{pc.lower()}",
            "source_kind": "decoded_dispatch_selector",
            "address": table["table"],
            "width": "selector_index",
            "classification": "selector",
            "domain": f"0..{count - 1}",
            "consumers": [{"pc": pc, "function": table["function"]}],
            "evidence": [jr_rel],
            "status": "resolved",
            "entries": count,
            "named_targets": int(table["named_targets"]),
        })

    independent_errors = []
    if unknown_scope_ids:
        independent_errors.append(f"campaign scope IDs absent from semantic registry: {unknown_scope_ids}")
    if unscoped_scalars:
        independent_errors.append(f"semantic scalars absent from campaign scope: {unscoped_scalars}")
    if len(dispatch_rows) != jr["classification"]["table_dispatch"]:
        independent_errors.append(
            "decoded dispatch selector rows do not equal classified table-dispatch sites")

    all_rows = state_rows + record_rows + dispatch_rows
    return {
        "_comment": "WP3 fixed-width native domain/consumer census joined from "
                    "independent campaign scope, semantic state, typed records, and "
                    "decoded dispatch selectors. No source can self-certify "
                    "exhaustiveness. Regenerate: python3 tools/phase3_native_domains.py",
        "generated": date.today().isoformat(),
        "exhaustive": not independent_errors,
        "exhaustive_over": {
            "campaign_state_manifest": scope_rel,
            "typed_record_fields": rec_rel,
            "decoded_dispatch_selectors": jr_rel,
        },
        "independent_universe_errors": independent_errors,
        "unknown_campaign_scope_ids": unknown_scope_ids,
        "unscoped_semantic_scalar_ids": unscoped_scalars,
        "source_sha256": {
            rel: sha256(rel) for rel in (sem_rel, scope_rel, rec_rel, xr_rel, jr_rel)
        },
        "counts": {
            "campaign_state_domains": len(state_rows),
            "typed_record_field_domains": len(record_rows),
            "decoded_dispatch_selector_domains": len(dispatch_rows),
            "total": len(all_rows),
        },
        "domains": all_rows,
    }


def main() -> int:
    doc = build()
    out = ROOT / "analysis/phase3_native_domains.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    bounded = sum(row["status"] != "resolved" for row in doc["domains"])
    selectors = sum(row["classification"] == "selector" for row in doc["domains"])
    print(f"[native-domains] {doc['counts']}; {selectors} selectors; "
          f"{bounded} explicit bounded unknowns; "
          f"independent_errors={len(doc['independent_universe_errors'])}")
    return 0 if doc["exhaustive"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
