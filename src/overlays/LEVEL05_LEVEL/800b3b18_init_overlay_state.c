/* LEVEL05_LEVEL overlay @ 0x800b3b18. Initializes six overlay-local state
 * words; only 0x800b42f0 is nonzero.
 */
extern int g_800b42e4;
extern int g_800b42f0;
extern int g_800b42ec;
extern int g_800b42fc;
extern int g_800b42e8;
extern int g_800b42f8;

void level05_init_overlay_state(void)
{
    g_800b42e4 = 0;
    g_800b42f0 = 250;
    g_800b42ec = 0;
    g_800b42fc = 0;
    g_800b42e8 = 0;
    g_800b42f8 = 0;
}
