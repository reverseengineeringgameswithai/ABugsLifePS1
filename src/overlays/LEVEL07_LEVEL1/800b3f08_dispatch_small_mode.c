/* LEVEL07_LEVEL1 overlay @ 0x800b3f08. Dispatches values below 13 to
 * sub_800b3b54 with a small mode derived from the input.
 */
extern void sub_800b3b54(int value, int mode);

void level07_level1_dispatch_small_mode(int value)
{
    if (value < 13) {
        int mode;

        mode = (value < 4) * 2;
        if (value < 2) {
            mode = 5;
        }
        sub_800b3b54(value, mode);
    }
}
