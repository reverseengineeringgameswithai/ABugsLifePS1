/* pass2_object_transform_update (gp) - stamp attr + write 3-word transform for object idx. */
struct attr_rec { unsigned short h; char pad[14]; };

extern int **g_80082338;
extern struct attr_rec g_80091216[];

void pass2_object_transform_update(int idx, int x, int y, int z)
{
    int *table = (int *)g_80082338;
    int *obj = (int *)table[idx + 1];
    if (obj == 0)
        return;
    if (table[0] < idx)
        return;
    *(short *)((char *)obj + 14) = g_80091216[idx].h;
    {
        int *sub = (int *)((int *)table[idx + 1])[4];
        int *dst = (int *)sub[6];
        dst[0] = x;
        dst[1] = y;
        dst[2] = z;
    }
}
