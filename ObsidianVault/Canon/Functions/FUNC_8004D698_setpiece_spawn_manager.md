---
kind: function
id: FUNC_8004D698
aliases: [FUNC_8004D698, 0x8004d698, setpiece_spawn_manager, setpiece_spawn_refs]
address: 0x8004D698
name: setpiece_spawn_manager
status: static_seen
confidence: medium
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/setpiece_spawn_8004d698.c
  - EXP_2026-07-09_identity_reconciliation
src_paths:
  - src_re/setpiece_spawn_8004d698.c
patch_policy: unknown
---

# FUNC_8004D698 - setpiece spawn refs

> **RCA a3 identity fix (2026-07-09):** Renamed setpiece_spawn_refs -> **setpiece_spawn_manager** (authoritative `re_symbols.sym`; the scripted setpiece/bird spawn path, per the enemy-spawn correction 2026-07-03).


## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x8004D698`
- Name: `setpiece_spawn_refs`
- Source path: `src_re/setpiece_spawn_8004d698.c`

## C source excerpt

Source: `src_re/setpiece_spawn_8004d698.c`

```c
/* ============================================================================
 * setpiece_spawn_8004d698.c — scripted setpiece/bird actor spawn (trigger + init)
 * ----------------------------------------------------------------------------
 * Enemy-spawning track C (2026-07-03). Live + static (isolated DuckStation,
 * SCUS-94288, spider_walking.sav et al).
 *
 * IMPORTANT ATTRIBUTION CORRECTION (2026-07-03):
 *   This spawn path was previously documented as "the CHASER spawn"
 *   ([[enemy-chaser-spawn-areas]]). It is NOT. It spawns the SCRIPTED
 *   SETPIECE actor at 0x80090bc0 (the bird / finale / Thumper-approach actor,
 *   FUNC_8004DD98's subject), which is EMPTY (+0 == 0) in all 5 ordinary
 *   gameplay saves checked — it only exists during scripted sequences.
 *   Additionally, live motion testing shows **0x80095358 is the CAMERA-state
 *   struct** (GAP-0028's cam struct; θ@+0x20 is a 12-bit angle in every save),
 *   NOT a "chaser slot": moving Flik, the struct lags at ~half his motion,
 *   sits ~24k ABOVE him, and its distance GROWS (follow-cam smoothing
 *   C += (target−C)>>3), the opposite of homing. The real regular enemies are
 *   the actor structs registered in damageable_object_ptr_table 0x80090748
 *   (e.g. LEVEL01 spider = id 9 @ 0x8009fd80) — their spawn is track A.
 *
 * ---------------------------------------------------------------------------
 * SPAWN MANAGER — FUNC_8004D698 (0x8004d698, body 0x8004d6a8..0x8004d9e4)
 * ---------------------------------------------------------------------------
 * Called EVERY FRAME by the gameplay state machine fcn.8004ecd4 (jal @0x8004f040,
 * one of its per-frame subsystem calls). Behaviour:
 *
 *   idx   = [0x800823cc];                    // which spawn-path record
 *   state = [0x800824dc];                    // the TRIGGER variable
 *   rec   = [0x80096dc8 + idx*4];            // record ptr (DAT-resident)
 *   if (state == 0 || state < -9) {          // idle/expired
 *       [0x800a652c] = 0; [0x800a6534] = 0;  // zero player velocity fields
 *   }
 *   if (state == -1) {                       // <-- THE SPAWN TRIGGER VALUE
 *       // spawn position/target from the record's first two waypoints (file<<5):
 *       spawn_init(rec[+0x4]<<5, rec[+0x8]<<5, rec[+0xc]<<5,     // WP0 (a3,+sp)
 *                  rec[+0x10]<<5, rec[+0x14]<<5, rec[+0x18]<<5,  // WP1 (a0..a2)
 *                  mode = 2);
 *       [0x800824dc] = -2;                   // consume the trigger (one-shot)
 *   }
 *   ... (further states step the scripted flight along the record's 16 waypoints)
 *
 * So the spawn fires exactly once when something writes -1 into 0x800824dc; the
 * writer of that -1 is the SCRIPT/EVENT layer (scene code / mover-VM CALL), which
 * is why teleporting Flik into a "spawn area" never triggered anything.
 *
 * ---------------------------------------------------------------------------
 * SPAWN INIT — FUNC_8004D9E8 (0x8004d9e8..0x8004da90)
 * ---------------------------------------------------------------------------
 * Populates the setpiece actor block at 0x80090bc0 (args a0..a3 + 3 stack args):
 *   [0x80090bc0/bc4/bc8] = pos (X,Y,Z)     [0x80090bd8/bdc/be0] = pos copy (cur/target)
 *   [0x80090bcc/bd0/bd4] = second point    [0x80090be4] = 0
 *   [0x80090be6] = atan2_heading(dx,dz)    (initial facing, via 0x80060ae4)
 *   [0x80090be8] = 0                       [0x80090bec] = 2 (state/mode)
 *   [0x80090bee] = type halfword (sp+0x30) — the same flag word whose bit 0 the
 *                  Thumper defeat-chain sets (see [[Enemy AI state machine]]).
 *
 * ---------------------------------------------------------------------------
 * THE "SPAWN-AREA" RECORDS (LEVEL01 @ DAT 0x94c / 0xa10 / 0xad4)
 * ---------------------------------------------------------------------------
 * The 0xc4-byte records behind table 0x80096dc8 (LEVEL01 runtime 0x80161144/
 * 0x80161208/0x801612cc; IDs 0x000B0010/0x000C0010/0x000D0010) are 16-waypoint
 * XYZ loops (file<<5). Given the consumer above, they are SETPIECE FLIGHT PATHS
 * (bird patrol/flight loops), not chaser patrol areas. They remain fully
 * disc-editable (LEVEL.DAT is uncompressed) — relocating them relocates the
 * scripted flight path.
 * ============================================================================ */

#include "re_types.h"

#define G_SETPIECE_SPAWN_STATE 0x800824dcu /* -1 = spawn now; -2 = spawned; 0/<-9 idle */
#define G_SETPIECE_RECORD_IDX  0x800823ccu /* index into the record pointer table       */
#define G_SETPIECE_RECORD_TBL  0x80096dc8u /* -> 0xc4-byte 16-waypoint path records      */
#define G_SETPIECE_ACTOR       0x80090bc0u /* the scripted bird/finale actor block       */
#define G_CAMERA_STATE         0x80095358u /* CAMERA struct (NOT a chaser slot)          */

void setpiece_spawn_refs(void)
{
    volatile unsigned t = G_SETPIECE_SPAWN_STATE ^ G_SETPIECE_RECORD_IDX ^
                          G_SETPIECE_RECORD_TBL ^ G_SETPIECE_ACTOR ^ G_CAMERA_STATE;
    (void)t;
}
```

## Evidence

- Source: `src_re/setpiece_spawn_8004d698.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`
