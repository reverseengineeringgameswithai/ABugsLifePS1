/* binds an animation sequence to an actor via descriptor table 0x80077e28. Fields partially UNKNOWN. */
extern unsigned char *g_80077e28[];

void actor_set_anim_sequence(char *actor, int frame, int seq)
{
    unsigned char *desc;

    *(int *)(actor + 68) = frame;
    desc = g_80077e28[seq];
    *(unsigned char **)(actor + 76) = desc;
    *(int *)(actor + 64) = desc[0] << 16;
}
