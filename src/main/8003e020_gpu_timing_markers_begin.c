/* gpu_timing_markers_begin @ 0x8003e020 */
extern int GetRCnt(int spec);
extern int g_800b1e60[4];
extern int g_80082468;

void gpu_timing_markers_begin(void) {
    g_800b1e60[0] = GetRCnt(0xf2000001);
    g_80082468 = 1;
}
