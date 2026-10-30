/* pad_direct_port_to_info @ 0x800743bc - select the info block for a port slot. */
extern char g_800890c8[];
void *pad_direct_port_to_info(int slot)
{
    char *p = g_800890c8;
    if (slot & 0xf0)
        p += 240;
    return p;
}
