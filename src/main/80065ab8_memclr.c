/* memclr @ 0x80065ab8 - word-granular zero fill: clear n words at dst. */
void memclr(int *dst, int n)
{
    int i;

    for (i = n - 1; i != -1; i--) {
        *dst = 0;
        dst++;
    }
}
