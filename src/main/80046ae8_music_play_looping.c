/* music_play_looping @ 0x80046ae8 (gp) — queue a looping streamed music id.
 * Sets the loop flag, stores the packed id, and defers to music_start.
 *   li v0,1; sw v0,g_800821c4(gp); sw a0,g_800821c8(gp); jal music_start */
extern int g_800821c4;   /* gp+0x42c: loop flag (1 = loop) */
extern int g_800821c8;   /* gp+0x430: packed music id */
extern int music_start(int);

void music_play_looping(int id)
{
    g_800821c4 = 1;
    g_800821c8 = id;
    music_start(id);
}
