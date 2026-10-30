/* cd_mix_shim @ 0x80044ce8 — stash the l/r attenuation words, build a 4-byte
 * CdMix packet {l,0,l,0}, and submit it.
 *   g_80082218 = l; g_8008247e = r; CdMix({l,0,l,0}); */
extern unsigned short g_80082218;
extern unsigned short g_8008247e;
extern void CdMix(void *);

void cd_mix_shim(int l, int r)
{
    unsigned char pkt[4];
    g_80082218 = l;
    g_8008247e = r;
    pkt[0] = l;
    pkt[1] = 0;
    pkt[2] = l;
    pkt[3] = 0;
    CdMix(pkt);
}
