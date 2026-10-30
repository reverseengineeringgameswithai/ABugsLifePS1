/* FUNC_80046B14 @ 0x80046B14 — returns bit 0 of the gp-relative global at
 * 0x80082478 (gp+0x6e0). GP-RELATIVE class proof (substrate v2: small_data + _gp).
 *   lw v0,0x6e0(gp); jr ra; andi v0,v0,1
 */
extern int g_80082478;
int gp_flag_test(void)
{
    return g_80082478 & 1;
}
