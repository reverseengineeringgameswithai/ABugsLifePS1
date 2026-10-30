/* @ 0x800252a0 (16 B) — SUBSTRATE v3.2 gp-scaling proof. Reset two gp-relative
 * state globals: the halfword at gp+0x732 (0x800824ca) and the word at gp+0x5dc
 * (0x80082374). Extends the substrate-v2 small_data gp path from getters to setters.
 *   sh zero,0x732(gp); sw zero,0x5dc(gp); jr ra; nop
 */
extern short g_800824ca;
extern int   g_80082374;
void reset_pickup_state(void)
{
    g_800824ca = 0;
    g_80082374 = 0;
}
