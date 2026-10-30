/* seq_state_init_wrapper_one_arg @ 0x80068134 */
extern void seq_playback_state_init(int a, int b);

void seq_state_init_wrapper_one_arg(short id) {
    seq_playback_state_init(id, 0);
}
