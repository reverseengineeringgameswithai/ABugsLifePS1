/* gpu_timing_marker_append (gp) - record RCnt stamp + packed GP0(0x61) color into two rings, advance index. */
extern int GetRCnt(int spec);
extern int g_80082468;
extern int g_800b1e60[];
extern int g_800902e0[];

void gpu_timing_marker_append(int r, int g, int b)
{
    int stamp = GetRCnt(0xf2000001);
    int idx = g_80082468;

    g_800b1e60[idx] = stamp;
    g_80082468 = idx + 1;
    g_800902e0[idx] = r + (g << 8) + (b << 16) + 0x61000000;
}
