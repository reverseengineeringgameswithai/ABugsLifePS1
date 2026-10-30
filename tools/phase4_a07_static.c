/*
 * Phase 4 A07: verify the pristine directional-spin recognizer and replay the
 * operator movie's input history without running the emulator.
 *
 * This is an evidence guard, not matching game source. It reads the immutable
 * retail executable and an external Interpreter movie; it never writes either.
 */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    EXE_HEADER_SIZE = 0x800,
    EXE_LOAD_ADDRESS = 0x80010000,
    PAD_UP = 0x10,
    PAD_RIGHT = 0x20,
    PAD_DOWN = 0x40,
    PAD_LEFT = 0x80,
    PAD_OTHER = 0x10000,
};

typedef struct {
    uint32_t address;
    uint32_t word;
    const char *meaning;
} Anchor;

static const Anchor anchors[] = {
    {0x800481a8, 0x84842488, "read current pad"},
    {0x800481b0, 0x84422380, "read previous pad"},
    {0x800481cc, 0x306200f0, "direction-nibble gate"},
    {0x800482ac, 0x3c068007, "reference-table high half"},
    {0x800482b0, 0x24c67304, "reference table 0x80077304"},
    {0x800482b4, 0x3c078009, "history-ring high half"},
    {0x800482b8, 0x24e794d0, "history ring 0x800894d0"},
    {0x80048304, 0x24020008, "eight-match threshold"},
    {0x80048308, 0x14820029, "reject fewer than eight matches"},
    {0x8004831c, 0x30420080, "player+0x90 bit-0x80 gate"},
    {0x80048338, 0x24020078, "initial animation-13 SFX timer 120"},
    {0x80048340, 0xac222294, "store timer at 0x80082294"},
    {0x8004837c, 0x0c01069d, "call indexed attachment reset 0x80041a74"},
    {0x80048384, 0x2402000d, "animation 13"},
    {0x8004838c, 0xa420657a, "clear player+0x7a action lock"},
    {0x80048394, 0xac20655c, "clear player+0x5c carried offset"},
    {0x8004839c, 0xa02065a3, "clear player+0xa3 seed action"},
    {0x800483a4, 0xa4226588, "request animation 13"},
    {0x800483ac, 0xa420659e, "clear player+0x9e queued action"},
    {0x80046b38, 0x248494d0, "spawn obtains history ring"},
    {0x80046b40, 0x24060010, "spawn clears 16 history bytes"},
    {0x80046b5c, 0xa7800618, "spawn resets ring index"},
    {0x80046b60, 0xa7800502, "spawn resets inactivity counter"},
    {0x80056790, 0x28420040, "animation-13 first motion threshold"},
    {0x800567b4, 0x28420040, "animation-13 second motion threshold"},
    {0x800567c4, 0xa4226588, "retain animation 13 while moving"},
    {0x80056ee0, 0x8f8204fc, "read/decrement shared SFX timer"},
    {0x80056f3c, 0xaf8204fc, "random+60 SFX re-arm"},
    {0x80056f40, 0x0c014310, "call SFX helper 0x80050c40"},
};

static const uint16_t expected_sequence[8] = {
    PAD_UP, PAD_RIGHT, PAD_DOWN, PAD_LEFT,
    PAD_UP, PAD_RIGHT, PAD_DOWN, PAD_LEFT,
};

static uint32_t read_le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint16_t read_le16(const unsigned char *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static unsigned char *read_file(const char *path, size_t *size_out)
{
    FILE *fp = fopen(path, "rb");
    unsigned char *data;
    long size;

    if (fp == NULL) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        exit(2);
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (size = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fprintf(stderr, "%s: cannot size file\n", path);
        exit(2);
    }
    data = malloc((size_t)size + 1);
    if (data == NULL || fread(data, 1, (size_t)size, fp) != (size_t)size) {
        fprintf(stderr, "%s: cannot read file\n", path);
        exit(2);
    }
    fclose(fp);
    data[size] = 0;
    *size_out = (size_t)size;
    return data;
}

static size_t exe_offset(uint32_t address, size_t exe_size)
{
    uint64_t offset;

    if (address < EXE_LOAD_ADDRESS)
        return SIZE_MAX;
    offset = (uint64_t)EXE_HEADER_SIZE + address - EXE_LOAD_ADDRESS;
    return offset + 4 <= exe_size ? (size_t)offset : SIZE_MAX;
}

static int verify_exe(const unsigned char *exe, size_t size)
{
    size_t i;
    int errors = 0;
    unsigned table_refs = 0;
    unsigned ring_refs = 0;

    if (size != 471040 || memcmp(exe, "PS-X EXE", 8) != 0 ||
        read_le32(exe + 0x18) != EXE_LOAD_ADDRESS ||
        read_le32(exe + 0x1c) != size - EXE_HEADER_SIZE) {
        fprintf(stderr, "FAIL executable identity/header/size\n");
        errors++;
    }

    for (i = 0; i < sizeof(anchors) / sizeof(anchors[0]); i++) {
        size_t off = exe_offset(anchors[i].address, size);
        uint32_t got = off == SIZE_MAX ? 0 : read_le32(exe + off);
        if (got != anchors[i].word) {
            fprintf(stderr, "FAIL anchor %08" PRIx32 ": got %08" PRIx32
                    ", expected %08" PRIx32 " (%s)\n",
                    anchors[i].address, got, anchors[i].word,
                    anchors[i].meaning);
            errors++;
        }
    }

    for (i = EXE_HEADER_SIZE; i + 8 <= size; i += 4) {
        uint32_t a = read_le32(exe + i);
        uint32_t b = read_le32(exe + i + 4);
        if (a == 0x3c068007 && b == 0x24c67304)
            table_refs++;
        if (a == 0x3c078009 && b == 0x24e794d0)
            ring_refs++;
    }
    if (table_refs != 1 || ring_refs != 1) {
        fprintf(stderr, "FAIL pointer-pair uniqueness: table=%u ring=%u\n",
                table_refs, ring_refs);
        errors++;
    }

    {
        size_t off = exe_offset(0x80077304, size);
        printf("reference table:");
        for (i = 0; i < 8; i++) {
            uint16_t got = read_le16(exe + off + i * 2);
            printf(" %02x", got);
            if (got != expected_sequence[i])
                errors++;
        }
        printf("  (Up Right Down Left x2)\n");
    }

    printf("static anchors: %zu checked; table_refs=%u ring_refs=%u\n",
           sizeof(anchors) / sizeof(anchors[0]), table_refs, ring_refs);
    return errors;
}

static const char *find_before(const char *p, const char *end,
                               const char *needle)
{
    const char *found = strstr(p, needle);
    return found != NULL && found < end ? found : NULL;
}

static int bool_field(const char *begin, const char *end, const char *name)
{
    char needle[48];
    const char *p;

    snprintf(needle, sizeof(needle), "\"%s\"", name);
    p = find_before(begin, end, needle);
    if (p == NULL || (p = find_before(p, end, ":")) == NULL)
        return 0;
    p++;
    while (p < end && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n'))
        p++;
    return end - p >= 4 && memcmp(p, "true", 4) == 0;
}

static uint32_t frame_pad(const char *begin, const char *end)
{
    static const char *other_buttons[] = {
        "circle", "cross", "l1", "l2", "l3", "r1", "r2", "r3",
        "select", "square", "start", "triangle",
    };
    uint32_t pad = 0;
    size_t i;

    if (bool_field(begin, end, "up")) pad |= PAD_UP;
    if (bool_field(begin, end, "right")) pad |= PAD_RIGHT;
    if (bool_field(begin, end, "down")) pad |= PAD_DOWN;
    if (bool_field(begin, end, "left")) pad |= PAD_LEFT;
    for (i = 0; i < sizeof(other_buttons) / sizeof(other_buttons[0]); i++)
        if (bool_field(begin, end, other_buttons[i]))
            pad |= PAD_OTHER;
    return pad;
}

static uint32_t *parse_movie(const char *json, size_t size, size_t *count_out)
{
    const char *end = json + size;
    const char *p = strstr(json, "\"frames\"");
    uint32_t *pads = NULL;
    size_t count = 0;

    if (p == NULL || (p = strchr(p, '[')) == NULL) {
        fprintf(stderr, "FAIL movie frames array missing\n");
        exit(2);
    }
    while ((p = find_before(p, end, "\"frame\"")) != NULL) {
        const char *colon = find_before(p, end, ":");
        const char *next;
        char *number_end;
        unsigned long frame;
        uint32_t *grown;

        if (colon == NULL)
            break;
        frame = strtoul(colon + 1, &number_end, 10);
        if (number_end == colon + 1 || frame != count)
            break;
        next = find_before(number_end, end, "\"frame\"");
        grown = realloc(pads, (count + 1) * sizeof(*pads));
        if (grown == NULL) {
            fprintf(stderr, "FAIL movie allocation\n");
            exit(2);
        }
        pads = grown;
        pads[count++] = frame_pad(number_end, next != NULL ? next : end);
        p = next != NULL ? next : end;
    }
    *count_out = count;
    return pads;
}

static int is_cardinal(uint32_t pad)
{
    return pad == PAD_UP || pad == PAD_RIGHT ||
           pad == PAD_DOWN || pad == PAD_LEFT;
}

static int history_matches(const uint16_t ring[8], unsigned next)
{
    unsigned i;
    for (i = 0; i < 8; i++)
        if (ring[(next + i) & 7] != expected_sequence[i])
            return 0;
    return 1;
}

static int verify_movie(const uint32_t *pads, size_t count)
{
    uint16_t ring[8] = {0};
    uint32_t previous;
    unsigned next = 0;
    unsigned inactivity = 0;
    unsigned windows[8][2];
    unsigned window_count = 0;
    int open = 0;
    size_t relative_frame;

    if (count != 996) {
        fprintf(stderr, "FAIL movie frame count: %zu (expected 996)\n", count);
        return 1;
    }
    previous = pads[0];
    printf("accepted cardinals (player-update frame:value):");
    for (relative_frame = 1; relative_frame < count; relative_frame += 2) {
        uint32_t current = pads[relative_frame - 1];
        int accepted = current != previous && is_cardinal(current);
        int match;

        if (accepted) {
            ring[next] = (uint16_t)current;
            next = (next + 1) & 7;
            inactivity = 0;
            printf(" %zu:%02" PRIx32, relative_frame, current);
        } else {
            inactivity++;
            if (inactivity == 20) {
                ring[next] = 0;
                next = (next + 1) & 7;
                inactivity = 0;
            }
        }
        previous = current;
        match = history_matches(ring, next);
        if (match && !open) {
            if (window_count >= 8) {
                fprintf(stderr, "FAIL too many match windows\n");
                return 1;
            }
            windows[window_count][0] = (unsigned)relative_frame;
            open = 1;
        } else if (!match && open) {
            windows[window_count][1] = (unsigned)relative_frame - 2;
            window_count++;
            open = 0;
        }
    }
    if (open) {
        windows[window_count][1] = (unsigned)(count - 1);
        window_count++;
    }
    printf("\nmatch windows:");
    for (unsigned i = 0; i < window_count; i++)
        printf(" %u..%u", windows[i][0], windows[i][1]);
    printf("\n");

    if (window_count != 2 || windows[0][0] != 133 || windows[0][1] != 145 ||
        windows[1][0] != 209 || windows[1][1] != 247) {
        fprintf(stderr, "FAIL movie recognizer windows differ from retained runtime\n");
        return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *exe_path = argc > 1 ? argv[1] : "REBUILD/files/SCUS_942.88";
    const char *movie_path = argc > 2 ? argv[2] :
        "movies/Phase4/Interpreter/A07_spin.movie.json";
    unsigned char *exe;
    unsigned char *movie;
    uint32_t *pads;
    size_t exe_size, movie_size, frame_count;
    int errors;

    exe = read_file(exe_path, &exe_size);
    movie = read_file(movie_path, &movie_size);
    errors = verify_exe(exe, exe_size);
    pads = parse_movie((const char *)movie, movie_size, &frame_count);
    errors += verify_movie(pads, frame_count);
    free(pads);
    free(movie);
    free(exe);
    if (errors != 0) {
        fprintf(stderr, "A07 FAIL (%d errors)\n", errors);
        return 1;
    }
    printf("A07 PASS: pristine recognizer and positive movie agree\n");
    return 0;
}
