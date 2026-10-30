extern unsigned char g_800b3f80[];
extern unsigned char g_800b3f84[];

void level06_select_grid_offset(int index)
{
    /* The retail object retains an otherwise unused eight-byte frame. */
    volatile unsigned char frame_reservation[1];

    index *= 2;
    g_800b3f80[0] = g_800b3f84[index];
    g_800b3f80[1] = g_800b3f84[index + 1];
}
