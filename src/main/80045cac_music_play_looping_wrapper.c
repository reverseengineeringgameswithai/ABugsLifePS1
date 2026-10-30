extern int music_play_looping(int track);
int music_play_looping_wrapper(int track){
    char scratch[16]; (void)scratch;
    return music_play_looping(track - 2);
}
