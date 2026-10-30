/* clears three 16-bit gp-relative state words. Field meanings UNKNOWN (byte-match only). */
extern short g_80082298;
extern short g_80082290;
extern short g_800824e2;

void gp_state_clear_three_shorts(void)
{
    g_80082298 = 0;
    g_80082290 = 0;
    g_800824e2 = 0;
}
