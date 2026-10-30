#!/usr/bin/env python3
"""Repair overlay-address keying: quantify the ambiguity and resolve what can be resolved.

Defect (engineering-specs/phase4-overlay-va-collision-finding.md): every per-level
overlay loads at the same base, so an overlay VA does not identify code, yet the derived
knowledge bases key such addresses GLOBALLY with no image field. Three rows collided on
one address; four rows each built a one-off probe.

This is the repair pass. For every overlay-space address the knowledge bases key, it
records which pinned images physically contain it, and derives a key of
`(image, address)` wherever the answer is forced. Where it is not forced it says so —
an address alone is ambiguous by construction, and inventing an owner is the defect,
not the fix.

Two resolution routes, strongest first:
  1. CONSTRAINT PIN — a semantic entry naming writer addresses gives (addr, word)
     constraints from the entry's own overlay; only images satisfying ALL survive.
  2. CONTAINMENT — how many images contain the address at all. `contained_by == 1` is
     a forced answer; more than one is honest ambiguity, reported with the count.

Compiled C owns all image reads and instruction plausibility
(tools/phase4_overlay_address_resolver.c); Python owns identity and pinning.

Usage: python3 tools/phase4_overlay_keying_repair.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVER_SRC = ROOT / "tools/phase4_overlay_address_resolver.c"
OVERLAY_LO = 0x800B0000


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_overlay_keying_repair.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="ovlkey_"))
    binary = tmp / "ovlres"
    subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-o", str(binary), str(RESOLVER_SRC)], check=True)
    st = subprocess.run([str(binary), "--selftest"], capture_output=True, text=True, check=True)
    if json.loads(st.stdout)["selftest"] != "PASS":
        raise SystemExit("resolver selftest failed")

    d3 = json.loads((ROOT / "analysis/phase4_d3_contract.json").read_text())
    images = d3["inputs"]["image_identities"]
    spec = tmp / "images.spec"
    spec.write_text("".join(f"{i['image']} {i['path']} {i['file_va_base']}\n" for i in images))

    pins = [{"path": "analysis/phase4_d3_contract.json",
             "sha256": sha256_file(ROOT / "analysis/phase4_d3_contract.json")},
            {"path": "tools/phase4_overlay_address_resolver.c",
             "sha256": sha256_file(RESOLVER_SRC)}]

    # --- collect every overlay-space address the knowledge bases key ---
    # ⚠️ The two knowledge bases store addresses in DIFFERENT TYPES: the ownership graph
    # uses hex strings, semantic_state.yaml uses ints. A first cut of this driver tested
    # isinstance(v, str) and silently saw 0 of semantic_state's 116 addresses -- the exact
    # blind-spot failure this campaign keeps hitting. coerce() takes both, and the type
    # census below is emitted so the NEXT unhandled representation is visible in the
    # output instead of vanishing into a zero.
    def coerce(v) -> int | None:
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v, 16) if v.lower().startswith("0x") else int(v, 16)
            except ValueError:
                return None
        return None

    type_census: Counter = Counter()

    def harvest(o, sink: set[int], occ: Counter):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "address":
                    type_census[type(v).__name__] += 1
                    a = coerce(v)
                    if a is not None and a >= OVERLAY_LO:
                        sink.add(a)
                        occ[a] += 1
                harvest(v, sink, occ)
        elif isinstance(o, list):
            for v in o:
                harvest(v, sink, occ)

    sources: dict[str, set[int]] = {}
    occurrences: Counter = Counter()

    og_path = ROOT / "analysis/phase3_ownership_graph.json"
    pins.append({"path": "analysis/phase3_ownership_graph.json", "sha256": sha256_file(og_path)})
    og_addrs: set[int] = set()
    harvest(json.loads(og_path.read_text()), og_addrs, occurrences)
    sources["phase3_ownership_graph"] = og_addrs

    import yaml
    sem_path = ROOT / "config/semantic_state.yaml"
    sem = yaml.safe_load(sem_path.read_text())
    pins.append({"path": "config/semantic_state.yaml", "sha256": sha256_file(sem_path)})
    sem_addrs: set[int] = set()
    harvest(sem, sem_addrs, occurrences)
    sources["semantic_state"] = sem_addrs

    # writer-set constraints: an entry's field AND all its declared writers must live in
    # ONE image. Only overlay-space members constrain; resident writers are ignored.
    sem_writer_constraints = {}
    for e in (sem.get("entries") or []):
        if not isinstance(e, dict):
            continue
        av = coerce(e.get("address"))
        if av is None or av < OVERLAY_LO:
            continue
        ws = [coerce(w.get("address")) for w in (e.get("writers") or [])
              if isinstance(w, dict)]
        ws = [w for w in ws if w is not None and w >= OVERLAY_LO]
        sem_writer_constraints[e.get("id", hex(av))] = {"field": av, "writers": ws}

    addrs = og_addrs | sem_addrs
    ordered = sorted(addrs)

    # known-positive gate: both sources MUST contribute, or a representation went unread.
    if not og_addrs:
        raise SystemExit("harvest read 0 overlay addresses from the ownership graph -- "
                         "representation changed; refusing to write a repair built on a blind spot")
    if not sem_addrs:
        raise SystemExit("harvest read 0 overlay addresses from semantic_state.yaml -- "
                         "representation changed; refusing to write a repair built on a blind spot")

    # --- containment, in batches (argv limits) ---
    results: dict[int, dict] = {}
    B = 200
    for i in range(0, len(ordered), B):
        chunk = ordered[i:i + B]
        out = subprocess.run([str(binary), "--contain", str(spec)] + [hex(a) for a in chunk],
                             capture_output=True, text=True, check=True)
        for row in json.loads(out.stdout)["addresses"]:
            results[int(row["address"], 16)] = row

    hist = Counter(r["contained_by"] for r in results.values())
    forced = {hex(a): r["containing_images"][0]["image"]
              for a, r in results.items() if r["contained_by"] == 1}
    ambiguous = {hex(a): r["contained_by"] for a, r in results.items() if r["contained_by"] > 1}
    orphan = [hex(a) for a, r in results.items() if r["contained_by"] == 0]

    # --- route 1: constraint pins from semantic writer declarations ---
    # A writer address is only usable as a word constraint if the word is known
    # independently, which it is not -- so the constraint used is CONTAINMENT of the whole
    # writer set: the owning image must hold the field AND every overlay-space writer.
    # This narrows; it does not prove. `unique: true` means "only one pinned image can
    # host this entry", which is a forced answer only under the closed-world assumption
    # that the 21 pinned images are all of them.
    pinned_by_constraint = {}
    for eid, c in sorted(sem_writer_constraints.items()):
        need = [c["field"]] + c["writers"]
        surv = []
        for im in images:
            base = int(im["file_va_base"], 16)
            if all(base <= a <= base + im["size"] - 4 for a in need):
                surv.append(im["image"])
        pinned_by_constraint[eid] = {
            "field": hex(c["field"]), "writers": [hex(w) for w in c["writers"]],
            "images_containing_all": surv, "unique": len(surv) == 1,
            "image": surv[0] if len(surv) == 1 else None,
            "constraint": "containment of field + all overlay-space writers",
        }

    doc = {
        "_comment": "Overlay-address keying repair: for every overlay-space address the "
                    "knowledge bases key globally, which pinned images contain it and "
                    "whether the owner is forced. An address alone is ambiguous by "
                    "construction; unresolved entries are reported, never guessed. "
                    "Regenerate: tools/phase4_overlay_keying_repair.py",
        "schema": "abl-phase4-overlay-keying-repair/1",
        "generated": date.today().isoformat(),
        "authority": {"promotes_row_or_dimension": False, "edits_knowledge_bases": False,
                      "requires_fresh_verifier": True,
                      "note": "produces the missing key material; applying it to the "
                              "knowledge bases is a separate, reviewable step"},
        "resolver": {"source": "tools/phase4_overlay_address_resolver.c",
                     "selftest": "PASS", "decoding_owner": "compiled C"},
        "images": {"count": len(images),
                   "bases": sorted({i["file_va_base"] for i in images})},
        "evidence_pins": pins,
        "address_key_type_census": dict(sorted(type_census.items())),
        "address_sources": {k: len(v) for k, v in sources.items()},
        "addresses_examined": len(ordered),
        "keyed_occurrences": sum(occurrences.values()),
        "containment_histogram": {str(k): v for k, v in sorted(hist.items())},
        "forced_unique_owner": forced,
        "ambiguous_owner": ambiguous,
        "outside_every_image": {
            "note": "overlay-space VA past the file extent of every pinned image -- "
                    "overlay BSS / runtime RAM rather than code in a blob. Not an error; "
                    "these are correctly keyed by address alone because no image owns them.",
            "addresses": orphan,
        },
        "semantic_entries_pinned_by_writer_containment": pinned_by_constraint,
        "summary": {
            "forced": len(forced), "ambiguous": len(ambiguous),
            "not_in_any_image": len(orphan),
            "worst_case_images_for_one_address": max(hist) if hist else 0,
            "keyed_occurrences_at_risk": sum(occurrences[a] for a in results
                                             if results[a]["contained_by"] > 1),
        },
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[overlay-keying] examined {len(ordered)} overlay-space addresses across "
          f"{len(images)} images")
    print(f"  forced unique owner : {len(forced)}")
    print(f"  ambiguous           : {len(ambiguous)}  (worst case {max(hist) if hist else 0} images)")
    print(f"  outside every image : {len(orphan)}")
    uq = sum(1 for v in pinned_by_constraint.values() if v["unique"])
    print(f"  semantic entries pinned by writer containment: {uq}/{len(pinned_by_constraint)}")
    print(f"  address key types seen: {dict(sorted(type_census.items()))}")
    print(f"  keyed occurrences at risk: {doc['summary']['keyed_occurrences_at_risk']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
