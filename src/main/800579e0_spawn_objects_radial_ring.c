/* spawn_objects_radial_ring - 8 objects in a ring, sine-table sampled 90-phased, scaled 1/64. */
extern void contact_object_spawn_full(int x, int y, int z, int a, int b,
                                      int c, int d, int e);

extern short g_80074970[];

void spawn_objects_radial_ring(int *center)
{
    int ang = 0;
    short *p = g_80074970;

    for (; ang < 4096; ang += 512) {
        int cosv = (short)*p >> 6;

        contact_object_spawn_full(center[0], center[1], center[2],
                                  cosv, -1024,
                                  (short)g_80074970[(ang + 1024) & 0xfff] >> 6,
                                  64, 44);
        p += 512;
    }
}
