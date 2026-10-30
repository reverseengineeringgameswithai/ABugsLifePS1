/* FUNC_80038F20 @ 0x80038F20 — game code (Traveller's Tales), called from
 * player_vertical_update (0x80048138). Reads a signed 16-bit global and
 * returns whether it is at/above the threshold -0x2000.
 *
 * Matching reimplementation for the decomp substrate C path (docs/SUBSTRATE.md).
 * This is the STAGE-2 proof: a real game function, not SDK library code,
 * matched byte-exactly with the PsyQ-4.0.0-era compiler + flags pinned in
 * config/segments.yml c_toolchain. Evidence: EXP_2026-07-08_first_c_match.
 *
 * Original disassembly:
 *   lui  v0, 0x8008
 *   lh   v0, 0x2402(v0)        ; signed short at 0x80082402
 *   nop
 *   slti v0, v0, -0x2000
 *   jr   ra
 *   xori v0, v0, 1             ; -> return !(x < -0x2000)
 *
 * g_80082402: address-anchored name only — the field's meaning is UNKNOWN
 * (no evidence yet); resolved at link via the entry's `externs` in segments.yml.
 */
extern short g_80082402;

int flag_ge_threshold(void)
{
    return !(g_80082402 < -0x2000);
}
