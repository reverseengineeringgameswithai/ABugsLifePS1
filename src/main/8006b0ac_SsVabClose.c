/* SsVabClose @ 0x8006b0ac - free a VAB slot's SPU RAM and clear its table entry. */
extern unsigned char g_8009fa38[];
extern int g_800b1f60[];
extern short g_800b1e58;
extern void sub_8006ca04(int addr);
void SsVabClose(int vabId)
{
    short id;

    if ((unsigned int)(vabId & 0xffff) >= 16)
        return;
    id = vabId;
    if (g_8009fa38[id] != 1)
        return;
    sub_8006ca04(g_800b1f60[id]);
    g_8009fa38[id] = 0;
    g_800b1e58 = g_800b1e58 - 1;
}
