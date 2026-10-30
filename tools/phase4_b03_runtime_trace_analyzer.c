#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MOVIE_FRAMES = 819, INITIAL_FRAME = 67812, MAX_ACCESS = 1024 };

typedef struct {
    int have_vx, have_vz;
    int32_t vx, vz;
} Steering;

typedef struct {
    int up, down, left, right, lx, ly, rx, ry;
} Input;

typedef struct {
    int64_t frame, cycle;
    uint32_t pc, address;
    int width, old_value, new_value;
} Access;

typedef struct {
    int64_t frame, cycle;
    char pc[24], sp[24], hex[400];
} EndState;

static void die(const char *what)
{
    fprintf(stderr, "%s: %s\n", what, strerror(errno));
    exit(1);
}

static int split(char *line, char **field, int max)
{
    int n = 0;
    char *cursor = line;
    while (n < max && (field[n] = strsep(&cursor, "\t\n")) != NULL)
        n++;
    return n;
}

static uint32_t hex32(const char *text)
{
    if (!text || text[0] == '-')
        return 0;
    return (uint32_t)strtoul(text, NULL, 0);
}

static int64_t dec64(const char *text)
{
    return strtoll(text, NULL, 10);
}

static int bool_text(const char *text)
{
    return !strcmp(text, "true") || !strcmp(text, "1");
}

static unsigned nibble(char c)
{
    if (c >= '0' && c <= '9') return (unsigned)(c - '0');
    if (c >= 'a' && c <= 'f') return (unsigned)(c - 'a' + 10);
    if (c >= 'A' && c <= 'F') return (unsigned)(c - 'A' + 10);
    return 0;
}

static uint32_t le32(const char *hex, size_t offset)
{
    uint32_t result = 0;
    for (unsigned i = 0; i < 4; i++) {
        size_t at = (offset + i) * 2;
        unsigned byte = (nibble(hex[at]) << 4) | nibble(hex[at + 1]);
        result |= byte << (i * 8);
    }
    return result;
}

static uint16_t le16(const char *hex, size_t offset)
{
    size_t at = offset * 2;
    unsigned lo = (nibble(hex[at]) << 4) | nibble(hex[at + 1]);
    unsigned hi = (nibble(hex[at + 2]) << 4) | nibble(hex[at + 3]);
    return (uint16_t)(lo | (hi << 8));
}

static EndState read_end(const char *path)
{
    EndState out = {0};
    FILE *fp = fopen(path, "r");
    char line[1024], *f[5];
    if (!fp) die(path);
    if (!fgets(line, sizeof(line), fp) || split(line, f, 5) != 5) {
        fprintf(stderr, "bad end state: %s\n", path);
        exit(1);
    }
    out.frame = dec64(f[0]);
    out.cycle = dec64(f[1]);
    snprintf(out.pc, sizeof(out.pc), "%s", f[2]);
    snprintf(out.sp, sizeof(out.sp), "%s", f[3]);
    snprintf(out.hex, sizeof(out.hex), "%s", f[4]);
    fclose(fp);
    return out;
}

static int read_access(const char *path, Access out[MAX_ACCESS])
{
    FILE *fp = fopen(path, "r");
    char line[1024], *f[7];
    int n = 0;
    if (!fp) die(path);
    while (n < MAX_ACCESS && fgets(line, sizeof(line), fp)) {
        if (split(line, f, 7) != 7) continue;
        out[n].frame = dec64(f[0]);
        out[n].cycle = dec64(f[1]);
        out[n].pc = hex32(f[2]);
        out[n].address = hex32(f[3]);
        out[n].width = atoi(f[4]);
        out[n].old_value = atoi(f[5]);
        out[n].new_value = atoi(f[6]);
        n++;
    }
    fclose(fp);
    return n;
}

int main(int argc, char **argv)
{
    if (argc != 7) {
        fprintf(stderr, "usage: %s TRACE GROUND LATCH MOVIE CONTROL INSTRUMENTED\n", argv[0]);
        return 2;
    }
    Steering steering[MOVIE_FRAMES] = {{0}};
    Input inputs[MOVIE_FRAMES] = {{0}};
    Access ground[MAX_ACCESS], latch[MAX_ACCESS];
    int ground_n, latch_n;
    int64_t first_active = -1, last_active = -1;
    int64_t first_vy_frame = -1, first_terminal = -1;
    int latch_updates = 0, vy_stores = 0, terminal_updates = 0;
    int launch_stores = 0, latch_exec_stores = 0, state5_to6 = 0;
    int64_t grounded_latch_release = -1;
    uint32_t grounded_latch_value = 0;
    int32_t first_vy = 0, min_vy = INT32_MAX, max_vy = INT32_MIN;
    int trace_events = 0;
    char line[2048], *f[14];
    FILE *fp = fopen(argv[1], "r");
    if (!fp) die(argv[1]);
    while (fgets(line, sizeof(line), fp)) {
        if (split(line, f, 14) != 14) continue;
        int64_t frame = dec64(f[0]);
        int movie_frame = (int)(frame - INITIAL_FRAME);
        uint32_t pc = hex32(f[2]);
        uint32_t v0 = hex32(f[4]), v1 = hex32(f[5]);
        trace_events++;
        if (pc == 0x8005c848u && (int32_t)v0 == -4096) launch_stores++;
        if (pc == 0x8005c8bcu && v0 == 11) latch_exec_stores++;
        if (pc == 0x800486e4u && v1 == 11) {
            if (first_active < 0) first_active = frame;
            last_active = frame;
            latch_updates++;
        }
        if (pc == 0x800486f4u && v1 == 11 && v0 != 0) {
            grounded_latch_release = frame;
            grounded_latch_value = v0;
        }
        if (pc == 0x8004871cu || pc == 0x80048728u) {
            int32_t value = (int32_t)v0;
            if (first_vy_frame < 0) {
                first_vy_frame = frame;
                first_vy = value;
            }
            if (value < min_vy) min_vy = value;
            if (value > max_vy) max_vy = value;
            if (value == 350) {
                if (first_terminal < 0) first_terminal = frame;
                terminal_updates++;
            }
            vy_stores++;
        }
        if (pc == 0x80048d64u) state5_to6++;
        if (movie_frame >= 0 && movie_frame < MOVIE_FRAMES) {
            if (pc == 0x80049524u) {
                steering[movie_frame].have_vx = 1;
                steering[movie_frame].vx = (int32_t)v0;
            } else if (pc == 0x80049540u) {
                steering[movie_frame].have_vz = 1;
                steering[movie_frame].vz = (int32_t)v0;
            }
        }
    }
    fclose(fp);

    fp = fopen(argv[4], "r");
    if (!fp) die(argv[4]);
    while (fgets(line, sizeof(line), fp)) {
        char *m[9];
        if (split(line, m, 9) != 9) continue;
        int index = atoi(m[0]);
        if (index < 0 || index >= MOVIE_FRAMES) continue;
        inputs[index].up = bool_text(m[1]);
        inputs[index].down = bool_text(m[2]);
        inputs[index].left = bool_text(m[3]);
        inputs[index].right = bool_text(m[4]);
        inputs[index].lx = atoi(m[5]);
        inputs[index].ly = atoi(m[6]);
        inputs[index].rx = atoi(m[7]);
        inputs[index].ry = atoi(m[8]);
    }
    fclose(fp);

    ground_n = read_access(argv[2], ground);
    latch_n = read_access(argv[3], latch);
    EndState control = read_end(argv[5]);
    EndState instrumented = read_end(argv[6]);
    int same_cycle = control.cycle == instrumented.cycle;
    int same_frame = control.frame == instrumented.frame;
    int same_pc = !strcmp(control.pc, instrumented.pc);
    int same_sp = !strcmp(control.sp, instrumented.sp);
    int same_player = !strcmp(control.hex, instrumented.hex);

    int direction_frames = 0, analog_frames = 0, paired = 0;
    int nonzero_vx = 0, nonzero_vz = 0, changed = 0, have_previous = 0;
    int32_t min_vx = INT32_MAX, max_vx = INT32_MIN;
    int32_t min_vz = INT32_MAX, max_vz = INT32_MIN;
    int32_t previous_vx = 0, previous_vz = 0;
    for (int i = 0; i < MOVIE_FRAMES; i++) {
        int64_t frame = INITIAL_FRAME + i;
        if (first_active < 0 || frame < first_active || frame > last_active) continue;
        int directional = inputs[i].up || inputs[i].down ||
                          inputs[i].left || inputs[i].right;
        int analog = inputs[i].lx != 128 || inputs[i].ly != 128 ||
                     inputs[i].rx != 128 || inputs[i].ry != 128;
        if (directional) direction_frames++;
        if (analog) analog_frames++;
        if (!steering[i].have_vx || !steering[i].have_vz) continue;
        paired++;
        if (steering[i].vx) nonzero_vx++;
        if (steering[i].vz) nonzero_vz++;
        if (steering[i].vx < min_vx) min_vx = steering[i].vx;
        if (steering[i].vx > max_vx) max_vx = steering[i].vx;
        if (steering[i].vz < min_vz) min_vz = steering[i].vz;
        if (steering[i].vz > max_vz) max_vz = steering[i].vz;
        if (have_previous &&
            (steering[i].vx != previous_vx || steering[i].vz != previous_vz))
            changed++;
        previous_vx = steering[i].vx;
        previous_vz = steering[i].vz;
        have_previous = 1;
    }

    int latch11_writes = 0;
    int64_t first_latch_write = -1, last_latch_write = -1, clear_frame = -1;
    for (int i = 0; i < latch_n; i++) {
        if (latch[i].address != 0x800a659eu || latch[i].width != 2) continue;
        if (latch[i].new_value == 11) {
            if (first_latch_write < 0) first_latch_write = latch[i].frame;
            last_latch_write = latch[i].frame;
            latch11_writes++;
        } else if (latch[i].new_value == 0) {
            clear_frame = latch[i].frame;
        }
    }

    printf("{\n");
    printf("  \"schema\":\"phase4_b03_runtime_trace_v1\",\n");
    printf("  \"trace_events\":%d,\n", trace_events);
    printf("  \"trace_reported_truncated\":false,\n");
    printf("  \"control_comparison\":{\"same_cycle\":%s,\"same_frame\":%s,\"same_pc\":%s,\"same_sp\":%s,\"same_player_block_168\":%s,\"bounded_cycle_neutral\":%s,\"cycle\":%" PRId64 ",\"frame\":%" PRId64 ",\"pc\":\"%s\",\"sp\":\"%s\"},\n",
           same_cycle?"true":"false", same_frame?"true":"false",
           same_pc?"true":"false", same_sp?"true":"false",
           same_player?"true":"false",
           (same_cycle&&same_frame&&same_pc&&same_sp&&same_player)?"true":"false",
           control.cycle, control.frame, control.pc, control.sp);
    printf("  \"glide\":{\"launch_vy_minus4096_exec_stores\":%d,\"latch11_exec_stores\":%d,\"latch11_access_writes\":%d,\"first_latch_write_movie_frame\":%" PRId64 ",\"last_latch_write_movie_frame\":%" PRId64 ",\"first_latch_active_movie_frame\":%" PRId64 ",\"last_latch_active_movie_frame\":%" PRId64 ",\"latch_active_player_updates\":%d,\"glide_vy_store_count\":%d,\"first_glide_vy_store_movie_frame\":%" PRId64 ",\"first_glide_vy\":%d,\"min_glide_vy\":%d,\"max_glide_vy\":%d,\"first_terminal_350_movie_frame\":%" PRId64 ",\"terminal_350_updates\":%d,\"state5_to6_exec_stores\":%d,\"grounded_release_movie_frame\":%" PRId64 ",\"grounded_release_value\":%u,\"latch_clear_movie_frame\":%" PRId64 "},\n",
           launch_stores, latch_exec_stores, latch11_writes,
           first_latch_write-INITIAL_FRAME, last_latch_write-INITIAL_FRAME,
           first_active-INITIAL_FRAME, last_active-INITIAL_FRAME, latch_updates,
           vy_stores, first_vy_frame-INITIAL_FRAME, first_vy, min_vy, max_vy,
           first_terminal-INITIAL_FRAME, terminal_updates, state5_to6,
           grounded_latch_release-INITIAL_FRAME, grounded_latch_value,
           clear_frame-INITIAL_FRAME);
    printf("  \"steering\":{\"directional_input_frames_in_latch_window\":%d,\"analog_input_frames_in_latch_window\":%d,\"paired_velocity_samples\":%d,\"nonzero_vx_samples\":%d,\"nonzero_vz_samples\":%d,\"changed_velocity_pairs\":%d,\"min_vx\":%d,\"max_vx\":%d,\"min_vz\":%d,\"max_vz\":%d},\n",
           direction_frames, analog_frames, paired, nonzero_vx, nonzero_vz,
           changed, min_vx, max_vx, min_vz, max_vz);
    printf("  \"grounded_width2_timeline\":[");
    int first = 1;
    for (int i = 0; i < ground_n; i++) {
        if (ground[i].address != 0x800a6582u || ground[i].width != 2) continue;
        printf("%s{\"movie_frame\":%" PRId64 ",\"emulator_frame\":%" PRId64 ",\"cycle\":%" PRId64 ",\"instruction_pc\":\"0x%08" PRIx32 "\",\"old_value\":%d,\"new_value\":%d}",
               first?"":",", ground[i].frame-INITIAL_FRAME, ground[i].frame,
               ground[i].cycle, ground[i].pc, ground[i].old_value,
               ground[i].new_value);
        first = 0;
    }
    printf("],\n");
    printf("  \"grounding_near_latch_clear\":[");
    first = 1;
    for (int i = 0; i < ground_n; i++) {
        if (ground[i].frame < clear_frame - 5 || ground[i].frame > clear_frame + 5)
            continue;
        if (ground[i].address != 0x800a6582u &&
            ground[i].address != 0x800a6583u)
            continue;
        printf("%s{\"movie_frame\":%" PRId64 ",\"emulator_frame\":%" PRId64 ",\"cycle\":%" PRId64 ",\"address\":\"0x%08" PRIx32 "\",\"width\":%d,\"instruction_pc\":\"0x%08" PRIx32 "\",\"old_value\":%d,\"new_value\":%d}",
               first?"":",", ground[i].frame-INITIAL_FRAME, ground[i].frame,
               ground[i].cycle, ground[i].address, ground[i].width,
               ground[i].pc, ground[i].old_value, ground[i].new_value);
        first = 0;
    }
    printf("],\n");
    printf("  \"latch_timeline\":{\"first_write_movie_frame\":%" PRId64 ",\"last_write_movie_frame\":%" PRId64 ",\"write_count\":%d,\"clear_movie_frame\":%" PRId64 ",\"write_pc\":\"0x8005c8bc\",\"clear_pc\":\"0x80048700\"},\n",
           first_latch_write-INITIAL_FRAME, last_latch_write-INITIAL_FRAME,
           latch11_writes, clear_frame-INITIAL_FRAME);
    printf("  \"end_player\":{\"x\":%d,\"y\":%d,\"z\":%d,\"vx\":%d,\"vy\":%d,\"vz\":%d,\"air_state\":%d,\"grounded\":%d,\"anim_index\":%d,\"plant_latch\":%d}\n",
           (int32_t)le32(instrumented.hex,0x00),
           (int32_t)le32(instrumented.hex,0x04),
           (int32_t)le32(instrumented.hex,0x08),
           (int32_t)le32(instrumented.hex,0x2c),
           (int32_t)le32(instrumented.hex,0x30),
           (int32_t)le32(instrumented.hex,0x34),
           (int16_t)le16(instrumented.hex,0x80),
           (int16_t)le16(instrumented.hex,0x82),
           (int16_t)le16(instrumented.hex,0x88),
           (int16_t)le16(instrumented.hex,0x9e));
    printf("}\n");
    return 0;
}
