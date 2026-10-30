/* player_vertical_resident_level_glue - if counter 0x800a658c!=0, write -30 into stride-836 record (n-1), clear counter. */
extern short g_800a658c;

struct rec41a74 { short f0; char pad[834]; };
extern struct rec41a74 g_8009c874[];

void player_vertical_resident_level_glue(void)
{
    short *counter = &g_800a658c;
    short n = *counter;

    if (n != 0) {
        g_8009c874[n - 1].f0 = -30;
        *counter = 0;
    }
}
