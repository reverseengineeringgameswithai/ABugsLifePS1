/* ss_vab_set_transfer_mode - flag at 0x800814f8: mode 1 clears, else sets to 1. */
extern int g_800814f8;

void ss_vab_set_transfer_mode(int mode)
{
    if (mode == 1)
        g_800814f8 = 0;
    else
        g_800814f8 = 1;
}
