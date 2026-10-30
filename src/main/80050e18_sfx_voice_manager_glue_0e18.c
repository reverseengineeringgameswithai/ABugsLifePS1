/* sfx_voice_manager_glue_0e18 @ 0x80050e18 (gp) — gate + dispatch a voice.
 * Skips only when the subsystem flag is set AND the id is below 116; otherwise
 * forwards to sfx_voice_manager with a derived bank/offset.
 *   if (g && id < 116) return;
 *   sfx_voice_manager(chan, id-16, ((id-16)&0xf)<<7 + 4608, 128, chan, 0); */
extern int g_8008244c;   /* gp+1716: subsystem-enabled flag */
extern void sfx_voice_manager(int, int, int, int, int, int);

void sfx_voice_manager_glue_0e18(int id, int chan)
{
    if (g_8008244c != 0 && id < 116)
        return;
    sfx_voice_manager(chan, id - 16, (((id - 16) & 0xf) << 7) + 4608, 128, chan, 0);
}
