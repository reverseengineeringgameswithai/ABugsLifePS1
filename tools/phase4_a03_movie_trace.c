/*
 * Phase 4 A03: join jump, vertical-position, and swept-plane traces from one
 * Interpreter movie.  The official Python client is transport only; all
 * event parsing, signed arithmetic, plane classification, and joins are C.
 */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint64_t frame, cycle;
    uint32_t pc, s0, s2, s4, nx, ny, nz, v0, v1, fp, value, new_value;
    unsigned has_s0:1, has_s2:1, has_s4:1, has_normal:1;
    unsigned has_v0:1, has_v1:1, has_value:1, has_new_value:1;
} Event;

typedef struct {
    Event *v;
    size_t n, cap;
} Events;

static void fail(const char *what, const char *path)
{
    fprintf(stderr, "%s %s: %s\n", what, path, strerror(errno));
    exit(2);
}

static char *slurp(const char *path, size_t *size)
{
    FILE *fp = fopen(path, "rb");
    long n;
    char *p;
    if (!fp)
        fail("open", path);
    if (fseek(fp, 0, SEEK_END) || (n = ftell(fp)) < 0)
        fail("size", path);
    rewind(fp);
    p = malloc((size_t)n + 1);
    if (!p)
        fail("allocate", path);
    if (fread(p, 1, (size_t)n, fp) != (size_t)n)
        fail("read", path);
    fclose(fp);
    p[n] = 0;
    *size = (size_t)n;
    return p;
}

static int value_in(const char *begin, const char *end, const char *key,
                    uint64_t *out)
{
    char needle[48];
    const char *p;
    char *tail;
    int quoted = 0;
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    p = strstr(begin, needle);
    if (!p || p >= end)
        return 0;
    p += strlen(needle);
    while (p < end && *p != ':')
        p++;
    if (p == end)
        return 0;
    p++;
    while (p < end && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r'))
        p++;
    if (p < end && *p == '"') {
        quoted = 1;
        p++;
    }
    errno = 0;
    *out = strtoull(p, &tail, 0);
    if (errno || tail == p || tail > end)
        return 0;
    if (quoted && (tail >= end || *tail != '"'))
        return 0;
    return 1;
}

static void push(Events *a, Event e)
{
    if (a->n == a->cap) {
        size_t next = a->cap ? a->cap * 2 : 256;
        Event *p = realloc(a->v, next * sizeof(*p));
        if (!p) {
            fputs("event allocation failed\n", stderr);
            exit(2);
        }
        a->v = p;
        a->cap = next;
    }
    a->v[a->n++] = e;
}

static const char *object_end(const char *p, const char *limit)
{
    int depth = 0, in_string = 0, escape = 0;
    for (; p < limit; p++) {
        char c = *p;
        if (in_string) {
            if (escape)
                escape = 0;
            else if (c == '\\')
                escape = 1;
            else if (c == '"')
                in_string = 0;
            continue;
        }
        if (c == '"')
            in_string = 1;
        else if (c == '{')
            depth++;
        else if (c == '}' && --depth == 0)
            return p + 1;
    }
    return NULL;
}

static Events parse_events(const char *path)
{
    size_t size;
    char *json = slurp(path, &size);
    const char *limit = json + size;
    const char *p = strstr(json, "\"events\"");
    Events out = {0};
    if (!p || !(p = strchr(p, '['))) {
        fprintf(stderr, "events array missing in %s\n", path);
        exit(2);
    }
    p++;
    while (p < limit) {
        const char *end;
        uint64_t x;
        Event e = {0};
        while (p < limit && *p != '{' && *p != ']')
            p++;
        if (p == limit || *p == ']')
            break;
        end = object_end(p, limit);
        if (!end) {
            fprintf(stderr, "unterminated event in %s\n", path);
            exit(2);
        }
        if (!value_in(p, end, "frame", &e.frame)) {
            p = end;
            continue;
        }
        value_in(p, end, "cycle", &e.cycle);
        if (value_in(p, end, "pc", &x)) e.pc = (uint32_t)x;
        if (value_in(p, end, "s0", &x)) e.s0 = (uint32_t)x, e.has_s0 = 1;
        if (value_in(p, end, "s2", &x)) e.s2 = (uint32_t)x, e.has_s2 = 1;
        if (value_in(p, end, "s4", &x)) e.s4 = (uint32_t)x, e.has_s4 = 1;
        if (value_in(p, end, "t1", &x)) e.nx = (uint32_t)x, e.has_normal = 1;
        if (value_in(p, end, "a3", &x)) e.ny = (uint32_t)x;
        if (value_in(p, end, "a1", &x)) e.nz = (uint32_t)x;
        if (value_in(p, end, "v0", &x)) e.v0 = (uint32_t)x, e.has_v0 = 1;
        if (value_in(p, end, "v1", &x)) e.v1 = (uint32_t)x, e.has_v1 = 1;
        if (value_in(p, end, "fp", &x)) e.fp = (uint32_t)x;
        if (value_in(p, end, "value", &x))
            e.value = (uint32_t)x, e.has_value = 1;
        if (value_in(p, end, "new_value", &x))
            e.new_value = (uint32_t)x, e.has_new_value = 1;
        push(&out, e);
        p = end;
    }
    free(json);
    return out;
}

static unsigned abs16(int16_t v)
{
    return v < 0 ? (unsigned)-(int)v : (unsigned)v;
}

static int ceiling_normal(const Event *e)
{
    int16_t nx = (int16_t)e->nx, ny = (int16_t)e->ny, nz = (int16_t)e->nz;
    return e->has_normal && ny > 0 && abs16(ny) >= abs16(nx) &&
           abs16(ny) >= abs16(nz);
}

static const Event *matching(const Events *a, uint64_t frame, uint32_t s0,
                             int need_s2_nonnegative, int need_v0_nonzero)
{
    size_t i;
    for (i = 0; i < a->n; i++) {
        const Event *e = &a->v[i];
        if (!e->has_s0 || e->frame != frame || e->s0 != s0)
            continue;
        if (need_s2_nonnegative && (!e->has_s2 || (int32_t)e->s2 < 0))
            continue;
        if (need_v0_nonzero && (!e->has_v0 || e->v0 == 0))
            continue;
        return e;
    }
    return NULL;
}

static const Event *endpoint_for_keep(const Events *endpoint, const Event *keep)
{
    const Event *best = NULL;
    size_t i;
    for (i = 0; i < endpoint->n; i++) {
        const Event *e = &endpoint->v[i];
        if (!e->has_s0 || e->frame != keep->frame || e->s0 != keep->s0 ||
            (int32_t)e->s4 >= 0 || e->cycle > keep->cycle)
            continue;
        if (!best || e->cycle > best->cycle)
            best = e;
    }
    return best;
}

static int32_t y_at_jump(const Events *ys, uint64_t frame, int *ok)
{
    size_t i;
    *ok = 0;
    for (i = 0; i < ys->n; i++) {
        const Event *e = &ys->v[i];
        if (e->frame == frame && e->has_value) {
            *ok = 1;
            return (int32_t)e->value;
        }
    }
    return 0;
}

typedef struct {
    int32_t base_y, apex_y;
    uint64_t apex_frame;
    int32_t height;
    int returned_near_base;
    int velocity_apex_seen;
} Arc;

static Arc arc(const Events *ys, const Events *vertical, uint64_t start,
               uint64_t end)
{
    Arc a = {0};
    size_t i;
    int ok;
    int saw_rising = 0;
    uint64_t apex_limit = end;
    a.base_y = y_at_jump(ys, start, &ok);
    if (!ok) {
        fputs("no Y write before jump\n", stderr);
        exit(2);
    }
    for (i = 0; i < vertical->n; i++) {
        const Event *e = &vertical->v[i];
        int32_t vy;
        if (e->frame < start || e->frame >= end || !e->has_s4)
            continue;
        vy = (int32_t)e->s4;
        if (vy < 0)
            saw_rising = 1;
        else if (saw_rising) {
            apex_limit = e->frame + 3;
            a.velocity_apex_seen = 1;
            break;
        }
    }
    a.apex_y = a.base_y;
    a.apex_frame = start;
    for (i = 0; i < ys->n; i++) {
        const Event *e = &ys->v[i];
        int32_t y;
        if (e->frame < start || e->frame >= apex_limit || !e->has_new_value)
            continue;
        y = (int32_t)e->new_value;
        if (y < a.apex_y) {
            a.apex_y = y;
            a.apex_frame = e->frame;
        }
    }
    a.height = a.base_y - a.apex_y;
    for (i = 0; i < ys->n; i++) {
        const Event *e = &ys->v[i];
        int32_t y;
        if (e->frame <= a.apex_frame || e->frame >= end || !e->has_new_value)
            continue;
        y = (int32_t)e->new_value;
        if (y >= a.base_y - 1024 && y <= a.base_y + 1024)
            a.returned_near_base = 1;
    }
    return a;
}

int main(int argc, char **argv)
{
    Events jump, vertical, endpoint, start, poly, keep, ys;
    uint64_t j0, j1, second_end;
    Arc control, ceiling;
    const Event *candidate = NULL, *start_hit = NULL, *poly_hit = NULL, *keep_hit = NULL;
    size_t i;
    unsigned ceiling_endpoint_events = 0, positive_ny_wall_events = 0;
    int closure;

    if (argc != 8) {
        fprintf(stderr, "usage: %s JUMP VERTICAL ENDPOINT START POLY KEEP Y_WRITES\n", argv[0]);
        return 2;
    }
    jump = parse_events(argv[1]);
    vertical = parse_events(argv[2]);
    endpoint = parse_events(argv[3]);
    start = parse_events(argv[4]);
    poly = parse_events(argv[5]);
    keep = parse_events(argv[6]);
    ys = parse_events(argv[7]);
    if (jump.n != 2) {
        fprintf(stderr, "expected exactly two jump admissions, got %zu\n", jump.n);
        return 2;
    }
    j0 = jump.v[0].frame;
    j1 = jump.v[1].frame;
    second_end = j1 + 220;
    control = arc(&ys, &vertical, j0, j1);
    ceiling = arc(&ys, &vertical, j1, second_end);

    for (i = 0; i < endpoint.n; i++) {
        Event *e = &endpoint.v[i];
        int16_t nx = (int16_t)e->nx, ny = (int16_t)e->ny, nz = (int16_t)e->nz;
        if (e->frame < j1 || e->frame >= second_end || !e->has_normal)
            continue;
        if (ceiling_normal(e)) {
            ceiling_endpoint_events++;
            if ((int32_t)e->s4 < 0) {
                const Event *s = matching(&start, e->frame, e->s0, 1, 0);
                const Event *p = matching(&poly, e->frame, e->s0, 0, 1);
                const Event *k = matching(&keep, e->frame, e->s0, 0, 0);
                if (s && p && k && !candidate) {
                    candidate = e;
                    start_hit = s;
                    poly_hit = p;
                    keep_hit = k;
                }
            }
        } else if (ny > 0 && (abs16(ny) < abs16(nx) || abs16(ny) < abs16(nz))) {
            positive_ny_wall_events++;
        }
    }
    /* Curved/slanted ceilings can be wall-dominant.  A retained plane still
       qualifies as an upward obstacle when ny>0 and the second jump is rising. */
    if (!candidate) {
        for (i = 0; i < keep.n; i++) {
            const Event *k = &keep.v[i];
            const Event *e, *s, *p;
            if (!k->has_s0 || k->frame < j1 || k->frame > ceiling.apex_frame)
                continue;
            e = matching(&endpoint, k->frame, k->s0, 0, 0);
            if (!e || !e->has_normal || (int16_t)e->ny <= 0 || (int32_t)e->s4 >= 0)
                continue;
            s = matching(&start, k->frame, k->s0, 1, 0);
            p = matching(&poly, k->frame, k->s0, 0, 1);
            if (s && p) {
                candidate = e;
                start_hit = s;
                poly_hit = p;
                keep_hit = k;
                break;
            }
        }
    }
    closure = control.height - 3200 == 16896 && ceiling.height < control.height &&
              candidate && start_hit && poly_hit && keep_hit &&
              ceiling.returned_near_base && control.velocity_apex_seen &&
              ceiling.velocity_apex_seen;

    printf("{\n");
    printf("  \"schema\": \"phase4_a03_movie_trace_v1\",\n");
    printf("  \"jump_admissions\": 2,\n");
    printf("  \"control\": {\"start_frame\": %" PRIu64 ", \"base_y\": %d, "
           "\"apex_y\": %d, \"apex_frame\": %" PRIu64 ", \"height\": %d, "
           "\"entry_displacement\": 3200, \"recurrence_height\": %d, "
           "\"returned_near_base\": %s, \"velocity_apex_seen\": %s},\n",
           j0, control.base_y, control.apex_y, control.apex_frame, control.height,
           control.height - 3200,
           control.returned_near_base ? "true" : "false",
           control.velocity_apex_seen ? "true" : "false");
    printf("  \"ceiling_jump\": {\"start_frame\": %" PRIu64 ", \"base_y\": %d, "
           "\"apex_y\": %d, \"apex_frame\": %" PRIu64 ", \"height\": %d, "
           "\"truncated_vs_control\": %s, \"returned_near_base\": %s, "
           "\"velocity_apex_seen\": %s},\n",
           j1, ceiling.base_y, ceiling.apex_y, ceiling.apex_frame, ceiling.height,
           ceiling.height < control.height ? "true" : "false",
           ceiling.returned_near_base ? "true" : "false",
           ceiling.velocity_apex_seen ? "true" : "false");
    printf("  \"classification\": {\"ceiling_endpoint_events\": %u, "
           "\"positive_ny_wall_events_excluded\": %u},\n",
           ceiling_endpoint_events, positive_ny_wall_events);
    printf("  \"retained_winners\": [");
    {
        int first = 1;
        for (i = 0; i < keep.n; i++) {
            const Event *k = &keep.v[i];
            const Event *e = endpoint_for_keep(&endpoint, k);
            if (!e || !e->has_normal)
                continue;
            printf("%s{\"frame\":%" PRIu64 ",\"plane\":\"0x%08" PRIx32
                   "\",\"normal\":[%d,%d,%d],\"d_end\":%d,"
                   "\"during_control\":%s,\"during_ceiling_ascent\":%s}",
                   first ? "" : ",", k->frame, k->s0,
                   (int16_t)e->nx, (int16_t)e->ny, (int16_t)e->nz,
                   (int32_t)e->s4,
                   (k->frame >= j0 && k->frame <= control.apex_frame) ? "true" : "false",
                   (k->frame >= j1 && k->frame <= ceiling.apex_frame + 4) ? "true" : "false");
            first = 0;
        }
    }
    puts("],");
    if (candidate) {
        printf("  \"retained_ceiling\": {\"frame\": %" PRIu64 ", "
               "\"cycle\": %" PRIu64 ", \"plane\": \"0x%08" PRIx32 "\", "
               "\"sector\": %d, \"normal\": [%d,%d,%d], \"d_end\": %d, "
               "\"d_start\": %d, \"dominant_positive_ny\": %s, "
               "\"polygon_true\": true, \"retained_winner\": true},\n",
               candidate->frame, candidate->cycle, candidate->s0,
               (int16_t)candidate->fp, (int16_t)candidate->nx,
               (int16_t)candidate->ny, (int16_t)candidate->nz,
               (int32_t)candidate->s4, (int32_t)start_hit->s2,
               ceiling_normal(candidate) ? "true" : "false");
    } else {
        puts("  \"retained_ceiling\": null,");
    }
    printf("  \"closure_gate\": \"%s\"\n", closure ? "PASS" : "FAIL");
    puts("}");

    free(jump.v); free(vertical.v); free(endpoint.v); free(start.v);
    free(poly.v); free(keep.v); free(ys.v);
    return closure ? 0 : 1;
}
