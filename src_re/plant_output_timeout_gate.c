#include <stdint.h>

/* Retail addresses and offsets confirmed for SCUS-94288. */
#define A13_NEAREST_ELIGIBLE_ACTOR (*(void *volatile *)0x8008242cu)
#define A13_PLANT_OUTPUT_TIMER (*(volatile int32_t *)0x800824a4u)
#define A13_BROWN_SELECTOR (*(volatile uint8_t *)0x800a6598u)

typedef struct A13ActorView {
  uint8_t pad_00[0x04];
  int32_t x;
  int32_t y;
  int32_t z;
  uint8_t pad_10[0x30];
  uint32_t state;
  uint8_t pad_44[0x18];
  uint16_t flags;
  uint8_t pad_5e[0x22];
  void *descriptor;
} A13ActorView;

/*
 * The owner beginning at 0x80047284 clears the latch every gameplay tick,
 * then scans the actor list. A candidate must have actor+0x5c bit 0x20 set,
 * actor+0x40 not equal to 4, and squared distance below 0x57e40. The closest
 * candidate is stored at 0x8008242c. A separate direct path can also store an
 * actor at 0x80047398.
 *
 * The wrap movie produced two candidates, 0x800a0854 and 0x800a08d8. Both
 * were state 3, flags 0x4031, and referenced descriptors whose +0x0e color
 * byte was 0 (brown).
 */

/* Exact control flow of 0x80047558..0x80047588. */
static int a13_tick_plant_output_timer_model(void) {
  if (A13_PLANT_OUTPUT_TIMER <= 0)
    return 0;

  if (A13_NEAREST_ELIGIBLE_ACTOR == 0)
    A13_PLANT_OUTPUT_TIMER--;

  return A13_PLANT_OUTPUT_TIMER == 0;
}

/* Exact normalization performed on each selector when the timer expires. */
static uint8_t a13_normalize_selector(uint8_t selector) {
  uint8_t maximum = selector & 0x0fu;
  return (uint8_t)((maximum << 4) | maximum);
}

void a13_timeout_expiry_model(void) {
  if (!a13_tick_plant_output_timer_model())
    return;

  A13_BROWN_SELECTOR = a13_normalize_selector(A13_BROWN_SELECTOR);
  /* Retail continues over the other four selector bytes and emits event -16
   * once if at least one selector changed. */
}
