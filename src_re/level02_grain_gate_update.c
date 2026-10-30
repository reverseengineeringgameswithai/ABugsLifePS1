/* ============================================================================
 * level02_grain_gate_update.c -- LEVEL02 native grain-gate update (partial RE)
 * ----------------------------------------------------------------------------
 * Source-only reconstruction.  This file is not compiled into ALLMODS.
 *
 * Live anchor (pristine image, level02_graingate_locked.sav, 2026-07-11):
 *   update/compare window   0x800B44BC..0x800B4628
 *   nine-record table      0x800B4C1C, stride 0x14
 *   grain count            0x800A65A1 (u8)
 *   geometry/deform helper 0x80029030
 *
 * Nearest record at the supplied gate:
 *   {state=4295, id=26, threshold=20, x=193754, z=131692}
 *
 * Causal trace from the same locked state:
 *   - forcing grain to 20 and approaching wrote state 4295 -> 4200 at
 *     PC 0x800B4530;
 *   - PC 0x800B4624 then stepped 4200,4060,3920,...,1680 (delta -140,
 *     approximately once per five emulator frames);
 *   - the native helper lowered the gate geometry and Flik crossed it;
 *   - grain below the per-record threshold left state 4295 and collision shut.
 *   - threshold is evaluated inside the proximity-selected update; merely
 *     owning enough grain is not an activation event. Contact/proximity must
 *     select the gate first, after which its stepped state continues lowering.
 *
 * The current extracted LEVEL02 overlay bytes do not reproduce this live save's
 * exact 0x800B44xx body.  Addresses here are therefore runtime/save-overlay
 * provenance, not a claim that the checked-out overlay file byte-matches it.
 * The denial feedback/sound branch and the exact cadence predicate remain open.
 * ==========================================================================*/

#include "re_types.h"

#define LEVEL02_GATE_COUNT       9
#define LEVEL02_GATE_TABLE_LIVE  ((volatile GrainGateRecord *)0x800B4C1C)
#define GRAIN_COUNT              (*(volatile uint8_t *)0x800A65A1)

#define GATE_STATE_CLOSED        4295
#define GATE_STATE_ARMED         4200
#define GATE_STATE_STEP          140
#define GATE_STATE_PASSABLE_MAX  1800

typedef struct GrainGateRecord {
    int32_t state;             /* +0x00: live vertical/deformation state */
    int32_t id;                /* +0x04: nearest supplied gate = 26 */
    int32_t grain_threshold;   /* +0x08: nearest supplied gate = 20 */
    int32_t x;                 /* +0x0C: activation/geometry anchor X */
    int32_t z;                 /* +0x10: activation/geometry anchor Z */
} GrainGateRecord;

extern void gate_geometry_apply_80029030(GrainGateRecord *gate, int state);

/* Partial behavioral reconstruction of 0x800B44BC..0x800B4628.  The caller's
 * proximity/id selection and the cadence test are intentionally named rather
 * than fabricated: both surround the confirmed compare/store slice. */
void level02_grain_gate_update_partial(GrainGateRecord *gate,
                                       int proximity_triggered,
                                       int cadence_tick)
{
    if (!proximity_triggered)
        return;

    /* 0x800B44BC lbu grain; compare against gate->grain_threshold. */
    if (GRAIN_COUNT < (uint8_t)gate->grain_threshold) {
        /* Confirmed locked outcome.  Retail also reaches a denial-feedback
         * path here; its exact sound/UI contract is not yet resolved. */
        return;
    }

    if (gate->state == GATE_STATE_CLOSED) {
        /* Confirmed writer: 0x800B4530. */
        gate->state = GATE_STATE_ARMED;
    } else if (cadence_tick && gate->state >= GATE_STATE_PASSABLE_MAX) {
        /* Confirmed writer: 0x800B4624. */
        gate->state -= GATE_STATE_STEP;
    }

    gate_geometry_apply_80029030(gate, gate->state);
}
