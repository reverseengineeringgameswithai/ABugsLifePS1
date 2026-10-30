/* Phase 4 C14: pin the telescope/special-view state machine against the pristine EXE.
 *
 * The shared state variable 0x800824DC (gp+0x744) is owned by setpiece_spawn_manager
 * (0x8004D698). The sole pinned direct -1 producer is the kind-0x30 telescope
 * activation case inside the source dispatcher (0x80054554..). Lifecycle:
 *   0 idle -> -1 trigger -> -2 acknowledged -> 252 view countdown (-1 per manager call
 *   while goal latch 0x800823A0 is clear) -> 0 -> -120 return phase (+1 per call)
 *   -> -10 -> 0 idle.  Positive states 13/14 are setpiece-specific.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c14_telescope_static.c \
 *      -o /tmp/phase4_c14_telescope_static
 *   /tmp/phase4_c14_telescope_static REBUILD/files/SCUS_942.88
 *
 * Expected input SHA-256:
 *   1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum {
    EXE_HEADER_SIZE = 0x800,
    EXE_LOAD_VA = 0x80010000u
};

static uint8_t *image;
static size_t image_size;

static uint32_t read_u32(uint32_t va)
{
    size_t off;
    if (va < EXE_LOAD_VA) {
        fprintf(stderr, "va below load base: %08x\n", va);
        exit(2);
    }
    off = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (off + 4 > image_size) {
        fprintf(stderr, "va outside image: %08x\n", va);
        exit(2);
    }
    return (uint32_t)image[off] | ((uint32_t)image[off + 1] << 8) |
           ((uint32_t)image[off + 2] << 16) | ((uint32_t)image[off + 3] << 24);
}

struct pin {
    uint32_t pc;
    uint32_t word;
    const char *role;
};

/* Every instruction word verified against the retail image. */
static const struct pin pins[] = {
    /* telescope activation: kind-0x30 case in the source dispatcher */
    {0x80054554u, 0x3C028008u, "activation: lui for state read"},
    {0x80054558u, 0x8C4224DCu, "activation: read state 0x800824DC"},
    {0x80054560u, 0x1440000Fu, "activation: skip if already active"},
    {0x80054564u, 0x2402FFFFu, "activation: li -1 (the shared trigger)"},
    {0x8005456Cu, 0xAC3E23CCu, "activation: store telescope index 0x800823CC"},
    {0x80054574u, 0xAC2224DCu, "activation: state := -1"},
    {0x8005457Cu, 0xAC20652Cu, "activation: zero player vel X"},
    {0x80054584u, 0xAC206530u, "activation: zero player vel Y"},
    {0x8005458Cu, 0xAC206534u, "activation: zero player vel Z"},
    {0x80054594u, 0xA4206582u, "activation: zero grounded flag"},
    /* setpiece_spawn_manager 0x8004D698: the state-machine owner */
    {0x8004D738u, 0x2402FFFEu, "manager: li -2 (acknowledge)"},
    {0x8004D740u, 0xAC2224DCu, "manager: state := -2 after spawn"},
    {0x8004D76Cu, 0x240200FCu, "manager: li 252 (view-timer init)"},
    {0x8004D774u, 0xAC2224DCu, "manager: state := 252"},
    {0x8004D94Cu, 0x2402000Eu, "manager: li 14 (sensor state)"},
    {0x8004D954u, 0xAC2224DCu, "manager: state := 14 on 0x80082412 & 0xF000"},
    {0x8004D95Cu, 0x844223A0u, "manager: tick gate reads goal latch 0x800823A0"},
    {0x8004D978u, 0x2442FFFFu, "manager: countdown decrement"},
    {0x8004D980u, 0xAC2224DCu, "manager: store decremented state"},
    {0x8004D994u, 0x2402FF88u, "manager: li -120 (return-phase init)"},
    {0x8004D99Cu, 0xAC2224DCu, "manager: state := -120 at countdown 0"},
    {0x8004D9ACu, 0x2862FFF6u, "manager: slti state < -10"},
    {0x8004D9B4u, 0x24630001u, "manager: return-phase increment"},
    {0x8004D9BCu, 0xAC2324DCu, "manager: store incremented state"},
    {0x8004D9D0u, 0xAC2024DCu, "manager: state := 0 (idle) at -10"},
    /* external clears */
    {0x8005B324u, 0xAC2024DCu, "respawn tail: state := 0 (view cancelled on respawn)"},
    {0x8005B9D0u, 0xAC2024DCu, "scene init: state := 0"},
};

int main(int argc, char **argv)
{
    FILE *f;
    long end;
    size_t i, bad = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    f = fopen(argv[1], "rb");
    if (!f || fseek(f, 0, SEEK_END) != 0 || (end = ftell(f)) < 0 ||
        fseek(f, 0, SEEK_SET) != 0) {
        perror(argv[1]);
        return 2;
    }
    image_size = (size_t)end;
    image = malloc(image_size);
    if (!image || fread(image, 1, image_size, f) != image_size) {
        fprintf(stderr, "short read\n");
        return 2;
    }
    fclose(f);

    for (i = 0; i < sizeof(pins) / sizeof(pins[0]); i++) {
        uint32_t got = read_u32(pins[i].pc);
        if (got != pins[i].word) {
            fprintf(stderr, "MISMATCH %08" PRIx32 " (%s): got %08" PRIx32
                            " want %08" PRIx32 "\n",
                    pins[i].pc, pins[i].role, got, pins[i].word);
            bad++;
        }
    }
    free(image);
    if (bad) {
        fprintf(stderr, "%zu pin(s) failed\n", bad);
        return 1;
    }
    printf("C14 telescope state-machine pins: %zu/%zu OK\n",
           sizeof(pins) / sizeof(pins[0]), sizeof(pins) / sizeof(pins[0]));
    puts("STATE MACHINE 0x800824DC (owner setpiece_spawn_manager 0x8004D698):");
    puts("  0 idle -> -1 trigger (telescope 0x80054574 OR script) -> -2 ack");
    puts("  -> 252 view countdown (-1/call, gated on goal latch clear)");
    puts("  -> 0 -> -120 return (+1/call) -> -10 -> 0 idle; 13/14 setpiece states");
    return 0;
}
