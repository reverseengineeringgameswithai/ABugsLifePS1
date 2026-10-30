/* contact_scatter_component_decode @ 0x800593e8 (340 B).
 *
 * contact_metadata_table_a stores four selector/value pairs per row. Selectors
 * 1..6 consume one byte from the script/random stream; all other selectors
 * return the stored value unchanged. The six cases below reproduce the retail
 * jump-table semantics through the shared return at 0x80059534. */

extern unsigned char *g_800822f4;

int contact_scatter_component_decode(int selector, int value)
{
    unsigned char random;

    switch (selector) {
    case 1:
        random = *g_800822f4++;
        return ((random & value) - (value >> 1)) << 3;
    case 2:
        random = *g_800822f4++;
        return (random & value) << 3;
    case 3:
        random = *g_800822f4++;
        return -(random & value) << 3;
    case 4:
        random = *g_800822f4++;
        return ((random & value) + ((value & 0xff00) >> 4)) << 3;
    case 5:
        random = *g_800822f4++;
        return ((random & value) - ((value & 0xff00) >> 4)) << 3;
    case 6:
        random = *g_800822f4++;
        return ((random & value) - (value >> 1)) << 4;
    default:
        return value;
    }
}
