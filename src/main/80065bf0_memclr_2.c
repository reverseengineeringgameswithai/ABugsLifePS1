/* memclr_2 @ 0x80065bf0 - word-granular zero fill: clear n words at dst. */
void memclr_2(int *dst, int n)
{
    int i;

    for (i = n - 1; i != -1; i--) {
        *dst = 0;
        dst++;
    }
}
