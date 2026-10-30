/* actor_turn_toward_player @ 0x8004a234 - rotate the actor's sub-object heading
 * (field +20) 1/16 of the way toward the player's direction each call. */
extern int atan2_heading(int dx, int dz);
extern int g_800a6500;   /* player x */
extern int g_800a6508;   /* player z */

void actor_turn_toward_player(int *actor)
{
    int *s = (int *)actor[1];
    int dx = s[1] - g_800a6500;
    int dz = s[3] - g_800a6508;
    int target = atan2_heading(dx, dz);
    int cur = s[5];
    int delta = (target - cur + 2048) & 0xfff;
    int step;

    if (delta < 2048) {
        step = delta >> 4;
    } else {
        delta = delta - 4096;
        step = delta >> 4;
    }
    s[5] = (cur + step) & 0xfff;
}
