/* actor_index_conditional_store - table lookup + bounds-gated store. Fields partly UNKNOWN. */
extern int *g_800a6300[];

void actor_index_conditional_store(char *a0, int idx, int slot)
{
    char *p = (char *)g_800a6300[(short)idx];

    if (p == 0)
        return;
    if (*(short *)(p + 2) < (short)slot)
        return;
    *(int *)(p + (short)slot * 4 + 8) = *(int *)(a0 + 8) + (int)a0;
}
