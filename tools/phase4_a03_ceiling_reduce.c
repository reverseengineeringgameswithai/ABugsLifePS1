/*
 * Phase 4 A03: reduce DuckStation execTrace events from the player swept-plane
 * resolver at 0x80035464.  Python is used only by the official debugger client
 * as transport; this program performs all event classification and resolver
 * arithmetic.
 *
 * At 0x80035464 the shipping 0x80035280 resolver has:
 *   s4 = signed distance at the movement endpoint
 *   s2 = signed distance at the movement start (tested later at 0x800354b4)
 *   t1/a3/a1 = plane nx/ny/nz
 * The ASM accepts a crossing only when s4 < 0 and s2 >= 0.  Positive Y points
 * downward in the player coordinate frame, so dominant -Y planes catch falls
 * and dominant +Y planes can catch upward movement as ceilings.
 */

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint32_t ptr;
    int16_t nx, ny, nz;
    int16_t sector;
    unsigned events;
    unsigned endpoint_negative;
} PlaneSeen;

typedef struct {
    const char *path;
    unsigned events;
    unsigned floor_events;
    unsigned ceiling_events;
    unsigned wall_events;
    unsigned positive_ny_wall_events;
    PlaneSeen planes[4096];
    size_t plane_count;
} FileResult;

static void die(const char *what, const char *path)
{
    fprintf(stderr, "%s: %s: %s\n", what, path, strerror(errno));
    exit(2);
}

static char *slurp(const char *path, size_t *size_out)
{
    FILE *fp = fopen(path, "rb");
    long size;
    char *buf;

    if (!fp)
        die("open", path);
    if (fseek(fp, 0, SEEK_END) != 0 || (size = ftell(fp)) < 0)
        die("size", path);
    rewind(fp);
    buf = malloc((size_t)size + 1);
    if (!buf)
        die("allocate", path);
    if (fread(buf, 1, (size_t)size, fp) != (size_t)size)
        die("read", path);
    fclose(fp);
    buf[size] = '\0';
    *size_out = (size_t)size;
    return buf;
}

static int find_hex_reg(const char *begin, const char *end, const char *name,
                        uint32_t *value)
{
    char needle[32];
    const char *p;
    char *after;
    unsigned long parsed;

    snprintf(needle, sizeof(needle), "\"%s\"", name);
    p = strstr(begin, needle);
    if (!p || p >= end)
        return 0;
    p = strchr(p + strlen(needle), '"');
    if (!p || p >= end)
        return 0;
    errno = 0;
    parsed = strtoul(p + 1, &after, 0);
    if (errno || after == p + 1 || after > end || parsed > UINT32_MAX)
        return 0;
    *value = (uint32_t)parsed;
    return 1;
}

static unsigned abs16(int16_t v)
{
    return v < 0 ? (unsigned)(-(int)v) : (unsigned)v;
}

enum Orientation { ORIENT_FLOOR, ORIENT_CEILING, ORIENT_WALL };

static enum Orientation orientation(int16_t nx, int16_t ny, int16_t nz)
{
    unsigned ax = abs16(nx), ay = abs16(ny), az = abs16(nz);
    if (ay >= ax && ay >= az) {
        if (ny < 0)
            return ORIENT_FLOOR;
        if (ny > 0)
            return ORIENT_CEILING;
    }
    return ORIENT_WALL;
}

static PlaneSeen *remember_plane(FileResult *out, uint32_t ptr, int16_t nx,
                                 int16_t ny, int16_t nz, int16_t sector)
{
    size_t i;
    for (i = 0; i < out->plane_count; i++) {
        PlaneSeen *p = &out->planes[i];
        if (p->ptr == ptr && p->nx == nx && p->ny == ny && p->nz == nz &&
            p->sector == sector)
            return p;
    }
    if (out->plane_count == sizeof(out->planes) / sizeof(out->planes[0])) {
        fprintf(stderr, "too many unique planes in %s\n", out->path);
        exit(2);
    }
    PlaneSeen *p = &out->planes[out->plane_count++];
    *p = (PlaneSeen){ptr, nx, ny, nz, sector, 0, 0};
    return p;
}

static void reduce_file(FileResult *out)
{
    size_t size;
    char *json = slurp(out->path, &size);
    const char *cursor = json;
    const char *limit = json + size;

    (void)limit;
    while ((cursor = strstr(cursor, "\"regs\"")) != NULL) {
        const char *begin = strchr(cursor, '{');
        const char *end = begin ? strchr(begin, '}') : NULL;
        uint32_t s0, s4, nx32, ny32, nz32, sector32;
        int16_t nx, ny, nz, sector;
        enum Orientation kind;
        PlaneSeen *plane;

        if (!begin || !end)
            break;
        if (!find_hex_reg(begin, end, "s0", &s0) ||
            !find_hex_reg(begin, end, "s4", &s4) ||
            !find_hex_reg(begin, end, "t1", &nx32) ||
            !find_hex_reg(begin, end, "a3", &ny32) ||
            !find_hex_reg(begin, end, "a1", &nz32) ||
            !find_hex_reg(begin, end, "fp", &sector32)) {
            fprintf(stderr, "missing resolver register in %s\n", out->path);
            exit(2);
        }
        nx = (int16_t)nx32;
        ny = (int16_t)ny32;
        nz = (int16_t)nz32;
        sector = (int16_t)sector32;
        kind = orientation(nx, ny, nz);
        plane = remember_plane(out, s0, nx, ny, nz, sector);
        plane->events++;
        if ((int32_t)s4 < 0)
            plane->endpoint_negative++;

        out->events++;
        if (kind == ORIENT_FLOOR)
            out->floor_events++;
        else if (kind == ORIENT_CEILING)
            out->ceiling_events++;
        else {
            out->wall_events++;
            if (ny > 0)
                out->positive_ny_wall_events++;
        }
        cursor = end + 1;
    }
    free(json);
}

static int32_t dot_y(int16_t ny, int32_t y, int32_t plane_y)
{
    return ((int32_t)ny * (y - plane_y)) >> 14;
}

static int asm_accepts(int32_t d_end, int32_t d_start)
{
    /* 0x80035464 bgez s4 skips; 0x800354b4 bltz s2 skips. */
    return d_end < 0 && d_start >= 0;
}

int main(int argc, char **argv)
{
    FileResult *files;
    unsigned total_events = 0, total_floor = 0, total_ceiling = 0;
    unsigned total_wall = 0, total_positive_ny_wall = 0;
    size_t total_planes = 0, floor_planes = 0, ceiling_planes = 0;
    size_t wall_planes = 0, positive_ny_wall_planes = 0;
    int i;
    int32_t floor_start = dot_y(-0x4000, 90, 100);
    int32_t floor_end = dot_y(-0x4000, 110, 100);
    int32_t ceiling_start = dot_y(0x4000, 110, 100);
    int32_t ceiling_end = dot_y(0x4000, 90, 100);

    if (argc < 2) {
        fprintf(stderr, "usage: %s TRACE.json...\n", argv[0]);
        return 2;
    }
    files = calloc((size_t)argc - 1, sizeof(*files));
    if (!files)
        return 2;

    for (i = 1; i < argc; i++) {
        size_t j;
        files[i - 1].path = argv[i];
        reduce_file(&files[i - 1]);
        total_events += files[i - 1].events;
        total_floor += files[i - 1].floor_events;
        total_ceiling += files[i - 1].ceiling_events;
        total_wall += files[i - 1].wall_events;
        total_positive_ny_wall += files[i - 1].positive_ny_wall_events;
        total_planes += files[i - 1].plane_count;
        for (j = 0; j < files[i - 1].plane_count; j++) {
            PlaneSeen *p = &files[i - 1].planes[j];
            enum Orientation kind = orientation(p->nx, p->ny, p->nz);
            if (kind == ORIENT_FLOOR)
                floor_planes++;
            else if (kind == ORIENT_CEILING)
                ceiling_planes++;
            else {
                wall_planes++;
                if (p->ny > 0)
                    positive_ny_wall_planes++;
            }
        }
    }

    printf("{\n");
    printf("  \"schema\": \"phase4_a03_ceiling_reduce_v1\",\n");
    printf("  \"resolver\": {\"endpoint_branch_pc\": \"0x80035464\", "
           "\"start_branch_pc\": \"0x800354b4\", "
           "\"law\": \"d_end < 0 && d_start >= 0\", "
           "\"floor_fall_accepts\": %s, \"ceiling_rise_accepts\": %s},\n",
           asm_accepts(floor_end, floor_start) ? "true" : "false",
           asm_accepts(ceiling_end, ceiling_start) ? "true" : "false");
    printf("  \"totals\": {\"files\": %d, \"events\": %u, "
           "\"unique_planes_per_fixture\": %zu, \"floor_events\": %u, "
           "\"ceiling_events\": %u, \"wall_events\": %u, "
           "\"positive_ny_wall_events\": %u, \"floor_planes\": %zu, "
           "\"ceiling_planes\": %zu, \"wall_planes\": %zu, "
           "\"positive_ny_wall_planes\": %zu},\n",
           argc - 1, total_events, total_planes, total_floor, total_ceiling,
           total_wall, total_positive_ny_wall, floor_planes, ceiling_planes,
           wall_planes, positive_ny_wall_planes);
    printf("  \"fixtures\": [\n");
    for (i = 1; i < argc; i++) {
        FileResult *f = &files[i - 1];
        printf("    {\"trace\": \"%s\", \"events\": %u, "
               "\"unique_planes\": %zu, \"floor_events\": %u, "
               "\"ceiling_events\": %u, \"wall_events\": %u, "
               "\"positive_ny_wall_events\": %u}%s\n",
               f->path, f->events, f->plane_count, f->floor_events,
               f->ceiling_events, f->wall_events,
               f->positive_ny_wall_events, i + 1 == argc ? "" : ",");
    }
    printf("  ],\n");
    printf("  \"ceiling_candidates\": [");
    {
        int first = 1;
        for (i = 1; i < argc; i++) {
            FileResult *f = &files[i - 1];
            size_t j;
            for (j = 0; j < f->plane_count; j++) {
                PlaneSeen *p = &f->planes[j];
                if (orientation(p->nx, p->ny, p->nz) != ORIENT_CEILING)
                    continue;
                printf("%s{\"trace\":\"%s\",\"ptr\":\"0x%08" PRIx32
                       "\",\"sector\":%d,\"normal\":[%d,%d,%d],"
                       "\"events\":%u,\"endpoint_negative\":%u}",
                       first ? "" : ",", f->path, p->ptr, p->sector,
                       p->nx, p->ny, p->nz, p->events,
                       p->endpoint_negative);
                first = 0;
            }
        }
    }
    printf("]\n}\n");
    free(files);
    return 0;
}
