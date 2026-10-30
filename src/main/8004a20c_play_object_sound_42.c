/* play_object_sound_42 - play sound 42 on (actor->obj)+4. */
extern void play_sound(int id, void *obj);

void play_object_sound_42(void *actor)
{
    char *obj = *(char **)((char *)actor + 4);
    play_sound(42, obj + 4);
}
