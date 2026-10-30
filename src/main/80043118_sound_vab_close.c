/* closes a VAB by id then marks the gp handle global free (-1); no-op for negative ids. */
extern int sub_8006b0ac(int vabid);
extern short g_800821a8;

void sound_vab_close(int id)
{
    if (id >= 0) {
        sub_8006b0ac(id);
        g_800821a8 = -1;
    }
}
