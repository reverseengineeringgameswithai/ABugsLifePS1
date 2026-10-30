/* actor_sound40_on_low_state - if obj(+0x44)<2 play sound 40 on obj+4. */
extern void play_sound(int id, void *obj);

void actor_sound40_on_low_state(void *actor)
{
    char *obj = *(char **)((char *)actor + 4);
    if (*(int *)(obj + 0x44) < 2)
        play_sound(40, obj + 4);
}
