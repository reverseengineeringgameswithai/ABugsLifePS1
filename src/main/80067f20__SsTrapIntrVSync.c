/* _SsTrapIntrVSync @ 0x80067f20 - the SEQ VSync trap handler: call the optional
 * pre-hook (if installed) then the mandatory tick handler. m2c-seeded (dc-10). */
extern void (*g_80080ebc)(void);
extern void (*g_80080eb8)(void);
void _SsTrapIntrVSync(void)
{
    if (g_80080ebc != 0) {
        g_80080ebc();
    }
    g_80080eb8();
}
