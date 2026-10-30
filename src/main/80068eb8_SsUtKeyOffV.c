/* SsUtKeyOffV @ 0x80068eb8 - key-off a voice by id (guarded by a re-entry lock). */
extern int g_80096d9c;
extern short g_8009fa22;
extern void sub_8006a3a0(int a);
int SsUtKeyOffV(int voice)
{
    int v = voice;

    if (g_80096d9c == 1)
        return -1;
    g_80096d9c = 1;
    if ((unsigned int)(v & 0xffff) < 24) {
        g_8009fa22 = v;
        sub_8006a3a0(0);
        g_80096d9c = 0;
        return 0;
    }
    g_80096d9c = 0;
    return -1;
}
