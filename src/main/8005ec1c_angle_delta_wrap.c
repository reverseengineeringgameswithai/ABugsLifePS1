/* angle_delta_wrap - wrap (b-a) into (-2048,2048] mod 4096. */
short angle_delta_wrap(short *a, short *b)
{
    int d;
    register int aa asm("$4");
    int q;
    d = *b - *a;
    if (d >= 0)
        q = d;
    else
        q = d + 4095;
    q = (q >> 12) << 12;
    d -= q;
    if ((short)d < 2049)
        aa = d;
    else
        aa = d - 4096;
    d = aa;
    if ((short)d < -2048)
        aa = d + 4096;
    return (short)aa;
}
