/* seed_plant_dande_seed_plant_min_glue - squared 3D distance < r*r (>>8 fixed point). */
int seed_plant_dande_seed_plant_min_glue(int *a, int *b, int r)
{
    int dx = (a[0] - b[0]) >> 8;
    int dy = (a[1] - b[1]) >> 8;
    int dz = (a[2] - b[2]) >> 8;
    return (dx * dx + dy * dy + dz * dz) < (r * r);
}
