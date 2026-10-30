/* @ 0x8005d50c (16 B) — SUBSTRATE v3.2 gp-scaling proof. Store (arg + 0xc) into the
 * gp-relative pointer global at gp+0x584 (0x8008231c).
 *   addiu a0,a0,0xc; sw a0,0x584(gp); jr ra; nop
 */
extern char *g_8008231c;
void set_gp_ptr_plus_c(char *p)
{
    g_8008231c = p + 0xc;
}
