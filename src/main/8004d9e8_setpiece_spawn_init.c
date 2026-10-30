/* setpiece_spawn_init - record scripted setpiece/bird spawn (start+target pos + atan2 heading). */
extern int atan2_heading(int dx, int dz);

extern int   g_80090bc0, g_80090bc4, g_80090bc8, g_80090bcc;
extern int   g_80090bd0, g_80090bd4, g_80090bd8, g_80090bdc, g_80090be0;
extern short g_80090be4, g_80090be6, g_80090be8, g_80090bec, g_80090bee;

void setpiece_spawn_init(int x, int y, int z, int tx, int ty, int tz,
                         unsigned short flags)
{
    g_80090bc0 = x;
    g_80090bd8 = x;
    g_80090bc4 = y;
    g_80090bc8 = z;
    g_80090bcc = tx;
    g_80090bdc = y;
    g_80090be0 = z;
    g_80090be4 = 0;
    g_80090bd0 = ty;
    g_80090bd4 = tz;
    g_80090be6 = atan2_heading(tx - x, tz - z);
    g_80090be8 = 0;
    g_80090bec = 2;
    g_80090bee = flags;
}
