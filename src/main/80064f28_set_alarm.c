/* set_alarm @ 0x80064f28 - arm an alarm 0xf0 ticks ahead of the current counter. */
extern int sub_800651d0(int a);
extern int g_8007fce0, g_8007fce4;
void set_alarm(void)
{
    g_8007fce0 = sub_800651d0(-1) + 0xf0;
    g_8007fce4 = 0;
}
