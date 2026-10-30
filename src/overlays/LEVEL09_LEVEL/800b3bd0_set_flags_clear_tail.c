/* LEVEL09_LEVEL overlay @ 0x800b3bd0. Sets 21 stride-0x54 halfword flags
 * for the selected entry and clears the following flag.
 */
struct Obj800a6300 {
    char pad0[4];
    short index;
};

struct Entry80089f58 {
    char pad0[0x32];
    short flag;
    char pad1[0x20];
};

extern struct Obj800a6300 *D_800a6300[];
extern struct Entry80089f58 D_80089f58[];

void level09_set_flags_clear_tail(int *slot)
{
    int value = 1;
    struct Entry80089f58 *entry;
    int count;

    entry = &D_80089f58[D_800a6300[*slot]->index];
    for (count = 20; count >= 0; count--) {
        entry->flag = value;
        entry++;
    }
    entry->flag = 0;
}
