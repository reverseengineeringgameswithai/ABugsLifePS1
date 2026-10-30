---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Dot guide NPC.md
aliases:
  - "Dot guide NPC"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Dot guide NPC.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Dot_guide_NPC.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Dot guide NPC
type: system
updated: 2026-07-03
confidence: CONFIRMED (live level01.sav; path record + guide law + wait behavior verified)
tags: [system, npc, dot, guide, path, mover-vm, level01, rcg-032]
---

# Dot, the guide NPC (LEVEL01) — solved

> RCG-032 (created + solved 2026-07-03). How Dot guides Flik to the LEVEL01 ending: her actor,
> her path, the guide law, and what she does when Flik lags. RE: `src_re/dot_guide_npc.c`.

## Who she is (engine terms)
- A **regular chunk-31 actor**: LEVEL01 record **type `0x070e`** (unique — one per level), actor **id 14** (`0x800a0a64` in `level01.sav`). She sits in the damageable table with the **targetable bit clear** (`+0x5c` bit `0x1` = 0) → berries can't hit her, homing acquisition skips her. A friendly NPC riding the ordinary enemy/actor machinery.
- ⚠️ **Correction**: the [[Enemy AI movement programs]] sweep's "mosquito = path-patrol" row **was Dot** (the id-14 actor picked in `mosquito.sav` is her). The real mosquito enemy = the id-10 chaser (the one Thumper throws).

## Her path — LEVEL.DAT record @ +0x468 (type 1, 104 waypoints)
Header `{count 0x68 = 104, type 1}`, waypoints at `+0x46c`, stride `0xc`, s32 file coords (`<<5` = runtime). It runs from **Flik's spawn area** `(159296,−40192,528512)` across the whole level to `(−195552,−183200,−97440)` — **terminating at the exit region (sector 177)**. Live-verified: her move-target `+0x34` == `waypoint[wp_idx]<<5` exactly. (This is the same "rec1" path the old mover-relocation experiment moved — so **her route is disc-editable**, LEVEL.DAT is uncompressed.)

## The guide law — the proximity-gated path program
Her mover-VM program (shared path-follower @ `0x800775fa`):
```
op5   next waypoint → target
op10  PARK (walk the leg)
op17  s3 = dist(FLIK) < 1200        ; ≈38,400 runtime units
op9   if (s3) → advance to next leg
op0   LOOP
```
**She only advances while Flik is within the radius.** Live: Flik 53k away → she finishes her current leg and **parks** (wp frozen 240f+); Flik beside her → wp advances (1→6 over ~400f) as she walks ahead (~147 u/frame), leg by leg, toward the exit.

## What if Flik takes too long?
**Nothing punitive — she waits forever.** The op17 wait-loop has no timeout and she never regresses down the path. While parked she emits a **periodic idle cue**: `0x8005044c(id=7, &her_pos)` from the per-actor update handler (`ra 0x80049eb4`), **every ~50 frames** — the waiting/beckoning effect+sound.

## Voice lines (partial)
Her callouts do **not** ride `sfx_dispatch 0x80050994` (zero calls while guiding *and* waiting). The only per-actor audio/FX trigger caught is the periodic `0x8005044c(7)` cue above. Full voice attribution needs the **SPU key-on trace** — the standing GAP-0031 residual (named; not yet traced).

## Modding levers
- **Reroute the guide — ✅ PROVEN ON DISC (2026-07-03)**: rewrote the 104 waypoints at LEVEL.DAT `+0x46c` (size-preserving) → disc **`REBUILD/ABL_DOT_REROUTE2.cue`** → cold boot: the new coordinates load, and Dot **homes to the rewritten waypoints verbatim** (`target +0x34 == new_wp<<5` **260/260** samples; old coords 0/260) while the guide law (advance-only-when-Flik-near) stays intact. **Design rules learned** (from a failed naive attempt, `ABL_DOT_REROUTE`): keep waypoint **Y terrain-plausible** (she flies/walks straight at the waypoint — a flat-Y ring far below her hillside start made her drift) and keep **legs of reasonable length** (very short legs cause overshoot). **For a NEW level (Tier-3): give her the custom route to the end-goal by rewriting these waypoints; to make her STOP at the goal, repeat the goal waypoint through the tail of the record (op5 wraps the path — a repeated tail parks her there).**
- **Follow radius**: the op17 operand (1200) at `0x80077600` — EXE u16.
- **Impatience**: her wait-loop could be given a timeout by patching the loop (EXE program bytes).

## Residuals
- End-of-path/arrival behavior (a waypoint-poke test perturbed her leg state; needs a natural full walk — a long movie would close it). Note op5 wraps at the end — the repeated-tail trick (above) sidesteps this for custom routes.
- The exact op17 distance scale; the SPU voice key-on; whether other levels' guide NPCs (LEVEL08 DIM/MANNY/ROSIE/TUCKROLL saves exist) reuse this program.

## Related
[[Enemy AI movement programs]] (corrected) · [[Enemy spawn architecture]] · [[Event and scripting system]] · [[LEVEL01 exit trigger|Level Goal and Exit Trigger Matrix]] · [[Retail Gameplay Completeness Gap Audit]] RCG-032 · `src_re/dot_guide_npc.c`
