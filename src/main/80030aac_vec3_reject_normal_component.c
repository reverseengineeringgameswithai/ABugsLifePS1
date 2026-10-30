/* vec3_reject_normal_component @ 0x80030aac - short-typed plane/out variant of
 * vector_project_onto_plane (depth term /1024). */
void vec3_reject_normal_component(short *n, short *plane, short *out)
{
    int t = (n[0] * -plane[0] + n[1] * -plane[1] + n[2] * -plane[2]) / 1024;

    out[0] = (n[0] * t) / 131072 + plane[0];
    out[1] = (n[1] * t) / 131072 + plane[1];
    out[2] = (n[2] * t) / 131072 + plane[2];
}
