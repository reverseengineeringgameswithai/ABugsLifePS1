/* pad_reset_wait_delay - clear a hw at *g_80080e6c[5], spin a countdown, return 0. */
extern short *g_80080e6c;

int pad_reset_wait_delay(void)
{
    volatile int i[3];

    ((volatile short *)g_80080e6c)[5] = 0;
    i[0] = 10;
    i[0] = i[0] - 1;
    while (i[0] != -1)
        i[0] = i[0] - 1;
    return 0;
}
