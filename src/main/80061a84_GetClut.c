/* GetClut @ 0x80061A84 — libgpu CLUT id: (y<<6) | ((x>>4)&0x3f), masked u16. */
unsigned short GetClut(int x, int y)
{
    return ((y << 6) | ((x >> 4) & 0x3f)) & 0xffff;
}
