/* music_play_once_wrapper - play track (id-2); reserves a 16-byte scratch (40B frame). */
extern void music_play_once(int id);

void music_play_once_wrapper(int id)
{
    volatile int scratch[4];
    music_play_once(id - 2);
}
