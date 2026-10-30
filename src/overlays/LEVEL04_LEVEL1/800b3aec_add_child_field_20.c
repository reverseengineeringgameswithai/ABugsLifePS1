/* LEVEL04_LEVEL1 overlay @ 0x800b3aec. Adds 0x20 to a halfword field reached
 * through the resident pointer at 0x80082508.
 */
struct Obj80082508Child {
    char pad0[0xc];
    unsigned short field_c;
};

struct Obj80082508 {
    char pad0[0x10];
    struct Obj80082508Child *child;
};

extern struct Obj80082508 *g_80082508;

void level04_level1_add_child_field_20(void)
{
    g_80082508->child->field_c += 0x20;
}
