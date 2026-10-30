/* StSetStream @ 0x80070b20 - arm the CD-stream ring: reset the stream state
 * globals and latch (mode&1), the ready callback (a3) and the sector arg. */
extern void sub_80070d60(int);
extern int g_800b0cb8[3];
extern int g_800910f0[3];
extern int g_80090740[3];
extern int g_8009c208[3];
extern int g_80095388[3];
extern short g_800902dc[3];
extern int g_800894e0[3];
extern int g_800910f4[3];
void StSetStream(int mode, int a1, int a2, int a3, int arg5)
{
    sub_80070d60(1);
    g_800b0cb8[0] = 0;
    g_800910f0[0] = a3;
    g_80090740[0] = mode & 1;
    g_8009c208[0] = 0;
    g_80095388[0] = 0;
    g_800902dc[0] = 0;
    g_800894e0[0] = 0;
    g_800910f4[0] = arg5;
}
