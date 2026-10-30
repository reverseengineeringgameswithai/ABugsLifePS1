/* vector_project_onto_plane @ 0x800309cc - project plane-point onto the plane
 * whose (short) normal is n; out = plane + n * (-dot(n,plane)/1024) / 131072. */
void vector_project_onto_plane(short *n, int *plane, int *out)
{
    int t = (n[0] * -plane[0] + n[1] * -plane[1] + n[2] * -plane[2]) / 1024;

    out[0] = (n[0] * t) / 131072 + plane[0];
    out[1] = (n[1] * t) / 131072 + plane[1];
    out[2] = (n[2] * t) / 131072 + plane[2];
}
