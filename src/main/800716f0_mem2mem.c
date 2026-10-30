/* mem2mem @ 0x800716f0 - copy n words from src to dst. */
void mem2mem(int *dst, int *src, unsigned int n)
{
    unsigned int i;

    for (i = 0; i < n; i++)
        *dst++ = *src++;
}
