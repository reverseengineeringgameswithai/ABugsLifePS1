#!/usr/bin/env python3
"""Phase-3 WP1: derive the mechanic -> ownership frontier graph.

For EVERY row of the Phase-1 mechanics registry (all sections — omission is
impossible by construction), extract the addresses its bindings cite and
resolve each against the committed knowledge bases:

  functions   analysis/functions.json (census bounds + classification)
  symbols     symbols/re_symbols.sym  (authoritative names)
  state       config/semantic_state.yaml (owned semantic entries)
  canon       ObsidianVault/Canon/{Functions,Memory}/ (address-keyed notes)

The output is a FRONTIER map, not a completion claim: every row lists what is
resolved (function identity, state ownership) and what is not, as computed
`gaps` — a mechanic with no address bindings, a cited function that is still
unnamed/unknown, or cited state with no semantic-registry owner. The Phase-3
exit gate consumes the gap inventory ("every mechanic maps to a bounded
semantic frontier rather than an isolated address"); this artifact IS that
bound, and it shrinks only by adding evidence to the knowledge bases, never
by editing verdicts here (Phase-2 lesson: no self-grading artifacts).

Usage: python3 tools/phase3_ownership_graph.py
Output: analysis/phase3_ownership_graph.json (always exit 0 — gaps are the
        phase's WORK QUEUE, not a failure; the freshness test guards drift)
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))
import fixture_reference_sets  # noqa: E402
ADDR_RE = re.compile(r"0x(?:80|1F8)[0-9A-Fa-f]{6}|0x1F80[0-9A-Fa-f]{4}")
# bindings also reference addresses in the canonical Canon form FUNC_XXXXXXXX /
# MEM_XXXXXXXX — the old scan missed those, under-counting rows like A03_jump that
# cite FUNC_80048138. Recognise them (audit-adjacent fix).
CANON_REF_RE = re.compile(r"(?:FUNC|MEM)_([0-9A-Fa-f]{8})")

RAM_LO, RAM_HI = 0x80000000, 0x80200000
# an evidence-artifact path a disproven row may cite (must EXIST to count)
ARTIFACT_RE = re.compile(r"[\w./-]+\.(?:json|sav|movie\.json)")


def existing_evidence(r, reference_sets=None):
    """Evidence-artifact paths a row cites (in bindings or fixture_have) that
    actually EXIST on disk. A `disproven` row is a bounded frontier ONLY if it
    names real committed evidence — a CHECKED predicate, not a blanket waiver, and
    distinct from any 'blocker' clause: here the disproof IS the frontier, so it
    must be backed by files that exist."""
    text = " ".join(str(b) for b in (r.get("bindings") or []))
    text += " " + " ".join(fixture_reference_sets.resolve_row(r, reference_sets))
    found = []
    for m in ARTIFACT_RE.findall(text):
        p = ROOT / m
        if p.exists() and str(p.relative_to(ROOT)) not in found:
            found.append(str(p.relative_to(ROOT)))
    return found


def load_functions():
    """Two sorted lists: resident functions, then overlay functions (overlays
    reuse the same RAM window, so a bare address is only unambiguous in the
    resident space — overlay hits are reported with their overlay tag)."""
    doc = json.loads((ROOT / "analysis" / "functions.json").read_text())
    res, ovl = [], []
    for f in doc["functions"]:
        start = int(f["start"], 16)
        end = int(f["end"], 16)
        (res if f.get("space") == "resident" else ovl).append((start, end, f))
    res.sort(key=lambda t: t[:2])
    ovl.sort(key=lambda t: t[:2])
    return res, ovl


def load_symbols():
    syms = {}
    for line in (ROOT / "symbols" / "re_symbols.sym").read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            try:
                syms[int(parts[0], 16)] = parts[1].strip()
            except ValueError:
                pass
    return syms


def load_semantic():
    doc = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    by_addr = {}
    for e in doc["entries"]:
        if isinstance(e.get("address"), int):
            by_addr.setdefault(e["address"], []).append(e["id"])
    return by_addr


def load_xrefs():
    """Reader/writer evidence keyed by semantic-state ID.

    The xref generator is deliberately honest about pointer/indexed accesses.  A
    row carrying ``no_static_xref_because`` is therefore a bounded method limit,
    not an empty reader/writer claim.
    """
    path = ROOT / "analysis" / "phase3_xrefs.json"
    return json.loads(path.read_text()).get("entries", {}) if path.exists() else {}


def load_canon_index():
    idx = {}
    for sub in ("Functions", "Memory"):
        for p in (ROOT / "ObsidianVault" / "Canon" / sub).glob("*.md"):
            for m in re.finditer(r"(?:FUNC|MEM)_([0-9A-Fa-f]{8})", p.name):
                idx.setdefault(int(m.group(1), 16), []).append(
                    str(p.relative_to(ROOT)))
    return idx


def find_function(funcs, addr):
    """Binary search. CORRECT ONLY for the resident space, where ranges are disjoint.

    ⚠️ Do NOT call this on the overlay list. Every overlay is loaded at the same VA, so
    the overlay intervals fully overlap and a binary search over them is undefined: it
    returns whichever entry the midpoint arithmetic lands on, and it can return None while
    candidates exist. Measured on the live graph: of 135 overlay-window addresses, 114
    were resolved to one arbitrary image out of as many as 19, and 3 returned None despite
    candidates existing -- 86.7% arbitrary or absent. Use find_functions() instead.
    """
    lo, hi = 0, len(funcs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        start, end, f = funcs[mid]
        if addr < start:
            hi = mid - 1
        elif addr >= end:
            lo = mid + 1
        else:
            return f
    return None


def find_functions(funcs, addr):
    """Every entry whose range contains addr, in list order. Overlap-safe."""
    return [f for start, end, f in funcs if start <= addr < end]


def overlay_window(ovl_funcs):
    """[lo, hi) actually covered by censused overlay code, derived -- never hardcoded."""
    if not ovl_funcs:
        return None
    return (min(s for s, _e, _f in ovl_funcs), max(e for _s, e, _f in ovl_funcs))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis" / "phase3_ownership_graph.json"),
                    help="write elsewhere to diff a regeneration without staling pins")
    opts = ap.parse_args(argv)
    reg = yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())
    reference_sets = fixture_reference_sets.load()
    fixture_reference_sets.validate_rows(reg["rows"], reference_sets)
    funcs, ovl_funcs = load_functions()
    ovl_win = overlay_window(ovl_funcs)
    syms = load_symbols()
    semantic = load_semantic()
    xrefs = load_xrefs()
    canon = load_canon_index()

    rows = {}
    totals = {"mechanics": 0, "bound": 0, "functions_cited": 0,
              "functions_named": 0, "state_cited": 0, "state_owned": 0}
    gap_counts = {}

    for r in reg["rows"]:
        rid = r["id"]
        totals["mechanics"] += 1
        # ONLY the bindings are confirmed evidence. The `next` field is
        # future-experiment prose — an address mentioned there is a plan, not a
        # binding, and counting it inflates the frontier (the audit caught 5 such
        # rows, incl. the unresolved Bug Bar / Thud boss).
        text = " ".join(str(b) for b in (r.get("bindings") or []))
        addrs = {int(a, 16) for a in ADDR_RE.findall(text)}
        addrs |= {int(a, 16) for a in CANON_REF_RE.findall(text)}
        addrs = sorted(addrs)
        fentries, sentries, gaps = [], [], []

        for a in addrs:
            f = find_function(funcs, a)
            space, cands = "resident", None
            if f is None or f.get("range_type") not in ("code", "thunk"):
                # OVERLAY SPACE: every overlay loads at the same VA, so an address can be
                # inside a real function in many images at once. Enumerate them all and
                # publish the ambiguity; picking one is the defect this replaced.
                f2s = [g for g in find_functions(ovl_funcs, a)
                       if g.get("range_type") in ("code", "thunk")]
                if f2s:
                    cands = sorted({g.get("overlay", "overlay") for g in f2s})
                    f = f2s[0]
                    space = cands[0] if len(cands) == 1 else "overlay:ambiguous"
                else:
                    f = None
            if f is not None:
                if cands is not None and len(cands) > 1:
                    # only report a name/start the candidates AGREE on
                    starts = sorted({g["start"] for g in f2s})
                    names = sorted({(g.get("name") or syms.get(int(g["start"], 16)) or "")
                                    for g in f2s})
                    name = names[0] if len(names) == 1 else None
                    classes = sorted({g.get("classification") for g in f2s}, key=str)
                    ent = {"address": f"0x{a:08X}",
                           "function_start": starts[0] if len(starts) == 1 else None,
                           "space": space,
                           "overlay_candidates": cands,
                           "overlay_ambiguous": True,
                           "name": name,
                           "name_candidates": names if len(names) > 1 else None,
                           "classification": classes[0] if len(classes) == 1 else None,
                           "canon": canon.get(a, [])}
                    gaps.append(f"overlay address 0x{a:08X} is inside a real function in "
                                f"{len(cands)} images ({', '.join(cands)}); the owning "
                                "image is not determined by the address alone")
                else:
                    name = f.get("name") or syms.get(int(f["start"], 16))
                    ent = {"address": f"0x{a:08X}",
                           "function_start": f["start"],
                           "space": space,
                           "name": name,
                           "classification": f.get("classification"),
                           "canon": canon.get(a, [])}
                    if cands is not None:
                        ent["overlay_candidates"] = cands
                        ent["overlay_ambiguous"] = False
                fentries.append(ent)
                totals["functions_cited"] += 1
                if name or f.get("classification") not in (None, "unknown"):
                    totals["functions_named"] += 1
                else:
                    gaps.append(f"function 0x{a:08X} cited but unnamed/unknown "
                                "in census+symbols")
            elif RAM_LO <= a < RAM_HI or a >= 0x1F800000:
                ent = {"address": f"0x{a:08X}",
                       "semantic_ids": semantic.get(a, []),
                       "canon": canon.get(a, [])}
                # An address inside the overlay window is OVERLAY-LOCAL: the same VA is
                # different state in every resident overlay, so the address is not a key.
                # Say so on the record instead of letting consumers treat it as global.
                if ovl_win and ovl_win[0] <= a < ovl_win[1]:
                    ent["overlay_local"] = True
                    ent["image_required"] = True
                    ent["note"] = ("overlay-local VA: identity requires (image, address); "
                                   "the semantic registry supplies the image where known")
                sentries.append(ent)
                totals["state_cited"] += 1
                if ent["semantic_ids"]:
                    totals["state_owned"] += 1
                else:
                    # a Canon note is NOT ownership. The gate bullet asks for an
                    # OWNER (in the semantic registry), so an unowned address is a
                    # gap even when a Canon note documents it. The note is recorded
                    # in `ent["canon"]` for the reader, but it does not close the gap.
                    tag = (" (has a Canon note, but a note is not ownership)"
                           if ent["canon"] else "")
                    gaps.append(f"state 0x{a:08X} cited with no semantic-registry "
                                f"owner{tag}")

        # A `disproven` mechanic must be backed by REAL committed evidence — the
        # operator's rule, enforced as a CHECKED predicate independent of any
        # address citation: no evidence artifact on disk => it is still a gap.
        disproof_evidence = []
        if r.get("status") == "disproven":
            disproof_evidence = existing_evidence(r, reference_sets)
            if disproof_evidence:
                totals["disproven_bounded"] = totals.get("disproven_bounded", 0) + 1
            else:
                gaps.append("status 'disproven' but names no existing evidence "
                            "artifact — an unbacked disproof is not a bounded frontier")
        if addrs:
            totals["bound"] += 1
        elif r.get("status") not in ("not_applicable", "disproven"):
            gaps.append("no address bindings — mechanic is narrative-only")

        for g in gaps:
            key = g.split(" 0x")[0]
            gap_counts[key] = gap_counts.get(key, 0) + 1

        # Complete the semantic-frontier facets required by WP1.  These are not
        # completion verdicts: a missing facet is represented by a structured,
        # evidence-backed blocker with the exact next experiment.  That is the
        # phase contract's permitted bounded frontier, and is materially stronger
        # than the old address-only row.
        blocker_evidence = "; ".join(str(b) for b in (r.get("bindings") or [])) \
            or f"analysis/mechanics_baseline.yaml:{rid}"
        next_experiment = str(r.get("next") or r.get("fixture_need") or
                              "Trace the owning pristine boundary and bank it.")
        frontier_blockers = {}

        if not fentries:
            frontier_blockers["functions"] = {
                "missing_link": "no original function boundary is confirmed for this mechanic",
                "evidence": blocker_evidence,
                "next_experiment": next_experiment,
            }
        if not sentries:
            frontier_blockers["state"] = {
                "missing_link": "no fixed original state address is confirmed for this mechanic",
                "evidence": blocker_evidence,
                "next_experiment": next_experiment,
            }

        asset_refs = []
        for ref in fixture_reference_sets.resolve_row(r, reference_sets):
            asset_refs.append({"reference": str(ref), "role": "fixture_or_asset_evidence"})
        for ref in existing_evidence(r, reference_sets):
            if ref not in {a["reference"] for a in asset_refs}:
                asset_refs.append({"reference": ref, "role": "retained_evidence"})
        if not asset_refs:
            frontier_blockers["assets"] = {
                "missing_link": str(r.get("missing") or
                                    "no mechanic-specific asset dependency is confirmed"),
                "evidence": blocker_evidence,
                "next_experiment": next_experiment,
            }

        overlays = []
        for f in fentries:
            item = {"space": f["space"], "function_start": f["function_start"]}
            if item not in overlays:
                overlays.append(item)
        if not overlays:
            frontier_blockers["overlay"] = {
                "missing_link": "the exact resident/overlay execution owner is not yet bound",
                "evidence": blocker_evidence,
                "next_experiment": next_experiment,
            }

        readers, writers = [], []
        for state in sentries:
            for sid in state["semantic_ids"]:
                xr = xrefs.get(sid, {})
                for key, target in (("readers", readers), ("writers", writers)):
                    events = xr.get(key) or []
                    if events:
                        target.append({"state_id": sid, "sites": events})
                    elif xr.get("no_static_xref_because"):
                        target.append({
                            "state_id": sid,
                            "status": "bounded_static_method_limit",
                            "evidence": xr["no_static_xref_because"],
                        })
        for facet, values in (("readers", readers), ("writers", writers)):
            if not values:
                frontier_blockers[facet] = {
                    "missing_link": f"no {facet} are attributable from the current static/pointer evidence",
                    "evidence": "analysis/phase3_xrefs.json; " + blocker_evidence,
                    "next_experiment": next_experiment,
                }

        lifecycle = [{
            "stage_scope": r.get("stages"),
            "registry_status": r.get("status"),
            "known_limit": r.get("missing"),
            "next_experiment": next_experiment,
            "evidence": "analysis/mechanics_baseline.yaml",
        }]

        rows[rid] = {
            "name": r["name"],
            "section": r["section"],
            "registry_status": r["status"],
            "functions": fentries,
            "state": sentries,
            "assets": asset_refs,
            "overlay": overlays,
            "readers": readers,
            "writers": writers,
            "lifecycle": lifecycle,
            "frontier_blockers": frontier_blockers,
            "gaps": gaps,
        }
        if disproof_evidence:
            rows[rid]["disproof_evidence"] = disproof_evidence

    doc = {
        "_comment": "Phase-3 WP1 ownership-frontier graph, DERIVED from the "
                    "mechanics registry x functions census x symbols x semantic "
                    "registry x Canon index. Gaps are computed and shrink only "
                    "by adding evidence to the knowledge bases. Regenerate: "
                    "tools/phase3_ownership_graph.py.",
        "generated": date.today().isoformat(),
        "totals": totals,
        "gap_summary": dict(sorted(gap_counts.items())),
        "rows": rows,
    }
    out = Path(opts.out)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    open_gaps = sum(len(r["gaps"]) for r in rows.values())
    print(f"[ownership] {totals['mechanics']} mechanics: {totals['bound']} "
          f"address-bound; functions {totals['functions_named']}/"
          f"{totals['functions_cited']} named; state {totals['state_owned']}/"
          f"{totals['state_cited']} semantically owned; {open_gaps} open gaps")
    for k, v in sorted(gap_counts.items()):
        print(f"  {v:3d}  {k}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
