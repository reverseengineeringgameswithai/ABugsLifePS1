/* sets the id-mapped 48-byte slot record's 16-bit field to 6. Meanings UNKNOWN. */
struct slot48 { short f; char pad[46]; };
extern short g_800a2080[];
extern struct slot48 g_800a7e74[];

void object_slot_set_field_6(int id)
{
    short slot = g_800a2080[id];
    if (slot)
        g_800a7e74[slot].f = 6;
}
