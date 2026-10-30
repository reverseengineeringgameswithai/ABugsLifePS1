/* vector_remove_normal_component @ 0x80030c78 - short-typed variant, depth /2048. */
void vector_remove_normal_component(short *n, short *plane, short *out)
{
    int t = (n[0] * -plane[0] + n[1] * -plane[1] + n[2] * -plane[2]) / 2048;

    out[0] = (n[0] * t) / 131072 + plane[0];
    out[1] = (n[1] * t) / 131072 + plane[1];
    out[2] = (n[2] * t) / 131072 + plane[2];
}
