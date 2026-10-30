#!/usr/bin/env python3
"""Phase-1 unclassified-unknowns inventory: enumerate what is NOT yet classified,
without guessing roles.

Work package: "Identify unclassified object kinds, actor slots, overlay handlers,
and asset families without guessing their roles." Reads the existing analysis
artifacts and emits analysis/phase1_unclassified.json listing every axis of
still-unclassified surface with counts and explicit item lists, so the exit gate
("all disc object kinds, actor/model families, and overlays are classified or
explicitly preserved as unknown") is auditable instead of anecdotal.

Axes covered (source artifact in parentheses):
  * resident/overlay functions whose names are still address-derived placeholders
    or weakly named (analysis/functions.json)
  * LEVEL.RAW chunk roles below 'confirmed' confidence (analysis/level_raw_chunks.json)
  * mover/event-VM opcodes without confirmed semantics (analysis/vm_programs.json)
  * VM programs without behavior notes (analysis/vm_programs.json)

Usage: python3 tools/phase1_unclassified_inventory.py [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Names that are placeholders or carry an address suffix are "weakly named":
# they locate code without asserting semantics. Not an accusation of wrongness —
# just not yet a classification.
PLACEHOLDER = re.compile(r"^(FUNC_|fcn\.|sub_|loc_|unk_?)", re.IGNORECASE)
ADDR_SUFFIX = re.compile(r"_[0-9a-f]{4,8}$")


def functions_axis() -> dict:
    doc = json.loads((ROOT / "analysis" / "functions.json").read_text())
    out = {"placeholder_named": [], "address_suffixed": [], "counts": {}}
    total = {"resident": 0, "overlay": 0}
    for f in doc["functions"]:
        if f.get("classification") not in ("game", "data"):
            continue
        space = f.get("space", "resident")
        total[space] = total.get(space, 0) + 1
        name = f.get("name") or ""
        entry = {"name": name, "start": f.get("start"), "space": space,
                 "overlay": f.get("overlay"), "classification": f.get("classification")}
        if not name or PLACEHOLDER.match(name):
            out["placeholder_named"].append(entry)
        elif ADDR_SUFFIX.search(name):
            out["address_suffixed"].append(entry)
    out["counts"] = {
        "game_or_data_functions": total,
        "placeholder_named": len(out["placeholder_named"]),
        "address_suffixed_weak_names": len(out["address_suffixed"]),
    }
    return out


def chunks_axis() -> dict:
    doc = json.loads((ROOT / "analysis" / "level_raw_chunks.json").read_text())
    by_conf: dict = {}
    unconfirmed = []
    for ch in doc["chunks"]:
        conf = ch.get("confidence", "?")
        by_conf[conf] = by_conf.get(conf, 0) + 1
        if conf not in ("confirmed",):
            unconfirmed.append({"chunk_id": ch.get("chunk_id"), "confidence": conf,
                                "decomp_size": ch.get("decomp_size")})
    return {"counts": by_conf, "not_fully_confirmed": unconfirmed,
            "note": "confidence below 'confirmed' = role known by format/likelihood, "
                    "not by traced consumer; each needs a load-trace experiment"}


def vm_axis() -> dict:
    """Mover/event-VM coverage. In analysis/vm_programs.json, `opcode_table` is the
    TABLE ADDRESS (a string — never len() it); the opcode universe is the
    `handler_advances` map (indices 0..25 = 26 opcodes) and per-instruction
    confidence lives in each program instruction's `conf` field."""
    doc = json.loads((ROOT / "analysis" / "vm_programs.json").read_text())
    advances = doc.get("handler_advances") or {}
    progs = doc.get("programs") or []
    total_ops = len(advances)

    observed: dict = {}   # opcode idx -> set of conf values seen in disassembled programs
    for p in progs:
        for ins in p.get("instructions", []):
            observed.setdefault(int(ins["idx"]), set()).add(ins.get("conf", "?"))
    unconfirmed = sorted(
        idx for idx in range(total_ops)
        if idx not in observed or any(c != "CONFIRMED" for c in observed[idx]))
    never_observed = sorted(idx for idx in range(total_ops) if idx not in observed)
    # a program's behavior note is the parenthetical description in its id,
    # e.g. "program_0 (mosquito path header)"
    unnoted = [p.get("id", f"#{i}") for i, p in enumerate(progs)
               if "(" not in str(p.get("id", ""))]
    return {"counts": {"opcodes_total": total_ops,
                       "opcodes_observed_in_programs": len(observed),
                       "opcodes_not_fully_confirmed": len(unconfirmed),
                       "programs_listed": len(progs),
                       "programs_without_behavior_notes": len(unnoted)},
            "opcode_table_address": doc.get("opcode_table"),
            "opcodes_not_fully_confirmed": unconfirmed,
            "opcodes_never_observed_in_disassembled_programs": never_observed,
            "programs_without_behavior_notes": unnoted}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "analysis" / "phase1_unclassified.json"))
    args = ap.parse_args()
    doc = {
        "_comment": "Phase-1 unclassified-unknowns inventory (no role guesses). "
                    "Regenerate: tools/phase1_unclassified_inventory.py. Each listed "
                    "item is an explicit unknown awaiting an evidence-producing "
                    "experiment; see analysis/mechanics_baseline.yaml rows D02/E07/E16.",
        "generated": date.today().isoformat(),
        "functions": functions_axis(),
        "level_raw_chunks": chunks_axis(),
        "vm": vm_axis(),
    }
    out = Path(args.out)
    out.write_text(json.dumps(doc, indent=2) + "\n")
    f, c, v = doc["functions"]["counts"], doc["level_raw_chunks"]["counts"], doc["vm"]["counts"]
    print(f"[phase1_unclassified] wrote {out}")
    print(f"  functions: {f['game_or_data_functions']} total; "
          f"{f['placeholder_named']} placeholder-named, "
          f"{f['address_suffixed_weak_names']} address-suffixed weak names")
    print(f"  LEVEL.RAW chunks: {c} (below-confirmed listed: "
          f"{len(doc['level_raw_chunks']['not_fully_confirmed'])})")
    print(f"  VM: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
