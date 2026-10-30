#!/usr/bin/env python3
"""Generate the complete pristine staged-asset provenance/load-owner report."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools/build_baselines.json"
STAGED = ROOT / "REBUILD/files"

OWNER = {
    "geometry": ("level_load_chunks / geometry decompressor", "ObsidianVault/Canon/Memory/MEM_LEVEL.RAW_CHUNK_INVENTORY_LEVEL.RAW_chunk_inventory.md"),
    "collision": ("level_load_chunks / collision source converter", "ObsidianVault/Canon/Memory/MEM_800D0000_Collision_plane_record.md"),
    "textures": ("VRAM asset loader", "analysis/phase3_render_descriptors.json"),
    "models": ("named asset loader + model fixup", "ObsidianVault/Canon/Systems/Asset_-_ALL_ANM_Format_Grammar.md"),
    "animation": ("named asset loader + animation fixup", "ObsidianVault/Canon/Systems/Asset_-_ALL_ANM_Format_Grammar.md"),
    "audio": ("VAB loader or XA stream selector", "ObsidianVault/Canon/Systems/SYS_sfx_system.md"),
    "fmv": ("FMV.BIN/STR streaming path", "ObsidianVault/Canon/Systems/SYS_fmv_player_streaming.md"),
    "ui": ("frontend/loading-screen resource loader", "ObsidianVault/Canon/Systems/SYS_menu_and_frontend.md"),
    "level_specific": ("resource_id_dat_load_dispatcher / level_load_chunks", "analysis/phase3_scene_asset_graph.json"),
    "code_overlay": ("level_file_path_build / region swap loader", "analysis/phase3_overlay_map.json"),
    "resident_executable": ("PS-X EXE loader", "tools/build_baselines.json"),
    "filesystem_support": ("disc/build filesystem", "tools/build_baselines.json"),
}


def categories(path: str) -> list[str]:
    upper = path.upper()
    suffix = Path(upper).suffix
    roles = []
    if upper == "SCUS_942.88":
        return ["resident_executable"]
    if suffix == ".ANM":
        roles.append("animation")
    if suffix == ".ALL":
        roles.append("models")
        if "TERRAIN" in upper:
            roles.append("geometry")
    if suffix in (".VH", ".VB", ".XA"):
        roles.append("audio")
    if suffix == ".STR" or upper == "FMV/FMV.BIN":
        roles.append("fmv")
    if upper.startswith("GFX/") or suffix == ".BGR":
        roles.extend(["textures", "ui"])
    if upper.startswith("LEVEL"):
        roles.append("level_specific")
        if suffix == ".RAW":
            roles.extend(["geometry", "collision", "textures"])
        elif suffix == ".BIN" and not upper.startswith("LEVEL00/"):
            roles.append("code_overlay")
    if upper == "BITS/MEMORY.BIN":
        roles.extend(["code_overlay", "ui"])
    if not roles:
        roles.append("filesystem_support")
    return list(dict.fromkeys(roles))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    baseline = json.loads(BASELINE.read_text())
    assets = {}
    gaps = []
    role_counts = Counter()
    for rel, pin in sorted(baseline["staged_inputs"].items()):
        path = STAGED / rel
        actual = digest(path) if path.is_file() else None
        if actual != pin["sha256"]:
            gaps.append({"path": rel, "expected": pin["sha256"], "actual": actual})
        roles = categories(rel)
        role_counts.update(roles)
        assets[rel] = {
            "sha256": pin["sha256"],
            "size": pin["size"],
            "local_hash_matches_pin": actual == pin["sha256"],
            "roles": roles,
            "load_owners": [
                {"owner": OWNER[role][0], "evidence": OWNER[role][1]}
                for role in roles
            ],
        }
    required = {"geometry", "collision", "textures", "models", "animation",
                "audio", "fmv", "ui", "level_specific"}
    missing_roles = sorted(required - set(role_counts))
    return {
        "_comment": "WP8 asset-provenance report over every centrally pinned "
                    "pristine staged input. It verifies local bytes, classifies "
                    "all required asset families, and names the load-owner frontier. "
                    "Regenerate: python3 tools/phase3_asset_provenance.py",
        "generated": date.today().isoformat(),
        "exhaustive": not gaps and not missing_roles,
        "exhaustive_over": "every tools/build_baselines.json staged_inputs entry",
        "baseline_sha256": digest(BASELINE),
        "summary": {
            "assets": len(assets),
            "role_counts": dict(sorted(role_counts.items())),
            "missing_required_roles": missing_roles,
            "hash_mismatches_or_missing": gaps,
        },
        "assets": assets,
    }


def main() -> int:
    doc = build()
    (ROOT / "analysis/phase3_asset_provenance.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    print(f"[asset-provenance] {doc['summary']['assets']} assets; "
          f"{len(doc['summary']['role_counts'])} roles; "
          f"{len(doc['summary']['hash_mismatches_or_missing'])} hash gaps")
    return 0 if doc["exhaustive"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
