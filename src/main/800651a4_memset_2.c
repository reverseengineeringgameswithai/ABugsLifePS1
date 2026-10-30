/* memset_2 @ 0x800651a4 - byte fill: write c to n bytes at dst. */
void memset_2(char *dst, int c, int n)
{
    int i;

    for (i = n - 1; i != -1; i--) {
        *dst = c;
        dst++;
    }
}
