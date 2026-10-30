/* clears a 16-bit field of the id-mapped 48-byte slot record. Meanings UNKNOWN. */
struct slot48 { short f; char pad[46]; };
extern short g_800a2080[];
extern struct slot48 g_800a7e74[];

void object_slot_clear_field(int id)
{
    short slot = g_800a2080[id];
    if (slot)
        g_800a7e74[slot].f = 0;
}
