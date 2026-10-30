/* GetTPage @ 0x80061a48 - pack a texture-page attribute id. */
int GetTPage(int tp, int abr, int x, int y)
{
    return ((tp & 3) << 7) | ((abr & 3) << 5) | ((y & 0x100) >> 4)
         | ((x & 0x3ff) >> 6) | ((y & 0x200) << 2);
}
