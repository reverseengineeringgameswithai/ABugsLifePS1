/* _SsInit @ 0x80067B10 - libsnd: program the SPU register file from two ROM init
 * tables, hand the voice count to sub_800699c8, then zero the 32 x 0x40-byte
 * sound-slot pool at 0x800B02B0 and reset three state globals.
 *   - 24 voices x 8 regs at 0x1F801C00 seeded from g_80080e80 (same 8 values per voice)
 *   - 16 control regs at 0x1F801D80 seeded from g_80080e90
 * Byte-exact needs: `table` hoisted before loop 1; loop 3 indexing its slot from
 * the counter (`g_800b02b0 + j * 16` - the address giv blocks GCC's down-count
 * reversal and strength-reduces to the +0x40 walking pointer); and the i/j
 * counter roles SWAPPED in loop 3 so register allocation lands as retail. */
typedef unsigned short u16;

extern u16 g_80080e80[];
extern u16 g_80080e90[];
extern int g_800b02b0[];
extern int g_800a7e18;
extern int g_8009edd8;
extern int g_80096d9c;
extern int sub_800699c8(int);

void _SsInit(void)
{
    u16 *dst;
    u16 *src;
    u16 *table;
    int *slot;
    int *p;
    int i;
    int j;

    dst = (u16 *)0x1F801C00;
    i = 0;
    table = g_80080e80;
    do {
        j = 0;
        src = table;
        do {
            *dst++ = *src++;
            j++;
        } while (j < 8);
        i++;
    } while (i < 24);

    dst = (u16 *)0x1F801D80;
    i = 0;
    src = g_80080e90;
    do {
        *dst++ = *src++;
        i++;
    } while (i < 16);

    sub_800699c8(24);

    j = 0;
    do {
        slot = g_800b02b0 + j * 16;
        i = 15;
        p = slot + 15;
        do {
            *p-- = 0;
            i--;
        } while (i >= 0);
        j++;
    } while (j < 32);

    g_800a7e18 = 0x3C;
    g_8009edd8 = 0;
    g_80096d9c = 0;
}
