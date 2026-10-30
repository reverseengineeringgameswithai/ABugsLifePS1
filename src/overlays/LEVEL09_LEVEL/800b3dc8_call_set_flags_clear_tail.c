/* LEVEL09_LEVEL overlay @ 0x800b3dc8. Thin wrapper around the neighboring
 * overlay routine at 0x800b3bd0.
 */
extern void sub_800b3bd0(void);

void level09_call_set_flags_clear_tail(void)
{
    sub_800b3bd0();
}
