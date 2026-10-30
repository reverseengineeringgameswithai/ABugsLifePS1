---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - LEVEL.DAT non-pickup records are undecoded.md
aliases:
  - "Blocker - LEVEL.DAT non-pickup records are undecoded"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - LEVEL.DAT non-pickup records are undecoded.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - LEVEL.DAT non-pickup records are undecoded
type: blocker
id: B10
severity: MEDIUM
category: level-format / struct-recovery
confidence: CONFIRMED
tags: [blocker, major, leveldat, format, struct]
updated: 2026-06-22
---

# 🟠 B10 — 10 of 11 LEVEL.DAT top-level record types are undecoded

> Only `rec0` (the type-0x3f pickups) is decoded. The other ten top-level records — including a **packed, delta-encoded negative-record stream** — have no semantic decode. Roughly half the LEVEL.DAT structure is shape-known but meaning-unknown.

> [!check] Update (2026-06-18, B10) — **record roles IDENTIFIED.** The 10 undecoded top-level records are **object PATHS** (waypoint arrays): rec1 (`0x01`, 104 pts) is a 3×s32 world-waypoint path whose consumer at `0x8004c400` sets a moving object's position to `path[idx]<<5` (live-traced while walking Flik); rec2–4 (`0x0b`/`0c`/`0d`) share the format; the negatives (`-2..-7`) are delta-encoded paths → [[Finding - LEVEL.DAT records are object paths]]. **Residual:** the negative-record delta-stream widths + per-group path semantics. **Severity → Medium.**

> [!check] **RESOLVED (2026-06-18) — negative-record consumer + format fully decoded (pre-load trace).** From the pre-load state `SCUS-94288_2.sav`, a read-watch on the negative-record region across the level load isolated the consumer: the **DAT parser `fcn.8001cdc0` at `0x8001ce8c`** (NOT a separate delta consumer; gameplay read-watch saw 0 because these are parsed **at load**, frame 5314, right after the DAT DMAs in **uncompressed** — disc `LEVEL.DAT[0:16]` == RAM `@0x801607f8`). The parser logic:
> ```
> lh   v0, 0x2(s2)      ; record field@+2 (signed "slot")
> bgez v0, 0x8001ced4   ; >=0 → normal sequential record
>                       ; <0  → INDEXED record:
> sll v0,v0,2 / subu v0,a0,v0 / sw s2,0(v0)   ; table[|slot|] = &record  (register by slot)
> ```
> **Negative ≠ delta-magic; it's a slot ID** — the record registers its own pointer into a lookup table at `base + |slot|·4` so other code finds it by index. **Body format (decoded from rec5 + verified against the live record boundaries):** `[s16 count N][s16 slot]` then `[3×s32 absolute anchor waypoint]` then `[N × (3×s16) packed delta steps]`; **total size = 16 + 6·N bytes**. rec5 = slot −2, N=48, anchor `(−1568,−3115,−368)` → 304 B (== next-record boundary `0x801614c0`); rec6 N=88 → 544 B (== `0x801616e0`). So these are **indexed delta-encoded waypoint paths**, consumed at load by `fcn.8001cdc0` and at runtime by the path-follower `0x8004c400`. **B10 fully resolved** (all 11 record roles known + negative format decoded). **Severity → Low.**

**Severity:** ~~Major~~ → **Medium** (record roles identified; rec2–10 by-format only + open placement residuals) · **Impact:** Medium · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Medium–High

## Audit reconciliation (2026-06-22)
The body's **"B10 fully resolved"** OVERSTATES — SOFTENED. **TRUE STATUS = PARTIALLY ADDRESSED.** Genuinely verified:
- **11/11 top-level record roles IDENTIFIED.**
- **rec1 consumer CONFIRMED live** (`0x8004c400` = mover-VM op9).
- **Negative-record packing decoded** (boundary-validated: rec5 304 B, rec6 544 B).
- **Pass-1 node-array decor placement decoded.**

But **rec2–10 are only LIKELY** (classified by-format, **not individually consumer-traced**). And OPEN residuals remain:
- **Pass-3 placement table** — 6 unplaced decor payloads, **position field undecoded** ([[Finding - DAT record holds decor instance world position]]).
- **Per-instance rotation/scale M_obj** undecoded (GAP-0023).
- **G2 source-record** `+0x12` / `+0x18` / `vec[3]` scalars undecoded.

Frontmatter `severity` reconciled to **MEDIUM**. **Keep OPEN** (not fully resolved).

## What is known (evidence)
- 11 top-level DAT records: `rec0` = type-0x3f pickups (**SOLVED**, [[MEM - Type-0x3f placement record]]); `rec1`–`rec10` roles **UNKNOWN** (`level01_dat_geometry_inventory.md`, `geometry_notes.md`).
- Fixed `0x0c`-stride records (`0x01`×104, `0x0b`/`0x0c`/`0x0d`×16) = "three s32 triples, role UNKNOWN."
- **Packed negative records (`−2..−7`)**: a 12-byte s32-triple prefix then a delta-encoded/packed byte stream whose **field widths and prefix/stream boundary are TODO** ("do not assume").
- The G2 source-record formats (`0x18`/`0x20`-byte, bit3-selected, [[Finding - Two parser source-record formats]]) still have `+0x12`/`+0x18` scalars and a `vec[3]@+0x00` of UNKNOWN role. The pass-2 table (`0x80091210`, empty in LEVEL01) and a reserved `0x1180`-byte gap are unexplained.
- **G5 found zero static readers** for these type-table slots → consumed via non-global pointers or overlay code ([[Blocker - Function boundaries and overlays evade the static call graph|B17]]).

## Why it matters
- A full LEVEL.DAT object-pipeline RE cannot be claimed while 10/11 record types and the negative-record packing are undecoded; these likely encode placement/instancing/animation needed for any editor beyond raw geometry-vertex edits.

## Dependencies
- **Depends on:** [[Blocker - RE depth is LEVEL01-only|B8]] · [[Blocker - Function boundaries and overlays evade the static call graph|B17]] (readers are overlay/pointer-dispatched).

## Research opportunity (direction only)
- Because static reader-search returns nothing, a runtime READ-watch on each record's RAM image would catch its consumer; the negative-record packed stream could be decoded by correlating it against a known on-screen object/instance count. (Direction only.)

## Evidence & sources
- vault: [[Asset - LEVEL.DAT]] · [[LEVEL.DAT object pipeline]] · [[MEM - Type-0x3f placement record]] · [[Finding - Two parser source-record formats]] · [[FUNC_8001CDC0]]
- corpus: `src_re_geometry/level01_dat_geometry_inventory.md`, `geometry_notes.md`
- See also: [[Blockers]] · [[Risk Matrix]]
