/* _SsSndPause @ 0x80067148 - pause one voice of a SEQ/SEP slot: index the
 * seq-base table by voice i, step to sub-slot j (stride 176), poke the
 * pause flag off and clear bit 1 of the voice status word. */
extern unsigned char *g_800b01a0[];
extern int sub_8006af4c(int);
void _SsSndPause(short i, short j)
{
    unsigned char *e = g_800b01a0[i] + j * 176;
    sub_8006af4c((short)(i | (j << 8)));
    e[20] = 0;
    *(int *)(g_800b01a0[i] + j * 176 + 152) &= ~2;
}
