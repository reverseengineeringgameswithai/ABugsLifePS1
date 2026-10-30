/* _spu_Fw1ts @ 0x8006c344 - SPU write-settle busy-wait: spin 0x3c times,
 * scaling a throwaway counter by 13 each pass (volatile locals keep the
 * delay loop from being optimised away). */
void _spu_Fw1ts(void)
{
    volatile int i;
    volatile int x;
    x = 13;
    i = 0;
    while (i < 0x3c) {
        x = x * 13;
        i++;
    }
}
