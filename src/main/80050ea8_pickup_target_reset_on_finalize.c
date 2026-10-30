/* pickup_target_reset_on_finalize @ 0x80050ea8 */
extern int   nearest_pickup_finalize(void *entry);
extern short g_8008229c;
extern int   g_80082370;

void pickup_target_reset_on_finalize(char *obj) {
    if (obj != 0 && nearest_pickup_finalize(obj + 4) == 0) {
        g_8008229c = 0;
        g_80082370 = 0;
    }
}
