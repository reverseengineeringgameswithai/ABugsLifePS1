/* cd_audio_volume_apply @ 0x800507f8 — map two channel indices through the
 * paired s16 volume tables and hand the pair to cd_mix_shim.
 *   cd_mix_shim(g_80078b64[l], g_80078b84[r]); */
extern short g_80078b64[];
extern short g_80078b84[];
extern void cd_mix_shim(int, int);

void cd_audio_volume_apply(int l, int r)
{
    cd_mix_shim(g_80078b64[l], g_80078b84[r]);
}
