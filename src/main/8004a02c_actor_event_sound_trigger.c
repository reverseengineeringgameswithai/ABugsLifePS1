/* actor_event_sound_trigger - sub state 0 & type 22/10 -> sound 38; state 1 -> sound 26. */
extern void play_sound(int id, void *obj);

struct sub {
    unsigned char pad[0x44];
    int state;
};
struct actor {
    short type;
    short pad;
    struct sub *sub;
};

void actor_event_sound_trigger(struct actor *a)
{
    struct sub *s = a->sub;

    if (s->state == 0) {
        short t = a->type;
        if (t == 22 || t == 10)
            play_sound(38, (char *)s + 4);
    }
    if (s->state == 1)
        play_sound(26, (char *)s + 4);
}
