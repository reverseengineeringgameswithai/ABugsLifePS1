/* token_descriptor_reskin - re-skin a seed/token sprite descriptor (g_80096b98[idx]): CLUT +6 + texpage UV. */
extern unsigned char *g_80096b98[];

void token_descriptor_reskin(int model_idx, int level)
{
    int off;

    *(unsigned short *)(g_80096b98[model_idx] + 6) =
        (*(unsigned short *)(g_80096b98[model_idx] + 6) & 0xfffc) + level;

    for (off = 0; off < 12; off += 2) {
        unsigned char *p = g_80096b98[model_idx] + off;
        p[8] = (p[8] & 0x3f) + (level << 6);
    }
}
