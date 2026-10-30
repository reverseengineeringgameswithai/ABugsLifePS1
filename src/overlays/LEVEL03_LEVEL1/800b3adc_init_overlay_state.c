/* LEVEL03_LEVEL1 overlay @ 0x800b3adc. Initializes overlay-local state words
 * and mirrors two resident globals. Names are address-anchored until the
 * overlay data layout is understood.
 */
extern short g_8009fffe;
extern int g_80077e3c;
extern int g_800b4600;
extern int g_800b460c;
extern int g_800b4608;
extern int g_800b4604;
extern int g_800b45f8;
extern int g_800b45f4;
extern int g_8009ffdc;

void level03_level1_init_overlay_state(void)
{
    g_800b4600 = 0;
    g_800b460c = 0;
    g_800b4608 = 0;
    g_800b4604 = 0;
    g_800b45f8 = 0;
    g_800b45f4 = g_8009fffe;
    g_8009ffdc = g_80077e3c;
}
