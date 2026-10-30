/* memclr_3 @ 0x80065e98 - word-granular zero fill: clear n words at dst. */
void memclr_3(int *dst, int n)
{
    int i;

    for (i = n - 1; i != -1; i--) {
        *dst = 0;
        dst++;
    }
}
