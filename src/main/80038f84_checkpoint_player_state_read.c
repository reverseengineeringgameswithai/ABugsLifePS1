/* checkpoint_player_state_read @ 0x80038f84 — for a valid record (flag byte==1),
 * follow the record's pointer and test its s16 field[1] against -3900.
 * The `if (ok) return expr; return 0;` shape folds the return-0 into the bne
 * delay slot, matching the retail schedule.
 *   if (*flag != 1) return 0; return rec[idx].ptr[1] < -3900; */
struct cp_rec { short *ptr; char pad[16]; };   /* 20-byte stride */
extern struct cp_rec g_80090564[];

int checkpoint_player_state_read(int idx, unsigned char *flag)
{
    if (*flag == 1)
        return g_80090564[idx].ptr[1] < -3900;
    return 0;
}
