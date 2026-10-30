/* sfx_voice_manager_glue @ 0x80050d98 (gp) — same bank-resolve + gate as
 * sfx_voice_manager_glue_0d1c, but drives sfx_voice_manager at priority 128
 * with the trailing slot set to 1 (looping/hold variant). */
extern int g_8008244c;             /* gp+1716: subsystem-enabled flag */
extern unsigned char g_800a6500[]; /* default sample bank */
extern void sfx_voice_manager(int, int, int, int, int, int);

void sfx_voice_manager_glue(int chan, unsigned char *obj)
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
                      128, (int)bank, 1);
}
