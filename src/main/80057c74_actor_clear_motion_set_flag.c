/* actor_clear_motion_set_flag @ 0x80057c74 */
void actor_clear_motion_set_flag(char *actor) {
    unsigned short flags = *(unsigned short *)(actor + 92);
    *(unsigned short *)(actor + 92) = (flags & 0xfffd) | 0x80;
    *(int *)(actor + 80) = (*(int *)(actor + 8) - 16384) & ~1;
}
