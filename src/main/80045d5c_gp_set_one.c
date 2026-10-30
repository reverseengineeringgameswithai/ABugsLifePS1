/* FUNC_80045D5C @ 0x80045D5C — stores 1 into the gp-relative global at 0x80082484
 * (gp+0x6ec). GP-relative class proof (substrate v2).
 *   addiu v0,zero,1; sw v0,0x6ec(gp); jr ra; nop
 */
extern int g_80082484;
void gp_set_one(void)
{
    g_80082484 = 1;
}
