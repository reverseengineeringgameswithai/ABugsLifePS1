/* FUNC_80038F38 @ 0x80038F38 — the LEVEL exit / region-code query. Behavior from
 * src_re/level_exit_trigger.c (SOLVED 2026-06-24): if the Flik gate byte at
 * *p != 1 return 0, else read the player's current collision sector from
 * G_CUR_SECTOR (0x80090560, stride 20) and return that sector's region_code
 * halfword from SECTOR_TABLE (0x800A7E48, stride 0x30, code @ +0x2E).
 * Consumed by FUNC_80048138 (region code 2 -> LEVEL01 exit). Clean (no internal j).
 *   lbu v1,0(a1); if(v1!=1) return 0; v0=idx*20; v1=*(0x80090560+v0);
 *   v0=sector*48; return *(short*)(0x800a7e76 + v0)
 */
struct cur_sector {
    int cur;                        /* +0x00: current collision sector index */
    unsigned char pad[16];          /* stride 20 */
};
struct sector {
    unsigned char pad[0x2e];
    short region_code;              /* +0x2e; struct stride 0x30 */
};
extern struct cur_sector g_80090560[];
extern struct sector g_800a7e48[];

short sector_region_code_query(int player_idx, unsigned char *flik_gate)
{
    int sector;

    if (*flik_gate != 1)
        return 0;
    sector = g_80090560[player_idx].cur;
    return g_800a7e48[sector].region_code;
}
