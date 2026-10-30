/* resident_level_t_seed_plant_dan_glue - clear record fields + flag, run glue, reset indices. Layout partly UNKNOWN. */
extern int g_800a655c;
extern short g_800a657a;
extern unsigned char g_800a65a3;
extern char g_8009fd80[];
extern void player_vertical_resident_level_glue(void);

void resident_level_t_seed_plant_dan_glue(void)
{
    int *slot = &g_800a655c;
    int idx = *slot;

    if (idx > 0) {
        char *p = g_8009fd80 + idx;
        unsigned short h = *(unsigned short *)(p + 92);
        *(int *)(p + 28) = 0;
        *(int *)(p + 32) = 0;
        *(int *)(p + 36) = 0;
        *(unsigned short *)(p + 92) = h & 0xffbf;
    }
    player_vertical_resident_level_glue();
    g_800a657a = 0;
    *slot = 0;
    g_800a65a3 = 0;
}
