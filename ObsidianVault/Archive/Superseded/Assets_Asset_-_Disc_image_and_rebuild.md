---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - Disc image and rebuild.md
aliases:
  - "Asset - Disc image and rebuild"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - Disc image and rebuild.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_Disc_image_and_rebuild.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - Disc image and rebuild
type: asset
confidence: CONFIRMED
tags: [asset, disc, rebuild, tooling]
---

# Asset — Disc image & rebuild workflow

> The original disc image (read-only) and how patched images are rebuilt for testing.

## Original image (treat as read-only)
- `Disney-Pixar A Bug's Life (v1.0).bin/.cue` — 738,285,744 B, 313,897 sectors, MODE2/2352, single track.
- ISO9660 vol `A_BUGS_LIFE`, publisher `PIXAR_DISNEY`, region `SCEA`, dated 1998-10-20. `SYSTEM.CNF`: `BOOT=cdrom:\SCUS_942.88;1`.
- Boot exe `SCUS_942.88` sha1 `af43de22474f15664d0e17498fbd27faeb7ed111`, 471,040 B.

## Rebuild workflow
1. Extract once: `dumpsxiso -x REBUILD/files -s REBUILD/abl.xml -l "<orig>.cue"`.
2. Patch a **copy** of the DAT (e.g. via a `tools/patch_g*.py` or `tools/dat_reloc.py`).
3. Stage it over `REBUILD/files/LEVEL01/LEVEL.DAT` (back up `.orig` first).
4. `tools/rebuild_with_patched_dat.py` → `mkpsxiso -y -o OUT.bin -c OUT.cue REBUILD/abl.xml`.
5. **Restore `.orig` after every build.** Verify embedded `LEVEL01/LEVEL.DAT;1` (LBA **2906**) sha1 == patched DAT.

Each geometry build emits a `DAT/LEVEL01_LEVEL_*_REBUILD.md` manifest (patched size 332824, patched=embedded sha1). Pristine LEVEL01 DAT sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`.

> [!warning] Keep the original `.bin/.cue` pristine; all edits go to copies. Build artifacts are gitignored.

## Provenance & fidelity (verified 2026-06-18)
- **Master = USA V1.0**, hash-verified: CRC32 `607704bb` · MD5 `2c3861a3a568d0e8119693f2117d2e00` · SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1` (matches the public release; the **V1.1** rerelease differs, CRC `ed6e4cb9`).
- **Rebuild is byte-exact:** a full `dumpsxiso`→`mkpsxiso` round-trip = **0 / 313,897 sectors differ** vs the master (incl. EDC/ECC, gaps, Form2 XA/STR) → [[Finding - Disc rebuild is byte-exact]].

## Related
- Tools: [[Tools Catalog]] · `tools/rebuild_with_patched_dat.py`
- Assets: [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.BIN and overlays]]
- Playbook: [[Playbook - Create a deterministic experiment]]
- Source: `docs/TOOLING.md`
