/* LEVEL05_LEVEL1 overlay @ 0x800b3bd4. Compares a resident halfword against
 * an overlay-local short table indexed by the overlay word at 0x800b4bb8.
 */
extern int g_800b4bb8;
extern short g_800a0282;
extern short g_800b4b80[];

int level05_level1_compare_overlay_halfword(void)
{
    return g_800a0282 != g_800b4b80[g_800b4bb8];
}
