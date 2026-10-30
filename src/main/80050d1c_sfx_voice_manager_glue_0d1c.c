/* sfx_voice_manager_glue_0d1c @ 0x80050d1c (gp) — resolve the sample bank (a
 * default table when no object, else the object's own bank once its 0x4000 flag
 * is set), gate on the subsystem flag + channel, then drive sfx_voice_manager
 * with priority 180. */
extern int g_8008244c;             /* gp+1716: subsystem-enabled flag */
extern unsigned char g_800a6500[]; /* default sample bank */
extern void sfx_voice_manager(int, int, int, int, int, int);

void sfx_voice_manager_glue_0d1c(int chan, unsigned char *obj)
{
    unsigned char *bank;
    if (obj == 0)
        bank = g_800a6500;
    else {
        if ((*(unsigned short *)(obj + 92) & 0x4000) == 0)
            return;
        bank = obj + 4;
    }
    if (g_8008244c != 0 && chan < 116)
        return;
    sfx_voice_manager((int)bank, chan - 16, (((chan - 16) & 0xf) << 7) + 4608,
                      180, (int)bank, 0);
}
