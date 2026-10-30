/* vec3_project_point_onto_plane @ 0x80030b98 - like vector_project_onto_plane but
 * the depth term divides by 2048 instead of 1024. */
void vec3_project_point_onto_plane(short *n, int *plane, int *out)
{
    int t = (n[0] * -plane[0] + n[1] * -plane[1] + n[2] * -plane[2]) / 2048;

    out[0] = (n[0] * t) / 131072 + plane[0];
    out[1] = (n[1] * t) / 131072 + plane[1];
    out[2] = (n[2] * t) / 131072 + plane[2];
}
