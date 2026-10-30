/* music_play_once @ 0x80046ac0 (gp) — queue a one-shot streamed music id.
 * Clears the loop flag, stores the packed id, and defers to music_start.
 *   sw zero,g_800821c4(gp); sw a0,g_800821c8(gp); jal music_start */
extern int g_800821c4;   /* gp+0x42c: loop flag (0 = play once) */
extern int g_800821c8;   /* gp+0x430: packed music id */
extern int music_start(int);

void music_play_once(int id)
{
    g_800821c4 = 0;
    g_800821c8 = id;
    music_start(id);
}
