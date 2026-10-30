#!/usr/bin/env python3
"""Measured evidence census for every F (stage) row — the input a real scorecard needs.

Context: `engineering-specs/phase4-two-standards-finding.md` established that no row
except F01 has a measured scorecard; the 16 "complete" rows carry one blanket basis
string across nine dimensions. The remedy is per-dimension measurement against the bars
AS WRITTEN — but measurement needs measurable inputs, and nobody has ever inventoried
what evidence each stage row actually holds.

This tool does the part that is MECHANICALLY CHECKABLE for all 19 F rows, and refuses to
pretend about the rest:

  * `durable_evidence` is MEASURED, not judged: every fixture the row declares must
    exist on disk, be centrally pinned, and its bytes must match the pin. Fractions are
    reported before any adjective. A row declaring no fixtures is not_met, not "n/a".
  * the other eight dimensions get an EVIDENCE INVENTORY (present / absent, with what
    was found), never a state. Turning an inventory into a state is the per-row
    measurement job and it needs a human-or-verifier judgment on the bars.

⚠️ This tool cannot and must not promote anything. It exists so that per-row measurement
stops being blocked on "what do we even have for this row?".

Usage: python3 tools/phase4_f_row_measured_census.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ["durable_evidence", "original_oracle", "complete_frontier", "typed_state",
              "lifecycle", "cross_system_behavior", "original_interfaces",
              "source_closure", "campaign_breadth"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def progression_table() -> list[int]:
    """Read the campaign progression table 0x80077FA0 from the pristine executable.

    ⚠️ This was a hand-typed Python list until 2026-08-11. The project's own standing
    rule is to GENERATE boundary tables and never hand-type them -- a hand-typed
    boundary is exactly what produced the 7,063-instruction truncation this campaign
    already has a memory about. It happened to be correct (an F12/F13/F15 assessment
    verified it against the image), but correct-by-luck is not the bar.
    """
    exe = ROOT / "SCUS_942.88"
    blob = exe.read_bytes()
    t_addr = struct.unpack_from("<I", blob, 0x18)[0]
    off = 0x80077FA0 - t_addr + 0x800
    table = []
    for i in range(17):                       # 16 ordinals + the -1 terminator
        v = struct.unpack_from("<i", blob, off + i * 4)[0]
        if v < 0:
            break
        table.append(v)
    if len(table) != 16:
        raise SystemExit(f"progression table read {len(table)} entries, expected 16")
    return table


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f_row_measured_census.json"))
    args = ap.parse_args()

    baseline = ROOT / "analysis/mechanics_baseline.yaml"
    doc = yaml.safe_load(baseline.read_text())
    rows = doc["rows"] if isinstance(doc, dict) and "rows" in doc else doc
    frows = {r["id"]: r for r in rows
             if isinstance(r, dict) and re.match(r"^F\d\d_", str(r.get("id", "")))}

    pinset = json.loads((ROOT / "analysis/phase0_2_external_fixture_set.json").read_text())
    entries = pinset["entries"]

    # one repo-wide listing each, rather than a subprocess per row
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True).stdout.split()
    analysis_files = [f for f in tracked if f.startswith("analysis/")]
    vault_files = [f for f in tracked if f.startswith("ObsidianVault/")]
    # ⚠️ THERE ARE TWO SOURCE/BUILD REGISTRIES. Searching only src_re/ +
    # asm/hand_written/ + config/segments.yml made this tool blind to the entire OVERLAY
    # decomp track (config/overlays.yml, tools/build_overlay.py, src/overlays/, 158
    # overlay functions with 15 matched) -- and on the strength of that blindness I
    # banked, then had to retract, a claim that overlay source_closure was structurally
    # impossible. See engineering-specs/phase4-overlay-source-closure-cap.md.
    src_files = [f for f in tracked
                 if f.startswith(("src_re/", "asm/hand_written/", "src/overlays/",
                                  "src/main/"))]
    segments = (ROOT / "config/segments.yml").read_text() if (ROOT / "config/segments.yml").exists() else ""
    overlays_yml = (ROOT / "config/overlays.yml").read_text() if (ROOT / "config/overlays.yml").exists() else ""
    try:
        ovl_prog = json.loads((ROOT / "analysis/overlay_decomp_progress.json").read_text())
    except (OSError, json.JSONDecodeError):
        ovl_prog = {}

    out_rows = {}
    for rid, r in sorted(frows.items()):
        stem = rid.split("_")[0].lower()                    # f10
        tail = "_".join(rid.split("_")[1:]).lower()         # clover_forest
        pats = [stem, tail] + ([tail.replace("_", "")] if tail else [])

        # ⚠️ Filename matching alone UNDERCOUNTS, badly. Several rows carry no
        # row-named artifact yet cite their evidence by path inside bindings/next/
        # missing prose -- F12's boss mechanics live in the D19 (Molt) campaign, and
        # F05/F07/F13 cite the shared analysis/phase4_f08_scene_binding.json. Reading
        # only filenames reported those four as "zero registered evidence", which was
        # false. Follow explicit references too.
        prose = " ".join(str(r.get(k, "")) for k in
                         ("bindings", "next", "missing", "evidence_paths", "verifier_verdict"))
        referenced = set(re.findall(r"(?:analysis|tools|src_re|asm/hand_written|config)/[\w./-]+", prose))

        # ⚠️ Naive substring matching on the row stem collides with HEX ADDRESSES:
        # "f11" matches asm/hand_written/8005f110_sub_8005f110.s, which credited F11
        # with a byte-matched source it does not own and corrupted its source_closure
        # triage. Require the stem to be delimited by non-alphanumerics so an address
        # digit cannot follow it. Caught by the F11 assessment, not by this tool.
        stem_re = re.compile(rf"(?<![0-9a-z]){re.escape(stem)}(?![0-9a-z])")

        def hits(pool):
            by_name = {f for f in pool
                       if stem_re.search(f.lower())
                       or any(p and p != stem and p in f.lower() for p in pats)}
            by_ref = {f for f in pool if f in referenced}
            return sorted(by_name | by_ref)

        # --- durable_evidence: MEASURED ---
        declared = r.get("fixture_have") or []
        if isinstance(declared, str):
            declared = [declared]
        # ⚠️ Two shapes had to be handled, and getting them wrong produced three FALSE
        # defects on the first run. (1) Some entries append a prose description after
        # the path: "path/x.movie.json (operator-supplied 100% run, 12917 frames)".
        # (2) Not every declared fixture is EXTERNAL: in-repo analysis artifacts are
        # git-tracked and must NOT appear in the external preservation set, which exists
        # for bytes kept outside git. Judging both by the same predicate is a category
        # error that reads as "unpinned" when the artifact is correctly tracked instead.
        tracked_set = set(tracked)
        fx = []
        for raw in declared:
            raw = str(raw)
            rel = raw.split(" (")[0].strip()
            note = raw[len(rel):].strip() or None
            p = ROOT / rel
            ex = p.exists()
            external = not rel.startswith(("analysis/", "tools/", "src_re/", "config/"))
            if external:
                pin = entries.get(rel)
                match = sha256_file(p) == pin["sha256"] if (ex and pin and pin.get("sha256")) else None
                intact = bool(ex and pin and match)
                fx.append({"path": rel, "kind": "external_fixture", "description": note,
                           "exists": ex, "centrally_pinned": bool(pin),
                           "bytes_match_pin": match, "intact": intact})
            else:
                intact = bool(ex and rel in tracked_set)
                fx.append({"path": rel, "kind": "in_repo_artifact", "description": note,
                           "exists": ex, "git_tracked": rel in tracked_set,
                           "centrally_pinned": "n/a -- bytes live in git",
                           "intact": intact})
        n = len(fx)
        ok = sum(1 for f in fx if f["intact"])
        if n == 0:
            de_state, de_reason = "not_met", "row declares no fixtures"
        elif ok == n:
            de_state, de_reason = "met", (
                f"{ok}/{n} declared fixtures intact -- external ones exist, are centrally "
                "pinned and byte-match; in-repo ones exist and are git-tracked")
        else:
            de_state, de_reason = "not_met", f"only {ok}/{n} declared fixtures are intact"

        # --- evidence inventory for the other eight (inventory, NOT a state) ---
        a_hits, v_hits, s_hits = hits(analysis_files), hits(vault_files), hits(src_files)
        seg_hits = len([m for m in re.findall(r"(?:src/main|asm/hand_written)/\S+", segments)
                        if stem_re.search(m.lower())])
        # Overlays attach to rows by SCENE -> BLOB, never by row id: the scene-to-level
        # law (banked 2026-08-01) is dir = scene<=10 ? scene : scene-10, file = LEVEL vs
        # LEVEL1, so F03 (scene 2) is overlay LEVEL02_LEVEL. Matching src/overlays paths
        # against the row stem finds nothing and silently reports "no source", which is
        # how the retracted overlay-cap claim survived its first check.
        # ⚠️ THREE NUMBERING SPACES, and `stages` holds the FIRST of them. It is the
        # stage ORDINAL (1..15, or "Training"/"bonus"), not the scene id and not the disc
        # dir. The campaign progression table 0x80077FA0 maps ordinal -> scene, and only
        # then does the scene->level law give the blob. Reading `stages` as a scene id
        # attributed one row and missed the rest -- the same conflation the
        # scene-to-level-data-law experiment was written to stop.
        PROGRESSION = progression_table()
        stages_txt = str(r.get("stages", "")).strip()
        scene = None
        m_scene = re.search(r"scene\s+(\d+)", stages_txt)
        if m_scene:                                   # a row that already states its scene
            scene = int(m_scene.group(1))
        elif stages_txt.lower().startswith("training"):
            scene = PROGRESSION[0]
        elif stages_txt.isdigit() and 1 <= int(stages_txt) <= 15:
            scene = PROGRESSION[int(stages_txt)]
        overlay_name = None
        if scene and 1 <= scene <= 17:
            overlay_name = f"LEVEL{(scene if scene <= 10 else scene - 10):02d}_" \
                           f"{'LEVEL' if scene <= 10 else 'LEVEL1'}"
        ovl_src = sorted(f for f in tracked
                         if overlay_name and f.startswith(f"src/overlays/{overlay_name}/"))
        ovl_hits = len(ovl_src)
        ev = r.get("evidence") or []
        bindings = r.get("bindings") or []

        # ⚠️ The row's own `evidence` list is a DECLARATION and is under-reported on 8
        # of 19 rows (they declare no static_code while holding analysis artifacts full
        # of pinned instruction words). Trusting it repeats the registration-vs-reality
        # error this whole census exists to correct, so derive the classes from what the
        # artifacts actually contain and report the discrepancy.
        # Signature derived by inspecting real artifacts rather than guessed: static
        # evidence keys on pc/insn/function/writers/sites and carries resident
        # 0x8xxxxxxx addresses; runtime evidence keys on movie/frames/cycle/watch.
        # (A first attempt guessed key names like "instruction_word" and detected
        # almost nothing -- the failure mode of asserting a schema you never read.)
        STATIC_KEYS = ("pc", "insn", "function", "exe", "writers", "readers", "sites",
                       "address", "instruction_pc", "instruction_word")
        RUNTIME_KEYS = ("movie", "frames", "exec_trace", "access_log", "replay",
                        "sessions", "cycle", "watch", "movie_sha256", "save")
        ADDR = re.compile(r"0x8[0-9a-fA-F]{7}")
        derived = {"static_code": False, "runtime_trace": False}
        probed = []
        for rel in a_hits[:12]:                     # bounded: these files can be large
            try:
                blob = (ROOT / rel).read_text(errors="ignore")[:400000]
            except OSError:
                continue
            naddr = len(ADDR.findall(blob))
            s = naddr >= 5 or any(f'"{k}"' in blob for k in STATIC_KEYS)
            rt = any(f'"{k}"' in blob for k in RUNTIME_KEYS)
            derived["static_code"] |= s
            derived["runtime_trace"] |= rt
            probed.append({"artifact": rel, "static": s, "runtime": rt,
                           "resident_addresses": naddr})

        inventory = {
            "declared_evidence_classes": ev,
            "derived_evidence_classes": [k for k, v in derived.items() if v],
            "declaration_understates_reality": sorted(
                k for k, v in derived.items() if v and k not in ev),
            "artifacts_probed": probed,
            "binding_claims": len(bindings) if isinstance(bindings, list) else 1,
            "analysis_artifacts": a_hits,
            "vault_pages": v_hits,
            "source_files": s_hits,
            "segments_entries": seg_hits,
            "stage_ordinal": stages_txt,
            "scene_id": scene,
            "overlay_name": overlay_name,
            "overlay_matched_sources": ovl_src,
            "overlay_build_entries": ovl_hits,
            "overlay_track_totals": {"functions": ovl_prog.get("overlay_code_functions"),
                                     "matched": (ovl_prog.get("matched") or {}).get("functions"),
                                     "pct": (ovl_prog.get("matched") or {}).get("pct_functions")},
            "has_static_code_evidence": "static_code" in ev,
            "has_runtime_trace_evidence": "runtime_trace" in ev,
            "declares_missing_work": bool(r.get("missing")),
            "declares_fixture_need": bool(r.get("fixture_need")),
        }
        # measurability triage, stated as what is BLOCKING measurement, not as a state
        triage = {}
        for d in DIMENSIONS:
            if d == "durable_evidence":
                continue
            if not a_hits and not v_hits:
                triage[d] = "no_registered_evidence -- measurement blocked until a " \
                            "campaign artifact exists for this row"
            elif d == "source_closure":
                triage[d] = ("measurable: source/build entries exist (resident and/or "
                             "overlay track)"
                             if (seg_hits or s_hits or ovl_hits) else
                             "no byte-matched source registered for this row in EITHER "
                             "registry (config/segments.yml resident, config/overlays.yml "
                             "overlay)")
            elif d in ("original_oracle", "lifecycle", "cross_system_behavior"):
                triage[d] = ("measurable: runtime evidence present in artifacts"
                             if derived["runtime_trace"] else
                             "no runtime evidence found in this row's artifacts")
            else:
                triage[d] = ("measurable: static evidence present in artifacts"
                             if derived["static_code"] else
                             "no static evidence found in this row's artifacts")

        out_rows[rid] = {
            "name": r.get("name"),
            "status": r.get("status"),
            "durable_evidence": {"state": de_state, "reason": de_reason,
                                 "fixtures": fx, "intact_pinned": f"{ok}/{n}"},
            "evidence_inventory": inventory,
            "measurability_triage": triage,
            "row_declared_next": str(r.get("next", ""))[:300],
        }

    de_met = [k for k, v in out_rows.items() if v["durable_evidence"]["state"] == "met"]
    blocked = {k: sum(1 for t in v["measurability_triage"].values()
                      if t.startswith("no_registered_evidence"))
               for k, v in out_rows.items()}
    result = {
        "_comment": "Measured evidence census for the F (stage) rows. durable_evidence "
                    "is MEASURED against pinned bytes; the other eight dimensions get an "
                    "evidence inventory and a measurability triage, never a state. "
                    "Promotes nothing. Regenerate: tools/phase4_f_row_measured_census.py",
        "schema": "abl-phase4-f-row-measured-census/1",
        "generated": date.today().isoformat(),
        "authority": {"promotes_row_or_dimension": False, "assigns_states": False,
                      "measures": ["durable_evidence"],
                      "requires_fresh_verifier": True},
        "baseline_sha256": sha256_file(baseline),
        "fixture_set_sha256": sha256_file(ROOT / "analysis/phase0_2_external_fixture_set.json"),
        "rows_assessed": len(out_rows),
        "durable_evidence_met": sorted(de_met),
        "durable_evidence_met_fraction": f"{len(de_met)}/{len(out_rows)}",
        "rows_with_zero_registered_evidence": sorted(k for k, n in blocked.items() if n == 8),
        "rows": out_rows,
    }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(f"[f-census] rows={len(out_rows)}  durable_evidence met "
          f"{result['durable_evidence_met_fraction']}")
    for rid, v in out_rows.items():
        de = v["durable_evidence"]
        inv = v["evidence_inventory"]
        print(f"  {rid:26s} durable={de['state']:8s} ({de['intact_pinned']:>5s})  "
              f"artifacts={len(inv['analysis_artifacts']):2d} vault={len(inv['vault_pages']):2d} "
              f"src={len(inv['source_files']):2d} seg={inv['segments_entries']:2d}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
