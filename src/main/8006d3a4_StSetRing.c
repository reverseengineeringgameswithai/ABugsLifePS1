/* StSetRing @ 0x8006d3a4 - configure the streaming ring buffer and (re)start it. */
extern int g_800b0d10, g_800b3980;
extern void sub_8007094c(void);
void StSetRing(int ring, int count)
{
    g_800b0d10 = ring;
    g_800b3980 = count;
    sub_8007094c();
}
