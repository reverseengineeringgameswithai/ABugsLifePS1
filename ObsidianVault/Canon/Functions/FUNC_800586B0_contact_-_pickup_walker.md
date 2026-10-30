---
kind: function
id: FUNC_800586B0
aliases: [FUNC_800586B0, 0x800586b0]
address: 0x800586B0
name: contact_-_pickup_walker
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths:
  - src_re/contact_walker_800586b0.c
patch_policy: unknown
---

# FUNC_800586B0 - contact - pickup walker

## Purpose

Scans the 64-entry contact array and fires a pickup's action when Flik is within its radius. This is PICKUP proximity — **not** world floor collision.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_800586B0.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x800586B0`
- Name: `contact_-_pickup_walker`
- Original note: `ObsidianVault/Functions/FUNC_800586B0.md`
- Source path: `src_re/contact_walker_800586b0.c`

## C source excerpt

Source: `src_re/contact_walker_800586b0.c`

```c
/* ============================================================================
 * contact_walker_800586b0.c  — player-proximity / pickup walker [PHASE 4 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.800586b0  (size 580 bytes, 0x800586b0..0x80058af4)
 * CONFIDENCE       : CONFIRMED walker loop, live gates, distance math, radius test,
 *                    action_id dispatch table. Action case bodies are summarized only;
 *                    detailed handler decompilation is Phase 5.
 * SOURCE NOTES     : docs/EXPERIMENT_LOG.md (exact math), docs/COORDINATE_MODDING.md
 *                    (auto-collect/weak-Y), docs/EXECUTABLE_AND_OVERLAYS.md,
 *                    Phase 3 contact_alloc_80059e44.c, r2 disasm.
 * KNOWN CALLERS    : fcn.8004ecd4 @0x8004f074.
 * KNOWN CALLEES    : per-action cases via table G_WALKER_DISPATCH(0x8001b570);
 *                    fcn.800503fc, fcn.8005044c, fcn.80050994, fcn.80054eac,
 *                    fcn.8004a700.
 * KNOWN GLOBALS    : G_CONTACT_ARRAY(0x800b0d18, 64*0x38), G_PLAYER_X/Y/Z,
 *                    G_BERRY_MARKER, G_GRAIN_COUNT, G_WALKER_DISPATCH,
 *                    0x80082504 (scene id), 0x800a6590/0x800a6594/0x800a657e,
 *                    0x800822f4 (script cursor), 0x80089938 marker table.
 * UNRESOLVED       : action-case bodies and gameplay semantics (Phase 5); meaning of
 *                    player-Y bias -0x1cc0; exact meanings of rec+0x2c writes and
 *                    post-hit 0x8004a700 call; marker-table shift at 0x80089938.
 *
 * CONFIRMED WALKER FACTS:
 *   - Array base 0x800b0d18, loop count 64, stride 0x38.
 *   - Live gate: lh rec+0x22 > 0, then (lbu rec+0x33 & 2) != 0.
 *   - Player snapshot is taken once before the loop:
 *       X = [0x800a6500], Y = [0x800a6504] - 0x1cc0, Z = [0x800a6508].
 *   - Distance scaling uses signed multiply and arithmetic shift:
 *       dx = ((playerX - rec.x) * 0x300) >> 13
 *       dy = ((playerY - rec.y) * 0x100) >> 13
 *       dz = ((playerZ - rec.z) * 0x300) >> 13
 *   - Radius = 0x12c + (lh rec+0x28). Contact if dist2 < radius*radius.
 *   - Dispatch index = (int16_t)((lhu rec+0x20) - 2); if (uint32_t)idx < 0x75,
 *     jump through word table 0x8001b570[idx], else use default case 0x800589d4.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define CONTACT_SLOT_COUNT      0x40
#define CONTACT_ACTION_LIMIT    0x75
#define PLAYER_Y_CONTACT_BIAS   0x1cc0
#define MARKER_ROTATE_TABLE     0x80089938u /* LIKELY table at 0x80090000-0x66c8; semantics TODO */
#define G_SCENE_ID              0x80082504u /* CONFIRMED read by action_id 2 case */
#define G_SCRIPT_CURSOR         0x800822f4u /* CONFIRMED read by action_id 0x20 case */
#define G_UNK_800A6590          0x800a6590u /* UNKNOWN flags halfword; action_id 0x0f ORs 0x20 */
#define G_UNK_800A6594          0x800a6594u /* UNKNOWN halfword counter; action_id 9 increments */
#define G_UNK_800A657E          0x800a657eu /* UNKNOWN halfword; action_id 0x32 stores -3 */

extern void fcn_800503fc(void *arg);           /* Phase 5 / later: semantics UNKNOWN */
extern void fcn_8005044c(int result, void *rec);/* post-pickup bookkeeping (CONFIRMED call shape) */
extern void fcn_80050994(int sound_or_event_id);/* sound/event helper; exact meaning Phase 5 */
extern void fcn_80054eac(void);                /* grain pickup handler; body Phase 5 */
extern void fcn_8004a700(int dx, int dz, void *out, int zero); /* post-hit helper; UNKNOWN */

typedef enum WalkerActionCase {







static int32_t walker_scaled_delta(int32_t player, int32_t record, int32_t scale)
{
    /* MIPS: subu; mult signed; mflo; sra 13. Overflow/HI ignored. */
    return ((player - record) * scale) >> 13;
}
/* Full source is in the listed source path. */
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_800586B0.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_800586B0.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_800586B0.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

