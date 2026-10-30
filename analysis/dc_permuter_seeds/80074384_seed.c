extern char g_800890c8[];
int pad_direct_ptr_to_port(void *ptr)
{
    char *base = g_800890c8;
    int sz = 16, i;
    for (i = 0; i < 2; i++, base += 240, sz += 16) {
        if (ptr == base) return sz;
    }
    return 255;
}
