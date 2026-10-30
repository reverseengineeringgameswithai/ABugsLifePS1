---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - LBA Shift Rebuild Proof.md
aliases:
  - "Asset - LBA Shift Rebuild Proof"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - LBA Shift Rebuild Proof.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_LBA_Shift_Rebuild_Proof.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - LBA Shift Rebuild Proof
type: asset
updated: 2026-06-22
tags: [asset, rebuild, lba, mkpsxiso, milestone4, b4, gap-0025]
---

# Asset — LBA-shift rebuild proof (status + budget)

> Result for [[Gap Audit|GAP-0025]] / [[Blocker - Byte-exact disc reproduction is unproven|B4]]. **Outcome (✅ 2026-06-22): both in-slack AND oversize/LBA-shifting edits now PROVEN to boot + load in-level.** A reflow image — grow `BITS/MEMORY.BIN` +8192 B → **274/276 files shift +4 sectors** (only `SCUS_942.88`/`SYSTEM.CNF`, which precede it, stay) — was built with mkpsxiso 2.20 and **booted to LEVEL01** on the isolated fork (Flik at the spawn-table point `(197091,2734,492897)`, collision `0x800a7e48` populated, frame visually LEVEL01) ⇒ **in-level asset loading is by-name / LBA-shift-tolerant**, not just the EXE boot. Recipe: `REBUILD/abl_autolayout.xml` (no-`offs` reflow) + an oversize source redirect + `mkpsxiso -lba` diff; pristine disc kept pristine (build to /tmp). Optional follow-up: a committed `tools/build_reflow_image.py` to package the recipe.

## Baseline (CONFIRMED)
Unpatched `dumpsxiso → mkpsxiso` round-trip of `REBUILD/abl.xml` = **0 / 313,897 sectors differ** vs the master ([[Finding - Disc rebuild is byte-exact]] · [[Checksum Manifest]]). Works because `abl.xml` carries **explicit per-file LBA `offs`**. Tools: `mkpsxiso` + `dumpsxiso` (`/usr/local/bin`).

## How LBAs are assigned (mechanism)
- With **explicit `offs`** (as in `abl.xml`), mkpsxiso pins each file's LBA. If a file's data exceeds its slot `(next_offs − offs)` sectors, the build **overruns/overlaps** — it does **not** silently reflow.
- To grow a file past its slot you must **drop the fixed `offs`** (let mkpsxiso auto-assign), which **shifts the LBA of every file after it**. ABL loads files **by name**, so shifts *should* be tolerated — but this is **only proven for the boot EXE** ([[Finding - File loading is by-name (LBA-shift tolerant)]]); the in-level asset load under a shift is unverified.

## The one size-changing edit tested (in-slack — PROVEN)
Seed-move (chunk 31, [[Seed planting system]]): recompressed one chunk, spliced into LEVEL.RAW. Size **grew +1242 B but stayed within LEVEL01/LEVEL.RAW's slack (1820 B) → same 366 sectors, no LBA shift** (LBA 3069 unchanged, next file still 3435). **Operator-booted → seed spawned at the new location.** This is the in-slack, no-shift case — solid for modding.

## Per-file slack budget — LEVEL01 (computed from `abl.xml` + REBUILD sizes)
`slack = (next_file_LBA − file_LBA)·2048 − file_size`. Every LEVEL01 file has **< 1 sector** of slack:

| file | LBA | size B | slack B |
|---|---:|---:|---:|
| LEVEL.BIN | 2905 | 1,680 | 368 |
| LEVEL.DAT | 2906 | 332,824 | 1,000 |
| **LEVEL.RAW** | 3069 | 747,748 | **1,820** |
| LEVEL1.BIN | 3435 | 2,700 | 1,396 |
| LEVEL1.DAT | 3437 | 107,880 | 664 |
| LEVEL1.RAW | 3490 | 541,200 | 1,520 |
| LEVEL1A.VB | 3755 | 501,680 | 80 |
| LEVEL2.DAT | 4003 | 264,068 | 124 |
| TERRAIN.ALL | 4414 | 236,940 | 2,676 |

→ **Modder rule:** an edit is LBA-safe iff `(post-edit file size − original size) ≤ slack`. Combine with the literal-recompression overhead in [[Asset - PROPACK Rebuild Strategy]].

## Was a true LBA-shift tested? (No — blocker documented)
An oversize edit that **exceeds slack** was **not** rebuilt-and-booted here. Generating the reflowed image is allowed (local-only, `REBUILD/` is gitignored, **never committed**), but the decisive check — **does a reflowed/LBA-shifted image still boot and load LEVEL01 in-level?** — requires the **local-only DuckStation fork** (dirty, not independently reproducible; [[DuckStation Fork Reproducibility]]). 

**Exact missing prerequisite:** a reflow rebuild (drop `offs` for the grown file) → boot on the local emulator → confirm LEVEL01 in-level load. Until run, **oversize edits must be treated as unproven**.

## Safety rules for future modders
1. Prefer **in-place edits that don't grow the decompressed chunk** (change values, not record counts).
2. If growth is needed, keep `(literal_size − original) ≤ file slack` (table above) → no shift.
3. Exceeding slack ⇒ **reflow path + a local boot test** before relying on it.
4. Always keep the pristine disc read-only; build to a separate, ignored output ([[Preservation Policy]]).

## Next action
Run the reflow boot test (local-only) on one oversize LEVEL.RAW edit; record fixture/frame/command/observed-output per [[DuckStation Fork Reproducibility]]. Promotes GAP-0025 from "budgeted" to "shift proven."

## Related
[[Finding - Disc rebuild is byte-exact]] · [[Asset - PROPACK Rebuild Strategy]] · [[Asset - Disc file map]] · [[Checksum Manifest]] · `tools/rebuild_with_patched_dat.py` · `REBUILD/abl.xml`
