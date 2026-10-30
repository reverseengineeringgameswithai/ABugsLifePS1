/* sign-extends two short args and forwards to seq_playback_state_init. */
extern void seq_playback_state_init(short a, short b);

void seq_state_init_wrapper_two_arg(short a, short b)
{
    seq_playback_state_init(a, b);
}
