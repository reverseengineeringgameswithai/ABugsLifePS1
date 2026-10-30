/* Documentation-grade semantic reconstruction of the pristine pause shell.
 * Retail bytes and retained ASM remain authoritative; this is not a build unit.
 */

#include <stdint.h>

enum {
    PAD_START = 0x0008,
    PAD_UP = 0x0010,
    PAD_RIGHT = 0x0020,
    PAD_DOWN = 0x0040,
    PAD_LEFT = 0x0080,
    PAD_CROSS = 0x4000
};

typedef struct PauseState {
    volatile uint32_t *shell_state_8008216c;
    volatile uint16_t *previous_pad_800822e4;
    volatile uint32_t *entry_block_800822f8;
    volatile int16_t *mode_80082388;
    volatile int16_t *flow_state_800823a0;
    volatile uint16_t *current_pad_80082412;
    volatile int16_t *pause_8008224e;
    volatile int16_t *transition_timer_80082470;
    volatile int16_t *exit_option_80082472;
    volatile uint32_t *confirmation_800824bc;
    volatile uint16_t *player_flags_800a6590;
} PauseState;

static int rising(uint16_t current, uint16_t previous, uint16_t mask)
{
    return (current & mask) != 0 && (previous & mask) == 0;
}

/* gameplay_state_machine 0x8004ECD4, admission slice 0x8004F308..0x8004F3C4 */
static int pause_admitted(const PauseState *s)
{
    return rising(*s->current_pad_80082412, *s->previous_pad_800822e4,
                  PAD_START) &&
           *s->entry_block_800822f8 == 0 &&
           *s->shell_state_8008216c == 3 &&
           *s->mode_80082388 == 0x80;
}

static void enter_pause(PauseState *s)
{
    /* Retail calls 0x80045A60 and 0x80043500 first. */
    *s->pause_8008224e = 1;
    *s->exit_option_80082472 = 0;
    *s->confirmation_800824bc = 0;
    /* Retail dispatches SFX 0x1C. */
}

/* gameplay_frame_render 0x8004F480, input slice 0x8004F720..0x8004FA20. */
static void pause_menu_input(PauseState *s)
{
    uint16_t current = *s->current_pad_80082412;
    uint16_t previous = *s->previous_pad_800822e4;

    if (*s->confirmation_800824bc == 0) {
        if (rising(current, previous, PAD_DOWN))
            *s->exit_option_80082472 = 1;
        if (rising(current, previous, PAD_UP))
            *s->exit_option_80082472 = 0;
        if (rising(current, previous, PAD_CROSS) ||
            rising(current, previous, PAD_START)) {
            if (*s->exit_option_80082472 == 0) {
                *s->pause_8008224e = 0;       /* resume */
            } else {
                *s->confirmation_800824bc = 1; /* open yes/no */
            }
        }
        return;
    }

    if (rising(current, previous, PAD_LEFT) &&
        *s->confirmation_800824bc == 1)
        *s->confirmation_800824bc = 2;
    if (rising(current, previous, PAD_RIGHT) &&
        *s->confirmation_800824bc == 2)
        *s->confirmation_800824bc = 1;

    if (rising(current, previous, PAD_CROSS) ||
        rising(current, previous, PAD_START)) {
        if (*s->confirmation_800824bc == 1) {
            *s->exit_option_80082472 = 0;
            *s->confirmation_800824bc = 0;    /* cancel exit */
        } else {
            *s->pause_8008224e = 0;
            *s->flow_state_800823a0 = 5;
            *s->transition_timer_80082470 = 23;
            *s->player_flags_800a6590 |= 4;   /* exit-level handoff */
        }
    }
}

/* Outer scene-flow dispatch at 0x8004FEB8..0x8004FEE8. */
static void shell_frame(PauseState *s)
{
    if (*s->pause_8008224e == 0) {
        /* gameplay_state_machine(); player/actor/contact/plant/HUD updates */
    } else {
        /* gameplay_frame_render(); scene OT + pause menu + pause input */
        pause_menu_input(s);
    }
    /* 0x8003E104 still runs after either branch. */
}

/* Keep otherwise-unused documentation helpers visible to source indexers. */
void pause_shell_semantic_reference(PauseState *s)
{
    if (pause_admitted(s))
        enter_pause(s);
    shell_frame(s);
}
