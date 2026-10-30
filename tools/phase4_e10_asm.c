#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char *text;
    uint32_t pc;
} Instruction;

typedef struct {
    Instruction *items;
    size_t count;
    size_t capacity;
} Listing;

static void die(const char *message)
{
    fprintf(stderr, "phase4_e10_asm: %s\n", message);
    exit(2);
}

static void *resize(void *pointer, size_t size)
{
    pointer = realloc(pointer, size);
    if (!pointer)
        die("out of memory");
    return pointer;
}

static int is_instruction(const char *line)
{
    while (isspace((unsigned char)*line))
        line++;
    if (!*line || *line == '#' || strchr(line, ':'))
        return 0;
    if (*line == '.' && strncmp(line, ".word", 5))
        return 0;
    return 1;
}

static Listing load_listing(const char *path, uint32_t base)
{
    FILE *file = fopen(path, "rb");
    Listing listing = {0};
    char *line = NULL;
    size_t line_capacity = 0;
    ssize_t line_size;
    uint32_t pc = base;
    if (!file) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        exit(2);
    }
    while ((line_size = getline(&line, &line_capacity, file)) >= 0) {
        if (!is_instruction(line))
            continue;
        if (listing.count == listing.capacity) {
            listing.capacity = listing.capacity ? listing.capacity * 2 : 512;
            listing.items = resize(listing.items,
                                   listing.capacity * sizeof(*listing.items));
        }
        listing.items[listing.count].text = malloc((size_t)line_size + 1);
        if (!listing.items[listing.count].text)
            die("out of memory");
        memcpy(listing.items[listing.count].text, line,
               (size_t)line_size + 1);
        listing.items[listing.count].pc = pc;
        listing.count++;
        pc += 4;
    }
    free(line);
    fclose(file);
    return listing;
}

static int contains(const Listing *listing, const char *needle)
{
    for (size_t i = 0; i < listing->count; i++)
        if (strstr(listing->items[i].text, needle))
            return 1;
    return 0;
}

static void inspect(const char *path, uint32_t base, uint32_t target,
                    const char *const *required, size_t required_count)
{
    Listing listing = load_listing(path, base);
    size_t target_index = SIZE_MAX;
    int passed = 1;

    for (size_t i = 0; i < listing.count; i++)
        if (listing.items[i].pc == target)
            target_index = i;
    printf("=== %s base=0x%08x target=0x%08x instructions=%zu ===\n",
           path, base, target, listing.count);
    if (target_index == SIZE_MAX) {
        puts("TARGET_NOT_MAPPED");
        passed = 0;
    } else {
        size_t low = target_index > 12 ? target_index - 12 : 0;
        size_t high = target_index + 14 < listing.count ?
                      target_index + 14 : listing.count - 1;
        for (size_t i = low; i <= high; i++)
            printf("%c 0x%08x %s", i == target_index ? '*' : ' ',
                   listing.items[i].pc, listing.items[i].text);
    }
    for (size_t i = 0; i < required_count; i++) {
        int found = contains(&listing, required[i]);
        printf("require[%zu]=%s %s\n", i, required[i],
               found ? "PASS" : "FAIL");
        passed &= found;
    }
    printf("semantic_guard=%s\n", passed ? "PASS" : "FAIL");

    for (size_t i = 0; i < listing.count; i++)
        free(listing.items[i].text);
    free(listing.items);
}

int main(void)
{
    static const char *player_required[] = {
        "jal 0x8004a700", "lh\t$v0,126($s1)", "lh\t$v0,146($s1)"
    };
    static const char *actor_required[] = {
        "jal 0x8004a700", "ori\t$v0,$v0,0x1000",
        "lh\t$s0,26004($s0)"
    };
    static const char *contact_required[] = {
        "jal 0x8004a700", "slti\t$v0,$s4,64",
        "subu\t$a0,$v1,$a0", "subu\t$a1,$v0,$a1"
    };
    static const char *damage_required[] = {
        "addiu\t$v1,$v1,-1", "sh\t$v1,26004($at)",
        "addiu\t$v1,$zero,-45", "addiu\t$v0,$zero,45"
    };
    static const char *respawn_required[] = {
        "sw\t$a2,0($a1)", "sh\t$v0,26004($at)",
        "sb\t$a2,26016($at)", "jal 0x8004dc0c"
    };

    inspect("asm/hand_written/80048138_player_vertical_update.s",
            0x80048138, 0x80049740, player_required,
            sizeof(player_required) / sizeof(player_required[0]));
    inspect("asm/hand_written/8004abf4_proximity_updater.s",
            0x8004abf4, 0x8004b4a0, actor_required,
            sizeof(actor_required) / sizeof(actor_required[0]));
    inspect("asm/hand_written/800586b0_contact_walker.s",
            0x800586b0, 0x80058a48, contact_required,
            sizeof(contact_required) / sizeof(contact_required[0]));
    inspect("asm/hand_written/8004a700_resident_level_transition_initiator.s",
            0x8004a700, 0x8004a880, damage_required,
            sizeof(damage_required) / sizeof(damage_required[0]));
    inspect("asm/hand_written/8005b134_respawn_transition_state_handler.s",
            0x8005b134, 0x8005b31c, respawn_required,
            sizeof(respawn_required) / sizeof(respawn_required[0]));
    return 0;
}
