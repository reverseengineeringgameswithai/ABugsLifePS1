/* serialize_savegame_buffer - pack savegame state (header + status + 19B + 64x5B) into dst. Fields UNKNOWN. */
extern unsigned char  g_800a65a0;
extern unsigned short g_80082284;
extern unsigned char  g_8009b878[];
extern unsigned char  g_80089938[];

void serialize_savegame_buffer(unsigned char *dst)
{
    int i;

    dst[0] = g_800a65a0;
    dst[1] = (unsigned char)g_80082284;

    for (i = 0; i < 19; i++)
        *(dst + i + 2) = g_8009b878[i];

    for (i = 0; i < 320; i += 5) {
        *(dst + i + 28) = g_80089938[i];
        *(dst + i + 29) = g_80089938[i + 1];
        *(dst + i + 30) = g_80089938[i + 2];
        *(dst + i + 31) = g_80089938[i + 3];
        *(dst + i + 32) = g_80089938[i + 4];
    }
}
