/* spawn_fx_object - clamp the signed 16-bit field at *p. */
void spawn_fx_object(short *p)
{
    short x = *p;

    if (x >= 0xc00)
        *p = (short)(0x1000 - x);
    else if (x >= 0x401)
        *p = 0x400;

    if (*p == 0)
        *p = 0x40;
}
