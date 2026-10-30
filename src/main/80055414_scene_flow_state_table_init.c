/* scene_flow_state_table_init - header {5,1}, zero 19 bytes, 64 stride-5 {100,255,255,255,255} recs. */
void scene_flow_state_table_init(unsigned char *p)
{
    int i = 18;
    unsigned char *q = p + 18;

    p[0] = 5;
    p[1] = 1;
    for (; i >= 0; i--) {
        q[2] = 0;
        q--;
    }
    for (i = 0; i < 320; i += 5) {
        unsigned char *r = p + i;
        r[28] = 100;
        r[29] = 255;
        r[30] = 255;
        r[31] = 255;
        r[32] = 255;
    }
}
