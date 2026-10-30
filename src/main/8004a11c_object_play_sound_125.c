/* plays sound id 125 for the actor (actor->field4 + 4). */
extern void play_sound(int id, int arg);

void object_play_sound_125(int *actor)
{
    play_sound(125, actor[1] + 4);
}
