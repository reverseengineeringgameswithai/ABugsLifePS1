#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    uint32_t streak;
    uint32_t progress;
    uint16_t latch;
    uint16_t fade;
    uint8_t flags;
} State;

enum { BONUS_SCENE=0x10, EARNED=0x20, UNLOCK=0x02, TARGET=5 };

static int register_qualifying_interaction(State *s, uint32_t scene) {
    uint32_t old;
    if ((s->flags & EARNED) != 0 || scene == BONUS_SCENE)
        return 0;
    old = s->streak;
    s->progress = old + 114;
    s->streak = old + 1;
    if (s->streak != TARGET)
        return 1;
    s->flags |= UNLOCK;
    s->latch = 6;
    s->fade = 30;
    s->streak = 0;
    return 2;
}

static void transition_reset(State *s) { s->streak = 0; }
static void require(int ok, const char *name) { if(!ok){fprintf(stderr,"FAIL %s\n",name);exit(1);}printf("PASS %s\n",name); }

int main(void) {
    State four={.streak=3};
    require(register_qualifying_interaction(&four,0x11)==1 && four.streak==4 && four.progress==117 && four.flags==0 && four.latch==0 && four.fade==0,"four_does_not_unlock");
    State five={.streak=4};
    require(register_qualifying_interaction(&five,0x11)==2 && five.streak==0 && five.progress==118 && five.flags==2 && five.latch==6 && five.fade==30,"five_unlocks_exactly");
    State earned={.streak=4,.progress=77,.latch=3,.fade=9,.flags=0x22};State earned_before=earned;
    require(register_qualifying_interaction(&earned,0x11)==0 && earned.streak==earned_before.streak && earned.progress==earned_before.progress && earned.latch==earned_before.latch && earned.fade==earned_before.fade && earned.flags==earned_before.flags,"earned_guard_is_side_effect_free");
    State bonus={.streak=4,.progress=88,.latch=2,.fade=7,.flags=2};State bonus_before=bonus;
    require(register_qualifying_interaction(&bonus,0x10)==0 && bonus.streak==bonus_before.streak && bonus.progress==bonus_before.progress && bonus.latch==bonus_before.latch && bonus.fade==bonus_before.fade && bonus.flags==bonus_before.flags,"bonus_scene_guard_is_side_effect_free");
    State reset={.streak=4};transition_reset(&reset);require(reset.streak==0,"shared_transition_reset_clears_streak");
    return 0;
}
