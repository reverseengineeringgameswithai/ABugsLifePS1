/* scans a 16-entry table of 12-byte records at 0x8009165A, returns first tag==-1, else -1. */
struct slot { short tag; char pad[10]; };
extern struct slot g_8009165a[16];

int find_free_slot_16entry(void)
{
    int i;
    for (i = 0; i < 16; i++)
        if (g_8009165a[i].tag == -1)
            return i;
    return -1;
}
