/* LEVEL02_LEVEL overlay @ 0x800B3B70 — sets the overlay-local state word at
 * 0x800B4950 to 60 (0x3C). OVERLAY TRACK proof: compiles to the exact bytes in
 * OVL/LEVEL02_LEVEL.BIN at its Region-A load VA. Global meaning UNKNOWN (byte-match).
 *   addiu v0,zero,60; lui at,0x800b; sw v0,0x4950(at); jr ra; nop
 */
extern int g_800b4950;
void level02_set_state_60(void)
{
    g_800b4950 = 60;
}
