/* vmNoiseOff @ 0x8006a35c - clear a voice's (stride-52) noise entry and the two
 * global noise halfwords. */
extern char g_80089a93[];
extern short g_80089a7c[];
extern int g_80080ec8;
void vmNoiseOff(int voice)
{
    int off = (voice & 0xff) * 52;
    char *base;

    *(char *)(g_80089a93 + off) = 0;
    base = (char *)g_80080ec8;
    *(short *)((char *)g_80089a7c + off) = 0;
    *(short *)(base + 0x194) = 0;
    *(short *)(base + 0x196) = 0;
}
