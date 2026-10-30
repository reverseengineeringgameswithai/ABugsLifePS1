/*
 * Documentation-grade reconstruction of the resident FMV caller identity.
 *
 * This file is not a build input and makes no matching-C claim. Exact words,
 * ranges, and hashes are regenerated from the pristine resident executable by
 * tools/phase4_fmv_resident_identity.py. The scene-flow owner remains the
 * hash-pinned handwritten ASM at
 * asm/hand_written/8004fca0_scene_flow_dispatcher.s.
 */
#include <stdint.h>

enum {
    FMV_SELECTOR_LEV15C = 40,
    FMV_SELECTOR_LOSE = 46,
};

struct resident_fmv_callsite_identity {
    uint32_t selector_pc;
    uint32_t selector_word;
    uint32_t call_pc;
    uint32_t call_word;
    uint32_t delay_pc;
    uint32_t delay_word;
    uint32_t return_pc;
};

static const struct resident_fmv_callsite_identity resident_fmv_calls[] = {
    {
        0x800500D4, 0x2404002E, /* addiu a0, zero, 46 */
        0x800500D8, 0x0C00F9F0, /* jal fmv_bin_load */
        0x800500DC, 0x00002821, /* addu a1, zero, zero */
        0x800500E0,
    },
    {
        0x80050280, 0x24040028, /* addiu a0, zero, 40 */
        0x80050284, 0x0C00F9F0, /* jal fmv_bin_load */
        0x80050288, 0x00002821, /* addu a1, zero, zero */
        0x8005028C,
    },
};

/*
 * Bare PC coverage is not code identity. A runtime event may be attributed to
 * either row only after the resident executable identity, the owning
 * 0x8004FCA0..0x800502C4 code-range identity, and the selector/call/delay
 * words above all match.
 *
 * The bounded synthetic lifecycle discriminator changes only the natural C16
 * game-over selector instruction from 0x2404002E to 0x24040028. The unchanged
 * 0x800500D8 call then supplies selector 40/mode 0 through the already natural
 * C16 callsite; the unmodified same-anchor branch supplies selector 46/mode 0.
 * This can test selector-specific playback lifecycle without claiming that a
 * pristine Menu or finale route naturally reaches 0x80050284.
 *
 * The current load-state scenario can advance recorded input and guest state
 * through a typed staged prelude, report its actual playback counters, arm
 * observers, and then apply one identity-checked code write. The Phase-4 batch
 * adapter requires the same staged boundary in both control jobs and derives
 * replay/observer spans from those raw results. This remains a static method
 * specification until a fresh escalation and paired live receipts are
 * predeclared; it is not natural Menu/finale ownership evidence.
 */
