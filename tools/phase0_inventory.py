#!/usr/bin/env python3
"""Phase-0 WIP inventory: classify everything in the working tree by role.

Roadmap work package (Phase 0 - Stabilize and Establish Identity): "Produce a WIP
inventory grouped by source, generated artifact, local media, and experiment
evidence." Read-only — never moves or deletes anything.

Groups:
  source              — project-authored files (tools, mods, notes, tests, asm/C).
  generated_artifact  — regenerable build outputs (modded discs, objects, reports).
  local_media         — copyrighted game media / extractions (never committed).
  experiment_evidence — save states, input movies, captures, logs, smoke reports.
  other               — nothing matched; review and extend the rules.

Bulk directories are rolled up (count+bytes) instead of enumerated file-by-file.

Usage: python3 tools/phase0_inventory.py [--out analysis/phase0_wip_inventory.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Bulk trees: one rollup line each (group, note). Everything else is enumerated.
ROLLUP_DIRS = {
    "build": ("generated_artifact", "disc builds, objects, probes (gitignored)"),
    "REBUILD": ("local_media", "mkpsxiso staging tree extracted from the pristine disc "
                               "(hash-pinned by tools/build_baselines.json)"),
    "extracted": ("local_media", "bulk extracted media (regenerable; hash manifest tracked)"),
    "DAT": ("local_media", "extracted level data"),
    "OVL": ("local_media", "extracted overlays"),
    "jpsxdec_v2.1-beta": ("generated_artifact", "third-party tool (downloadable)"),
    "psxavenc": ("generated_artifact", "third-party tool (buildable)"),
    "ghidra": ("generated_artifact", "Ghidra cross-check project (regenerable)"),
    "captures": ("experiment_evidence", "frame captures"),
    "movies": ("experiment_evidence", "input movies"),
    "logs": ("experiment_evidence", "session logs"),
    "backdrop": ("experiment_evidence", "backdrop experiments"),
    "backdrop_issue": ("experiment_evidence", "backdrop regression evidence"),
    "G28_Deformity": ("experiment_evidence", "G28 terrain experiment evidence"),
    "ground_pebbles": ("experiment_evidence", "terrain experiment evidence"),
    "starry_night_result": ("experiment_evidence", "GPU injection experiment evidence"),
    "scratchpad": ("generated_artifact", "session scratch"),
    "level_editor/.venv": ("generated_artifact", "python venv (regenerable from requirements)"),
    ".git": (None, None),
    ".claude": (None, None),
}

EVIDENCE_EXT = {".sav", ".mcr", ".log", ".avi"}
MEDIA_EXT = {".iso", ".img", ".chd", ".mp3", ".mp4", ".str", ".xa"}
SOURCE_EXT = {".py", ".md", ".yaml", ".yml", ".json", ".asm", ".c", ".h", ".s",
              ".sh", ".toml", ".desktop", ".blend", ".blend1", ".xml", ".sym", ".cfg",
              ".ini", ".java", ".js", ".html", ".css", ".txt", ".qml", ".rst"}
GENERATED_EXT = {".pyc", ".pyo", ".o", ".so", ".exe", ".class"}

PRISTINE_NAMES = {"Disney-Pixar A Bug's Life (v1.0).bin",
                  "Disney-Pixar A Bug's Life (v1.0).cue"}


def git_lines(args: list) -> list:
    proc = subprocess.run(["git", *args], cwd=str(ROOT), text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return [l for l in proc.stdout.splitlines() if l]


def classify(rel: str, tracked: bool) -> tuple[str, str]:
    """Return (group, why) for an enumerated (non-rollup) path."""
    p = Path(rel)
    name, ext = p.name, p.suffix.lower()
    if rel in ("Disney-Pixar A Bug's Life (v1.0).bin", "Disney-Pixar A Bug's Life (v1.0).cue"):
        return "local_media", "PRISTINE retail image (immutable sole build base)"
    if tracked:
        return "source", "git-tracked"
    if "__pycache__" in rel or ext in GENERATED_EXT:
        return "generated_artifact", "compiled/derived object"
    if ".movie." in name or name.endswith(".movie.json"):
        return "experiment_evidence", "input movie"
    if name.endswith("_smoke.json") or name.endswith("_smoke.png"):
        return "generated_artifact", "smoke-gate report"
    if ext == ".bak":
        base = name[:-4]
        if base.endswith(".sav") or "." not in base:
            return "experiment_evidence", "save-state backup"
        return "other", "backup file"
    if ext in EVIDENCE_EXT:
        return "experiment_evidence", "runtime evidence"
    if ext in (".png", ".jpg", ".gif"):
        return "experiment_evidence", "visual evidence/screenshot"
    if name in PRISTINE_NAMES:
        return "local_media", "pristine retail image"
    if ext in (".bin", ".cue"):
        return "generated_artifact", "built test disc (derives from pristine)"
    if ext in MEDIA_EXT or name in ("SCUS_942.88", "MEMORY.BIN") or name.startswith("LEVEL"):
        return "local_media", "extracted game media"
    if ext in (".dat", ".raw"):
        return "local_media", "extracted game data"
    if ext in SOURCE_EXT:
        return "source", "untracked source-like WIP"
    return "other", "unmatched"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "analysis" / "phase0_wip_inventory.json"))
    args = ap.parse_args()

    tracked = set(git_lines(["ls-files"]))
    status = {}
    for line in git_lines(["status", "--porcelain"]):
        status[line[3:].strip('"')] = line[:2].strip()

    groups: dict = {g: {"files": 0, "bytes": 0, "entries": []}
                    for g in ("source", "generated_artifact", "local_media",
                              "experiment_evidence", "other")}
    rollups = []

    # 1) bulk rollups
    for d, (group, note) in ROLLUP_DIRS.items():
        p = ROOT / d
        if group is None or not p.is_dir():
            continue
        n = b = 0
        for f in p.rglob("*"):
            try:
                if f.is_file():
                    n += 1
                    b += f.stat().st_size
            except OSError:
                pass
        rollups.append({"dir": d + "/", "group": group, "files": n, "bytes": b, "note": note})
        groups[group]["files"] += n
        groups[group]["bytes"] += b

    # 2) enumerate everything outside rollups
    skip = tuple(d + "/" for d in ROLLUP_DIRS)
    for f in sorted(ROOT.rglob("*")):
        rel = str(f.relative_to(ROOT))
        if rel.startswith(skip) or not f.is_file():
            continue
        group, why = classify(rel, rel in tracked)
        st = status.get(rel, "tracked-clean" if rel in tracked else "untracked/ignored")
        try:
            size = f.stat().st_size
        except OSError:
            size = 0
        groups[group]["files"] += 1
        groups[group]["bytes"] += size
        groups[group]["entries"].append(
            {"path": rel, "bytes": size, "git": st, "why": why})

    doc = {
        "_comment": "Phase-0 WIP inventory (read-only classification; regenerate with "
                    "tools/phase0_inventory.py). Rollup dirs are counted, not enumerated.",
        "generated": date.today().isoformat(),
        "git_head": git_lines(["rev-parse", "HEAD"])[0],
        "git_dirty": {"modified": sum(1 for v in status.values() if "M" in v),
                      "untracked": sum(1 for v in status.values() if v == "??"),
                      "total_status_lines": len(status)},
        "rollups": rollups,
        "groups": {g: {"files": v["files"], "bytes": v["bytes"],
                       "entries": v["entries"]} for g, v in groups.items()},
    }
    out = Path(args.out)
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"[phase0_inventory] wrote {out}")
    for g, v in groups.items():
        print(f"  {g:20s} {v['files']:6d} files  {v['bytes']/1e6:10.1f} MB")
    unmatched = groups["other"]["entries"]
    if unmatched:
        print(f"  NOTE: {len(unmatched)} unmatched path(s) in group 'other' — extend the rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
