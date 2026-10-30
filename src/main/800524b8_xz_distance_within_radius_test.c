/* xz_distance_within_radius_test - squared XZ distance < r*r (>>8 fixed point). */
int xz_distance_within_radius_test(int *a, int *b, int r)
{
    int dx = (a[0] - b[0]) >> 8;
    int dz = (a[2] - b[2]) >> 8;
    return (dx * dx + dz * dz) < (r * r);
}
